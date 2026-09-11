from __future__ import annotations

"""Append-only, research-only archive of official NFL injury-report snapshots.

The production context path already parses NFL.com's official weekly injury page. This
module reuses that parser but persists point-in-time observations away from production.
Each capture appends an observation to JSONL. Both the raw HTTP body and normalized report
content are stored once by SHA-256, so repeated unchanged polls are cheap while future
audits can both reconstruct the parsed state and reparse the original source bytes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import requests

from nfl_forecast.injuries import NFL_INJURY_URL, parse_nfl_injury_html

ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_ID = "NFL-INJURY-SNAPSHOT-2026-V1"
SEASON = 2026
MANIFEST_NAME = "observations.jsonl"
OBJECT_DIR = "objects"
RAW_DIR = "raw"


def _iso_utc(value: datetime | str | None = None) -> str:
    if value is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_gzip_deterministic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zf:
            zf.write(data)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"injury archive manifest has invalid JSON on line {line_no}") from exc
        if row.get("archive_id") != ARCHIVE_ID:
            raise ValueError("injury archive manifest contains a foreign archive_id")
        rows.append(row)
    return rows


def _append_manifest(path: Path, row: dict[str, Any]) -> None:
    existing = _load_manifest(path)
    identity = (int(row["season"]), int(row["week"]), str(row["captured_at_utc"]))
    if any(
        (int(x.get("season", -1)), int(x.get("week", -1)), str(x.get("captured_at_utc"))) == identity
        for x in existing
    ):
        raise ValueError(f"duplicate injury archive observation identity: {identity}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _normalize_reports(reports: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for team in sorted(reports):
        rows: list[dict[str, Any]] = []
        for item in reports[team]:
            rows.append(
                {
                    "name": str(item.get("name") or "").strip(),
                    "position": str(item.get("position") or "").strip().upper(),
                    "injuries": str(item.get("description") or "").strip(),
                    "practice_status": str(item.get("practice_status") or "").strip(),
                    "game_status": str(item.get("game_status") or "").strip(),
                }
            )
        rows.sort(key=lambda x: (x["name"].casefold(), x["position"], x["practice_status"], x["game_status"], x["injuries"]))
        normalized[str(team)] = rows
    return normalized


@dataclass(frozen=True)
class CaptureResult:
    observation: dict[str, Any]
    object_path: Path | None
    object_created: bool
    raw_object_path: Path | None = None
    raw_object_created: bool = False


def capture_week(
    *,
    season: int,
    week: int,
    output_dir: str | Path,
    captured_at: datetime | str | None = None,
    session=requests,
    timeout_seconds: int = 25,
) -> CaptureResult:
    if int(season) != SEASON:
        raise ValueError(f"{ARCHIVE_ID} is frozen to season {SEASON}; got {season}")
    if not 1 <= int(week) <= 18:
        raise ValueError("regular-season injury archive week must be 1..18")

    root = Path(output_dir)
    manifest = root / MANIFEST_NAME
    captured = _iso_utc(captured_at)
    source_url = NFL_INJURY_URL.format(season=int(season), week=int(week))

    base = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "archive_id": ARCHIVE_ID,
        "season": int(season),
        "week": int(week),
        "captured_at_utc": captured,
        "source_name": "NFL.com official injury report",
        "source_url": source_url,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }

    raw_sha: str | None = None
    raw_object_path: Path | None = None
    raw_created = False
    http_status: int | None = None
    try:
        response = session.get(
            source_url,
            timeout=timeout_seconds,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; nfl-forecast-model/1.0; +https://github.com/levine26/nfl-forecast-model)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        http_status = int(getattr(response, "status_code", 200))
        response.raise_for_status()
        raw = response.content if isinstance(response.content, bytes) else bytes(response.content)
        raw_sha = _sha256(raw)
        raw_object_path = root / RAW_DIR / f"{raw_sha}.html.gz"
        raw_created = not raw_object_path.exists()
        _write_gzip_deterministic(raw_object_path, raw)

        html = response.text
        reports = parse_nfl_injury_html(html, source_url)
        table_count = html.lower().count("<table")
        if table_count and not reports:
            raise ValueError("NFL injury tables were present but no team rows parsed")

        normalized = _normalize_reports(reports)
        payload = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "archive_id": ARCHIVE_ID,
            "season": int(season),
            "week": int(week),
            "source_name": "NFL.com official injury report",
            "source_url": source_url,
            "reports": normalized,
        }
        canonical = _canonical_bytes(payload)
        canonical_sha = _sha256(canonical)
        object_path = root / OBJECT_DIR / f"{canonical_sha}.json.gz"
        created = not object_path.exists()
        _write_gzip_deterministic(object_path, canonical)
        players = sum(len(v) for v in normalized.values())
        observation = {
            **base,
            "status": "captured",
            "http_status": http_status,
            "raw_body_sha256": raw_sha,
            "raw_object_relpath": str(raw_object_path.relative_to(root)),
            "raw_object_created": raw_created,
            "canonical_snapshot_sha256": canonical_sha,
            "object_relpath": str(object_path.relative_to(root)),
            "object_created": created,
            "teams_with_reported_players": len(normalized),
            "players": players,
            "parser_table_count": int(table_count),
        }
        _append_manifest(manifest, observation)
        return CaptureResult(
            observation=observation,
            object_path=object_path,
            object_created=created,
            raw_object_path=raw_object_path,
            raw_object_created=raw_created,
        )
    except Exception as exc:
        observation = {
            **base,
            "status": "failed",
            "http_status": http_status,
            "error": str(exc)[:500],
            "raw_body_sha256": raw_sha,
            "raw_object_relpath": str(raw_object_path.relative_to(root)) if raw_object_path else None,
            "raw_object_created": raw_created,
            "canonical_snapshot_sha256": None,
            "object_relpath": None,
            "object_created": False,
        }
        _append_manifest(manifest, observation)
        return CaptureResult(
            observation=observation,
            object_path=None,
            object_created=False,
            raw_object_path=raw_object_path,
            raw_object_created=raw_created,
        )


def _verify_gzip_object(
    *,
    root: Path,
    row_number: int,
    relpath: Any,
    expected_sha: Any,
    label: str,
    failures: list[str],
) -> str | None:
    sha = str(expected_sha or "")
    if len(sha) != 64 or not relpath:
        failures.append(f"row {row_number} lacks {label} object identity")
        return None
    path = root / str(relpath)
    if not path.exists():
        failures.append(f"row {row_number} {label} object missing: {relpath}")
        return None
    try:
        with gzip.open(path, "rb") as handle:
            payload = handle.read()
    except Exception as exc:
        failures.append(f"row {row_number} {label} object unreadable: {exc}")
        return None
    if _sha256(payload) != sha:
        failures.append(f"row {row_number} {label} SHA mismatch")
        return None
    return sha


def verify_archive(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    rows = _load_manifest(root / MANIFEST_NAME)
    failures: list[str] = []
    captured = 0
    unique_objects: set[str] = set()
    unique_raw_objects: set[str] = set()
    seen_identity: set[tuple[int, int, str]] = set()
    for i, row in enumerate(rows, start=1):
        identity = (int(row["season"]), int(row["week"]), str(row["captured_at_utc"]))
        if identity in seen_identity:
            failures.append(f"duplicate observation identity at row {i}: {identity}")
        seen_identity.add(identity)

        raw_relpath = row.get("raw_object_relpath")
        raw_sha = row.get("raw_body_sha256")
        if raw_relpath is not None or raw_sha is not None:
            verified_raw = _verify_gzip_object(
                root=root,
                row_number=i,
                relpath=raw_relpath,
                expected_sha=raw_sha,
                label="raw",
                failures=failures,
            )
            if verified_raw:
                unique_raw_objects.add(verified_raw)

        if row.get("status") != "captured":
            continue
        captured += 1
        if raw_relpath is None or raw_sha is None:
            failures.append(f"captured row {i} lacks preserved raw source")
        verified = _verify_gzip_object(
            root=root,
            row_number=i,
            relpath=row.get("object_relpath"),
            expected_sha=row.get("canonical_snapshot_sha256"),
            label="canonical",
            failures=failures,
        )
        if verified:
            unique_objects.add(verified)
    return {
        "archive_id": ARCHIVE_ID,
        "observations": len(rows),
        "captured_observations": captured,
        "failed_observations": len(rows) - captured,
        "unique_snapshot_objects": len(unique_objects),
        "unique_raw_objects": len(unique_raw_objects),
        "integrity_ok": not failures,
        "failures": failures,
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
    }

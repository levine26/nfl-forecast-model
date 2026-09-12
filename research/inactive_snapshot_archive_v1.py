from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import requests

ARCHIVE_ID = "NFL-INACTIVE-SNAPSHOT-2026-V1"
SCHEMA_VERSION = 1
SOURCE_URL = "https://www.nfl.com/inactives/"
MANIFEST_NAME = "observations.jsonl"
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_gzip_deterministic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(data)


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
            raise ValueError(f"inactive archive manifest has invalid JSON on line {line_no}") from exc
        if row.get("archive_id") != ARCHIVE_ID:
            raise ValueError("inactive archive contains foreign archive_id")
        rows.append(row)
    return rows


def _append_manifest(path: Path, row: dict[str, Any]) -> None:
    existing = _load_manifest(path)
    identity = str(row["captured_at_utc"])
    if any(str(item.get("captured_at_utc")) == identity for item in existing):
        raise ValueError(f"duplicate inactive archive observation identity: {identity}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _page_signals(text: str) -> dict[str, Any]:
    normalized = " ".join(str(text or "").split()).casefold()
    return {
        "contains_inactive_reports_label": "inactive reports" in normalized,
        "contains_check_back_signal": "please check back soon" in normalized,
        "contains_inactives_word": "inactives" in normalized or "inactive" in normalized,
        "raw_text_length": len(str(text or "")),
    }


@dataclass(frozen=True)
class CaptureResult:
    observation: dict[str, Any]
    raw_object_path: Path | None
    raw_object_created: bool


def capture_inactives(
    *,
    output_dir: str | Path,
    due_games: list[dict[str, Any]],
    captured_at: datetime | str | None = None,
    session=requests,
    timeout_seconds: int = 25,
) -> CaptureResult:
    root = Path(output_dir)
    manifest = root / MANIFEST_NAME
    captured = _iso_utc(captured_at)
    base = {
        "schema_version": SCHEMA_VERSION,
        "archive_id": ARCHIVE_ID,
        "captured_at_utc": captured,
        "source_name": "NFL.com official inactives page",
        "source_url": SOURCE_URL,
        "due_games": due_games,
        "research_only": True,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "completed_2026_outcomes_used": 0,
    }

    raw_sha: str | None = None
    raw_path: Path | None = None
    raw_created = False
    http_status: int | None = None
    signals: dict[str, Any] = {}
    try:
        response = session.get(
            SOURCE_URL,
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
        raw_path = root / RAW_DIR / f"{raw_sha}.html.gz"
        raw_created = not raw_path.exists()
        _write_gzip_deterministic(raw_path, raw)
        signals = _page_signals(response.text)
        observation = {
            **base,
            "status": "captured_raw",
            "http_status": http_status,
            "raw_body_sha256": raw_sha,
            "raw_object_relpath": str(raw_path.relative_to(root)),
            "raw_object_created": raw_created,
            "player_level_parser_qualified": False,
            **signals,
        }
        _append_manifest(manifest, observation)
        return CaptureResult(observation, raw_path, raw_created)
    except Exception as exc:
        observation = {
            **base,
            "status": "failed",
            "http_status": http_status,
            "error": str(exc)[:500],
            "raw_body_sha256": raw_sha,
            "raw_object_relpath": str(raw_path.relative_to(root)) if raw_path else None,
            "raw_object_created": raw_created,
            "player_level_parser_qualified": False,
            **signals,
        }
        _append_manifest(manifest, observation)
        return CaptureResult(observation, raw_path, raw_created)


def verify_archive(output_dir: str | Path) -> dict[str, Any]:
    root = Path(output_dir)
    rows = _load_manifest(root / MANIFEST_NAME)
    failures: list[str] = []
    seen: set[str] = set()
    unique_raw: set[str] = set()
    for index, row in enumerate(rows, start=1):
        captured = str(row.get("captured_at_utc") or "")
        if captured in seen:
            failures.append(f"duplicate captured_at_utc at row {index}: {captured}")
        seen.add(captured)
        if row.get("production_authorized") is not False:
            failures.append(f"row {index} violates production firewall")
        if row.get("probability_feature_authorized") is not False:
            failures.append(f"row {index} violates probability-feature firewall")
        relpath = row.get("raw_object_relpath")
        sha = str(row.get("raw_body_sha256") or "")
        if not relpath and not sha:
            continue
        if not relpath or len(sha) != 64:
            failures.append(f"row {index} has incomplete raw object identity")
            continue
        path = root / str(relpath)
        if not path.exists():
            failures.append(f"row {index} raw object missing: {relpath}")
            continue
        try:
            with gzip.open(path, "rb") as handle:
                raw = handle.read()
        except Exception as exc:
            failures.append(f"row {index} raw object unreadable: {exc}")
            continue
        if _sha256(raw) != sha:
            failures.append(f"row {index} raw SHA mismatch")
        else:
            unique_raw.add(sha)
    return {
        "archive_id": ARCHIVE_ID,
        "observations": len(rows),
        "unique_raw_objects": len(unique_raw),
        "integrity_ok": not failures,
        "failures": failures,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "completed_2026_outcomes_used": 0,
    }

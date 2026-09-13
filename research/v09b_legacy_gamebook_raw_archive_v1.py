from __future__ import annotations

"""Archive and audit official 2012-2016 NFLGSIS Game Book bytes.

Research-only source qualification. This module deliberately stops before player identity,
active-label construction, roster-universe construction, or model fitting.
"""

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

from research.v09b_legacy_gamebook_locator_audit_v1 import (
    EXPECTED_GAMES,
    _canonical_games,
    _canonical_team,
    legacy_gamebook_url,
    load_discovery_crosswalk,
)

ARCHIVE_ID = "V09B-LEGACY-GAMEBOOK-BYTES-2012-2016-V1"
PARSER_VERSION = "V09B-GAMEBOOK-TEXT-STRUCTURE-V1"
NOT_ACTIVE_RE = re.compile(r"(?im)\bNot\s+Active\s*:")
DID_NOT_PLAY_RE = re.compile(r"(?im)\bDid\s+Not\s+Play\s*:")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_gzip_deterministic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with gzip.open(path, "rb") as handle:
            existing = handle.read()
        if existing != data:
            raise ValueError(f"content-addressed raw object mismatch: {path}")
        return
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(data)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
        handle.write(pdf_bytes)
        handle.flush()
        result = subprocess.run(
            ["pdftotext", "-layout", handle.name, "-"],
            check=False,
            capture_output=True,
        )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"pdftotext failed ({result.returncode}): {stderr[:500]}")
    text = result.stdout.decode("utf-8", errors="replace")
    if not text.strip():
        raise RuntimeError("pdftotext produced empty text")
    return text


def source_structure_signals(text: str) -> dict[str, Any]:
    not_active = list(NOT_ACTIVE_RE.finditer(text))
    did_not_play = list(DID_NOT_PLAY_RE.finditer(text))
    not_active_valid = len(not_active) >= 1
    did_not_play_valid = len(did_not_play) >= 1
    return {
        "not_active_heading_occurrences": len(not_active),
        "did_not_play_heading_occurrences": len(did_not_play),
        "not_active_structure_valid": not_active_valid,
        "did_not_play_structure_valid": did_not_play_valid,
        "semantic_headings_distinct": bool(not_active_valid and did_not_play_valid),
        "text_sha256": _sha256(text.encode("utf-8")),
        "text_length": len(text),
    }


def _manifest_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid archive manifest JSON at {path}:{line_no}") from exc
        if row.get("archive_id") != ARCHIVE_ID:
            raise ValueError(f"foreign archive_id at {path}:{line_no}")
        rows.append(row)
    return rows


def _stable_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    stable = dict(row)
    stable.pop("retrieved_at_utc", None)
    return stable


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    """Create a season manifest once; later runs may only reproduce it exactly.

    Retrieval timestamps are observational metadata and may differ on a revalidation run.
    Every source identity, SHA, parser result, and semantic structure field is immutable.
    """
    identities = [str(row["game_id"]) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate canonical game identity in archive manifest")
    ordered = sorted(rows, key=lambda item: (int(item["week"]), str(item["game_id"])))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _manifest_rows(path)
        existing_by_game = {str(row["game_id"]): row for row in existing}
        proposed_by_game = {str(row["game_id"]): row for row in ordered}
        if set(existing_by_game) != set(proposed_by_game):
            raise ValueError("historical archive manifest game universe changed after first capture")
        changed = [
            game_id
            for game_id in sorted(existing_by_game)
            if _stable_manifest_row(existing_by_game[game_id])
            != _stable_manifest_row(proposed_by_game[game_id])
        ]
        if changed:
            raise ValueError(
                "historical archive manifest is immutable; changed source/parser rows: "
                + ", ".join(changed[:10])
            )
        return
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in ordered
    )
    path.write_text(payload, encoding="utf-8")


def verify_archive(root: Path, season: int) -> dict[str, Any]:
    manifest = root / "manifests" / f"{season}.jsonl"
    rows = _manifest_rows(manifest)
    failures: list[str] = []
    game_ids: set[str] = set()
    shas: dict[str, str] = {}
    for index, row in enumerate(rows, start=1):
        game_id = str(row.get("game_id") or "")
        if game_id in game_ids:
            failures.append(f"duplicate game_id at row {index}: {game_id}")
        game_ids.add(game_id)
        sha = str(row.get("raw_pdf_sha256") or "")
        relpath = str(row.get("raw_object_relpath") or "")
        if len(sha) != 64 or not relpath:
            failures.append(f"row {index} incomplete raw object identity")
            continue
        if sha in shas and shas[sha] != game_id:
            failures.append(f"duplicate source sha across games: {shas[sha]} and {game_id}")
        else:
            shas[sha] = game_id
        path = root / relpath
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
        if int(row.get("content_length", -1)) != len(raw):
            failures.append(f"row {index} content length mismatch")
        if not raw.startswith(b"%PDF"):
            failures.append(f"row {index} missing PDF magic")
    return {
        "season": season,
        "manifest_rows": len(rows),
        "unique_game_ids": len(game_ids),
        "unique_source_sha256": len(shas),
        "integrity_ok": not failures,
        "failures": failures,
    }


@dataclass(frozen=True)
class GameBookArchiveRow:
    archive_id: str
    parser_version: str
    season: int
    week: int
    game_id: str
    away_team: str
    home_team: str
    gamekey: str | None
    source_url: str | None
    retrieved_at_utc: str
    http_status: int | None
    content_type: str | None
    content_length: int | None
    raw_pdf_sha256: str | None
    raw_object_relpath: str | None
    pdf_magic_valid: bool
    pdf_text_extraction_success: bool
    text_sha256: str | None
    text_length: int | None
    not_active_heading_occurrences: int | None
    did_not_play_heading_occurrences: int | None
    not_active_structure_valid: bool
    did_not_play_structure_valid: bool
    semantic_headings_distinct: bool
    source_row_qualified: bool
    error: str | None
    discovery_crosswalk_is_label_authority: bool
    player_identity_resolution_performed: bool
    game_day_roster_universe_constructed: bool
    model_fit_performed: bool
    game_outcomes_used: int
    completed_2026_outcomes_used: int


def archive_season(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"season must be one of {sorted(EXPECTED_GAMES)}")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; source-qualification)",
        "Accept": "application/pdf,*/*;q=0.8",
    })
    crosswalk = load_discovery_crosswalk(session, timeout)
    rows: list[GameBookArchiveRow] = []

    for game in _canonical_games(season):
        week = int(game["week"])
        away = _canonical_team(game["away_team"])
        home = _canonical_team(game["home_team"])
        game_id = str(game["game_id"])
        match = crosswalk.get((season, week, away, home))
        raw_gamekey = None if match is None else match.get("gamekey")
        gamekey = None if raw_gamekey in (None, "") else str(raw_gamekey)
        source_url = None if gamekey is None else legacy_gamebook_url(season, week, gamekey)
        retrieved_at = _utc_now()
        status: int | None = None
        content_type: str | None = None
        content_length: int | None = None
        raw_sha: str | None = None
        raw_relpath: str | None = None
        pdf_magic = False
        text_success = False
        signals: dict[str, Any] = {
            "text_sha256": None,
            "text_length": None,
            "not_active_heading_occurrences": None,
            "did_not_play_heading_occurrences": None,
            "not_active_structure_valid": False,
            "did_not_play_structure_valid": False,
            "semantic_headings_distinct": False,
        }
        error: str | None = None

        if match is None:
            error = "legacy discovery crosswalk missing canonical game"
        elif gamekey is None:
            error = "legacy discovery crosswalk missing gamekey"
        else:
            last_error: Exception | None = None
            response: requests.Response | None = None
            for attempt in range(attempts):
                try:
                    response = session.get(source_url, timeout=timeout, allow_redirects=True)
                    status = int(response.status_code)
                    content_type = (
                        (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                    )
                    if status >= 500 and attempt + 1 < attempts:
                        response.close()
                        response = None
                        continue
                    break
                except requests.RequestException as exc:
                    last_error = exc
                    response = None
            if response is None:
                error = f"request failed: {last_error}"
            else:
                raw = bytes(response.content)
                response.close()
                content_length = len(raw)
                pdf_magic = raw.startswith(b"%PDF")
                if status != 200:
                    error = f"Game Book HTTP {status}"
                elif content_type != "application/pdf":
                    error = f"unexpected Game Book content type: {content_type!r}"
                elif not pdf_magic:
                    error = "Game Book missing PDF magic"
                else:
                    raw_sha = _sha256(raw)
                    raw_path = archive_root / "raw" / f"{raw_sha}.pdf.gz"
                    _write_gzip_deterministic(raw_path, raw)
                    raw_relpath = str(raw_path.relative_to(archive_root))
                    try:
                        text = _extract_pdf_text(raw)
                        text_success = True
                        signals = source_structure_signals(text)
                        if signals["not_active_structure_valid"] is not True:
                            error = "Not Active heading not found"
                        elif signals["did_not_play_structure_valid"] is not True:
                            error = "Did Not Play heading not found"
                        elif signals["semantic_headings_distinct"] is not True:
                            error = "Not Active and Did Not Play structures not both present"
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"

        qualified = bool(
            error is None
            and status == 200
            and content_type == "application/pdf"
            and content_length
            and raw_sha
            and raw_relpath
            and pdf_magic
            and text_success
            and signals["not_active_structure_valid"] is True
            and signals["did_not_play_structure_valid"] is True
            and signals["semantic_headings_distinct"] is True
        )
        rows.append(GameBookArchiveRow(
            archive_id=ARCHIVE_ID,
            parser_version=PARSER_VERSION,
            season=season,
            week=week,
            game_id=game_id,
            away_team=away,
            home_team=home,
            gamekey=gamekey,
            source_url=source_url,
            retrieved_at_utc=retrieved_at,
            http_status=status,
            content_type=content_type,
            content_length=content_length,
            raw_pdf_sha256=raw_sha,
            raw_object_relpath=raw_relpath,
            pdf_magic_valid=pdf_magic,
            pdf_text_extraction_success=text_success,
            text_sha256=signals["text_sha256"],
            text_length=signals["text_length"],
            not_active_heading_occurrences=signals["not_active_heading_occurrences"],
            did_not_play_heading_occurrences=signals["did_not_play_heading_occurrences"],
            not_active_structure_valid=bool(signals["not_active_structure_valid"]),
            did_not_play_structure_valid=bool(signals["did_not_play_structure_valid"]),
            semantic_headings_distinct=bool(signals["semantic_headings_distinct"]),
            source_row_qualified=qualified,
            error=error,
            discovery_crosswalk_is_label_authority=False,
            player_identity_resolution_performed=False,
            game_day_roster_universe_constructed=False,
            model_fit_performed=False,
            game_outcomes_used=0,
            completed_2026_outcomes_used=0,
        ))

    manifest_rows = [asdict(row) for row in rows]
    manifest_path = archive_root / "manifests" / f"{season}.jsonl"
    _write_manifest(manifest_path, manifest_rows)
    integrity = verify_archive(archive_root, season)

    qualified = sum(row.source_row_qualified for row in rows)
    byte_verified = sum(
        row.raw_pdf_sha256 is not None and row.pdf_magic_valid and row.content_length is not None
        for row in rows
    )
    text_ok = sum(row.pdf_text_extraction_success for row in rows)
    not_active_ok = sum(row.not_active_structure_valid for row in rows)
    did_not_play_ok = sum(row.did_not_play_structure_valid for row in rows)
    distinct_ok = sum(row.semantic_headings_distinct for row in rows)
    duplicate_source_sha = len(rows) - len(
        {row.raw_pdf_sha256 for row in rows if row.raw_pdf_sha256}
    )
    errors = [row for row in rows if row.error is not None]
    expected = EXPECTED_GAMES[season]
    receipt = {
        "contract_id": "V09B-LEGACY-GAMEBOOK-RAW-ARCHIVE-V1",
        "archive_id": ARCHIVE_ID,
        "parser_version": PARSER_VERSION,
        "season": season,
        "canonical_games": len(rows),
        "expected_games": expected,
        "source_bytes_verified": byte_verified,
        "source_bytes_verified_rate": byte_verified / expected,
        "pdf_text_extractions": text_ok,
        "pdf_text_extraction_rate": text_ok / expected,
        "not_active_structure_valid_games": not_active_ok,
        "not_active_structure_rate": not_active_ok / expected,
        "did_not_play_structure_valid_games": did_not_play_ok,
        "did_not_play_structure_rate": did_not_play_ok / expected,
        "distinct_semantic_structure_games": distinct_ok,
        "distinct_semantic_structure_rate": distinct_ok / expected,
        "qualified_source_rows": qualified,
        "canonical_game_coverage_rate": qualified / expected,
        "duplicate_canonical_game_rows": len(rows) - len({row.game_id for row in rows}),
        "duplicate_source_sha_across_distinct_games": duplicate_source_sha,
        "source_row_errors": len(errors),
        "archive_integrity_ok": integrity["integrity_ok"],
        "archive_integrity_failures": integrity["failures"],
        "all_frozen_gates_pass": bool(
            len(rows) == expected
            and qualified == expected
            and byte_verified == expected
            and text_ok == expected
            and not_active_ok == expected
            and did_not_play_ok == expected
            and distinct_ok == expected
            and duplicate_source_sha == 0
            and not errors
            and integrity["integrity_ok"] is True
        ),
        "player_identity_resolution_performed": False,
        "game_day_roster_universe_constructed": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "error_rows": [asdict(row) for row in errors],
    }
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)
    receipt = archive_season(
        args.season,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in receipt.items() if key != "error_rows"},
            indent=2,
            sort_keys=True,
        )
    )
    if receipt["all_frozen_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Snapshot-backed raw-source audit for 2017-2021 NFL Game Books.

This V2 deliberately removes mutable Game Center rediscovery from the V1 source path.
The only discovery input is the already-qualified and durably persisted 1,296-row
Game Book locator snapshot. V2 independently re-fetches those first-party PDFs,
re-validates redirect provenance and bytes, extracts text, and checks the unchanged
Not Active / Did Not Play source structure. Season jobs have no layer-qualification
authority; only the separate aggregate five-season gate may qualify the modern source.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_modern_gamebook_locator_audit_v1 as locator_v1
from research import v09b_modern_gamebook_locator_audit_v2 as locator_v2
from research import v09b_modern_gamebook_raw_archive_v1 as v1

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2"
ARCHIVE_ID = "V09B-MODERN-GAMEBOOK-BYTES-2017-2021-V2"
PARSER_VERSION = "V09B-MODERN-GAMEBOOK-TEXT-STRUCTURE-V2"
EXPECTED_GAMES = dict(locator_v1.EXPECTED_GAMES)
SNAPSHOT_SHA256 = "d26b2cab8bdd05c223de0239cfaf70b09b75b6487c8ba2c353bd7749d1730351"
SNAPSHOT_BYTES = 154920
SNAPSHOT_ROWS = 1296
REQUIRED_HOST = "static.www.nfl.com"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frozen_snapshot(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    if len(raw) != SNAPSHOT_BYTES:
        raise ValueError(f"locator snapshot byte length changed: {len(raw)} != {SNAPSHOT_BYTES}")
    digest = _sha256(raw)
    if digest != SNAPSHOT_SHA256:
        raise ValueError(f"locator snapshot SHA changed: {digest}")

    mapping: dict[str, str] = {}
    urls: set[str] = set()
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"invalid locator snapshot row {line_no}")
        game_id, url = parts
        if not game_id or not url:
            raise ValueError(f"empty locator snapshot field at row {line_no}")
        if game_id in mapping:
            raise ValueError(f"duplicate game_id in locator snapshot: {game_id}")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != REQUIRED_HOST:
            raise ValueError(f"non-first-party locator snapshot URL at row {line_no}: {url}")
        if url in urls:
            raise ValueError(f"duplicate Game Book URL in locator snapshot: {url}")
        mapping[game_id] = url
        urls.add(url)

    if len(mapping) != SNAPSHOT_ROWS or len(urls) != SNAPSHOT_ROWS:
        raise ValueError(
            f"locator snapshot population changed: games={len(mapping)} urls={len(urls)}"
        )
    return mapping


def _read_manifest(path: Path) -> list[dict[str, Any]]:
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
    game_ids = [str(row["game_id"]) for row in rows]
    if len(game_ids) != len(set(game_ids)):
        raise ValueError("duplicate canonical game identity in modern V2 archive manifest")
    ordered = sorted(rows, key=lambda row: (int(row["week"]), str(row["game_id"])))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = _read_manifest(path)
        existing_by_game = {str(row["game_id"]): row for row in existing}
        proposed_by_game = {str(row["game_id"]): row for row in ordered}
        if set(existing_by_game) != set(proposed_by_game):
            raise ValueError("modern V2 archive manifest game universe changed after first capture")
        changed = [
            game_id
            for game_id in sorted(existing_by_game)
            if _stable_manifest_row(existing_by_game[game_id])
            != _stable_manifest_row(proposed_by_game[game_id])
        ]
        if changed:
            raise ValueError(
                "modern V2 archive manifest is immutable; changed source/parser rows: "
                + ", ".join(changed[:10])
            )
        return
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in ordered),
        encoding="utf-8",
    )


def verify_archive(root: Path, season: int) -> dict[str, Any]:
    rows = _read_manifest(root / "manifests" / f"{season}.jsonl")
    failures: list[str] = []
    seen_games: set[str] = set()
    seen_shas: dict[str, str] = {}
    for index, row in enumerate(rows, start=1):
        game_id = str(row.get("game_id") or "")
        if game_id in seen_games:
            failures.append(f"duplicate game_id at row {index}: {game_id}")
        seen_games.add(game_id)
        sha = str(row.get("raw_pdf_sha256") or "")
        relpath = str(row.get("raw_object_relpath") or "")
        if len(sha) != 64 or not relpath:
            failures.append(f"row {index} incomplete raw object identity")
            continue
        if sha in seen_shas and seen_shas[sha] != game_id:
            failures.append(f"duplicate source sha across games: {seen_shas[sha]} and {game_id}")
        else:
            seen_shas[sha] = game_id
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
        source_url = str(row.get("source_url") or "")
        final_url = str(row.get("final_url") or "")
        if not locator_v2.redirect_target_allowed(source_url, final_url):
            failures.append(f"row {index} unauthorized final redirect target")
    return {
        "season": season,
        "manifest_rows": len(rows),
        "unique_game_ids": len(seen_games),
        "unique_source_sha256": len(seen_shas),
        "integrity_ok": not failures,
        "failures": failures,
    }


def _first_party_request(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    attempts: int,
) -> requests.Response:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != REQUIRED_HOST:
        raise RuntimeError(f"snapshot source URL is not authorized first-party HTTPS: {url}")
    response = locator_v1._request(session, url, timeout=timeout, attempts=attempts)
    final_url = str(getattr(response, "url", url) or url)
    if not locator_v2.redirect_target_allowed(url, final_url):
        response.close()
        raise RuntimeError(
            "snapshot document request redirected outside authorized host class: "
            f"requested={url} final={final_url}"
        )
    return response


def archive_season(
    season: int,
    *,
    snapshot_path: Path,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"season must be one of {sorted(EXPECTED_GAMES)}")

    snapshot = load_frozen_snapshot(snapshot_path)
    canonical = locator_v1._canonical_games(season)
    canonical_ids = {str(game["game_id"]) for game in canonical}
    snapshot_ids_for_season = {game_id for game_id in snapshot if game_id.startswith(f"{season}_")}
    if snapshot_ids_for_season != canonical_ids:
        missing = sorted(canonical_ids - snapshot_ids_for_season)
        extra = sorted(snapshot_ids_for_season - canonical_ids)
        raise RuntimeError(
            f"frozen locator snapshot/canonical schedule mismatch for {season}: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/2.0; snapshot-source-qualification)",
        "Accept": "application/pdf,*/*;q=0.8",
    })

    rows: list[dict[str, Any]] = []
    for game in canonical:
        game_id = str(game["game_id"])
        week = int(game["week"])
        away = str(game["away_team"])
        home = str(game["home_team"])
        source_url = snapshot[game_id]
        retrieved_at = v1._utc_now()
        final_url: str | None = None
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
            "lineups_heading_occurrences": None,
            "substitutions_heading_occurrences": None,
            "not_active_structure_valid": False,
            "did_not_play_structure_valid": False,
            "semantic_headings_distinct": False,
        }
        error: str | None = None

        try:
            response = _first_party_request(session, source_url, timeout=timeout, attempts=attempts)
            status = int(response.status_code)
            content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
            final_url = str(getattr(response, "url", source_url) or source_url)
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
                raw_helpers._write_gzip_deterministic(raw_path, raw)
                raw_relpath = str(raw_path.relative_to(archive_root))
                try:
                    text = raw_helpers._extract_pdf_text(raw)
                    text_success = True
                    signals = v1.source_structure_signals(text)
                    if signals["not_active_structure_valid"] is not True:
                        error = "Not Active heading not found"
                    elif signals["did_not_play_structure_valid"] is not True:
                        error = "Did Not Play heading not found"
                    elif signals["semantic_headings_distinct"] is not True:
                        error = "Not Active and Did Not Play structures not both present"
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        qualified = bool(
            error is None
            and source_url
            and final_url
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
        rows.append({
            "archive_id": ARCHIVE_ID,
            "parser_version": PARSER_VERSION,
            "season": season,
            "week": week,
            "game_id": game_id,
            "away_team": away,
            "home_team": home,
            "locator_snapshot_sha256": SNAPSHOT_SHA256,
            "locator_snapshot_game_present": True,
            "source_url": source_url,
            "final_url": final_url,
            "retrieved_at_utc": retrieved_at,
            "http_status": status,
            "content_type": content_type,
            "content_length": content_length,
            "raw_pdf_sha256": raw_sha,
            "raw_object_relpath": raw_relpath,
            "pdf_magic_valid": pdf_magic,
            "pdf_text_extraction_success": text_success,
            **signals,
            "source_row_qualified": qualified,
            "error": error,
            "live_game_center_rediscovery_used": False,
            "page_order_tie_break_used": False,
            "snapshot_is_label_authority": False,
            "player_identity_resolution_performed": False,
            "game_day_roster_universe_constructed": False,
            "model_fit_performed": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
        })

    manifest_path = archive_root / "manifests" / f"{season}.jsonl"
    _write_manifest(manifest_path, rows)
    integrity = verify_archive(archive_root, season)

    expected = EXPECTED_GAMES[season]
    snapshot_ok = sum(row["locator_snapshot_game_present"] is True for row in rows)
    byte_verified = sum(
        row["raw_pdf_sha256"] is not None
        and row["pdf_magic_valid"] is True
        and row["content_length"] is not None
        for row in rows
    )
    text_ok = sum(row["pdf_text_extraction_success"] is True for row in rows)
    not_active_ok = sum(row["not_active_structure_valid"] is True for row in rows)
    dnp_ok = sum(row["did_not_play_structure_valid"] is True for row in rows)
    distinct_ok = sum(row["semantic_headings_distinct"] is True for row in rows)
    qualified = sum(row["source_row_qualified"] is True for row in rows)
    source_shas = [str(row["raw_pdf_sha256"]) for row in rows if row["raw_pdf_sha256"]]
    duplicate_source_sha = len(source_shas) - len(set(source_shas))
    errors = [row for row in rows if row["error"] is not None]

    season_pass = bool(
        len(rows) == expected
        and snapshot_ok == expected
        and byte_verified == expected
        and text_ok == expected
        and not_active_ok == expected
        and dnp_ok == expected
        and distinct_ok == expected
        and qualified == expected
        and len(rows) == len({str(row["game_id"]) for row in rows})
        and duplicate_source_sha == 0
        and not errors
        and integrity["integrity_ok"] is True
    )

    return {
        "contract_id": CONTRACT_ID,
        "archive_id": ARCHIVE_ID,
        "parser_version": PARSER_VERSION,
        "season": season,
        "canonical_games": len(rows),
        "expected_games": expected,
        "locator_snapshot_sha256": SNAPSHOT_SHA256,
        "snapshot_covered_games": snapshot_ok,
        "snapshot_coverage_rate": snapshot_ok / expected,
        "source_bytes_verified": byte_verified,
        "source_bytes_verified_rate": byte_verified / expected,
        "pdf_text_extractions": text_ok,
        "pdf_text_extraction_rate": text_ok / expected,
        "not_active_structure_valid_games": not_active_ok,
        "not_active_structure_rate": not_active_ok / expected,
        "did_not_play_structure_valid_games": dnp_ok,
        "did_not_play_structure_rate": dnp_ok / expected,
        "distinct_semantic_structure_games": distinct_ok,
        "distinct_semantic_structure_rate": distinct_ok / expected,
        "qualified_source_rows": qualified,
        "canonical_game_coverage_rate": qualified / expected,
        "lineups_heading_present_games": sum((row["lineups_heading_occurrences"] or 0) >= 1 for row in rows),
        "substitutions_heading_present_games": sum((row["substitutions_heading_occurrences"] or 0) >= 1 for row in rows),
        "duplicate_canonical_game_rows": len(rows) - len({str(row["game_id"]) for row in rows}),
        "duplicate_source_sha_across_distinct_games": duplicate_source_sha,
        "source_row_errors": len(errors),
        "archive_integrity_ok": integrity["integrity_ok"],
        "archive_integrity_failures": integrity["failures"],
        "season_frozen_source_gates_pass": season_pass,
        "season_has_layer_qualification_authority": False,
        "modern_raw_source_bytes_qualified": False,
        "modern_gamebook_structure_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "live_game_center_rediscovery_used": False,
        "page_order_tie_break_used": False,
        "player_identity_resolution_performed": False,
        "game_day_roster_universe_constructed": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "error_rows": errors,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)
    receipt = archive_season(
        args.season,
        snapshot_path=args.snapshot,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "error_rows"}, indent=2, sort_keys=True))
    if receipt["season_frozen_source_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

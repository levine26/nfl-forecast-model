from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from research.v09b_legacy_gamebook_raw_archive_v1 import (
    ARCHIVE_ID,
    _manifest_rows,
    _sha256,
    _write_gzip_deterministic,
    _write_manifest,
    source_structure_signals,
    verify_archive,
)


def _row(*, game_id: str = "2012_01_DAL_NYG", raw_sha: str = "a" * 64) -> dict[str, object]:
    return {
        "archive_id": ARCHIVE_ID,
        "parser_version": "V09B-GAMEBOOK-TEXT-STRUCTURE-V1",
        "season": 2012,
        "week": 1,
        "game_id": game_id,
        "away_team": "DAL",
        "home_team": "NYG",
        "gamekey": "55504",
        "source_url": "https://www.nflgsis.com/2012/Reg/01/55504/Gamebook.pdf",
        "retrieved_at_utc": "2026-09-12T00:00:00Z",
        "http_status": 200,
        "content_type": "application/pdf",
        "content_length": 10,
        "raw_pdf_sha256": raw_sha,
        "raw_object_relpath": f"raw/{raw_sha}.pdf.gz",
        "pdf_magic_valid": True,
        "pdf_text_extraction_success": True,
        "text_sha256": "b" * 64,
        "text_length": 100,
        "not_active_heading_occurrences": 1,
        "did_not_play_heading_occurrences": 1,
        "not_active_structure_valid": True,
        "did_not_play_structure_valid": True,
        "semantic_headings_distinct": True,
        "source_row_qualified": True,
        "error": None,
        "discovery_crosswalk_is_label_authority": False,
        "player_identity_resolution_performed": False,
        "game_day_roster_universe_constructed": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def test_not_active_and_did_not_play_are_distinct_semantic_structures() -> None:
    text = "Header\nNot Active: A. Player\nOther\nDid Not Play: B. Player\n"
    signals = source_structure_signals(text)
    assert signals["not_active_heading_occurrences"] == 1
    assert signals["did_not_play_heading_occurrences"] == 1
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is True


def test_repeated_team_specific_headings_do_not_fail_presence_gate() -> None:
    text = (
        "Not Active: A\nDid Not Play: B\n"
        "Second team Not Active: C\nSecond team Did Not Play: D\n"
    )
    signals = source_structure_signals(text)
    assert signals["not_active_heading_occurrences"] == 2
    assert signals["did_not_play_heading_occurrences"] == 2
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is True


def test_missing_did_not_play_heading_fails_structure() -> None:
    signals = source_structure_signals("Not Active: A\n")
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is False
    assert signals["semantic_headings_distinct"] is False


def test_missing_not_active_heading_fails_structure() -> None:
    signals = source_structure_signals("Did Not Play: A\n")
    assert signals["not_active_structure_valid"] is False
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is False


def test_content_addressed_gzip_is_deterministic_and_immutable(tmp_path: Path) -> None:
    raw = b"%PDF-test"
    path = tmp_path / "raw" / f"{_sha256(raw)}.pdf.gz"
    _write_gzip_deterministic(path, raw)
    first = path.read_bytes()
    _write_gzip_deterministic(path, raw)
    assert path.read_bytes() == first
    with gzip.open(path, "rb") as handle:
        assert handle.read() == raw


def test_manifest_first_capture_is_preserved_across_revalidation_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2012.jsonl"
    row = _row()
    _write_manifest(path, [row])
    before = path.read_text(encoding="utf-8")
    rerun = dict(row)
    rerun["retrieved_at_utc"] = "2026-09-13T00:00:00Z"
    _write_manifest(path, [rerun])
    assert path.read_text(encoding="utf-8") == before
    assert _manifest_rows(path)[0]["retrieved_at_utc"] == "2026-09-12T00:00:00Z"


def test_manifest_rejects_changed_historical_source_sha(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2012.jsonl"
    _write_manifest(path, [_row()])
    changed = _row(raw_sha="c" * 64)
    with pytest.raises(ValueError, match="manifest is immutable"):
        _write_manifest(path, [changed])


def test_manifest_rejects_changed_game_universe(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2012.jsonl"
    _write_manifest(path, [_row()])
    with pytest.raises(ValueError, match="game universe changed"):
        _write_manifest(path, [_row(game_id="2012_01_IND_CHI")])


def test_verify_archive_checks_sha_length_and_pdf_magic(tmp_path: Path) -> None:
    raw = b"%PDF-test"
    sha = _sha256(raw)
    raw_path = tmp_path / "raw" / f"{sha}.pdf.gz"
    _write_gzip_deterministic(raw_path, raw)
    row = _row(raw_sha=sha)
    row["content_length"] = len(raw)
    row["raw_object_relpath"] = str(raw_path.relative_to(tmp_path))
    _write_manifest(tmp_path / "manifests" / "2012.jsonl", [row])
    result = verify_archive(tmp_path, 2012)
    assert result["integrity_ok"] is True
    assert result["failures"] == []


def test_manifest_json_is_canonicalized(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2012.jsonl"
    _write_manifest(path, [_row()])
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["archive_id"] == ARCHIVE_ID
    assert parsed["completed_2026_outcomes_used"] == 0

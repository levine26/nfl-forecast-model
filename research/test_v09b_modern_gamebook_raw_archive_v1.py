from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.v09b_modern_gamebook_raw_archive_v1 import (
    ARCHIVE_ID,
    _read_manifest,
    _write_manifest,
    source_structure_signals,
)


def test_modern_structure_accepts_official_no_colon_paired_headings() -> None:
    text = (
        "Lineups\n"
        "Substitutions                         Substitutions\n"
        "Did Not Play                         Did Not Play\n"
        "Not Active                           Not Active\n"
    )
    result = source_structure_signals(text)
    assert result["not_active_heading_occurrences"] == 1
    assert result["did_not_play_heading_occurrences"] == 1
    assert result["lineups_heading_occurrences"] == 1
    assert result["substitutions_heading_occurrences"] == 1
    assert result["not_active_structure_valid"] is True
    assert result["did_not_play_structure_valid"] is True
    assert result["semantic_headings_distinct"] is True


def test_not_active_and_did_not_play_are_independent_required_signals() -> None:
    not_active_only = source_structure_signals("Not Active Not Active\n")
    assert not_active_only["not_active_structure_valid"] is True
    assert not_active_only["did_not_play_structure_valid"] is False
    assert not_active_only["semantic_headings_distinct"] is False

    dnp_only = source_structure_signals("Did Not Play Did Not Play\n")
    assert dnp_only["not_active_structure_valid"] is False
    assert dnp_only["did_not_play_structure_valid"] is True
    assert dnp_only["semantic_headings_distinct"] is False


def test_lineups_and_substitutions_are_measured_but_not_raw_structure_authority() -> None:
    text = "Did Not Play Did Not Play\nNot Active Not Active\n"
    result = source_structure_signals(text)
    assert result["lineups_heading_occurrences"] == 0
    assert result["substitutions_heading_occurrences"] == 0
    assert result["semantic_headings_distinct"] is True


def _manifest_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "archive_id": ARCHIVE_ID,
        "parser_version": "V09B-MODERN-GAMEBOOK-TEXT-STRUCTURE-V1",
        "season": 2017,
        "week": 1,
        "game_id": "2017_01_ARI_DET",
        "source_url": "https://static.www.nfl.com/image/upload/gamecenter/foo.pdf",
        "final_url": "https://static.www.nfl.com/image/upload/gamecenter/foo.pdf",
        "retrieved_at_utc": "2026-09-13T00:00:00Z",
        "raw_pdf_sha256": "a" * 64,
        "raw_object_relpath": "raw/" + "a" * 64 + ".pdf.gz",
        "content_length": 123,
        "not_active_structure_valid": True,
        "did_not_play_structure_valid": True,
    }
    row.update(overrides)
    return row


def test_manifest_replay_allows_only_retrieval_timestamp_to_change(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2017.jsonl"
    first = _manifest_row()
    _write_manifest(path, [first])
    replay = _manifest_row(retrieved_at_utc="2026-09-13T01:00:00Z")
    _write_manifest(path, [replay])
    stored = _read_manifest(path)
    assert len(stored) == 1
    assert stored[0]["retrieved_at_utc"] == "2026-09-13T00:00:00Z"


def test_manifest_replay_rejects_source_or_parser_change(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2017.jsonl"
    _write_manifest(path, [_manifest_row()])
    with pytest.raises(ValueError, match="immutable"):
        _write_manifest(path, [_manifest_row(source_url="https://static.www.nfl.com/other.pdf")])


def test_manifest_rejects_duplicate_game_identity(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2017.jsonl"
    with pytest.raises(ValueError, match="duplicate canonical game identity"):
        _write_manifest(path, [_manifest_row(), _manifest_row(raw_pdf_sha256="b" * 64)])


def test_manifest_json_is_compact_and_round_trippable(tmp_path: Path) -> None:
    path = tmp_path / "manifests" / "2017.jsonl"
    _write_manifest(path, [_manifest_row()])
    line = path.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["archive_id"] == ARCHIVE_ID
    assert parsed["game_id"] == "2017_01_ARI_DET"

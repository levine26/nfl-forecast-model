from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research import v09b_modern_gamebook_raw_archive_v1 as v1
from research import v09b_modern_gamebook_raw_archive_v2 as v2


def test_contract_preserves_v1_thresholds_and_closes_downstream_authority() -> None:
    c = json.loads(
        Path("research/availability/v09b_modern_gamebook_raw_archive_contract_v2.json").read_text()
    )
    assert c["status"] == "PREREGISTERED_SNAPSHOT_BACKED_FULL_SOURCE_QUALIFICATION"
    assert c["canonical_universe"]["expected_games_total"] == 1296
    assert c["locator_snapshot_dependency"]["sha256"] == v2.SNAPSHOT_SHA256
    assert c["locator_snapshot_dependency"]["live_game_center_rediscovery_allowed"] is False
    assert c["locator_snapshot_dependency"]["page_order_tie_break_allowed"] is False
    assert c["governance"]["thresholds_unchanged_from_v1"] is True
    assert c["governance"]["label_semantics_unchanged_from_v1"] is True
    assert c["qualification_authority"]["season_jobs_may_qualify_layer"] is False
    assert c["qualification_authority"]["aggregate_five_season_job_required"] is True
    assert c["not_yet_qualified"]["modern_game_day_roster_universe"] is True
    assert c["not_yet_qualified"]["modern_player_team_game_identity"] is True
    assert c["not_yet_qualified"]["v09b_model_fit"] is True


def test_v2_source_has_no_live_game_center_rediscovery_call() -> None:
    source = Path("research/v09b_modern_gamebook_raw_archive_v2.py").read_text()
    assert "locator_v2.audit_season" not in source
    assert "extract_gamebook_evidence" not in source
    assert "nfl.com/games/" not in source
    assert "load_frozen_snapshot" in source


def test_parser_semantics_remain_v1_semantics() -> None:
    text = """
Lineups
Substitutions
Did Not Play
Not Active
"""
    signals = v1.source_structure_signals(text)
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is True


def test_snapshot_parser_requires_unique_first_party_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = (
        "2017_01_ARI_DET\thttps://static.www.nfl.com/gamecenter/a.pdf\n"
        "2019_15_BUF_PIT\thttps://static.www.nfl.com/gamecenter/b.pdf\n"
    ).encode()
    path = tmp_path / "locator_snapshot.tsv"
    path.write_bytes(raw)
    monkeypatch.setattr(v2, "SNAPSHOT_BYTES", len(raw))
    monkeypatch.setattr(v2, "SNAPSHOT_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(v2, "SNAPSHOT_ROWS", 2)
    mapping = v2.load_frozen_snapshot(path)
    assert mapping["2017_01_ARI_DET"].endswith("a.pdf")
    assert len(mapping) == 2


def test_snapshot_parser_rejects_duplicate_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = (
        "2017_01_ARI_DET\thttps://static.www.nfl.com/gamecenter/a.pdf\n"
        "2019_15_BUF_PIT\thttps://static.www.nfl.com/gamecenter/a.pdf\n"
    ).encode()
    path = tmp_path / "locator_snapshot.tsv"
    path.write_bytes(raw)
    monkeypatch.setattr(v2, "SNAPSHOT_BYTES", len(raw))
    monkeypatch.setattr(v2, "SNAPSHOT_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(v2, "SNAPSHOT_ROWS", 2)
    with pytest.raises(ValueError, match="duplicate Game Book URL"):
        v2.load_frozen_snapshot(path)


def test_snapshot_parser_rejects_non_first_party_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = "2017_01_ARI_DET\thttps://example.com/gamebook.pdf\n".encode()
    path = tmp_path / "locator_snapshot.tsv"
    path.write_bytes(raw)
    monkeypatch.setattr(v2, "SNAPSHOT_BYTES", len(raw))
    monkeypatch.setattr(v2, "SNAPSHOT_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(v2, "SNAPSHOT_ROWS", 1)
    with pytest.raises(ValueError, match="non-first-party"):
        v2.load_frozen_snapshot(path)

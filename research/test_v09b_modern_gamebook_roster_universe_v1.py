from __future__ import annotations

import json
from pathlib import Path

from research.v09b_legacy_gamebook_roster_universe_v1 import PlayerEntry
from research.v09b_modern_gamebook_roster_universe_v1 import (
    era_bounds,
    partition_from_sections,
    validate_upstream_archive,
)


def _entry(number: int, name: str, position: str = "WR") -> PlayerEntry:
    return PlayerEntry(position=position, jersey_number=str(number), display_name=name)


def _sections(active_count: int, inactive_count: int) -> dict[str, list[PlayerEntry]]:
    lineup = [_entry(i + 1, f"Starter{i + 1}") for i in range(22)]
    subs_count = max(0, active_count - 22)
    substitutions = [_entry(i + 30, f"Sub{i + 1}") for i in range(subs_count)]
    inactive = [_entry(i + 70, f"Inactive{i + 1}") for i in range(inactive_count)]
    return {
        "lineup": lineup,
        "substitutions": substitutions,
        "did_not_play": [],
        "not_active": inactive,
    }


def test_era_bounds_preserve_2017_2019_rule() -> None:
    for season in (2017, 2018, 2019):
        bounds = era_bounds(season)
        assert (bounds.active_min, bounds.active_max, bounds.roster_max) == (43, 46, 53)


def test_era_bounds_preserve_2020_2021_cba_rule() -> None:
    for season in (2020, 2021):
        bounds = era_bounds(season)
        assert (bounds.active_min, bounds.active_max, bounds.roster_max) == (44, 48, 55)


def test_pre_2020_partition_accepts_46_active_and_53_total() -> None:
    partition = partition_from_sections(
        _sections(active_count=46, inactive_count=7),
        team="ARI",
        side="visitor_left",
        season=2019,
    )
    assert partition.active_candidate_count == 46
    assert partition.roster_candidate_count == 53
    assert partition.active_count_sanity_pass is True
    assert partition.roster_count_sanity_pass is True


def test_pre_2020_partition_rejects_47_active() -> None:
    partition = partition_from_sections(
        _sections(active_count=47, inactive_count=6),
        team="ARI",
        side="visitor_left",
        season=2019,
    )
    assert partition.active_count_sanity_pass is False


def test_2020_partition_accepts_44_through_48_active_and_up_to_55_total() -> None:
    for active in range(44, 49):
        inactive = 55 - active
        partition = partition_from_sections(
            _sections(active_count=active, inactive_count=inactive),
            team="ARI",
            side="visitor_left",
            season=2020,
        )
        assert partition.active_count_sanity_pass is True
        assert partition.roster_count_sanity_pass is True


def test_2020_partition_rejects_below_44_active_or_above_55_total() -> None:
    too_few = partition_from_sections(
        _sections(active_count=43, inactive_count=10),
        team="ARI",
        side="visitor_left",
        season=2020,
    )
    assert too_few.active_count_sanity_pass is False

    too_many_total = partition_from_sections(
        _sections(active_count=48, inactive_count=8),
        team="ARI",
        side="visitor_left",
        season=2020,
    )
    assert too_many_total.roster_candidate_count == 56
    assert too_many_total.roster_count_sanity_pass is False


def test_did_not_play_contributes_to_active_not_inactive() -> None:
    sections = _sections(active_count=45, inactive_count=8)
    moved = sections["substitutions"].pop()
    sections["did_not_play"].append(moved)
    partition = partition_from_sections(
        sections,
        team="ARI",
        side="visitor_left",
        season=2018,
    )
    assert partition.active_candidate_count == 45
    assert partition.not_active_count == 8
    assert partition.active_inactive_overlaps == 0


def test_same_section_repeat_is_diagnostic_but_set_deduplicated() -> None:
    sections = _sections(active_count=46, inactive_count=7)
    sections["substitutions"].append(sections["substitutions"][0])
    partition = partition_from_sections(
        sections,
        team="ARI",
        side="visitor_left",
        season=2019,
    )
    assert partition.active_candidate_count == 46
    assert partition.repeated_within_section_occurrences == 1
    assert partition.repeated_within_section_identities == 1
    assert partition.cross_active_semantic_section_conflicts == 0


def test_cross_active_semantic_membership_is_hard_conflict_signal() -> None:
    sections = _sections(active_count=46, inactive_count=7)
    sections["did_not_play"].append(sections["lineup"][0])
    partition = partition_from_sections(
        sections,
        team="ARI",
        side="visitor_left",
        season=2019,
    )
    assert partition.cross_active_semantic_section_conflicts == 1


def test_active_inactive_overlap_is_hard_conflict_signal() -> None:
    sections = _sections(active_count=46, inactive_count=7)
    sections["not_active"].append(sections["lineup"][0])
    partition = partition_from_sections(
        sections,
        team="ARI",
        side="visitor_left",
        season=2019,
    )
    assert partition.active_inactive_overlaps == 1


def test_upstream_guard_requires_aggregate_v2_qualification_and_season_gate(tmp_path: Path) -> None:
    (tmp_path / "receipts").mkdir()
    (tmp_path / "aggregate_qualification.json").write_text(json.dumps({
        "qualification_id": "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2-QUALIFICATION",
        "canonical_games": 1296,
        "qualified_source_rows": 1296,
        "source_row_errors": 0,
        "modern_raw_source_bytes_qualified": True,
        "modern_gamebook_structure_qualified": True,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
    }))
    (tmp_path / "receipts" / "2019.json").write_text(json.dumps({
        "contract_id": "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2",
        "season": 2019,
        "expected_games": 256,
        "canonical_games": 256,
        "season_frozen_source_gates_pass": True,
        "snapshot_coverage_rate": 1.0,
        "source_bytes_verified_rate": 1.0,
        "pdf_text_extraction_rate": 1.0,
        "not_active_structure_rate": 1.0,
        "did_not_play_structure_rate": 1.0,
        "source_row_errors": 0,
        "live_game_center_rediscovery_used": False,
        "page_order_tie_break_used": False,
        "completed_2026_outcomes_used": 0,
    }))
    result = validate_upstream_archive(tmp_path, 2019)
    assert result == {
        "aggregate_qualified": True,
        "season_source_gate_pass": True,
        "upstream_passed": True,
    }


def test_upstream_guard_rejects_v1_receipt_even_if_other_fields_look_green(tmp_path: Path) -> None:
    (tmp_path / "receipts").mkdir()
    (tmp_path / "aggregate_qualification.json").write_text(json.dumps({
        "qualification_id": "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2-QUALIFICATION",
        "canonical_games": 1296,
        "qualified_source_rows": 1296,
        "source_row_errors": 0,
        "modern_raw_source_bytes_qualified": True,
        "modern_gamebook_structure_qualified": True,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
    }))
    (tmp_path / "receipts" / "2019.json").write_text(json.dumps({
        "contract_id": "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V1",
        "season": 2019,
        "expected_games": 256,
        "canonical_games": 256,
        "season_frozen_source_gates_pass": True,
        "snapshot_coverage_rate": 1.0,
        "source_bytes_verified_rate": 1.0,
        "pdf_text_extraction_rate": 1.0,
        "not_active_structure_rate": 1.0,
        "did_not_play_structure_rate": 1.0,
        "source_row_errors": 0,
        "live_game_center_rediscovery_used": False,
        "page_order_tie_break_used": False,
        "completed_2026_outcomes_used": 0,
    }))
    result = validate_upstream_archive(tmp_path, 2019)
    assert result["aggregate_qualified"] is True
    assert result["season_source_gate_pass"] is False
    assert result["upstream_passed"] is False

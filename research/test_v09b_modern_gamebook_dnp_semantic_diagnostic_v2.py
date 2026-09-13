from __future__ import annotations

from research.v09b_legacy_gamebook_roster_universe_v1 import PlayerEntry
from research.v09b_modern_gamebook_dnp_semantic_diagnostic_v2 import diagnose_partition


def _entry(number: int, name: str, position: str = "WR") -> PlayerEntry:
    return PlayerEntry(position=position, jersey_number=str(number), display_name=name)


def _sections(*, lineup: int, substitutions: int, dnp: int, inactive: int) -> dict[str, list[PlayerEntry]]:
    return {
        "lineup": [_entry(i + 1, f"L{i + 1}") for i in range(lineup)],
        "substitutions": [_entry(i + 30, f"S{i + 1}") for i in range(substitutions)],
        "did_not_play": [_entry(i + 60, f"D{i + 1}") for i in range(dnp)],
        "not_active": [_entry(i + 80, f"N{i + 1}") for i in range(inactive)],
    }


def test_2021_dnp_addition_can_create_active_max_contradiction() -> None:
    row = diagnose_partition(
        _sections(lineup=22, substitutions=26, dnp=1, inactive=3),
        season=2021,
        game_id="2021_10_KC_LV",
        team="KC",
        side="visitor_left",
    )
    assert row["lineups_plus_substitutions_union_count"] == 48
    assert row["v1_active_candidate_count"] == 49
    assert row["era_active_max"] == 48
    assert row["active_max_contradiction"] is True
    assert row["minimum_dnp_non_active_required_by_active_max"] == 1
    assert row["did_not_play_identity_classification_performed"] is False
    assert row["diagnostic_has_membership_authority"] is False


def test_2018_multiple_dnp_entries_produce_lower_bound_not_player_labels() -> None:
    row = diagnose_partition(
        _sections(lineup=22, substitutions=22, dnp=4, inactive=7),
        season=2018,
        game_id="2018_16_DEN_OAK",
        team="OAK",
        side="home_right",
    )
    assert row["lineups_plus_substitutions_union_count"] == 44
    assert row["v1_active_candidate_count"] == 48
    assert row["era_active_max"] == 46
    assert row["active_max_contradiction"] is True
    assert row["minimum_dnp_non_active_required_by_active_max"] == 2
    assert row["did_not_play_only_count"] == 4


def test_dnp_within_active_max_is_not_classified() -> None:
    row = diagnose_partition(
        _sections(lineup=22, substitutions=23, dnp=1, inactive=7),
        season=2019,
        game_id="2019_01_X_Y",
        team="X",
        side="visitor_left",
    )
    assert row["v1_active_candidate_count"] == 46
    assert row["active_max_contradiction"] is False
    assert row["minimum_dnp_non_active_required_by_active_max"] == 0
    assert row["did_not_play_identity_classification_performed"] is False


def test_total_roster_contradiction_is_distinct_from_active_contradiction() -> None:
    row = diagnose_partition(
        _sections(lineup=22, substitutions=25, dnp=1, inactive=8),
        season=2020,
        game_id="2020_13_NO_ATL",
        team="NO",
        side="visitor_left",
    )
    assert row["v1_active_candidate_count"] == 48
    assert row["active_max_contradiction"] is False
    assert row["v1_roster_candidate_count"] == 56
    assert row["era_roster_max"] == 55
    assert row["total_roster_max_contradiction"] is True
    assert row["v1_partition_failed"] is True


def test_dnp_identity_already_in_participation_sections_is_not_dnp_only() -> None:
    sections = _sections(lineup=22, substitutions=23, dnp=0, inactive=7)
    sections["did_not_play"].append(sections["substitutions"][0])
    row = diagnose_partition(
        sections,
        season=2019,
        game_id="2019_01_X_Y",
        team="X",
        side="visitor_left",
    )
    assert row["did_not_play_unique_count"] == 1
    assert row["did_not_play_only_count"] == 0
    assert row["v1_active_candidate_count"] == 45

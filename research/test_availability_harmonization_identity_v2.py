from __future__ import annotations

import pandas as pd

from research.run_availability_harmonization_identity_v2 import (
    attach_stable_identity_v2,
    build_player_master_alias_lookup,
    reverse_identity_audit_v2,
)


def _official(player: str, *, team: str = "WAS", week: int = 1) -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2022,
        "week": week,
        "team": team,
        "external_player": player,
        "external_position": "S",
        "external_injury": "Thumb",
        "external_practice_status": "Limited Participation in Practice",
        "external_game_status": "Questionable",
        "external_source": "nfl_com_official_injury_page",
        "source_url": "https://www.nfl.com/injuries/league/2022/reg1",
    }])


def _injury(*, full_name: str = "Kamren Curl", gsis_id: str = "00-0036383", team: str = "WAS", week: int = 1) -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2022,
        "week": week,
        "team": team,
        "gsis_id": gsis_id,
        "position": "S",
        "full_name": full_name,
        "first_name": full_name.split()[0],
        "last_name": full_name.split()[-1],
        "practice_status": "Limited Participation in Practice",
        "report_status": "Questionable",
        "date_modified": "2022-09-09 16:00:00",
    }])


def _master(rows: list[dict] | None = None) -> pd.DataFrame:
    if rows is None:
        rows = [{
            "gsis_id": "00-0036383",
            "display_name": "Kamren Curl",
            "football_name": "Kam Curl",
            "common_first_name": "Kam",
            "first_name": "Kamren",
            "last_name": "Curl",
        }]
    return pd.DataFrame(rows)


def test_player_master_exact_alias_resolves_only_with_same_week_injury_presence() -> None:
    matched = attach_stable_identity_v2(_official("Kam Curl"), _injury(), _master(), season=2022)
    assert matched.iloc[0].gsis_id == "00-0036383"
    assert matched.iloc[0].identity_match_state == "unique"
    assert matched.iloc[0].identity_match_method == "player_master_exact_alias_plus_injury_presence"


def test_player_master_alias_cannot_manufacture_cross_team_identity() -> None:
    matched = attach_stable_identity_v2(
        _official("Kam Curl", team="WAS"),
        _injury(team="NYG"),
        _master(),
        season=2022,
    )
    assert matched.iloc[0].identity_match_state == "unmatched"
    assert matched.iloc[0].gsis_id == ""


def test_player_master_alias_ambiguity_fails_closed() -> None:
    official = _official("Alex Example")
    injuries = pd.concat([
        _injury(full_name="Alexander Example", gsis_id="00-0000001"),
        _injury(full_name="Alexis Example", gsis_id="00-0000002"),
    ], ignore_index=True)
    master = _master([
        {"gsis_id":"00-0000001","display_name":"Alexander Example","football_name":"Alex Example","common_first_name":"Alex","first_name":"Alexander","last_name":"Example"},
        {"gsis_id":"00-0000002","display_name":"Alexis Example","football_name":"Alex Example","common_first_name":"Alex","first_name":"Alexis","last_name":"Example"},
    ])
    matched = attach_stable_identity_v2(official, injuries, master, season=2022)
    assert matched.iloc[0].identity_match_state == "ambiguous"
    assert matched.iloc[0].gsis_id == ""
    assert matched.iloc[0].identity_match_method == "player_master_alias_ambiguous_after_injury_presence"


def test_no_fuzzy_typo_resolution() -> None:
    matched = attach_stable_identity_v2(_official("Kam Curll"), _injury(), _master(), season=2022)
    assert matched.iloc[0].identity_match_state == "unmatched"
    assert matched.iloc[0].gsis_id == ""


def test_existing_exact_injury_identity_remains_primary() -> None:
    official = _official("Kamren Curl")
    matched = attach_stable_identity_v2(official, _injury(), _master(), season=2022)
    assert matched.iloc[0].identity_match_state == "unique"
    assert matched.iloc[0].identity_match_method == "exact_full_name"


def test_reverse_audit_reports_bridge_rows_separately() -> None:
    metrics, unresolved, bridged = reverse_identity_audit_v2(
        _official("Kam Curl"), _injury(), _master(), season=2022
    )
    assert metrics["official_identity_resolution_rate"] == 1.0
    assert metrics["identity_bridge_resolved_rows"] == 1
    assert metrics["identity_bridge_unique_official_names"] == 1
    assert metrics["identity_bridge_fuzzy_matching_used"] is False
    assert unresolved.empty
    assert len(bridged) == 1


def test_alias_lookup_uses_only_preregistered_exact_name_forms() -> None:
    lookup = build_player_master_alias_lookup(_master())
    assert lookup["kamren curl"] == ("00-0036383",)
    assert lookup["kam curl"] == ("00-0036383",)
    assert "k curl" not in lookup

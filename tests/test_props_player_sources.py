import pandas as pd

from nfl_forecast.props_player_sources import (
    add_nflverse_kickoff_timestamp,
    normalize_snap_counts_player_ids,
)


def test_nflverse_gameday_gametime_are_converted_from_eastern_to_utc():
    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_03_X_Y",
                "gameday": "2026-09-20",
                "gametime": "16:25",
            }
        ]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert converted.loc[0, "kickoff"] == pd.Timestamp("2026-09-20T20:25:00Z")


def test_existing_timezone_aware_kickoff_is_preserved_as_utc():
    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_03_X_Y",
                "kickoff": "2026-09-20T13:05:00-07:00",
            }
        ]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert converted.loc[0, "kickoff"] == pd.Timestamp("2026-09-20T20:05:00Z")


def test_missing_schedule_time_fields_remains_explicitly_unknown():
    schedules = pd.DataFrame([{"game_id": "2026_03_X_Y"}])
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert pd.isna(converted.loc[0, "kickoff"])


def test_pfr_snap_ids_are_crosswalked_to_stable_gsis_ids():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "pfr_player_id": "PlayEr00", "offense_snaps": 61},
            {"game_id": "g1", "pfr_player_id": "NoMap00", "offense_snaps": 12},
        ]
    )
    players = pd.DataFrame(
        [
            {"pfr_id": "PlayEr00", "gsis_id": "00-0030001"},
        ]
    )
    normalized, audit = normalize_snap_counts_player_ids(snaps, players)
    assert normalized is not None
    assert normalized.loc[0, "player_id"] == "00-0030001"
    assert pd.isna(normalized.loc[1, "player_id"])
    assert audit["status"] == "pfr_to_gsis_crosswalk"
    assert audit["rows_mapped"] == 1
    assert audit["rows_unmapped"] == 1


def test_ambiguous_pfr_crosswalk_fails_closed_for_that_identity():
    snaps = pd.DataFrame(
        [{"game_id": "g1", "pfr_player_id": "SameId00", "offense_snaps": 40}]
    )
    players = pd.DataFrame(
        [
            {"pfr_id": "SameId00", "gsis_id": "00-0030001"},
            {"pfr_id": "SameId00", "gsis_id": "00-0030002"},
        ]
    )
    normalized, audit = normalize_snap_counts_player_ids(snaps, players)
    assert normalized is None
    assert audit["status"] == "unusable_no_mapped_rows"
    assert audit["ambiguous_pfr_ids"] == 1
    assert audit["rows_mapped"] == 0


def test_snap_rows_without_any_supported_identity_fail_closed():
    snaps = pd.DataFrame([{"game_id": "g1", "player": "Someone", "offense_snaps": 17}])
    normalized, audit = normalize_snap_counts_player_ids(snaps)
    assert normalized is None
    assert audit["status"] == "unusable_missing_identity"
    assert audit["rows_unmapped"] == 1

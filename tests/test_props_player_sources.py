import pandas as pd

from nfl_forecast.props_player_sources import (
    add_nflverse_kickoff_timestamp,
    normalize_snap_counts_player_ids,
    resolve_primary_qbs_from_depth_charts,
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



def test_naive_existing_kickoff_is_not_assumed_utc_and_uses_nflverse_time():
    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_03_X_Y",
                "kickoff": "2026-09-20 16:25:00",
                "gameday": "2026-09-20",
                "gametime": "16:25",
            }
        ]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert converted.loc[0, "kickoff"] == pd.Timestamp("2026-09-20T20:25:00Z")


def test_naive_kickoff_without_source_timezone_remains_unknown():
    schedules = pd.DataFrame(
        [{"game_id": "2026_03_X_Y", "kickoff": "2026-09-20 16:25:00"}]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert pd.isna(converted.loc[0, "kickoff"])



def _depth_player_state():
    return pd.DataFrame(
        [
            {
                "game_id": "2026_03_LAR_ARI",
                "player_id": "A-QB1",
                "position": "QB",
                "team": "ARI",
            },
            {
                "game_id": "2026_03_LAR_ARI",
                "player_id": "A-QB2",
                "position": "QB",
                "team": "ARI",
            },
            {
                "game_id": "2026_03_LAR_ARI",
                "player_id": "L-QB1",
                "position": "QB",
                "team": "LAR",
            },
        ]
    )


def test_timestamped_depth_chart_resolves_unique_qb1_before_forecast():
    depth = pd.DataFrame(
        [
            {
                "dt": "2026-09-17T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
            {
                "dt": "2026-09-17T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB2",
                "pos_abb": "QB",
                "pos_rank": 2,
            },
            {
                "dt": "2026-09-17T18:00:00Z",
                "team": "LAR",
                "gsis_id": "L-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
        ]
    )
    resolved, audit = resolve_primary_qbs_from_depth_charts(
        depth,
        _depth_player_state(),
        game_id="2026_03_LAR_ARI",
        forecast_timestamp="2026-09-17T22:00:00Z",
    )
    assert resolved["ARI"]["player_id"] == "A-QB1"
    assert resolved["LAR"]["player_id"] == "L-QB1"
    assert "nflverse_timestamped_depth_chart" in resolved["ARI"]["provenance"]
    assert audit["teams_resolved"] == 2
    assert audit["status"] == "qualified"


def test_future_depth_chart_snapshot_is_discarded():
    depth = pd.DataFrame(
        [
            {
                "dt": "2026-09-17T23:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            }
        ]
    )
    resolved, audit = resolve_primary_qbs_from_depth_charts(
        depth,
        _depth_player_state(),
        game_id="2026_03_LAR_ARI",
        forecast_timestamp="2026-09-17T22:00:00Z",
    )
    assert resolved == {}
    assert audit["future_rows_discarded"] == 1
    assert audit["status"] == "unusable_no_pregame_rows"


def test_ambiguous_rank_one_depth_chart_fails_closed_for_team():
    depth = pd.DataFrame(
        [
            {
                "dt": "2026-09-17T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
            {
                "dt": "2026-09-17T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB2",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
        ]
    )
    resolved, audit = resolve_primary_qbs_from_depth_charts(
        depth,
        _depth_player_state(),
        game_id="2026_03_LAR_ARI",
        forecast_timestamp="2026-09-17T22:00:00Z",
    )
    assert "ARI" not in resolved
    assert audit["teams_ambiguous"][0]["team"] == "ARI"


def test_out_rank_one_qb_does_not_block_next_available_depth_qb():
    depth = pd.DataFrame(
        [
            {
                "dt": "2026-09-18T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
            {
                "dt": "2026-09-18T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB2",
                "pos_abb": "QB",
                "pos_rank": 2,
            },
        ]
    )
    state = _depth_player_state().copy()
    state["expected_active_state"] = "UNKNOWN"
    state.loc[state["player_id"].eq("A-QB1"), "expected_active_state"] = "OUT"
    state["roster_membership_state"] = "ACTIVE_ROSTER"

    resolved, audit = resolve_primary_qbs_from_depth_charts(
        depth,
        state,
        game_id="2026_03_LAR_ARI",
        forecast_timestamp="2026-09-18T22:00:00Z",
    )

    assert resolved["ARI"]["player_id"] == "A-QB2"
    assert audit["teams_resolved"] == 1


def test_doubtful_rank_one_qb_yields_to_non_doubtful_backup_without_media():
    depth = pd.DataFrame(
        [
            {
                "dt": "2026-09-18T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB1",
                "pos_abb": "QB",
                "pos_rank": 1,
            },
            {
                "dt": "2026-09-18T18:00:00Z",
                "team": "ARI",
                "gsis_id": "A-QB2",
                "pos_abb": "QB",
                "pos_rank": 2,
            },
        ]
    )
    state = _depth_player_state().copy()
    state["expected_active_state"] = "UNKNOWN"
    state.loc[state["player_id"].eq("A-QB1"), "expected_active_state"] = "DOUBTFUL"
    state["roster_membership_state"] = "ACTIVE_ROSTER"

    resolved, _ = resolve_primary_qbs_from_depth_charts(
        depth,
        state,
        game_id="2026_03_LAR_ARI",
        forecast_timestamp="2026-09-18T22:00:00Z",
    )

    assert resolved["ARI"]["player_id"] == "A-QB2"

import pandas as pd
import pytest

from research.props.v2.props_ngs_efficiency_state import build_lagged_ngs_state


def _passing():
    return pd.DataFrame(
        [
            {
                "season": 2025, "season_type": "REG", "week": 1,
                "player_gsis_id": "QB1", "attempts": 20,
                "avg_intended_air_yards": 7.0,
                "completion_percentage_above_expectation": 1.0,
                "avg_time_to_throw": 2.7,
            },
            {
                "season": 2025, "season_type": "REG", "week": 2,
                "player_gsis_id": "QB1", "attempts": 40,
                "avg_intended_air_yards": 9.0,
                "completion_percentage_above_expectation": 4.0,
                "avg_time_to_throw": 2.5,
            },
            {
                "season": 2025, "season_type": "REG", "week": 3,
                "player_gsis_id": "QB1", "attempts": 50,
                "avg_intended_air_yards": 99.0,
                "completion_percentage_above_expectation": 99.0,
                "avg_time_to_throw": 9.9,
            },
            {
                "season": 2025, "season_type": "REG", "week": 0,
                "player_gsis_id": "QB1", "attempts": 100,
                "avg_intended_air_yards": 88.0,
            },
        ]
    )


def _receiving():
    return pd.DataFrame(
        [
            {
                "season": 2025, "season_type": "REG", "week": 1,
                "player_gsis_id": "WR1", "targets": 5,
                "avg_air_distance": 10.0,
                "avg_yac_above_expectation": 1.0,
                "avg_separation": 2.5,
            },
            {
                "season": 2025, "season_type": "REG", "week": 2,
                "player_gsis_id": "WR1", "targets": 10,
                "avg_air_distance": 14.0,
                "avg_yac_above_expectation": 3.0,
                "avg_separation": 3.0,
            },
            {
                "season": 2025, "season_type": "REG", "week": 3,
                "player_gsis_id": "WR1", "targets": 15,
                "avg_air_distance": 90.0,
                "avg_yac_above_expectation": 50.0,
                "avg_separation": 8.0,
            },
        ]
    )


def _rushing():
    return pd.DataFrame(
        [
            {
                "season": 2025, "season_type": "REG", "week": 1,
                "player_gsis_id": "RB1", "rush_attempts": 8,
                "rush_yards_over_expected_per_att": 0.2,
                "percent_attempts_gte_eight_defenders": 20.0,
                "avg_time_to_los": 2.8,
            },
            {
                "season": 2025, "season_type": "REG", "week": 2,
                "player_gsis_id": "RB1", "rush_attempts": 16,
                "rush_yards_over_expected_per_att": 1.2,
                "percent_attempts_gte_eight_defenders": 35.0,
                "avg_time_to_los": 2.4,
            },
            {
                "season": 2025, "season_type": "REG", "week": 3,
                "player_gsis_id": "RB1", "rush_attempts": 30,
                "rush_yards_over_expected_per_att": 9.0,
                "percent_attempts_gte_eight_defenders": 90.0,
                "avg_time_to_los": 5.0,
            },
        ]
    )


def test_ngs_state_excludes_target_week_and_week_zero_summary():
    frame, audit = build_lagged_ngs_state(
        passing=_passing(),
        receiving=_receiving(),
        rushing=_rushing(),
        season=2025,
        week=3,
        player_ids=["QB1", "WR1", "RB1"],
    )
    state = frame.set_index("player_id")
    assert audit["target_week_rows_used"] == 0
    assert audit["historical_max_period_used"]["passing"] == {"season": 2025, "week": 2}
    assert state.loc["QB1", "ngs_pass_rows"] == 2
    assert state.loc["QB1", "ngs_pass_avg_intended_air_yards"] < 9.0
    assert state.loc["WR1", "ngs_rec_rows"] == 2
    assert state.loc["WR1", "ngs_rec_avg_air_distance"] < 14.0
    assert state.loc["RB1", "ngs_rush_rows"] == 2
    assert state.loc["RB1", "ngs_rush_rush_yards_over_expected_per_att"] < 1.2


def test_ngs_features_are_opportunity_weighted_not_simple_week_average():
    frame, _ = build_lagged_ngs_state(
        passing=_passing(),
        receiving=None,
        rushing=None,
        season=2025,
        week=3,
        player_ids=["QB1"],
    )
    value = frame.iloc[0]["ngs_pass_avg_intended_air_yards"]
    # Week 2 has twice the attempts and is more recent, so estimate exceeds 8.0.
    assert value > 8.0
    assert value < 9.0


def test_missing_ngs_row_is_missing_evidence_not_zero():
    frame, audit = build_lagged_ngs_state(
        passing=_passing(),
        receiving=None,
        rushing=None,
        season=2025,
        week=3,
        player_ids=["UNKNOWN"],
    )
    row = frame.iloc[0]
    assert row["ngs_pass_rows"] == 0
    assert pd.isna(row["ngs_pass_avg_intended_air_yards"])
    assert audit["missing_rows_mean_missing_evidence_not_zero"] is True

import numpy as np
import pandas as pd

from research.props.v2.props_ngs_efficiency_model import (
    build_efficiency_learning_table,
    evaluate_rolling_origin,
    fit_metric_model,
    predict_metric,
)


def _passing():
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for week in range(1, 7):
            for i in range(8):
                pid = f"QB{i}"
                expected = 62.0 + 0.5 * i
                cpoe = -2.0 + 0.8 * i
                completion = expected + cpoe + 0.25 * week
                rows.append(
                    {
                        "season": season,
                        "season_type": "REG",
                        "week": week,
                        "player_gsis_id": pid,
                        "attempts": 30 + i,
                        "completion_percentage": completion,
                        "expected_completion_percentage": expected,
                        "completion_percentage_above_expectation": cpoe,
                        "avg_intended_air_yards": 7.0 + 0.1 * i,
                        "avg_completed_air_yards": 5.0 + 0.1 * i,
                        "avg_time_to_throw": 2.5 + 0.01 * i,
                        "aggressiveness": 12.0 + i,
                    }
                )
    return pd.DataFrame(rows)


def _receiving():
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for week in range(1, 7):
            for i in range(12):
                pid = f"WR{i}"
                sep = 2.0 + 0.08 * i
                catch = 55.0 + 5.0 * sep + 0.2 * week
                rows.append(
                    {
                        "season": season,
                        "season_type": "REG",
                        "week": week,
                        "player_gsis_id": pid,
                        "targets": 6 + (i % 5),
                        "catch_percentage": catch,
                        "avg_air_distance": 10.0 + 0.2 * i,
                        "avg_cushion": 5.0 + 0.05 * i,
                        "avg_separation": sep,
                        "percent_share_of_intended_air_yards": 15.0 + i,
                        "avg_yac": 4.0 + 0.1 * i,
                        "avg_expected_yac": 3.8 + 0.08 * i,
                        "avg_yac_above_expectation": 0.2 + 0.02 * i,
                    }
                )
    return pd.DataFrame(rows)


def _rushing():
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for week in range(1, 7):
            for i in range(10):
                pid = f"RB{i}"
                ryoe = -0.5 + 0.2 * i
                ypc = 4.0 + 0.75 * ryoe + 0.03 * week
                rows.append(
                    {
                        "season": season,
                        "season_type": "REG",
                        "week": week,
                        "player_gsis_id": pid,
                        "rush_attempts": 10 + i,
                        "avg_rush_yards": ypc,
                        "rush_yards_over_expected_per_att": ryoe,
                        "rush_pct_over_expected": 35.0 + 2.0 * i,
                        "percent_attempts_gte_eight_defenders": 25.0 + i,
                        "avg_time_to_los": 2.8 - 0.02 * i,
                        "efficiency": 3.5 - 0.05 * i,
                    }
                )
    return pd.DataFrame(rows)


def test_learning_table_is_strictly_lagged_and_excludes_2026():
    passing = _passing()
    future = passing.iloc[[0]].copy()
    future["season"] = 2026
    passing = pd.concat([passing, future], ignore_index=True)

    table, audit = build_efficiency_learning_table(
        passing=passing,
        receiving=_receiving(),
        rushing=_rushing(),
        season_start=2022,
        season_end=2026,
    )
    assert not table.empty
    assert table["season"].max() == 2025
    assert audit["completed_2026_outcomes_used"] == 0
    assert audit["target_week_state_rows_used"] == 0
    # Week 1 of the first season has no same-week state leakage and therefore may
    # lack a row; later weeks must exist.
    assert (table["week"] >= 2).any()


def test_ridge_model_learns_incremental_efficiency_signal():
    table, _ = build_efficiency_learning_table(
        passing=_passing(),
        receiving=_receiving(),
        rushing=_rushing(),
        season_start=2022,
        season_end=2025,
    )
    train = table[(table["metric"].eq("rushing_ypc")) & (table["season"].lt(2025))]
    test = table[(table["metric"].eq("rushing_ypc")) & (table["season"].eq(2025))].copy()
    model = fit_metric_model(train, "rushing_ypc")
    test["prediction"] = predict_metric(test, model)
    baseline_mae = np.mean(np.abs(test["baseline"] - test["target"]))
    model_mae = np.mean(np.abs(test["prediction"] - test["target"]))
    assert model.training_season_max == 2024
    assert model_mae <= baseline_mae


def test_rolling_origin_never_trains_on_evaluation_season():
    table, _ = build_efficiency_learning_table(
        passing=_passing(),
        receiving=_receiving(),
        rushing=_rushing(),
        season_start=2022,
        season_end=2025,
    )
    result = evaluate_rolling_origin(table, evaluation_seasons=(2024, 2025))
    for season in ("2024", "2025"):
        for metric, payload in result["evaluation"][season].items():
            if payload["status"] != "evaluated":
                continue
            assert payload["model"]["training_season_max"] < int(season)
            assert payload["metrics"]["n"] > 0
    assert result["hyperparameter_tuning_performed"] is False
    assert result["completed_2026_outcomes_used"] == 0

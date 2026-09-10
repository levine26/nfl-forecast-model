from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_forecast.challenger_evaluation import (
    calibration_diagnostics,
    compare_forecasts,
    confidence_set_approximation,
    paired_bootstrap,
    paired_loss_difference_test,
    standard_slices,
)


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for week in range(1, 18):
            for game in range(4):
                y = int(rng.random() < 0.55)
                good = 0.82 if y else 0.18
                reference = 0.58 if y else 0.42
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "home_win": y,
                        "candidate": good,
                        "reference": reference,
                        "bad": 1.0 - good,
                        "market_prob": 0.60 if game % 2 == 0 else 0.40,
                        "home_qb_starter_changed": float(game == 0),
                        "away_qb_starter_changed": 0.0,
                    }
                )
    return pd.DataFrame(rows)


def test_paired_bootstrap_detects_clear_candidate_edge():
    frame = _frame()
    brier = paired_bootstrap(
        frame,
        "candidate",
        "reference",
        metric="brier",
        block_cols=("season", "week"),
        samples=300,
        seed=11,
    )
    assert brier.observed_delta < 0
    assert brier.ci_upper < 0
    assert brier.probability_better > 0.99

    accuracy = paired_bootstrap(
        frame,
        "candidate",
        "reference",
        metric="accuracy",
        samples=300,
        seed=11,
    )
    assert accuracy.observed_delta >= 0
    assert accuracy.ci_lower >= 0


def test_calibration_and_standard_slices_are_reported():
    frame = _frame()
    summary, bins = calibration_diagnostics(frame, "candidate")
    assert summary["games"] == len(frame)
    assert np.isfinite(summary["calibration_intercept"])
    assert np.isfinite(summary["calibration_slope"])
    assert bins.games.sum() == len(frame)

    slices = standard_slices(frame, "candidate", "reference")
    families = set(slices.slice_family)
    assert {"season", "season_phase", "market_side", "market_disagreement", "qb_change"}.issubset(families)


def test_paired_loss_test_and_full_comparison():
    frame = _frame()
    test = paired_loss_difference_test(frame, "candidate", "reference", loss="brier")
    assert test.mean_loss_delta < 0
    assert test.blocks == 4 * 17
    assert test.p_value_two_sided < 0.05

    result = compare_forecasts(frame, "candidate", "reference", bootstrap_samples=200, seed=4)
    assert result["metric_deltas"]["brier"] < 0
    assert set(result["bootstrap"].metric) == {"accuracy", "brier", "log_loss"}
    assert {"row", "season+week", "season"}.issubset(set(result["bootstrap"].block))
    assert len(result["paired_tests"]) == 3


def test_confidence_set_excludes_clearly_worse_model():
    frame = _frame()
    result = confidence_set_approximation(
        frame,
        ["candidate", "reference", "bad"],
        bootstrap_samples=300,
        seed=8,
    )
    membership = result.set_index("model").in_confidence_set.to_dict()
    assert membership["candidate"]
    assert not membership["bad"]

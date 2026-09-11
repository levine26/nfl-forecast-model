from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_margin_forensics import (
    bootstrap_large_gap_error_delta,
    current_large_gap_probes,
    summarize_margin_disagreements,
    walk_forward_margin_predictions,
)


def test_margin_forensics_refuse_2026_outcomes_before_fit() -> None:
    frame = pd.DataFrame(
        [
            {"season": 2025, "margin": 3.0, "spread_line": 2.0, "x": 1.0},
            {"season": 2026, "margin": -7.0, "spread_line": -2.0, "x": 2.0},
        ]
    )
    with pytest.raises(ValueError, match="2026"):
        walk_forward_margin_predictions(frame, ["x"])


def test_margin_bucket_summary_measures_model_vs_market_error() -> None:
    frame = pd.DataFrame(
        [
            {
                "gap_bucket": "6-8",
                "model_abs_error": 2.0,
                "market_abs_error": 6.0,
                "model_closer": True,
                "model_side_hit": True,
                "abs_model_market_gap": 7.0,
                "model_minus_market_abs_error": -4.0,
            },
            {
                "gap_bucket": "6-8",
                "model_abs_error": 10.0,
                "market_abs_error": 3.0,
                "model_closer": False,
                "model_side_hit": False,
                "abs_model_market_gap": 7.5,
                "model_minus_market_abs_error": 7.0,
            },
        ]
    )
    summary = summarize_margin_disagreements(frame)
    row = summary[summary.gap_bucket_points.eq("6-8")].iloc[0]
    assert row.games == 2
    assert row.model_closer_rate == pytest.approx(0.5)
    assert row.model_side_ats_hit_rate == pytest.approx(0.5)
    assert row.model_margin_mae == pytest.approx(6.0)
    assert row.market_spread_mae == pytest.approx(4.5)


def test_large_gap_bootstrap_reports_negative_delta_when_model_always_closer() -> None:
    rows = []
    for season in (2022, 2023):
        for week in (1, 2, 3):
            rows.append(
                {
                    "season": season,
                    "week": week,
                    "abs_model_market_gap": 7.0,
                    "model_minus_market_abs_error": -2.0,
                }
            )
    result = bootstrap_large_gap_error_delta(pd.DataFrame(rows), samples=200, seed=1)
    assert result.games == 6
    assert result.observed_model_minus_market_mae == pytest.approx(-2.0)
    assert result.probability_model_better == pytest.approx(1.0)
    assert result.ci_upper < 0


def test_current_large_gap_probe_is_ungraded_and_thresholded() -> None:
    slate = pd.DataFrame(
        [
            {
                "game_id": "2026_01_DEN_KC",
                "away_team": "DEN",
                "home_team": "KC",
                "expected_margin": -5.35,
                "spread_line": 2.5,
                "final_home_prob": 0.605,
                "market_home_prob": 0.572,
                "fst_pure_home_prob": 0.316,
            },
            {
                "game_id": "small",
                "away_team": "A",
                "home_team": "H",
                "expected_margin": 2.0,
                "spread_line": 1.0,
            },
        ]
    )
    probes = current_large_gap_probes(slate, minimum_gap_points=6.0)
    assert list(probes.game_id) == ["2026_01_DEN_KC"]
    assert probes.iloc[0].model_market_gap == pytest.approx(-7.85)
    assert bool(probes.iloc[0].research_only)
    assert not bool(probes.iloc[0].graded)

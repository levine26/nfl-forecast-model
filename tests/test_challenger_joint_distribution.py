from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_joint_distribution import (
    bivariate_normal_nll,
    blocked_continuous_bootstrap,
    season_forward_joint_distribution,
    summarize_joint_distribution,
)


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(26)
    rows = []
    game = 0
    for season, count in ((2020, 180), (2021, 180), (2022, 64)):
        for week in range(1, count + 1):
            x1 = rng.normal()
            x2 = rng.normal()
            spread = rng.normal(0.0, 5.0)
            total_line = 44.0 + rng.normal(0.0, 3.0)
            margin = spread + 0.8 * x1 - 0.4 * x2 + rng.normal(0.0, 10.0)
            game_total = total_line + 0.5 * x2 + rng.normal(0.0, 9.0)
            home_score = (game_total + margin) / 2.0
            away_score = (game_total - margin) / 2.0
            market_prob = 1.0 / (1.0 + np.exp(-spread / 13.0))
            rows.append(
                {
                    "game_id": f"g{game}",
                    "season": season,
                    "week": (week - 1) % 18 + 1,
                    "home_win": float(margin > 0),
                    "home_score": home_score,
                    "away_score": away_score,
                    "margin": margin,
                    "game_total": game_total,
                    "spread_line": spread,
                    "total_line": total_line,
                    "market_home_prob": market_prob,
                    "x1": x1,
                    "x2": x2,
                }
            )
            game += 1
    return pd.DataFrame(rows)


def test_joint_distribution_is_algebraically_coherent_and_capped() -> None:
    predictions, diagnostics = season_forward_joint_distribution(
        _frame(), ["x1", "x2"], target_seasons=(2022,)
    )
    assert len(predictions) == 64
    assert len(diagnostics) == 1
    assert predictions.margin_correction.abs().max() <= 3.0 + 1e-12
    assert predictions.total_correction.abs().max() <= 4.0 + 1e-12
    assert predictions.score_margin_identity_error.max() < 1e-10
    assert predictions.score_total_identity_error.max() < 1e-10
    assert predictions.probability_identity_error.max() < 1e-12
    summary = summarize_joint_distribution(predictions)
    assert summary["coherence_failures"] == 0
    assert "candidate_joint_nll" in summary
    assert "candidate_home_score_mae" in summary


def test_bivariate_nll_is_finite_and_prefers_exact_mean() -> None:
    margin = np.array([3.0, -1.0, 7.0])
    total = np.array([44.0, 50.0, 41.0])
    exact = bivariate_normal_nll(margin, total, margin, total, 10.0, 9.0, 0.2)
    shifted = bivariate_normal_nll(margin, total, margin + 5.0, total + 5.0, 10.0, 9.0, 0.2)
    assert np.isfinite(exact).all()
    assert exact.mean() < shifted.mean()


def test_continuous_bootstrap_preserves_week_blocks() -> None:
    predictions, _ = season_forward_joint_distribution(
        _frame(), ["x1", "x2"], target_seasons=(2022,)
    )
    result = blocked_continuous_bootstrap(
        predictions,
        "candidate_margin_abs_error",
        "market_margin_abs_error",
        metric="margin_mae",
        samples=100,
        seed=99,
    )
    assert result.games == 64
    assert result.blocks == predictions[["season", "week"]].drop_duplicates().shape[0]
    assert 0.0 <= result.probability_better <= 1.0


def test_phase3_refuses_2026_outcomes() -> None:
    frame = _frame()
    bad = frame.iloc[[0]].copy()
    bad["season"] = 2026
    combined = pd.concat([frame, bad], ignore_index=True)
    with pytest.raises(ValueError, match="refuses 2026"):
        season_forward_joint_distribution(combined, ["x1", "x2"], target_seasons=(2022,))

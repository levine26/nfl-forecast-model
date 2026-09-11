from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from nfl_forecast.challenger_probability_margin_bridge import (
    blocked_margin_bootstrap,
    chronological_probability_margin_bridge,
    margin_metrics,
    six_plus_disagreement_slice,
)


def _games() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    game = 0
    for season, count in ((2020, 180), (2021, 180), (2022, 72)):
        for i in range(count):
            spread = rng.normal(0, 5)
            margin = spread + rng.normal(0, 12)
            rows.append({
                "game_id": f"g{game}",
                "season": season,
                "week": i % 18 + 1,
                "margin": margin,
                "spread_line": spread,
            })
            game += 1
    return pd.DataFrame(rows)


def _probabilities(games: pd.DataFrame) -> pd.DataFrame:
    target = games[games.season.eq(2022)].copy()
    p = norm.cdf(target.spread_line.to_numpy(float) / 12.0)
    return pd.DataFrame({
        "game_id": target.game_id,
        "season": target.season,
        "market_prob": p,
        "market_plus_pure_prob": np.clip(p + 0.01, 1e-4, 1 - 1e-4),
    })


def test_bridge_uses_only_prior_season_sigma() -> None:
    games = _games()
    predictions, diagnostics = chronological_probability_margin_bridge(
        games, _probabilities(games), target_seasons=(2022,)
    )
    expected = np.std(
        (games.loc[games.season.lt(2022), "margin"] - games.loc[games.season.lt(2022), "spread_line"]).to_numpy(),
        ddof=1,
    )
    assert diagnostics.iloc[0].sigma_margin == pytest.approx(expected)
    expected_margin = expected * norm.ppf(predictions.market_prob.to_numpy())
    assert np.allclose(predictions.market_prob_bridge_margin, expected_margin)


def test_metrics_and_block_bootstrap_are_paired() -> None:
    games = _games()
    predictions, _ = chronological_probability_margin_bridge(
        games, _probabilities(games), target_seasons=(2022,)
    )
    metrics = margin_metrics(predictions, "market_prob_bridge_margin")
    assert metrics["games"] == 72
    result = blocked_margin_bootstrap(
        predictions,
        "market_prob_bridge_margin",
        "spread_line",
        samples=100,
        seed=4,
    )
    assert result.games == 72
    assert result.blocks == 18
    assert 0 <= result.probability_better <= 1


def test_large_disagreement_slice_is_descriptive_only() -> None:
    games = _games()
    probabilities = _probabilities(games)
    probabilities["market_plus_pure_prob"] = np.clip(probabilities.market_prob + 0.25, 1e-4, 1 - 1e-4)
    predictions, _ = chronological_probability_margin_bridge(
        games, probabilities, target_seasons=(2022,)
    )
    result = six_plus_disagreement_slice(predictions, "market_plus_pure_prob_bridge_margin")
    assert result["games"] > 0
    assert "bridge_minus_market_mae" in result


def test_bridge_refuses_2026_outcomes() -> None:
    games = _games()
    bad = games.iloc[[0]].copy()
    bad["season"] = 2026
    with pytest.raises(ValueError, match="refuses 2026"):
        chronological_probability_margin_bridge(
            pd.concat([games, bad], ignore_index=True),
            _probabilities(games),
            target_seasons=(2022,),
        )

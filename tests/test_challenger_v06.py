import numpy as np
import pandas as pd

from nfl_forecast.challenger_v06 import (
    HYBRID_PURE_WEIGHTS,
    _select_logit_weight,
    agreement_regime,
    fit_current_market_confidence_weights,
    logit_blend_probabilities,
    market_confidence_bucket,
    nested_agreement_backtest,
    nested_logit_hybrid_backtest,
    nested_market_confidence_backtest,
)


def _season_frame(seasons=(2020, 2021, 2022), n=180):
    rows = []
    for season in seasons:
        for i in range(n):
            y = i % 2
            # Market is directionally excellent. PURE contains useful but weaker signal.
            market = 0.74 if y else 0.26
            pure = 0.62 if y else 0.38
            rows.append({
                "season": season,
                "home_win": y,
                "pure_prob": pure,
                "market_prob": market,
            })
    return pd.DataFrame(rows)


def test_logit_blend_respects_endpoints_and_hybrid_floor():
    pure = np.array([0.70, 0.30])
    market = np.array([0.60, 0.40])
    assert np.allclose(logit_blend_probabilities(pure, market, 1.0), pure)
    assert np.allclose(logit_blend_probabilities(pure, market, 0.0), market)
    p = logit_blend_probabilities(pure, market, min(HYBRID_PURE_WEIGHTS))
    assert np.all((p > 0) & (p < 1))


def test_logit_weight_search_never_drops_below_25_percent_pure():
    frame = _season_frame(seasons=(2020,), n=180)
    weight, sweep = _select_logit_weight(frame, objective="brier")
    assert weight >= 0.25
    assert sweep.pure_weight.min() >= 0.25


def test_nested_logit_hybrid_is_prior_season_only():
    frame = _season_frame()
    result = nested_logit_hybrid_backtest(
        frame,
        target_seasons=[2022],
        objective="brier",
        calibrator="none",
    )
    assert len(result.predictions) == 180
    assert len(result.weights) == 1
    assert float(result.weights.iloc[0].pure_weight) >= 0.25
    assert np.isfinite(result.metrics["brier"])


def test_market_confidence_buckets_are_stable():
    buckets = market_confidence_bucket([0.50, 0.57, 0.60, 0.67, 0.80])
    assert buckets.tolist() == ["close", "close", "moderate", "moderate", "strong"]


def test_market_confidence_hybrid_preserves_pure_floor():
    frame = _season_frame()
    # Create all three confidence regimes while keeping direction correct.
    for i in frame.index:
        y = int(frame.at[i, "home_win"])
        mode = i % 3
        strength = [0.55, 0.64, 0.78][mode]
        frame.at[i, "market_prob"] = strength if y else 1.0 - strength
    result = nested_market_confidence_backtest(frame, target_seasons=[2022])
    assert result.predictions.pure_weight.min() >= 0.25
    current = frame[frame.season.eq(2022)].head(12)[["pure_prob", "market_prob"]].copy()
    p, weights = fit_current_market_confidence_weights(
        frame[frame.season.lt(2022)], current
    )
    assert len(p) == len(current)
    assert weights.min() >= 0.25


def test_agreement_regime_and_nested_backtest():
    frame = _season_frame()
    # Force a meaningful disagreement subset without using future outcomes in tuning.
    mask = frame.index % 4 == 0
    frame.loc[mask, "pure_prob"] = 1.0 - frame.loc[mask, "pure_prob"]
    regimes = agreement_regime(frame.head(8))
    assert set(regimes).issubset({"agree", "disagree"})
    result = nested_agreement_backtest(frame, target_seasons=[2022])
    assert result.predictions.pure_weight.min() >= 0.25
    assert set(result.predictions.regime.unique()).issubset({"agree", "disagree"})

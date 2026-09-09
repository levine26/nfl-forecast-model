import numpy as np
import pandas as pd

from nfl_forecast.challenger import (
    blend_probabilities,
    choose_shadow_candidate,
    fit_calibrator,
    nested_blend_backtest,
    score_probabilities,
    select_pure_weight,
)


def test_blend_falls_back_to_pure_when_market_is_missing():
    pure = np.array([0.60, 0.40, 0.72])
    market = np.array([0.50, np.nan, 0.64])
    out = blend_probabilities(pure, market, 0.75)
    assert np.isclose(out[0], 0.575)
    assert np.isclose(out[1], 0.40)
    assert np.isclose(out[2], 0.70)


def test_market_weight_selection_can_beat_fixed_75_25():
    n = 120
    y = np.array(([1] * 60) + ([0] * 60))
    frame = pd.DataFrame({
        "home_win": y,
        "pure_prob": np.where(y == 1, 0.40, 0.60),
        "market_prob": np.where(y == 1, 0.80, 0.20),
    })
    weight, sweep = select_pure_weight(frame, objective="accuracy")
    assert weight < 0.50
    chosen = sweep.loc[np.isclose(sweep.pure_weight, weight)].iloc[0]
    fixed = sweep.loc[np.isclose(sweep.pure_weight, 0.75)].iloc[0]
    assert chosen.winner_pct > fixed.winner_pct


def test_nested_blend_uses_only_prior_seasons_for_weight_selection():
    rows = []
    # 2020-21 say market is excellent, so the 2022 weight should favor market.
    for season in [2020, 2021]:
        for i in range(120):
            y = i % 2
            rows.append({
                "season": season,
                "home_win": y,
                "pure_prob": 0.35 if y else 0.65,
                "market_prob": 0.80 if y else 0.20,
            })
    # 2022 reverses the relationship. A leaking tuner would suddenly favor PURE.
    for i in range(120):
        y = i % 2
        rows.append({
            "season": 2022,
            "home_win": y,
            "pure_prob": 0.80 if y else 0.20,
            "market_prob": 0.35 if y else 0.65,
        })
    frame = pd.DataFrame(rows)
    result = nested_blend_backtest(
        frame,
        target_seasons=[2022],
        weight_objective="accuracy",
        calibrator="none",
    )
    assert len(result.weights) == 1
    assert float(result.weights.iloc[0].pure_weight) < 0.50


def test_platt_calibrator_returns_valid_probabilities():
    p = np.linspace(0.05, 0.95, 400)
    y = (p + np.sin(np.arange(400)) * 0.05 >= 0.5).astype(int)
    calibrator = fit_calibrator(y, p, mode="platt")
    out = calibrator.predict([0.10, 0.50, 0.90])
    assert np.all(out > 0)
    assert np.all(out < 1)
    assert out[0] < out[1] < out[2]


def test_shadow_candidate_prioritizes_accuracy_with_probability_guardrail():
    metrics = pd.DataFrame([
        {"candidate": "prod", "winner_pct": 0.650, "brier": 0.220, "log_loss": 0.630},
        {"candidate": "better", "winner_pct": 0.665, "brier": 0.219, "log_loss": 0.628},
        # Higher accuracy, but probability quality is too degraded to be eligible.
        {"candidate": "reckless", "winner_pct": 0.680, "brier": 0.235, "log_loss": 0.650},
    ])
    chosen = choose_shadow_candidate(metrics, "prod")
    assert chosen.candidate == "better"


def test_score_probabilities_matches_simple_accuracy():
    metrics = score_probabilities([1, 0, 1, 0], [0.8, 0.2, 0.4, 0.6])
    assert metrics["games"] == 4
    assert np.isclose(metrics["winner_pct"], 0.5)

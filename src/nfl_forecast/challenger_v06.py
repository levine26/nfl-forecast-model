from __future__ import annotations

"""Additional leakage-safe LevLine challenger methods.

These candidates remain research-only. They all preserve an explicit football-model
component and are evaluated with season-forward tuning. Production forecasting code
never imports this module.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .challenger import (
    BlendBacktestResult,
    fit_calibrator,
    score_probabilities,
    select_pure_weight,
)

EPS = 1e-6
HYBRID_PURE_WEIGHTS = tuple(float(x) for x in np.linspace(0.25, 1.0, 16))


def _clip(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values: Iterable[float]) -> np.ndarray:
    p = _clip(values)
    return np.log(p / (1.0 - p))


def _sigmoid(values: Iterable[float]) -> np.ndarray:
    z = np.asarray(values, dtype=float)
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def logit_blend_probabilities(
    pure_probability: Iterable[float],
    market_probability: Iterable[float],
    pure_weight: float,
) -> np.ndarray:
    """Blend PURE and market in log-odds space.

    Missing market values fall back to PURE. The weight is constrained by the caller;
    challenger research uses a minimum 25% PURE football contribution.
    """
    weight = float(pure_weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError("pure_weight must be between 0 and 1")
    pure = np.asarray(pure_probability, dtype=float)
    market = np.asarray(market_probability, dtype=float)
    if pure.shape != market.shape:
        raise ValueError("PURE and market arrays must have the same shape")
    out = _clip(pure)
    usable = np.isfinite(pure) & np.isfinite(market)
    if usable.any():
        blended_logit = weight * _logit(pure[usable]) + (1.0 - weight) * _logit(market[usable])
        out[usable] = _sigmoid(blended_logit)
    return _clip(out)


def _select_logit_weight(
    frame: pd.DataFrame,
    *,
    objective: str = "brier",
    weights: Iterable[float] = HYBRID_PURE_WEIGHTS,
) -> tuple[float, pd.DataFrame]:
    if objective not in {"brier", "accuracy"}:
        raise ValueError("objective must be 'brier' or 'accuracy'")
    usable = frame[
        frame.home_win.notna() & frame.pure_prob.notna() & frame.market_prob.notna()
    ].copy()
    if len(usable) < 100:
        raise ValueError(f"Need at least 100 market-covered games; found {len(usable)}")
    rows = []
    for weight in weights:
        p = logit_blend_probabilities(usable.pure_prob, usable.market_prob, weight)
        rows.append({
            "pure_weight": float(weight),
            "market_weight": 1.0 - float(weight),
            **score_probabilities(usable.home_win, p),
        })
    sweep = pd.DataFrame(rows)
    if objective == "brier":
        ranked = sweep.sort_values(
            ["brier", "log_loss", "winner_pct", "pure_weight"],
            ascending=[True, True, False, True],
        )
    else:
        ranked = sweep.sort_values(
            ["winner_pct", "brier", "log_loss", "pure_weight"],
            ascending=[False, True, True, True],
        )
    return float(ranked.iloc[0].pure_weight), sweep


def nested_logit_hybrid_backtest(
    frame: pd.DataFrame,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    objective: str = "brier",
    calibrator: str = "none",
) -> BlendBacktestResult:
    """Tune a log-odds hybrid on seasons before S, then score S."""
    prediction_parts = []
    weight_rows = []
    for test_season in [int(x) for x in target_seasons]:
        tune = frame[frame.season < test_season].copy()
        test = frame[frame.season == test_season].copy()
        if test.empty:
            continue
        weight, _ = _select_logit_weight(tune, objective=objective)
        tune_raw = logit_blend_probabilities(tune.pure_prob, tune.market_prob, weight)
        calibration = fit_calibrator(tune.home_win, tune_raw, mode=calibrator)
        test_raw = logit_blend_probabilities(test.pure_prob, test.market_prob, weight)
        part = test[["season", "home_win", "pure_prob", "market_prob"]].copy()
        part["raw_prob"] = test_raw
        part["probability"] = calibration.predict(test_raw)
        part["pure_weight"] = weight
        part["market_weight"] = 1.0 - weight
        part["calibrator"] = calibrator
        prediction_parts.append(part)
        weight_rows.append({
            "season": test_season,
            "pure_weight": weight,
            "market_weight": 1.0 - weight,
            "objective": objective,
            "calibrator": calibrator,
            **score_probabilities(part.home_win, part.probability),
        })
    if not prediction_parts:
        raise ValueError("No target-season logit-blend predictions generated")
    predictions = pd.concat(prediction_parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(weight_rows),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def market_confidence_bucket(probability: Iterable[float]) -> np.ndarray:
    """Three stable pregame market-confidence regimes."""
    p = np.asarray(probability, dtype=float)
    distance = np.abs(p - 0.5)
    return np.where(distance < 0.08, "close", np.where(distance < 0.18, "moderate", "strong"))


def _conditional_weights(
    tune: pd.DataFrame,
    *,
    regime_col: str,
    objective: str = "brier",
    min_games: int = 100,
) -> dict[str, float]:
    global_weight, _ = select_pure_weight(
        tune,
        objective=objective,
        weights=HYBRID_PURE_WEIGHTS,
    )
    weights = {"__global__": global_weight}
    for regime, group in tune.groupby(regime_col, observed=True):
        usable = group[
            group.home_win.notna() & group.pure_prob.notna() & group.market_prob.notna()
        ]
        if len(usable) < min_games:
            weights[str(regime)] = global_weight
            continue
        weight, _ = select_pure_weight(
            usable,
            objective=objective,
            weights=HYBRID_PURE_WEIGHTS,
        )
        weights[str(regime)] = weight
    return weights


def _apply_conditional_linear_blend(
    frame: pd.DataFrame,
    *,
    regime_col: str,
    weights: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    pure = frame.pure_prob.to_numpy(dtype=float)
    market = frame.market_prob.to_numpy(dtype=float)
    regimes = frame[regime_col].astype(str).to_numpy()
    effective = np.array([weights.get(r, weights["__global__"]) for r in regimes], dtype=float)
    probability = pure.copy()
    usable = np.isfinite(pure) & np.isfinite(market)
    probability[usable] = (
        effective[usable] * pure[usable] + (1.0 - effective[usable]) * market[usable]
    )
    return _clip(probability), effective


def nested_market_confidence_backtest(
    frame: pd.DataFrame,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    objective: str = "brier",
) -> BlendBacktestResult:
    """Use different prior-tuned hybrid weights for close/moderate/strong markets."""
    prediction_parts = []
    weight_rows = []
    work = frame.copy()
    work["regime"] = market_confidence_bucket(work.market_prob)
    for test_season in [int(x) for x in target_seasons]:
        tune = work[work.season < test_season].copy()
        test = work[work.season == test_season].copy()
        if test.empty:
            continue
        weights = _conditional_weights(tune, regime_col="regime", objective=objective)
        probability, effective = _apply_conditional_linear_blend(
            test, regime_col="regime", weights=weights
        )
        part = test[["season", "home_win", "pure_prob", "market_prob", "regime"]].copy()
        part["probability"] = probability
        part["pure_weight"] = effective
        part["market_weight"] = 1.0 - effective
        prediction_parts.append(part)
        for regime in ["close", "moderate", "strong"]:
            weight_rows.append({
                "season": test_season,
                "regime": regime,
                "pure_weight": weights.get(regime, weights["__global__"]),
                "market_weight": 1.0 - weights.get(regime, weights["__global__"]),
                "objective": objective,
            })
    if not prediction_parts:
        raise ValueError("No market-confidence predictions generated")
    predictions = pd.concat(prediction_parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(weight_rows),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def agreement_regime(frame: pd.DataFrame) -> np.ndarray:
    pure_side = np.asarray(frame.pure_prob, dtype=float) >= 0.5
    market_side = np.asarray(frame.market_prob, dtype=float) >= 0.5
    return np.where(pure_side == market_side, "agree", "disagree")


def nested_agreement_backtest(
    frame: pd.DataFrame,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    objective: str = "brier",
) -> BlendBacktestResult:
    """Tune separate hybrid weights when PURE agrees/disagrees with the market."""
    prediction_parts = []
    weight_rows = []
    work = frame.copy()
    work["regime"] = agreement_regime(work)
    for test_season in [int(x) for x in target_seasons]:
        tune = work[work.season < test_season].copy()
        test = work[work.season == test_season].copy()
        if test.empty:
            continue
        weights = _conditional_weights(tune, regime_col="regime", objective=objective)
        probability, effective = _apply_conditional_linear_blend(
            test, regime_col="regime", weights=weights
        )
        part = test[["season", "home_win", "pure_prob", "market_prob", "regime"]].copy()
        part["probability"] = probability
        part["pure_weight"] = effective
        part["market_weight"] = 1.0 - effective
        prediction_parts.append(part)
        for regime in ["agree", "disagree"]:
            weight_rows.append({
                "season": test_season,
                "regime": regime,
                "pure_weight": weights.get(regime, weights["__global__"]),
                "market_weight": 1.0 - weights.get(regime, weights["__global__"]),
                "objective": objective,
            })
    if not prediction_parts:
        raise ValueError("No agreement-regime predictions generated")
    predictions = pd.concat(prediction_parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(weight_rows),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def fit_current_market_confidence_weights(
    historical_research: pd.DataFrame,
    current_frame: pd.DataFrame,
    *,
    objective: str = "brier",
) -> tuple[np.ndarray, np.ndarray]:
    work = historical_research.copy()
    work["regime"] = market_confidence_bucket(work.market_prob)
    weights = _conditional_weights(work, regime_col="regime", objective=objective)
    current = current_frame.copy()
    current["regime"] = market_confidence_bucket(current.market_prob)
    return _apply_conditional_linear_blend(current, regime_col="regime", weights=weights)


def fit_current_agreement_weights(
    historical_research: pd.DataFrame,
    current_frame: pd.DataFrame,
    *,
    objective: str = "brier",
) -> tuple[np.ndarray, np.ndarray]:
    work = historical_research.copy()
    work["regime"] = agreement_regime(work)
    weights = _conditional_weights(work, regime_col="regime", objective=objective)
    current = current_frame.copy()
    current["regime"] = agreement_regime(current)
    return _apply_conditional_linear_blend(current, regime_col="regime", weights=weights)

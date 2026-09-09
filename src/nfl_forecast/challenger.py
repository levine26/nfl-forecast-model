from __future__ import annotations

"""Leakage-safe challenger research utilities.

This module is intentionally isolated from the production forecasting path.  It
exists to test possible LevLine upgrades using only pre-live-season information.
Nothing here changes the published 75% PURE / 25% MARKET contract.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline

from .models import _win_models

EPS = 1e-6
DEFAULT_PURE_WEIGHTS = tuple(float(x) for x in np.linspace(0.0, 1.0, 21))
BASE_MODEL_NAMES = ("logistic", "extra_trees", "xgboost", "catboost")


@dataclass
class NestedStackResult:
    base_oof: pd.DataFrame
    target_oof: pd.DataFrame


@dataclass
class BlendBacktestResult:
    predictions: pd.DataFrame
    weights: pd.DataFrame
    metrics: dict[str, float]


@dataclass
class ProbabilityCalibrator:
    mode: str
    model: object | None = None

    def predict(self, probability: Iterable[float]) -> np.ndarray:
        p = _clip(probability)
        if self.mode == "none" or self.model is None:
            return p
        if self.mode == "platt":
            x = _logit(p).reshape(-1, 1)
            return _clip(self.model.predict_proba(x)[:, 1])
        if self.mode == "isotonic":
            return _clip(self.model.predict(p))
        raise ValueError(f"Unknown calibrator mode: {self.mode}")


def _clip(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values: Iterable[float]) -> np.ndarray:
    p = _clip(values)
    return np.log(p / (1.0 - p))


def blend_probabilities(
    pure_probability: Iterable[float],
    market_probability: Iterable[float],
    pure_weight: float,
) -> np.ndarray:
    """Blend PURE and market probabilities, falling back to PURE if market is absent."""
    weight = float(pure_weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError("pure_weight must be between 0 and 1")
    pure = np.asarray(pure_probability, dtype=float)
    market = np.asarray(market_probability, dtype=float)
    if pure.shape != market.shape:
        raise ValueError("PURE and market arrays must have the same shape")
    out = pure.copy()
    usable = np.isfinite(pure) & np.isfinite(market)
    out[usable] = weight * pure[usable] + (1.0 - weight) * market[usable]
    return _clip(out)


def score_probabilities(target: Iterable[float], probability: Iterable[float]) -> dict[str, float]:
    y = np.asarray(target, dtype=float)
    p = np.asarray(probability, dtype=float)
    usable = np.isfinite(y) & np.isfinite(p)
    y = y[usable].astype(int)
    p = _clip(p[usable])
    if not len(y):
        return {"games": 0, "winner_pct": np.nan, "brier": np.nan, "log_loss": np.nan}
    pick = (p >= 0.5).astype(int)
    return {
        "games": int(len(y)),
        "winner_pct": float((pick == y).mean()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
    }


def _meta_template(seed: int) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", LogisticRegression(C=0.5, max_iter=3000, random_state=seed)),
    ])


def build_base_oof_predictions(
    df: pd.DataFrame,
    feature_cols: list[str],
    *,
    target: str = "home_win",
    season_col: str = "season",
    seed: int = 26,
    validation_start: int = 2018,
    validation_end: int = 2025,
) -> pd.DataFrame:
    """Generate season-forward base-model OOF predictions without a meta-model.

    Every row for season S is produced by a base model trained exclusively on
    seasons < S.  These rows can then be used to train a second-level model on
    *earlier* OOF seasons, avoiding the subtle meta-level in-sample evaluation
    that occurs when a stacker is fitted and scored on the same OOF matrix.
    """
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    templates = _win_models(seed)
    parts: list[pd.DataFrame] = []
    for test_season in seasons:
        if test_season < validation_start or test_season > validation_end:
            continue
        tr = train[train[season_col] < test_season]
        va = train[train[season_col] == test_season]
        if len(tr) < 100 or va.empty:
            continue
        part = pd.DataFrame(index=va.index)
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target].astype(int))
            part[name] = model.predict_proba(va[feature_cols])[:, 1]
        part[target] = va[target].astype(int)
        part[season_col] = test_season
        parts.append(part)
    if not parts:
        raise ValueError("No valid base-model OOF seasons were generated")
    return pd.concat(parts).sort_index()


def build_nested_stack_oof(
    base_oof: pd.DataFrame,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    target: str = "home_win",
    season_col: str = "season",
    seed: int = 26,
    min_meta_games: int = 300,
) -> NestedStackResult:
    """Create fully nested PURE probabilities for held-out target seasons."""
    parts: list[pd.DataFrame] = []
    for test_season in [int(x) for x in target_seasons]:
        meta_train = base_oof[base_oof[season_col] < test_season]
        test = base_oof[base_oof[season_col] == test_season]
        if test.empty:
            continue
        if len(meta_train) < min_meta_games or meta_train[target].nunique() < 2:
            raise ValueError(
                f"Insufficient pre-{test_season} meta training sample: {len(meta_train)}"
            )
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train[target].astype(int))
        part = test[[target, season_col]].copy()
        part["pure_prob"] = meta.predict_proba(test[list(BASE_MODEL_NAMES)])[:, 1]
        parts.append(part)
    if not parts:
        raise ValueError("No nested target seasons were generated")
    return NestedStackResult(base_oof=base_oof, target_oof=pd.concat(parts).sort_index())


def fit_future_nested_stack(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: list[str],
    *,
    target: str = "home_win",
    seed: int = 26,
) -> np.ndarray:
    """Fit the leakage-safe stack for a future/live season.

    Base models see all completed pre-live-season games.  The meta-model sees
    only base OOF predictions, never in-sample base predictions.
    """
    if base_oof[target].nunique() < 2:
        raise ValueError("Meta training target has fewer than two classes")
    meta = _meta_template(seed)
    meta.fit(base_oof[list(BASE_MODEL_NAMES)], base_oof[target].astype(int))

    base_current = pd.DataFrame(index=current.index)
    for name, template in _win_models(seed).items():
        model = clone(template)
        model.fit(historical[feature_cols], historical[target].astype(int))
        base_current[name] = model.predict_proba(current[feature_cols])[:, 1]
    return _clip(meta.predict_proba(base_current[list(BASE_MODEL_NAMES)])[:, 1])


def weight_sweep(
    frame: pd.DataFrame,
    *,
    weights: Iterable[float] = DEFAULT_PURE_WEIGHTS,
    target_col: str = "home_win",
    pure_col: str = "pure_prob",
    market_col: str = "market_prob",
) -> pd.DataFrame:
    rows: list[dict] = []
    for weight in weights:
        p = blend_probabilities(frame[pure_col], frame[market_col], float(weight))
        metrics = score_probabilities(frame[target_col], p)
        rows.append({"pure_weight": float(weight), "market_weight": 1.0 - float(weight), **metrics})
    return pd.DataFrame(rows)


def select_pure_weight(
    frame: pd.DataFrame,
    *,
    objective: str = "brier",
    weights: Iterable[float] = DEFAULT_PURE_WEIGHTS,
    target_col: str = "home_win",
    pure_col: str = "pure_prob",
    market_col: str = "market_prob",
) -> tuple[float, pd.DataFrame]:
    """Select a blend on prior data only.

    ``brier`` is the default because it rewards probability quality.  ``accuracy``
    is also tested because the public product's primary action is a winner pick.
    """
    if objective not in {"brier", "accuracy"}:
        raise ValueError("objective must be 'brier' or 'accuracy'")
    usable = frame[
        frame[target_col].notna() & frame[pure_col].notna() & frame[market_col].notna()
    ].copy()
    if len(usable) < 100:
        raise ValueError(f"Need at least 100 market-covered games to tune a blend; found {len(usable)}")
    sweep = weight_sweep(
        usable,
        weights=weights,
        target_col=target_col,
        pure_col=pure_col,
        market_col=market_col,
    )
    if objective == "brier":
        ranked = sweep.assign(distance=(sweep.pure_weight - 0.75).abs()).sort_values(
            ["brier", "log_loss", "winner_pct", "distance"],
            ascending=[True, True, False, True],
        )
    else:
        ranked = sweep.assign(distance=(sweep.pure_weight - 0.75).abs()).sort_values(
            ["winner_pct", "brier", "log_loss", "distance"],
            ascending=[False, True, True, True],
        )
    return float(ranked.iloc[0].pure_weight), sweep


def fit_calibrator(
    target: Iterable[float],
    probability: Iterable[float],
    *,
    mode: str = "none",
) -> ProbabilityCalibrator:
    if mode not in {"none", "platt", "isotonic"}:
        raise ValueError("mode must be none, platt, or isotonic")
    y = np.asarray(target, dtype=float)
    p = np.asarray(probability, dtype=float)
    usable = np.isfinite(y) & np.isfinite(p)
    y = y[usable].astype(int)
    p = _clip(p[usable])
    if mode == "none":
        return ProbabilityCalibrator("none", None)
    if len(y) < 200 or len(np.unique(y)) < 2:
        raise ValueError(f"Insufficient calibration sample for {mode}: {len(y)}")
    if mode == "platt":
        model = LogisticRegression(C=1.0, max_iter=3000, random_state=26)
        model.fit(_logit(p).reshape(-1, 1), y)
        return ProbabilityCalibrator(mode, model)
    model = IsotonicRegression(y_min=EPS, y_max=1.0 - EPS, out_of_bounds="clip")
    model.fit(p, y)
    return ProbabilityCalibrator(mode, model)


def nested_blend_backtest(
    frame: pd.DataFrame,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    weight_objective: str = "brier",
    calibrator: str = "none",
    season_col: str = "season",
    target_col: str = "home_win",
    pure_col: str = "pure_prob",
    market_col: str = "market_prob",
) -> BlendBacktestResult:
    """Tune on seasons before S, then score S. Never tune on the test season."""
    prediction_parts: list[pd.DataFrame] = []
    weight_rows: list[dict] = []
    for test_season in [int(x) for x in target_seasons]:
        tune = frame[frame[season_col] < test_season].copy()
        test = frame[frame[season_col] == test_season].copy()
        if test.empty:
            continue
        pure_weight, _ = select_pure_weight(
            tune,
            objective=weight_objective,
            target_col=target_col,
            pure_col=pure_col,
            market_col=market_col,
        )
        tune_raw = blend_probabilities(tune[pure_col], tune[market_col], pure_weight)
        calibration = fit_calibrator(tune[target_col], tune_raw, mode=calibrator)
        test_raw = blend_probabilities(test[pure_col], test[market_col], pure_weight)
        part = test[[season_col, target_col, pure_col, market_col]].copy()
        part["raw_prob"] = test_raw
        part["probability"] = calibration.predict(test_raw)
        part["pure_weight"] = pure_weight
        part["market_weight"] = 1.0 - pure_weight
        part["calibrator"] = calibrator
        prediction_parts.append(part)
        year_metrics = score_probabilities(part[target_col], part["probability"])
        weight_rows.append({
            "season": test_season,
            "pure_weight": pure_weight,
            "market_weight": 1.0 - pure_weight,
            "objective": weight_objective,
            "calibrator": calibrator,
            **year_metrics,
        })
    if not prediction_parts:
        raise ValueError("No target-season blend predictions were generated")
    predictions = pd.concat(prediction_parts).sort_index()
    metrics = score_probabilities(predictions[target_col], predictions["probability"])
    return BlendBacktestResult(predictions, pd.DataFrame(weight_rows), metrics)


def fixed_blend_backtest(
    frame: pd.DataFrame,
    pure_weight: float,
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    season_col: str = "season",
    target_col: str = "home_win",
    pure_col: str = "pure_prob",
    market_col: str = "market_prob",
) -> dict[str, float]:
    test = frame[frame[season_col].isin([int(x) for x in target_seasons])]
    p = blend_probabilities(test[pure_col], test[market_col], pure_weight)
    return score_probabilities(test[target_col], p)


def choose_shadow_candidate(candidate_metrics: pd.DataFrame, production_label: str) -> pd.Series:
    """Choose the best research candidate without authorizing production promotion.

    Accuracy is the first objective, but a candidate cannot buy accuracy by
    materially worsening probability quality relative to the production-like
    nested baseline.
    """
    production = candidate_metrics[candidate_metrics["candidate"].eq(production_label)]
    if len(production) != 1:
        raise ValueError(f"Expected one production reference row for {production_label}")
    ref = production.iloc[0]
    allowed = candidate_metrics[
        (candidate_metrics["brier"] <= float(ref.brier) + 0.001)
        & (candidate_metrics["log_loss"] <= float(ref.log_loss) + 0.003)
    ].copy()
    if allowed.empty:
        return ref
    allowed["accuracy_gain"] = allowed["winner_pct"] - float(ref.winner_pct)
    return allowed.sort_values(
        ["winner_pct", "brier", "log_loss"], ascending=[False, True, True]
    ).iloc[0]

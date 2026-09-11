from __future__ import annotations

"""Research-only test of whether football adds information beyond a calibrated market."""

from dataclasses import asdict
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .challenger_evaluation import forecast_metrics, paired_bootstrap
from .challenger_market_reliance import TARGET_SEASONS, prepare_frozen_historical_frame

EPS = 1e-6


def _logit(values: pd.Series) -> np.ndarray:
    p = np.clip(pd.to_numeric(values, errors="raise").to_numpy(dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def _fit_probability(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, LogisticRegression]:
    model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
    model.fit(x_train, y_train)
    return model.predict_proba(x_test)[:, 1], model


def walk_forward_incremental_stack(
    frame: pd.DataFrame,
    *,
    target_seasons: Sequence[int] = TARGET_SEASONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare market calibration with market+football using only prior seasons.

    The market-only calibration controls for the possibility that a two-input stack merely
    recalibrates market probabilities. A genuine incremental football contribution should
    improve the market+football candidate relative to this calibrated-market reference,
    not merely relative to raw market prices.
    """
    work = prepare_frozen_historical_frame(frame)
    parts: list[pd.DataFrame] = []
    rows: list[dict] = []
    for season in [int(x) for x in target_seasons]:
        train = work[work.season < season].copy()
        test = work[work.season == season].copy()
        if test.empty:
            continue
        if len(train) < 300 or train.home_win.nunique() < 2:
            raise ValueError(f"Insufficient pre-{season} history for incremental stack")

        y = train.home_win.astype(int).to_numpy()
        train_market = _logit(train.market_prob).reshape(-1, 1)
        test_market = _logit(test.market_prob).reshape(-1, 1)
        train_both = np.column_stack([_logit(train.market_prob), _logit(train.pure_prob)])
        test_both = np.column_stack([_logit(test.market_prob), _logit(test.pure_prob)])

        market_calibrated, market_model = _fit_probability(train_market, y, test_market)
        market_plus_pure, combined_model = _fit_probability(train_both, y, test_both)

        part = test[["game_id", "season", "week", "home_win", "market_prob", "pure_prob"]].copy()
        part["market_calibrated_prob"] = market_calibrated
        part["market_plus_pure_prob"] = market_plus_pure
        parts.append(part)

        market_metrics = forecast_metrics(part, "market_calibrated_prob")
        combined_metrics = forecast_metrics(part, "market_plus_pure_prob")
        rows.append(
            {
                "season": season,
                "training_games": int(len(train)),
                "market_only_intercept": float(market_model.intercept_[0]),
                "market_only_market_logit_coefficient": float(market_model.coef_[0, 0]),
                "combined_intercept": float(combined_model.intercept_[0]),
                "combined_market_logit_coefficient": float(combined_model.coef_[0, 0]),
                "combined_pure_logit_coefficient": float(combined_model.coef_[0, 1]),
                "market_calibrated_brier": market_metrics["brier"],
                "market_plus_pure_brier": combined_metrics["brier"],
                "market_plus_pure_minus_calibrated_market_brier": (
                    combined_metrics["brier"] - market_metrics["brier"]
                ),
                "market_calibrated_log_loss": market_metrics["log_loss"],
                "market_plus_pure_log_loss": combined_metrics["log_loss"],
                "market_calibrated_winner_pct": market_metrics["winner_pct"],
                "market_plus_pure_winner_pct": combined_metrics["winner_pct"],
            }
        )
    if not parts:
        raise ValueError("No target seasons available for incremental market-signal study")
    return pd.concat(parts).sort_index(), pd.DataFrame(rows)


def incremental_uncertainty(
    predictions: pd.DataFrame,
    *,
    bootstrap_samples: int = 5000,
    seed: int = 26,
) -> pd.DataFrame:
    """Week-block uncertainty for market+football versus calibrated and raw market."""
    rows: list[dict] = []
    comparisons = (
        ("market_calibrated_prob", "calibrated_market"),
        ("market_prob", "raw_market"),
    )
    for reference_col, reference_label in comparisons:
        for metric in ("brier", "log_loss", "accuracy"):
            result = paired_bootstrap(
                predictions,
                "market_plus_pure_prob",
                reference_col,
                metric=metric,
                block_cols=("season", "week"),
                samples=bootstrap_samples,
                seed=seed + len(rows),
            )
            rows.append({"reference_label": reference_label, **asdict(result)})
    return pd.DataFrame(rows)

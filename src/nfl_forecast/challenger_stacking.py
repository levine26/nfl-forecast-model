from __future__ import annotations

"""Research-only chronological market + v0.8 logit stack for F-ST-01."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

STACK_C = 1.0
STACK_MAX_ITER = 3000
EPS = 1e-6
TARGET_SEASONS = (2022, 2023, 2024, 2025)
HISTORICAL_END = 2025


@dataclass(frozen=True)
class StackingResult:
    predictions: pd.DataFrame
    coefficients: pd.DataFrame


def _logit(values: pd.Series | np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(probability / (1.0 - probability))


def build_chronological_logit_stack(
    oof_frame: pd.DataFrame,
    *,
    target_seasons: tuple[int, ...] = TARGET_SEASONS,
) -> StackingResult:
    """Fit the fixed two-input stack using only earlier-season OOF rows."""
    required = {"season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(oof_frame.columns)
    if missing:
        raise ValueError(f"stacking frame missing fields: {sorted(missing)}")

    work = oof_frame.copy()
    work["season_num"] = pd.to_numeric(work["season"], errors="coerce")
    work["home_win_num"] = pd.to_numeric(work["home_win"], errors="coerce")
    work["market_prob_num"] = pd.to_numeric(work["market_prob"], errors="coerce")
    work["pure_prob_num"] = pd.to_numeric(work["pure_prob"], errors="coerce")
    work = work[
        work["season_num"].notna()
        & work["home_win_num"].notna()
        & work["market_prob_num"].notna()
        & work["pure_prob_num"].notna()
    ].copy()
    if work.empty:
        raise ValueError("No usable OOF rows for F-ST-01")
    if int(work["season_num"].max()) > HISTORICAL_END:
        raise ValueError("F-ST-01 may not use outcomes after 2025")

    work["market_logit"] = _logit(work["market_prob_num"])
    work["v08_logit"] = _logit(work["pure_prob_num"])

    predictions: list[pd.DataFrame] = []
    coefficients: list[dict] = []
    for season in target_seasons:
        train = work[work["season_num"] < season].copy()
        test = work[work["season_num"] == season].copy()
        if test.empty:
            continue
        if len(train) < 300 or train["home_win_num"].nunique() < 2:
            raise RuntimeError(f"Insufficient chronological stack training history for {season}")

        model = LogisticRegression(
            C=STACK_C,
            penalty="l2",
            solver="lbfgs",
            max_iter=STACK_MAX_ITER,
        )
        features = ["market_logit", "v08_logit"]
        model.fit(train[features], train["home_win_num"].astype(int))
        probability = model.predict_proba(test[features])[:, 1]

        part = test[["season", "home_win", "market_prob", "pure_prob"]].copy()
        part["stack_probability"] = np.clip(probability, EPS, 1.0 - EPS)
        predictions.append(part)
        coefficients.append({
            "season": int(season),
            "training_games": int(len(train)),
            "training_first_season": int(train["season_num"].min()),
            "training_last_season": int(train["season_num"].max()),
            "intercept": float(model.intercept_[0]),
            "market_logit_coefficient": float(model.coef_[0, 0]),
            "v08_logit_coefficient": float(model.coef_[0, 1]),
            "C": STACK_C,
        })

    if not predictions:
        raise RuntimeError("F-ST-01 produced no target-season predictions")
    output = pd.concat(predictions).sort_index()
    missing_targets = set(target_seasons) - set(output["season"].astype(int).unique())
    if missing_targets:
        raise RuntimeError(f"F-ST-01 missing target seasons: {sorted(missing_targets)}")
    return StackingResult(output, pd.DataFrame(coefficients))

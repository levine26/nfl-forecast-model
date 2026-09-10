from __future__ import annotations

"""Frozen research-only F-ST-01 model materialization for prospective 2026 shadowing."""

from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .challenger_stacking import EPS, HISTORICAL_END, STACK_C, STACK_MAX_ITER, _logit

FROZEN_CANDIDATE_ID = "F-ST-01-FROZEN-2026"
FROZEN_FEATURE_SET = "market_plus_v08_pure_logit_stack"
FROZEN_METHOD = "stack"
FROZEN_TARGET_SEASON = 2026


@dataclass(frozen=True)
class FrozenStackFit:
    intercept: float
    market_logit_coefficient: float
    pure_logit_coefficient: float
    training_games: int
    training_first_season: int
    training_last_season: int
    training_data_sha256: str

    def as_dict(self) -> dict:
        return {
            "intercept": self.intercept,
            "market_logit_coefficient": self.market_logit_coefficient,
            "pure_logit_coefficient": self.pure_logit_coefficient,
            "training_games": self.training_games,
            "training_first_season": self.training_first_season,
            "training_last_season": self.training_last_season,
            "training_data_sha256": self.training_data_sha256,
            "C": STACK_C,
            "penalty": "l2",
            "solver": "lbfgs",
            "max_iter": STACK_MAX_ITER,
        }


def _canonical_training_hash(frame: pd.DataFrame) -> str:
    canonical = frame[["season_num", "home_win_num", "market_prob_num", "pure_prob_num"]].copy()
    canonical = canonical.sort_values(
        ["season_num", "market_prob_num", "pure_prob_num", "home_win_num"],
        kind="mergesort",
    )
    text = canonical.to_csv(index=False, float_format="%.12g", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prepare_frozen_training_frame(oof_frame: pd.DataFrame) -> pd.DataFrame:
    """Return the only admissible training rows for the frozen 2026 stack.

    The input must be historical OOF probabilities. Any row from 2026 or later is a
    hard failure rather than something silently filtered away.
    """
    required = {"season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(oof_frame.columns)
    if missing:
        raise ValueError(f"F-ST frozen training frame missing fields: {sorted(missing)}")

    work = oof_frame.copy()
    work["season_num"] = pd.to_numeric(work["season"], errors="coerce")
    if work["season_num"].dropna().ge(FROZEN_TARGET_SEASON).any():
        raise ValueError("F-ST frozen training may not load 2026-or-later rows")
    work["home_win_num"] = pd.to_numeric(work["home_win"], errors="coerce")
    work["market_prob_num"] = pd.to_numeric(work["market_prob"], errors="coerce")
    work["pure_prob_num"] = pd.to_numeric(work["pure_prob"], errors="coerce")
    work = work[
        work["season_num"].notna()
        & work["home_win_num"].notna()
        & work["market_prob_num"].notna()
        & work["pure_prob_num"].notna()
        & work["season_num"].le(HISTORICAL_END)
    ].copy()
    if len(work) < 300 or work["home_win_num"].nunique() < 2:
        raise RuntimeError("Insufficient leakage-safe OOF history to freeze F-ST-01")
    return work


def fit_frozen_2026_stack(oof_frame: pd.DataFrame) -> FrozenStackFit:
    """Fit the immutable architecture for target season 2026 on OOF rows through 2025."""
    work = prepare_frozen_training_frame(oof_frame)
    work["market_logit"] = _logit(work["market_prob_num"])
    work["v08_logit"] = _logit(work["pure_prob_num"])
    model = LogisticRegression(
        C=STACK_C,
        penalty="l2",
        solver="lbfgs",
        max_iter=STACK_MAX_ITER,
    )
    model.fit(work[["market_logit", "v08_logit"]], work["home_win_num"].astype(int))
    return FrozenStackFit(
        intercept=float(model.intercept_[0]),
        market_logit_coefficient=float(model.coef_[0, 0]),
        pure_logit_coefficient=float(model.coef_[0, 1]),
        training_games=int(len(work)),
        training_first_season=int(work["season_num"].min()),
        training_last_season=int(work["season_num"].max()),
        training_data_sha256=_canonical_training_hash(work),
    )


def frozen_stack_probability(
    market_probability,
    pure_probability,
    *,
    intercept: float,
    market_logit_coefficient: float,
    pure_logit_coefficient: float,
) -> np.ndarray:
    market = np.asarray(market_probability, dtype=float)
    pure = np.asarray(pure_probability, dtype=float)
    if np.isnan(market).any() or np.isnan(pure).any():
        raise ValueError("F-ST requires both market and v0.8 PURE probabilities")
    score = (
        float(intercept)
        + float(market_logit_coefficient) * _logit(market)
        + float(pure_logit_coefficient) * _logit(pure)
    )
    probability = 1.0 / (1.0 + np.exp(-score))
    return np.clip(probability, EPS, 1.0 - EPS)

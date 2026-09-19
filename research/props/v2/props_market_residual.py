from __future__ import annotations

"""Research-only market-prior residual calibration for LevLine Props.

The sportsbook no-vig probability is treated as a fixed prior:

    logit(p_challenger)
        = logit(p_market)
        + intercept
        + beta * (logit(p_levline) - logit(p_market))

Only intercept and beta are fitted, with explicit L2 shrinkage. This module never
mutates the underlying football simulation or official LevLine/F-ST winner model.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ENGINE_VERSION = "levline-props-market-prior-residual-v0.1.0"
RESEARCH_LABEL = "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE"
EPS = 1e-4
DEFAULT_RESIDUAL_L2 = 10.0
DEFAULT_INTERCEPT_L2 = 1.0

PREDICTION_REQUIRED = {
    "game_id", "player_id", "prop_type", "over_odds", "under_odds", "p_over",
}
TRAINING_REQUIRED = PREDICTION_REQUIRED | {"market_line", "actual_result"}


class MarketResidualError(ValueError):
    """Raised when a market-residual input violates the research contract."""


@dataclass(frozen=True)
class MarketPriorResidualModel:
    intercept: float
    residual_beta: float
    residual_l2: float
    intercept_l2: float
    training_rows: int
    training_games: int
    engine_version: str = ENGINE_VERSION
    research_label: str = RESEARCH_LABEL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite(value: Any, *, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise MarketResidualError(f"{label} must be numeric") from exc
    if not math.isfinite(parsed):
        raise MarketResidualError(f"{label} must be finite")
    return parsed


def _clip_probability(value: float) -> float:
    return min(1.0 - EPS, max(EPS, float(value)))


def _logit(value: float) -> float:
    p = _clip_probability(value)
    return math.log(p / (1.0 - p))


def _inv_logit(value: np.ndarray | float) -> np.ndarray:
    x = np.asarray(value, dtype=float)
    out = np.empty_like(x, dtype=float)
    positive = x >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    out[~positive] = exp_x / (1.0 + exp_x)
    return out


def american_implied_probability(american_odds: float) -> float:
    odds = _finite(american_odds, label="american_odds")
    if odds == 0:
        raise MarketResidualError("American odds cannot be zero")
    if odds < 0:
        return -odds / (-odds + 100.0)
    return 100.0 / (odds + 100.0)


def no_vig_over_probability(over_odds: float, under_odds: float) -> float:
    q_over = american_implied_probability(over_odds)
    q_under = american_implied_probability(under_odds)
    total = q_over + q_under
    if not math.isfinite(total) or total <= 0.0:
        raise MarketResidualError("invalid two-way market")
    return q_over / total


def _validate_columns(frame: pd.DataFrame, *, training: bool) -> None:
    required = TRAINING_REQUIRED if training else PREDICTION_REQUIRED
    missing = required - set(frame.columns)
    if missing:
        raise MarketResidualError(f"missing required fields: {sorted(missing)}")
    if frame.empty:
        raise MarketResidualError("market-residual frame is empty")


def _prediction_features(frame: pd.DataFrame) -> pd.DataFrame:
    _validate_columns(frame, training=False)
    rows: list[dict[str, Any]] = []
    for idx, row in frame.iterrows():
        p_market = no_vig_over_probability(row["over_odds"], row["under_odds"])
        p_levline = _clip_probability(_finite(row["p_over"], label=f"p_over[{idx}]"))
        market_logit = _logit(p_market)
        levline_logit = _logit(p_levline)
        rows.append(
            {
                "_row_index": idx,
                "market_p_over": p_market,
                "market_logit": market_logit,
                "levline_p_over": p_levline,
                "levline_logit": levline_logit,
                "levline_market_logit_gap": levline_logit - market_logit,
            }
        )
    return pd.DataFrame(rows).set_index("_row_index").reindex(frame.index)


def _training_arrays(frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
    _validate_columns(frame, training=True)
    actual = pd.to_numeric(frame["actual_result"], errors="coerce")
    line = pd.to_numeric(frame["market_line"], errors="coerce")
    if actual.isna().any() or line.isna().any():
        raise MarketResidualError("training actual_result/market_line must be complete")
    decided = ~np.isclose(actual.to_numpy(float), line.to_numpy(float), atol=1e-12)
    if not np.any(decided):
        raise MarketResidualError("training sample contains no decided non-push outcomes")
    work = frame.loc[decided].copy()
    features = _prediction_features(work)
    y = (
        pd.to_numeric(work["actual_result"]).to_numpy(float)
        > pd.to_numeric(work["market_line"]).to_numpy(float)
    ).astype(float)
    return features, y, work


def fit_market_prior_residual(
    frame: pd.DataFrame,
    *,
    residual_l2: float = DEFAULT_RESIDUAL_L2,
    intercept_l2: float = DEFAULT_INTERCEPT_L2,
) -> MarketPriorResidualModel:
    """Fit a two-parameter correction around the sportsbook prior."""

    residual_l2 = _finite(residual_l2, label="residual_l2")
    intercept_l2 = _finite(intercept_l2, label="intercept_l2")
    if residual_l2 < 0 or intercept_l2 < 0:
        raise MarketResidualError("L2 penalties must be non-negative")

    features, y, work = _training_arrays(frame)
    market = features["market_logit"].to_numpy(float)
    gap = features["levline_market_logit_gap"].to_numpy(float)

    def objective(theta: np.ndarray) -> float:
        intercept = float(theta[0])
        beta = float(theta[1])
        z = market + intercept + beta * gap
        nll = float(np.sum(np.logaddexp(0.0, z) - y * z))
        return nll + intercept_l2 * intercept * intercept + residual_l2 * beta * beta

    result = minimize(
        objective,
        x0=np.zeros(2, dtype=float),
        method="BFGS",
        options={"maxiter": 2000, "gtol": 1e-9},
    )
    if not np.isfinite(result.fun):
        raise MarketResidualError(f"residual optimization failed: {result.message}")

    return MarketPriorResidualModel(
        intercept=float(result.x[0]),
        residual_beta=float(result.x[1]),
        residual_l2=float(residual_l2),
        intercept_l2=float(intercept_l2),
        training_rows=int(len(features)),
        training_games=int(work["game_id"].astype(str).nunique()),
    )


def apply_market_prior_residual(
    frame: pd.DataFrame,
    model: MarketPriorResidualModel,
) -> pd.DataFrame:
    """Add market baseline and challenger probabilities/sides without outcomes."""

    features = _prediction_features(frame)
    z = (
        features["market_logit"].to_numpy(float)
        + float(model.intercept)
        + float(model.residual_beta)
        * features["levline_market_logit_gap"].to_numpy(float)
    )
    p = _inv_logit(z)
    out = frame.copy()
    out["market_no_vig_p_over"] = features["market_p_over"].to_numpy(float)
    market_p = out["market_no_vig_p_over"].to_numpy(float)
    out["market_price_side"] = np.where(
        market_p > 0.5 + 1e-12,
        "OVER",
        np.where(market_p < 0.5 - 1e-12, "UNDER", None),
    )
    out["challenger_p_over"] = p
    out["challenger_p_under"] = 1.0 - p
    out["challenger_side"] = np.where(p >= 0.5, "OVER", "UNDER")
    out["challenger_engine_version"] = model.engine_version
    out["challenger_research_label"] = model.research_label
    return out


def grade_directional_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Grade market/V1/challenger directions for research evaluation only."""

    required = {"market_line", "actual_result", "market_price_side", "challenger_side"}
    missing = required - set(frame.columns)
    if missing:
        raise MarketResidualError(f"grade frame missing fields: {sorted(missing)}")

    out = frame.copy()
    actual = pd.to_numeric(out["actual_result"], errors="coerce")
    line = pd.to_numeric(out["market_line"], errors="coerce")
    if actual.isna().any() or line.isna().any():
        raise MarketResidualError("grade actual_result/market_line must be complete")

    outcome = np.where(actual > line, "OVER", np.where(actual < line, "UNDER", "PUSH"))
    out["market_outcome_recomputed"] = outcome
    decided = out["market_outcome_recomputed"].ne("PUSH")
    market_informative = decided & out["market_price_side"].notna()
    out["market_price_correct"] = np.where(
        market_informative,
        out["market_price_side"].eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    out["challenger_correct"] = np.where(
        decided,
        out["challenger_side"].eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    if "model_side" in out.columns:
        valid_v1 = decided & out["model_side"].notna()
        out["v1_correct"] = np.where(
            valid_v1,
            out["model_side"].eq(out["market_outcome_recomputed"]).astype(float),
            np.nan,
        )
    return out

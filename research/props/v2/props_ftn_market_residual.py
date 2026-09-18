from __future__ import annotations

"""Regularized FTN matchup residual challenger around the sportsbook prior.

Research-development only. The sportsbook no-vig probability is a fixed offset.
The model may add information from the frozen LevLine probability gap plus strictly
lagged, live-capable FTN team matchup state. It cannot re-fit the sportsbook coefficient.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ENGINE_VERSION = "levline-props-ftn-market-residual-v0.1.0"
RESEARCH_LABEL = "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE"
EPS = 1e-4
DEFAULT_L2 = 10.0
DEFAULT_INTERCEPT_L2 = 1.0
MIN_TRAINING_ROWS = 75

COMMON_FEATURES = ("levline_market_logit_gap",)

FEATURES_BY_PROP = {
    "passing_yards": (
        "own_off_motion_rate",
        "own_off_play_action_rate",
        "own_off_no_huddle_rate",
        "own_off_qb_out_of_pocket_rate",
        "own_off_shotgun_rate",
        "own_off_catchable_rate",
        "own_off_drop_rate",
        "opp_def_blitz_play_rate",
        "opp_def_mean_blitzers",
        "opp_def_mean_pass_rushers",
        "opp_def_contested_ball_rate",
        "opp_def_catchable_allowed_rate",
        "opp_def_created_reception_allowed_rate",
    ),
    "passing_tds": (
        "own_off_motion_rate",
        "own_off_play_action_rate",
        "own_off_rpo_rate",
        "own_off_qb_out_of_pocket_rate",
        "opp_def_blitz_play_rate",
        "opp_def_mean_pass_rushers",
        "opp_def_contested_ball_rate",
        "opp_def_catchable_allowed_rate",
    ),
    "receiving_yards": (
        "own_off_motion_rate",
        "own_off_play_action_rate",
        "own_off_screen_rate",
        "own_off_catchable_rate",
        "own_off_drop_rate",
        "opp_def_blitz_play_rate",
        "opp_def_contested_ball_rate",
        "opp_def_catchable_allowed_rate",
        "opp_def_created_reception_allowed_rate",
    ),
    "receptions": (
        "own_off_motion_rate",
        "own_off_screen_rate",
        "own_off_catchable_rate",
        "own_off_drop_rate",
        "opp_def_contested_ball_rate",
        "opp_def_catchable_allowed_rate",
    ),
    "rushing_yards": (
        "own_off_motion_rate",
        "own_off_rpo_rate",
        "own_off_shotgun_rate",
        "own_off_pistol_rate",
        "own_off_mean_offense_backfield",
        "opp_def_mean_defense_box",
        "opp_def_blitz_play_rate",
        "opp_def_mean_blitzers",
    ),
}


class FTNResidualError(ValueError):
    pass


@dataclass(frozen=True)
class FeatureTransform:
    columns: tuple[str, ...]
    medians: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    add_missing_indicators: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FTNMarketResidualModel:
    prop_type: str
    intercept: float
    coefficients: tuple[float, ...]
    transformed_feature_names: tuple[str, ...]
    transform: FeatureTransform
    l2: float
    intercept_l2: float
    training_rows: int
    training_games: int
    engine_version: str = ENGINE_VERSION
    research_label: str = RESEARCH_LABEL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite(value: Any, *, label: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise FTNResidualError(f"{label} must be numeric") from exc
    if not math.isfinite(out):
        raise FTNResidualError(f"{label} must be finite")
    return out


def _clip_probability(value: float) -> float:
    return min(1.0 - EPS, max(EPS, float(value)))


def _logit(value: float) -> float:
    p = _clip_probability(value)
    return math.log(p / (1.0 - p))


def _inv_logit(value: np.ndarray) -> np.ndarray:
    x = np.asarray(value, dtype=float)
    out = np.empty_like(x, dtype=float)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def _american_implied(odds: Any) -> float:
    value = _finite(odds, label="american_odds")
    if value == 0:
        raise FTNResidualError("American odds cannot be zero")
    return -value / (-value + 100.0) if value < 0 else 100.0 / (value + 100.0)


def no_vig_over_probability(over_odds: Any, under_odds: Any) -> float:
    over = _american_implied(over_odds)
    under = _american_implied(under_odds)
    total = over + under
    if total <= 0:
        raise FTNResidualError("invalid two-way market")
    return over / total


def add_market_features(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"over_odds", "under_odds", "p_over"}
    missing = required - set(frame.columns)
    if missing:
        raise FTNResidualError(f"missing market/model fields: {sorted(missing)}")
    out = frame.copy()
    market = np.asarray(
        [no_vig_over_probability(o, u) for o, u in zip(out["over_odds"], out["under_odds"])],
        dtype=float,
    )
    levline = np.asarray(
        [_clip_probability(_finite(v, label="p_over")) for v in out["p_over"]],
        dtype=float,
    )
    market_logit = np.asarray([_logit(v) for v in market], dtype=float)
    levline_logit = np.asarray([_logit(v) for v in levline], dtype=float)
    out["market_no_vig_p_over"] = market
    out["market_logit"] = market_logit
    out["levline_market_logit_gap"] = levline_logit - market_logit
    return out


def candidate_features(prop_type: str) -> tuple[str, ...]:
    prop = str(prop_type)
    if prop not in FEATURES_BY_PROP:
        raise FTNResidualError(f"unsupported prop_type: {prop}")
    return COMMON_FEATURES + FEATURES_BY_PROP[prop]


def fit_transform(frame: pd.DataFrame, columns: Iterable[str]) -> FeatureTransform:
    kept: list[str] = []
    medians: list[float] = []
    means: list[float] = []
    scales: list[float] = []
    for column in columns:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        finite = values[np.isfinite(values)]
        if finite.empty:
            continue
        median = float(finite.median())
        filled = values.fillna(median).to_numpy(dtype=float)
        mean = float(np.mean(filled))
        scale = float(np.std(filled, ddof=0))
        if not math.isfinite(scale) or scale < 1e-8:
            scale = 1.0
        kept.append(column)
        medians.append(median)
        means.append(mean)
        scales.append(scale)
    if "levline_market_logit_gap" not in kept:
        raise FTNResidualError("LevLine-market probability gap must be available")
    return FeatureTransform(
        columns=tuple(kept),
        medians=tuple(medians),
        means=tuple(means),
        scales=tuple(scales),
    )


def transform_features(
    frame: pd.DataFrame,
    transform: FeatureTransform,
) -> tuple[np.ndarray, tuple[str, ...]]:
    base: list[np.ndarray] = []
    names: list[str] = []
    missing_parts: list[np.ndarray] = []
    missing_names: list[str] = []
    for column, median, mean, scale in zip(
        transform.columns, transform.medians, transform.means, transform.scales
    ):
        values = pd.to_numeric(
            frame.get(column, pd.Series(np.nan, index=frame.index)),
            errors="coerce",
        ).astype(float)
        missing = values.isna().to_numpy(dtype=float)
        filled = values.fillna(float(median)).to_numpy(dtype=float)
        base.append((filled - float(mean)) / float(scale))
        names.append(column)
        if transform.add_missing_indicators and column != "levline_market_logit_gap":
            missing_parts.append(missing)
            missing_names.append(f"{column}__missing")
    arrays = base + missing_parts
    if not arrays:
        return np.zeros((len(frame), 0), dtype=float), tuple()
    return np.column_stack(arrays), tuple(names + missing_names)


def _decided_training(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "market_line", "actual_result", "prop_type"}
    missing = required - set(frame.columns)
    if missing:
        raise FTNResidualError(f"training frame missing fields: {sorted(missing)}")
    actual = pd.to_numeric(frame["actual_result"], errors="coerce")
    line = pd.to_numeric(frame["market_line"], errors="coerce")
    if actual.isna().any() or line.isna().any():
        raise FTNResidualError("training outcomes/lines must be complete")
    decided = ~np.isclose(actual.to_numpy(float), line.to_numpy(float), atol=1e-12)
    return frame.loc[decided].copy()


def fit_ftn_market_residual(
    frame: pd.DataFrame,
    *,
    prop_type: str,
    feature_columns: Iterable[str] | None = None,
    l2: float = DEFAULT_L2,
    intercept_l2: float = DEFAULT_INTERCEPT_L2,
) -> FTNMarketResidualModel:
    prop = str(prop_type)
    work = add_market_features(_decided_training(frame))
    work = work[work["prop_type"].astype(str).eq(prop)].copy()
    if len(work) < MIN_TRAINING_ROWS:
        raise FTNResidualError(
            f"{prop} requires at least {MIN_TRAINING_ROWS} training rows; got {len(work)}"
        )
    requested = tuple(feature_columns) if feature_columns is not None else candidate_features(prop)
    if "levline_market_logit_gap" not in requested:
        raise FTNResidualError("feature_columns must include levline_market_logit_gap")
    transform = fit_transform(work, requested)
    x, names = transform_features(work, transform)
    market = work["market_logit"].to_numpy(dtype=float)
    y = (
        pd.to_numeric(work["actual_result"]).to_numpy(dtype=float)
        > pd.to_numeric(work["market_line"]).to_numpy(dtype=float)
    ).astype(float)

    l2 = _finite(l2, label="l2")
    intercept_l2 = _finite(intercept_l2, label="intercept_l2")
    if l2 < 0 or intercept_l2 < 0:
        raise FTNResidualError("penalties must be non-negative")

    def objective(theta: np.ndarray) -> float:
        intercept = float(theta[0])
        beta = theta[1:]
        z = market + intercept + x @ beta
        nll = float(np.sum(np.logaddexp(0.0, z) - y * z))
        return nll + intercept_l2 * intercept * intercept + l2 * float(beta @ beta)

    result = minimize(
        objective,
        x0=np.zeros(x.shape[1] + 1, dtype=float),
        method="L-BFGS-B",
        options={"maxiter": 3000, "ftol": 1e-12},
    )
    if not result.success or not np.isfinite(result.fun):
        raise FTNResidualError(f"optimization failed for {prop}: {result.message}")

    return FTNMarketResidualModel(
        prop_type=prop,
        intercept=float(result.x[0]),
        coefficients=tuple(float(v) for v in result.x[1:]),
        transformed_feature_names=names,
        transform=transform,
        l2=float(l2),
        intercept_l2=float(intercept_l2),
        training_rows=int(len(work)),
        training_games=int(work["game_id"].astype(str).nunique()),
    )


def apply_ftn_market_residual(
    frame: pd.DataFrame,
    models: dict[str, FTNMarketResidualModel],
) -> pd.DataFrame:
    out = add_market_features(frame)
    out["ftn_challenger_p_over"] = np.nan
    out["ftn_challenger_side"] = pd.NA
    out["ftn_model_version"] = pd.NA
    for prop, model in models.items():
        mask = out["prop_type"].astype(str).eq(str(prop))
        if not mask.any():
            continue
        subset = out.loc[mask].copy()
        x, names = transform_features(subset, model.transform)
        if names != model.transformed_feature_names:
            raise FTNResidualError(f"feature transform mismatch for {prop}")
        z = (
            subset["market_logit"].to_numpy(dtype=float)
            + float(model.intercept)
            + x @ np.asarray(model.coefficients, dtype=float)
        )
        p = _inv_logit(z)
        out.loc[mask, "ftn_challenger_p_over"] = p
        out.loc[mask, "ftn_challenger_side"] = np.where(p >= 0.5, "OVER", "UNDER")
        out.loc[mask, "ftn_model_version"] = model.engine_version
    return out

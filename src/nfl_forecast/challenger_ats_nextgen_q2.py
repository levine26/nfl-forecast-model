from __future__ import annotations

"""Frozen Stage-B Q2 discrete NFL margin-distribution machinery.

Research only.  This module implements the pre-result engineering contract in
``research/ats-nextgen/Q2_STAGE_B_OPENING_RECEIPT.md``.  It does not modify any
production forecasting surface and it never reads completed-2026 outcomes.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import gennorm, norm, t as student_t
from sklearn.metrics import mean_pinball_loss

from nfl_forecast.challenger_ats_nextgen_gate import TRAINING_FLOOR, validate_gate_frame
from nfl_forecast.challenger_ats_nextgen_q1 import (
    ALPHA_GRID,
    MIN_INNER_TRAIN_ROWS,
    choose_alpha,
    _fit_quantile_model,
)

CANDIDATE_ID = "ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1"
SUPPORT = np.arange(-75, 76, dtype=int)
SUPPORT_MIN = int(SUPPORT[0])
SUPPORT_MAX = int(SUPPORT[-1])
SUPPORT_SIZE = int(len(SUPPORT))
BOUNDARY_MASS_LIMIT = 1e-3
LOGLOSS_FLOOR = 1e-15
SCALE_GUARD = (0.25, 100.0)
TIE_TOLERANCE = 1e-12
GN_BETA_GRID = (1.0, 1.25, 1.5, 1.75, 2.0)
T_DF_GRID = (4.0, 6.0, 10.0)
KEY_VALUES = (3, 6, 7, 10, 14)
KEY_PENALTY_GRID = (1.0, 10.0, 100.0)
EMP_TOTAL_PSEUDOCOUNT = 1.0
EMP_PER_BIN_PSEUDOCOUNT = EMP_TOTAL_PSEUDOCOUNT / SUPPORT_SIZE

Family = Literal["gennorm", "norm", "t"]
Ablation = Literal[
    "no_key_conditional_scale",
    "key_constant_scale",
    "key_conditional_scale",
]
CenterMode = Literal["M1", "Q2"]


@dataclass(frozen=True)
class Q1MedianCenter:
    target_season: int
    selected_alpha: float
    inner_targets_used: tuple[int, ...]
    inner_targets_omitted: tuple[int, ...]
    train_game_ids: tuple[str, ...]
    train_residual_prediction: tuple[float, ...]
    target_game_ids: tuple[str, ...]
    target_residual_prediction: tuple[float, ...]


@dataclass(frozen=True)
class ScaleFit:
    family: Family
    shape: float | None
    conditional: bool
    total_median: float
    coefficients: tuple[float, ...]
    objective: float


@dataclass(frozen=True)
class KeyFit:
    penalty: float
    theta: tuple[float, ...]
    objective: float


@dataclass(frozen=True)
class ContinuousDistributionFit:
    family: Family
    shape: float | None
    ablation: Ablation
    scale: ScaleFit
    key: KeyFit | None


def _eligible(frame: pd.DataFrame, seasons: list[int] | tuple[int, ...]) -> pd.DataFrame:
    season = pd.to_numeric(frame["season"], errors="coerce")
    margin = pd.to_numeric(frame["margin"], errors="coerce")
    mask = (
        season.isin(list(seasons))
        & frame["ats_eligible"].astype(bool)
        & np.isfinite(margin.to_numpy(dtype=float))
    )
    return frame.loc[mask].copy()


def q1_median_center_for_target(frame: pd.DataFrame, target_season: int) -> Q1MedianCenter:
    """Build the frozen upstream Q1 median center for a Q2 target season.

    Target 2019 is deliberately unavailable: no earlier registered Q1 validation
    season exists from which to select alpha without inventing a fallback.
    """
    validate_gate_frame(frame)
    target = int(target_season)
    if target < 2020 or target > 2025:
        raise ValueError("Q2 Q1-center target must be 2020..2025; 2019 is mechanically omitted")

    alpha_targets: dict[float, list[np.ndarray]] = {a: [] for a in ALPHA_GRID}
    alpha_predictions: dict[float, list[np.ndarray]] = {a: [] for a in ALPHA_GRID}
    used: list[int] = []
    omitted: list[int] = []

    for inner in range(2019, target):
        train = _eligible(frame, list(range(TRAINING_FLOOR, inner)))
        valid = _eligible(frame, (inner,))
        if len(train) < MIN_INNER_TRAIN_ROWS or valid.empty:
            omitted.append(inner)
            continue
        used.append(inner)
        y = pd.to_numeric(valid["ats_residual"], errors="raise").to_numpy(dtype=float)
        for alpha in ALPHA_GRID:
            pred = _fit_quantile_model(
                train,
                valid,
                feature_set="full",
                quantile=0.5,
                alpha=float(alpha),
            )
            alpha_targets[float(alpha)].append(y)
            alpha_predictions[float(alpha)].append(pred)

    if not used:
        raise RuntimeError("Q2 upstream Q1 center has no prior rolling-origin alpha evidence")

    losses: dict[float, float] = {}
    for alpha in ALPHA_GRID:
        ys = alpha_targets[float(alpha)]
        ps = alpha_predictions[float(alpha)]
        if not ys:
            raise RuntimeError(f"Q2 upstream Q1 alpha {alpha} has no prior OOF rows")
        losses[float(alpha)] = float(
            mean_pinball_loss(
                np.concatenate(ys),
                np.concatenate(ps),
                alpha=0.5,
            )
        )
    selected, _ = choose_alpha(losses)

    train = _eligible(frame, list(range(TRAINING_FLOOR, target)))
    target_frame = _eligible(frame, (target,))
    if len(train) < MIN_INNER_TRAIN_ROWS or target_frame.empty:
        raise RuntimeError(f"Q2 upstream Q1 center lacks train/target rows for {target}")
    train_pred = _fit_quantile_model(
        train, train, feature_set="full", quantile=0.5, alpha=selected
    )
    target_pred = _fit_quantile_model(
        train, target_frame, feature_set="full", quantile=0.5, alpha=selected
    )
    return Q1MedianCenter(
        target_season=target,
        selected_alpha=float(selected),
        inner_targets_used=tuple(used),
        inner_targets_omitted=tuple(omitted),
        train_game_ids=tuple(train["game_id"].astype(str)),
        train_residual_prediction=tuple(float(x) for x in train_pred),
        target_game_ids=tuple(target_frame["game_id"].astype(str)),
        target_residual_prediction=tuple(float(x) for x in target_pred),
    )


def _shape_is_valid(family: Family, shape: float | None) -> bool:
    if family == "norm":
        return shape is None
    if family == "gennorm":
        return shape is not None and float(shape) in GN_BETA_GRID
    if family == "t":
        return shape is not None and float(shape) in T_DF_GRID
    return False


def _cdf(x: np.ndarray, center: np.ndarray, scale: np.ndarray, family: Family, shape: float | None) -> np.ndarray:
    if not _shape_is_valid(family, shape):
        raise ValueError(f"invalid frozen Q2 family/shape: {family}/{shape}")
    if family == "norm":
        return norm.cdf(x, loc=center, scale=scale)
    if family == "gennorm":
        return gennorm.cdf(x, float(shape), loc=center, scale=scale)
    return student_t.cdf(x, float(shape), loc=center, scale=scale)


def continuous_base_pmf(
    centers: np.ndarray,
    scales: np.ndarray,
    *,
    family: Family,
    shape: float | None,
) -> np.ndarray:
    """Integrate continuous mass over integer bins and fold both tails."""
    mu = np.asarray(centers, dtype=float).reshape(-1)
    sigma = np.asarray(scales, dtype=float).reshape(-1)
    if len(mu) != len(sigma) or not np.isfinite(mu).all() or not np.isfinite(sigma).all():
        raise ValueError("Q2 centers/scales must be aligned and finite")
    if (sigma <= 0).any():
        raise ValueError("Q2 scale must be positive")

    lower = (SUPPORT.astype(float) - 0.5)[None, :]
    upper = (SUPPORT.astype(float) + 0.5)[None, :]
    loc = mu[:, None]
    scl = sigma[:, None]
    lo = _cdf(lower, loc, scl, family, shape)
    hi = _cdf(upper, loc, scl, family, shape)
    pmf = hi - lo
    pmf[:, 0] = _cdf(np.full((len(mu), 1), -74.5), loc[:, :1], scl[:, :1], family, shape)[:, 0]
    pmf[:, -1] = 1.0 - _cdf(
        np.full((len(mu), 1), 74.5), loc[:, :1], scl[:, :1], family, shape
    )[:, 0]
    if (pmf < -1e-12).any() or not np.isfinite(pmf).all():
        raise RuntimeError("Q2 continuous discretization produced invalid mass")
    pmf = np.maximum(pmf, 0.0)
    sums = pmf.sum(axis=1)
    if (sums <= 0).any() or not np.isfinite(sums).all():
        raise RuntimeError("Q2 continuous PMF has invalid normalization")
    pmf = pmf / sums[:, None]
    return pmf


def endpoint_mass(pmf: np.ndarray) -> np.ndarray:
    p = np.asarray(pmf, dtype=float)
    return p[:, 0] + p[:, -1]


def validate_pmf(pmf: np.ndarray, *, enforce_boundary: bool = False) -> None:
    p = np.asarray(pmf, dtype=float)
    if p.ndim != 2 or p.shape[1] != SUPPORT_SIZE:
        raise ValueError("Q2 PMF must have 151 support columns")
    if not np.isfinite(p).all() or (p < -1e-12).any():
        raise ValueError("Q2 PMF contains invalid probability mass")
    if not np.allclose(p.sum(axis=1), 1.0, atol=1e-10, rtol=0.0):
        raise ValueError("Q2 PMF does not sum to one")
    cdf = np.cumsum(p, axis=1)
    if (np.diff(cdf, axis=1) < -1e-12).any():
        raise ValueError("Q2 CDF is not monotone")
    if enforce_boundary and (endpoint_mass(p) > BOUNDARY_MASS_LIMIT).any():
        raise RuntimeError("Q2 material endpoint mass exceeds frozen V1 threshold")


def _observed_indices(margins: np.ndarray) -> np.ndarray:
    y = np.asarray(margins, dtype=float).reshape(-1)
    if not np.all(np.equal(y, np.rint(y))):
        raise ValueError("Q2 observed NFL margins must be integer valued")
    yi = np.rint(y).astype(int)
    if (yi < SUPPORT_MIN).any() or (yi > SUPPORT_MAX).any():
        raise ValueError("Q2 observed margin lies outside frozen support")
    return yi - SUPPORT_MIN


def _observed_continuous_probability(
    margins: np.ndarray,
    centers: np.ndarray,
    scales: np.ndarray,
    *,
    family: Family,
    shape: float | None,
) -> np.ndarray:
    y = np.asarray(margins, dtype=float).reshape(-1)
    _observed_indices(y)
    mu = np.asarray(centers, dtype=float).reshape(-1)
    sigma = np.asarray(scales, dtype=float).reshape(-1)
    lower = y - 0.5
    upper = y + 0.5
    p = _cdf(upper, mu, sigma, family, shape) - _cdf(lower, mu, sigma, family, shape)
    left = y == SUPPORT_MIN
    right = y == SUPPORT_MAX
    if left.any():
        p[left] = _cdf(np.full(left.sum(), -74.5), mu[left], sigma[left], family, shape)
    if right.any():
        p[right] = 1.0 - _cdf(
            np.full(right.sum(), 74.5), mu[right], sigma[right], family, shape
        )
    return np.asarray(p, dtype=float)


def _scale_design(frame: pd.DataFrame, total_median: float, conditional: bool) -> np.ndarray:
    favorite = pd.to_numeric(frame["favorite_size"], errors="raise").to_numpy(dtype=float)
    total = pd.to_numeric(frame["market_total"], errors="coerce").to_numpy(dtype=float)
    total = np.where(np.isfinite(total), total, float(total_median))
    tc = (total - float(total_median)) / 10.0
    if conditional:
        return np.column_stack([np.ones(len(frame)), favorite, tc, favorite * tc])
    return np.ones((len(frame), 1), dtype=float)


def _scales_from_coefficients(design: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    eta = np.asarray(design, dtype=float) @ np.asarray(coefficients, dtype=float)
    if not np.isfinite(eta).all():
        return np.full(len(eta), np.nan)
    scale = np.exp(np.clip(eta, -50.0, 50.0))
    return scale


def fit_scale(
    frame: pd.DataFrame,
    centers: np.ndarray,
    *,
    family: Family,
    shape: float | None,
    conditional: bool,
) -> ScaleFit:
    if not _shape_is_valid(family, shape):
        raise ValueError("Q2 scale fit received non-frozen family/shape")
    y = pd.to_numeric(frame["margin"], errors="raise").to_numpy(dtype=float)
    mu = np.asarray(centers, dtype=float).reshape(-1)
    if len(y) != len(mu):
        raise ValueError("Q2 training center length mismatch")
    total = pd.to_numeric(frame["market_total"], errors="coerce")
    total_median = float(total.median(skipna=True))
    if not np.isfinite(total_median):
        raise ValueError("Q2 training window has no finite market-total median")
    design = _scale_design(frame, total_median, conditional)
    residual_sd = float(np.std(y - mu, ddof=0))
    start = np.zeros(design.shape[1], dtype=float)
    start[0] = float(np.log(max(residual_sd, 1.0)))

    def objective(beta: np.ndarray) -> float:
        scale = _scales_from_coefficients(design, beta)
        if not np.isfinite(scale).all():
            return 1e12
        if (scale <= SCALE_GUARD[0]).any() or (scale >= SCALE_GUARD[1]).any():
            return 1e10 + float(np.mean(np.square(np.log(np.maximum(scale, 1e-300)))))
        p = _observed_continuous_probability(y, mu, scale, family=family, shape=shape)
        if not np.isfinite(p).all() or (p <= 0).any():
            return 1e12
        return float(-np.mean(np.log(np.maximum(p, LOGLOSS_FLOOR))))

    result = minimize(objective, start, method="L-BFGS-B", options={"maxiter": 500})
    if not bool(result.success) or not np.isfinite(result.fun):
        raise RuntimeError(f"Q2 scale optimizer failed: {result.message}")
    coefficients = np.asarray(result.x, dtype=float)
    fitted_scale = _scales_from_coefficients(design, coefficients)
    if (
        (fitted_scale <= SCALE_GUARD[0]).any()
        or (fitted_scale >= SCALE_GUARD[1]).any()
        or not np.isfinite(fitted_scale).all()
    ):
        raise RuntimeError("Q2 fitted scale touched frozen numerical guard")
    return ScaleFit(
        family=family,
        shape=None if shape is None else float(shape),
        conditional=bool(conditional),
        total_median=total_median,
        coefficients=tuple(float(x) for x in coefficients),
        objective=float(result.fun),
    )


def predict_scale(frame: pd.DataFrame, fit: ScaleFit) -> np.ndarray:
    design = _scale_design(frame, fit.total_median, fit.conditional)
    scale = _scales_from_coefficients(design, np.asarray(fit.coefficients, dtype=float))
    if (
        (scale <= SCALE_GUARD[0]).any()
        or (scale >= SCALE_GUARD[1]).any()
        or not np.isfinite(scale).all()
    ):
        raise RuntimeError("Q2 prediction scale touched frozen numerical guard")
    return scale


def _distance_band(distance: np.ndarray) -> np.ndarray:
    d = np.asarray(distance, dtype=float)
    return np.where(d < 3.5, 0, np.where(d < 7.5, 1, 2)).astype(int)


def _key_theta_lookup(centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = np.asarray(centers, dtype=float).reshape(-1)
    support_positions: list[int] = []
    theta_index = np.empty((len(mu), len(KEY_VALUES) * 2), dtype=int)
    column = 0
    for key_idx, key in enumerate(KEY_VALUES):
        for signed in (-key, key):
            support_positions.append(int(signed - SUPPORT_MIN))
            band = _distance_band(np.abs(float(signed) - mu))
            theta_index[:, column] = key_idx * 3 + band
            column += 1
    return np.asarray(support_positions, dtype=int), theta_index


def _apply_key_excess(base_pmf: np.ndarray, centers: np.ndarray, theta: np.ndarray) -> np.ndarray:
    base = np.asarray(base_pmf, dtype=float)
    th = np.asarray(theta, dtype=float).reshape(-1)
    if len(th) != 15:
        raise ValueError("Q2 key-excess vector must contain exactly 15 coefficients")
    positions, lookup = _key_theta_lookup(centers)
    adjusted = base.copy()
    rows = np.arange(len(base))
    for j, pos in enumerate(positions):
        multiplier = np.exp(th[lookup[:, j]])
        adjusted[rows, pos] *= multiplier
    sums = adjusted.sum(axis=1)
    if (sums <= 0).any() or not np.isfinite(sums).all():
        raise RuntimeError("Q2 key adjustment destroyed PMF normalization")
    adjusted /= sums[:, None]
    validate_pmf(adjusted)
    return adjusted


def fit_key_excess(
    base_pmf: np.ndarray,
    centers: np.ndarray,
    margins: np.ndarray,
    *,
    penalty: float,
) -> KeyFit:
    if float(penalty) not in KEY_PENALTY_GRID:
        raise ValueError("Q2 key penalty is outside the frozen grid")
    base = np.asarray(base_pmf, dtype=float)
    validate_pmf(base)
    observed = _observed_indices(margins)
    rows = np.arange(len(base))

    def objective(theta: np.ndarray) -> float:
        if not np.isfinite(theta).all() or np.max(np.abs(theta)) > 50:
            return 1e12
        p = _apply_key_excess(base, centers, theta)
        nll = -np.mean(np.log(np.maximum(p[rows, observed], LOGLOSS_FLOOR)))
        return float(nll + 0.5 * float(penalty) * np.sum(np.square(theta)) / max(len(base), 1))

    result = minimize(
        objective,
        np.zeros(15, dtype=float),
        method="L-BFGS-B",
        options={"maxiter": 500},
    )
    if not bool(result.success) or not np.isfinite(result.fun):
        raise RuntimeError(f"Q2 key optimizer failed: {result.message}")
    return KeyFit(
        penalty=float(penalty),
        theta=tuple(float(x) for x in np.asarray(result.x, dtype=float)),
        objective=float(result.fun),
    )


def fit_continuous_distribution(
    frame: pd.DataFrame,
    centers: np.ndarray,
    *,
    family: Family,
    shape: float | None,
    ablation: Ablation,
    key_penalty: float | None,
) -> ContinuousDistributionFit:
    if ablation not in {
        "no_key_conditional_scale",
        "key_constant_scale",
        "key_conditional_scale",
    }:
        raise ValueError("Q2 ablation is outside the frozen set")
    has_key = ablation != "no_key_conditional_scale"
    if has_key != (key_penalty is not None):
        raise ValueError("Q2 key penalty presence must match the frozen ablation")
    conditional = ablation != "key_constant_scale"
    scale_fit = fit_scale(
        frame,
        centers,
        family=family,
        shape=shape,
        conditional=conditional,
    )
    scale = predict_scale(frame, scale_fit)
    base = continuous_base_pmf(centers, scale, family=family, shape=shape)
    key_fit: KeyFit | None = None
    if has_key:
        key_fit = fit_key_excess(
            base,
            centers,
            pd.to_numeric(frame["margin"], errors="raise").to_numpy(dtype=float),
            penalty=float(key_penalty),
        )
    return ContinuousDistributionFit(
        family=family,
        shape=None if shape is None else float(shape),
        ablation=ablation,
        scale=scale_fit,
        key=key_fit,
    )


def predict_continuous_distribution(
    frame: pd.DataFrame,
    centers: np.ndarray,
    fit: ContinuousDistributionFit,
    *,
    enforce_boundary: bool = True,
) -> np.ndarray:
    scale = predict_scale(frame, fit.scale)
    pmf = continuous_base_pmf(
        centers,
        scale,
        family=fit.family,
        shape=fit.shape,
    )
    if fit.key is not None:
        pmf = _apply_key_excess(pmf, centers, np.asarray(fit.key.theta, dtype=float))
    validate_pmf(pmf, enforce_boundary=enforce_boundary)
    return pmf


def empirical_residual_pmf(
    training_margins: np.ndarray,
    training_centers: np.ndarray,
    target_centers: np.ndarray,
) -> np.ndarray:
    y = np.asarray(training_margins, dtype=float).reshape(-1)
    mu_train = np.asarray(training_centers, dtype=float).reshape(-1)
    mu_target = np.asarray(target_centers, dtype=float).reshape(-1)
    _observed_indices(y)
    if len(y) != len(mu_train) or not np.isfinite(mu_train).all() or not np.isfinite(mu_target).all():
        raise ValueError("Q2 empirical residual inputs must be finite and aligned")
    residual = y - mu_train
    output = np.empty((len(mu_target), SUPPORT_SIZE), dtype=float)
    prior = np.full(SUPPORT_SIZE, EMP_PER_BIN_PSEUDOCOUNT, dtype=float)
    for i, center in enumerate(mu_target):
        shifted = center + residual
        bins = np.floor(shifted + 0.5).astype(int)
        bins = np.clip(bins, SUPPORT_MIN, SUPPORT_MAX) - SUPPORT_MIN
        counts = np.bincount(bins, minlength=SUPPORT_SIZE).astype(float) + prior
        output[i] = counts / counts.sum()
    validate_pmf(output)
    return output


def discrete_crps(pmf: np.ndarray, margins: np.ndarray) -> np.ndarray:
    p = np.asarray(pmf, dtype=float)
    validate_pmf(p)
    y = np.asarray(margins, dtype=float).reshape(-1)
    _observed_indices(y)
    if len(y) != len(p):
        raise ValueError("Q2 CRPS margin length mismatch")
    cdf = np.cumsum(p, axis=1)[:, :-1]
    thresholds = SUPPORT[:-1][None, :]
    observed_cdf = (y[:, None] <= thresholds).astype(float)
    return np.sum(np.square(cdf - observed_cdf), axis=1)


def cover_push_loss_probabilities(pmf: np.ndarray, home_spread: np.ndarray) -> np.ndarray:
    p = np.asarray(pmf, dtype=float)
    validate_pmf(p)
    spread = np.asarray(home_spread, dtype=float).reshape(-1)
    if len(spread) != len(p) or not np.isfinite(spread).all():
        raise ValueError("Q2 spread vector must be finite and aligned")
    outcomes = SUPPORT[None, :].astype(float) + spread[:, None]
    push_mask = np.isclose(outcomes, 0.0, atol=1e-12, rtol=0.0)
    cover = np.sum(np.where(outcomes > 0.0, p, 0.0), axis=1)
    push = np.sum(np.where(push_mask, p, 0.0), axis=1)
    loss = np.sum(np.where(outcomes < 0.0, p, 0.0), axis=1)
    half = np.isclose(np.mod(np.abs(spread), 1.0), 0.5, atol=1e-12, rtol=0.0)
    if not np.allclose(push[half], 0.0, atol=1e-15, rtol=0.0):
        raise RuntimeError("Q2 assigned push probability to a half-point line")
    result = np.column_stack([cover, push, loss])
    if not np.allclose(result.sum(axis=1), 1.0, atol=1e-10, rtol=0.0):
        raise RuntimeError("Q2 cover/push/loss probabilities do not sum to one")
    return result


def select_simple_tie(values: dict[float, float], *, larger_is_simpler: bool = True) -> tuple[float, float]:
    """Select minimum score with the frozen conservative numerical tie-break."""
    finite = {float(k): float(v) for k, v in values.items() if np.isfinite(v)}
    if len(finite) != len(values) or not finite:
        raise ValueError("Q2 tuning scores must all be finite")
    best = min(finite.values())
    tied = [k for k, v in finite.items() if abs(v - best) <= TIE_TOLERANCE]
    selected = max(tied) if larger_is_simpler else min(tied)
    return float(selected), float(finite[selected])

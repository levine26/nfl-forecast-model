from __future__ import annotations

"""Orthogonal market-residual research model for LevLine.

The market probability enters only as a fixed logit offset with coefficient 1.0. The
model learns a regularized residual from football features. This module is research-only
and is not imported by the production forecasting path.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

EPS = 1e-6
DEFAULT_L2 = 5.0


def _clip_probability(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values: Iterable[float]) -> np.ndarray:
    p = _clip_probability(values)
    return np.log(p / (1.0 - p))


def _sigmoid(values: Iterable[float]) -> np.ndarray:
    z = np.clip(np.asarray(values, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class OffsetLogitModel:
    features: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    coefficients: np.ndarray
    l2: float
    iterations: int
    converged: bool

    def _matrix(self, frame: pd.DataFrame) -> np.ndarray:
        raw = frame.loc[:, list(self.features)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float, copy=True)
        missing = ~np.isfinite(raw)
        if missing.any():
            rows, cols = np.where(missing)
            raw[rows, cols] = self.medians[cols]
        scaled = (raw - self.means) / self.scales
        return np.column_stack([np.ones(len(frame), dtype=float), scaled])

    def predict(self, frame: pd.DataFrame, market_probability: Iterable[float]) -> np.ndarray:
        offset = _logit(market_probability)
        return _clip_probability(_sigmoid(offset + self._matrix(frame) @ self.coefficients))


def _prepare_training_matrix(frame: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = frame.loc[:, features].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float, copy=True)
    raw[~np.isfinite(raw)] = np.nan
    medians = np.nanmedian(raw, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    missing = ~np.isfinite(raw)
    if missing.any():
        rows, cols = np.where(missing)
        raw[rows, cols] = medians[cols]
    means = raw.mean(axis=0)
    scales = raw.std(axis=0)
    scales = np.where(np.isfinite(scales) & (scales > 1e-8), scales, 1.0)
    matrix = np.column_stack([np.ones(len(frame), dtype=float), (raw - means) / scales])
    return matrix, medians, means, scales


def _objective(y: np.ndarray, offset: np.ndarray, matrix: np.ndarray, beta: np.ndarray, l2: float) -> float:
    linear = offset + matrix @ beta
    # Stable logistic negative log-likelihood: log(1 + exp(z)) - y*z.
    nll = np.logaddexp(0.0, linear).sum() - float(y @ linear)
    penalty = 0.5 * float(l2) * float(beta[1:] @ beta[1:])
    return float(nll + penalty)


def fit_offset_logistic(
    frame: pd.DataFrame,
    features: list[str],
    *,
    target_col: str = "home_win",
    market_col: str = "market_home_prob",
    l2: float = DEFAULT_L2,
    max_iter: int = 80,
    tolerance: float = 1e-8,
) -> OffsetLogitModel:
    """Fit deterministic L2 offset logistic regression by damped Newton/IRLS."""
    if l2 < 0:
        raise ValueError("l2 must be non-negative")
    usable = frame[
        frame[target_col].notna()
        & pd.to_numeric(frame[market_col], errors="coerce").between(EPS, 1.0 - EPS)
    ].copy()
    if len(usable) < 300:
        raise ValueError(f"Need at least 300 market-covered training games; found {len(usable)}")
    y = pd.to_numeric(usable[target_col], errors="coerce").to_numpy(dtype=float, copy=True)
    market = pd.to_numeric(usable[market_col], errors="coerce").to_numpy(dtype=float, copy=True)
    if not set(np.unique(y)).issubset({0.0, 1.0}) or len(np.unique(y)) < 2:
        raise ValueError("Target must contain both binary classes")

    matrix, medians, means, scales = _prepare_training_matrix(usable, features)
    offset = _logit(market)
    beta = np.zeros(matrix.shape[1], dtype=float)
    penalty = np.zeros(matrix.shape[1], dtype=float)
    penalty[1:] = float(l2)
    current = _objective(y, offset, matrix, beta, l2)
    converged = False

    for iteration in range(1, max_iter + 1):
        linear = offset + matrix @ beta
        probability = _sigmoid(linear)
        weight = np.clip(probability * (1.0 - probability), 1e-6, None)
        gradient = matrix.T @ (probability - y) + penalty * beta
        hessian = matrix.T @ (matrix * weight[:, None]) + np.diag(penalty)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hessian, gradient, rcond=None)[0]

        if float(np.max(np.abs(step))) < tolerance:
            converged = True
            break

        step_scale = 1.0
        accepted = False
        for _ in range(20):
            candidate = beta - step_scale * step
            candidate_objective = _objective(y, offset, matrix, candidate, l2)
            if candidate_objective <= current + 1e-10:
                beta = candidate
                current = candidate_objective
                accepted = True
                break
            step_scale *= 0.5
        if not accepted:
            break
        if float(np.max(np.abs(step_scale * step))) < tolerance:
            converged = True
            break
    else:
        iteration = max_iter

    return OffsetLogitModel(
        features=tuple(features),
        medians=medians,
        means=means,
        scales=scales,
        coefficients=beta,
        l2=float(l2),
        iterations=int(iteration),
        converged=bool(converged),
    )


def season_forward_market_residual(
    frame: pd.DataFrame,
    features: list[str],
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    target_col: str = "home_win",
    market_col: str = "market_home_prob",
    l2: float = DEFAULT_L2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit on seasons before S and predict S, fixing market-logit coefficient at one."""
    predictions: list[pd.DataFrame] = []
    diagnostics: list[dict] = []
    for season in [int(x) for x in target_seasons]:
        train = frame[pd.to_numeric(frame.season, errors="coerce").lt(season)].copy()
        test = frame[
            pd.to_numeric(frame.season, errors="coerce").eq(season)
            & frame[target_col].notna()
            & pd.to_numeric(frame[market_col], errors="coerce").between(EPS, 1.0 - EPS)
        ].copy()
        if test.empty:
            continue
        model = fit_offset_logistic(
            train,
            features,
            target_col=target_col,
            market_col=market_col,
            l2=l2,
        )
        probability = model.predict(test, pd.to_numeric(test[market_col], errors="coerce"))
        part = test[["season", target_col, market_col]].copy()
        part["probability"] = probability
        part["market_logit_offset_coefficient"] = 1.0
        predictions.append(part)
        diagnostics.append(
            {
                "season": season,
                "training_games": int(
                    train[target_col].notna().mul(
                        pd.to_numeric(train[market_col], errors="coerce").between(EPS, 1.0 - EPS)
                    ).sum()
                ),
                "test_games": int(len(test)),
                "l2": float(l2),
                "iterations": int(model.iterations),
                "converged": bool(model.converged),
                "residual_intercept": float(model.coefficients[0]),
                "football_coefficient_l2_norm": float(np.linalg.norm(model.coefficients[1:])),
                "market_logit_offset_coefficient": 1.0,
            }
        )
    if not predictions:
        raise ValueError("No market-residual target predictions generated")
    return pd.concat(predictions).sort_index(), pd.DataFrame(diagnostics)

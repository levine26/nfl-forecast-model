from __future__ import annotations

"""Pre-result reporting contract for ATS NextGen Q2 Stage B."""

import numpy as np
import pandas as pd
from scipy import optimize

from nfl_forecast.challenger_ats_nextgen_q1_reporting import fixed_slice_masks
from nfl_forecast.challenger_ats_nextgen_q2 import (
    LOGLOSS_FLOOR,
    SUPPORT,
    cover_push_loss_probabilities,
    discrete_crps,
    endpoint_mass,
    validate_pmf,
)

RELIABILITY_EDGES = np.linspace(0.0, 1.0, 11)
KEY_MARGINS = (3, 6, 7, 10, 14)
INTERVAL_LEVELS = (0.50, 0.80, 0.90)
CALIBRATION_DEGENERACY_TOL = 1e-12


def _binary_cover_probability(cpl: np.ndarray) -> np.ndarray:
    denom = cpl[:, 0] + cpl[:, 2]
    if not np.isfinite(denom).all() or (denom <= 0.0).any():
        raise RuntimeError("Q2 binary cover probability has invalid non-push denominator")
    return cpl[:, 0] / denom


def _observed_cpl_index(outcomes: pd.Series) -> np.ndarray:
    mapping = {"HOME_COVER": 0, "PUSH": 1, "HOME_LOSS": 2}
    values = outcomes.astype(str).map(mapping)
    if values.isna().any():
        raise ValueError("Q2 OOF contains unknown ATS outcome")
    return values.to_numpy(dtype=int)


def _margin_summaries(pmf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    expected = pmf @ SUPPORT.astype(float)
    cdf = np.cumsum(pmf, axis=1)
    median_index = np.argmax(cdf >= 0.5, axis=1)
    median = SUPPORT[median_index].astype(float)
    return expected, median


def _pmf_quantile(pmf: np.ndarray, probability: float) -> np.ndarray:
    if not 0.0 < float(probability) < 1.0:
        raise ValueError("Q2 reporting quantile probability must be inside (0,1)")
    cdf = np.cumsum(np.asarray(pmf, dtype=float), axis=1)
    index = np.argmax(cdf >= float(probability), axis=1)
    return SUPPORT[index].astype(float)


def _interval_metrics(pmf: np.ndarray, margin: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for level in INTERVAL_LEVELS:
        tail = (1.0 - float(level)) / 2.0
        lower = _pmf_quantile(pmf, tail)
        upper = _pmf_quantile(pmf, 1.0 - tail)
        covered = (margin >= lower) & (margin <= upper)
        label = str(int(round(level * 100)))
        out[f"interval_{label}_coverage"] = float(np.mean(covered))
        out[f"interval_{label}_mean_width"] = float(np.mean(upper - lower))
    return out


def _cover_calibration_intercept_slope(
    probability: np.ndarray,
    actual: np.ndarray,
) -> tuple[float, float]:
    """Unpenalized logistic calibration; NaN when mechanically non-estimable."""
    p = np.asarray(probability, dtype=float)
    y = np.asarray(actual, dtype=float)
    if len(p) != len(y) or len(p) == 0 or not np.isfinite(p).all() or not np.isfinite(y).all():
        return float("nan"), float("nan")
    if np.unique(y).size < 2:
        return float("nan"), float("nan")
    clipped = np.clip(p, LOGLOSS_FLOOR, 1.0 - LOGLOSS_FLOOR)
    logit = np.log(clipped) - np.log1p(-clipped)
    if float(np.std(logit)) <= CALIBRATION_DEGENERACY_TOL:
        return float("nan"), float("nan")

    def objective(beta: np.ndarray) -> float:
        eta = float(beta[0]) + float(beta[1]) * logit
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta))

    result = optimize.minimize(
        objective,
        np.asarray([0.0, 1.0], dtype=float),
        method="BFGS",
        options={"gtol": 1e-10, "maxiter": 1000},
    )
    if not result.success or not np.isfinite(result.x).all():
        return float("nan"), float("nan")
    return float(result.x[0]), float(result.x[1])


def _metrics_for_rows(meta: pd.DataFrame, pmf: np.ndarray) -> dict:
    validate_pmf(pmf)
    margin = pd.to_numeric(meta["margin"], errors="raise").to_numpy(dtype=float)
    spread = pd.to_numeric(meta["home_spread"], errors="raise").to_numpy(dtype=float)
    cpl = cover_push_loss_probabilities(pmf, spread)
    outcome_index = _observed_cpl_index(meta["ats_outcome"])
    row = np.arange(len(meta))
    cpl_logloss = -np.log(np.maximum(cpl[row, outcome_index], LOGLOSS_FLOOR))
    push_actual = (outcome_index == 1).astype(float)
    nonpush = outcome_index != 1
    binary = _binary_cover_probability(cpl)
    cover_actual = (outcome_index == 0).astype(float)
    if nonpush.any():
        binary_logloss = -(
            cover_actual[nonpush] * np.log(np.maximum(binary[nonpush], LOGLOSS_FLOOR))
            + (1.0 - cover_actual[nonpush])
            * np.log(np.maximum(1.0 - binary[nonpush], LOGLOSS_FLOOR))
        )
        brier = np.square(binary[nonpush] - cover_actual[nonpush])
        mean_brier = float(np.mean(brier))
        mean_binary_logloss = float(np.mean(binary_logloss))
        calibration_intercept, calibration_slope = _cover_calibration_intercept_slope(
            binary[nonpush], cover_actual[nonpush]
        )
    else:
        mean_brier = float("nan")
        mean_binary_logloss = float("nan")
        calibration_intercept = float("nan")
        calibration_slope = float("nan")
    expected, median = _margin_summaries(pmf)
    return {
        "n": int(len(meta)),
        "nonpush_n": int(nonpush.sum()),
        "mean_discrete_crps": float(np.mean(discrete_crps(pmf, margin))),
        "multinomial_cpl_logloss": float(np.mean(cpl_logloss)),
        "cover_brier_nonpush": mean_brier,
        "cover_logloss_nonpush": mean_binary_logloss,
        "cover_calibration_intercept": calibration_intercept,
        "cover_calibration_slope": calibration_slope,
        "mean_predicted_push": float(np.mean(cpl[:, 1])),
        "empirical_push_rate": float(np.mean(push_actual)),
        "push_calibration_error": float(np.mean(cpl[:, 1]) - np.mean(push_actual)),
        "expected_margin_mae": float(np.mean(np.abs(margin - expected))),
        "expected_margin_rmse": float(np.sqrt(np.mean(np.square(margin - expected)))),
        "median_margin_mae": float(np.mean(np.abs(margin - median))),
        "median_margin_rmse": float(np.sqrt(np.mean(np.square(margin - median)))),
        "mean_endpoint_mass": float(np.mean(endpoint_mass(pmf))),
        "max_endpoint_mass": float(np.max(endpoint_mass(pmf))),
        **_interval_metrics(pmf, margin),
    }


def q2_metric_table(metadata: pd.DataFrame, arms: dict[str, np.ndarray]) -> pd.DataFrame:
    rows: list[dict] = []
    groups: list[tuple[str, np.ndarray]] = [("ALL", np.arange(len(metadata), dtype=int))]
    for season, part in metadata.groupby("season", sort=True):
        groups.append((str(int(season)), part.index.to_numpy(dtype=int)))
    for season_label, idx in groups:
        meta = metadata.iloc[idx]
        for arm in sorted(arms):
            metrics = _metrics_for_rows(meta, np.asarray(arms[arm])[idx])
            rows.append({"season": season_label, "arm": arm, **metrics})
    return pd.DataFrame(rows)


def q2_fixed_slice_metrics(metadata: pd.DataFrame, arms: dict[str, np.ndarray]) -> pd.DataFrame:
    rows: list[dict] = []
    for slice_type, slice_name, mask in fixed_slice_masks(metadata):
        idx = np.flatnonzero(mask.to_numpy(dtype=bool))
        if len(idx) == 0:
            continue
        meta = metadata.iloc[idx]
        for arm in sorted(arms):
            metrics = _metrics_for_rows(meta, np.asarray(arms[arm])[idx])
            rows.append(
                {
                    "slice_type": slice_type,
                    "slice": slice_name,
                    "arm": arm,
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def q2_cover_reliability(metadata: pd.DataFrame, arms: dict[str, np.ndarray]) -> pd.DataFrame:
    rows: list[dict] = []
    spread = pd.to_numeric(metadata["home_spread"], errors="raise").to_numpy(dtype=float)
    observed = _observed_cpl_index(metadata["ats_outcome"])
    nonpush = observed != 1
    cover_actual = (observed == 0).astype(float)
    for arm in sorted(arms):
        cpl = cover_push_loss_probabilities(np.asarray(arms[arm]), spread)
        prob = _binary_cover_probability(cpl)
        for b in range(10):
            lower = float(RELIABILITY_EDGES[b])
            upper = float(RELIABILITY_EDGES[b + 1])
            if b == 9:
                mask = nonpush & (prob >= lower) & (prob <= upper)
            else:
                mask = nonpush & (prob >= lower) & (prob < upper)
            n = int(mask.sum())
            rows.append(
                {
                    "arm": arm,
                    "bin": b,
                    "lower": lower,
                    "upper": upper,
                    "n": n,
                    "mean_predicted_cover": float(np.mean(prob[mask])) if n else np.nan,
                    "empirical_cover_rate": float(np.mean(cover_actual[mask])) if n else np.nan,
                }
            )
    return pd.DataFrame(rows)


def q2_key_mass_calibration(metadata: pd.DataFrame, arms: dict[str, np.ndarray]) -> pd.DataFrame:
    """Report predicted versus observed mass at the five frozen absolute key margins."""
    margin = pd.to_numeric(metadata["margin"], errors="raise").to_numpy(dtype=float)
    groups: list[tuple[str, np.ndarray]] = [("ALL", np.arange(len(metadata), dtype=int))]
    for season, part in metadata.groupby("season", sort=True):
        groups.append((str(int(season)), part.index.to_numpy(dtype=int)))

    rows: list[dict] = []
    support_start = int(SUPPORT[0])
    for arm in sorted(arms):
        pmf = np.asarray(arms[arm], dtype=float)
        validate_pmf(pmf)
        if len(pmf) != len(metadata):
            raise ValueError(f"Q2 key calibration PMF rows do not align for {arm}")
        for season_label, idx in groups:
            y = margin[idx]
            p = pmf[idx]
            for key in KEY_MARGINS:
                neg_idx = int(-key - support_start)
                pos_idx = int(key - support_start)
                predicted_negative = float(np.mean(p[:, neg_idx]))
                predicted_positive = float(np.mean(p[:, pos_idx]))
                predicted_absolute = predicted_negative + predicted_positive
                observed_negative = float(np.mean(y == -float(key)))
                observed_positive = float(np.mean(y == float(key)))
                observed_absolute = observed_negative + observed_positive
                rows.append(
                    {
                        "season": season_label,
                        "arm": arm,
                        "absolute_key": int(key),
                        "n": int(len(idx)),
                        "predicted_negative_rate": predicted_negative,
                        "observed_negative_rate": observed_negative,
                        "predicted_positive_rate": predicted_positive,
                        "observed_positive_rate": observed_positive,
                        "predicted_absolute_rate": predicted_absolute,
                        "observed_absolute_rate": observed_absolute,
                        "absolute_key_calibration_error": float(
                            predicted_absolute - observed_absolute
                        ),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["season", "arm", "absolute_key"], kind="mergesort"
    ).reset_index(drop=True)

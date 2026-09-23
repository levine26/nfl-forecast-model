from __future__ import annotations

"""Pre-result reporting contract for ATS NextGen Q3 Stage C."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from nfl_forecast.challenger_ats_nextgen_q1_reporting import fixed_slice_masks
from nfl_forecast.challenger_ats_nextgen_q3 import (
    KEY_SPREADS,
    LOGLOSS_FLOOR,
    multinomial_log_loss,
)

ARMS = ("Q3_M2", "Q3")
PREFIX = {"Q3_M2": "q3_m2", "Q3": "q3"}
RELIABILITY_EDGES = np.linspace(0.0, 1.0, 11)


def _probabilities(oof: pd.DataFrame, arm: str) -> np.ndarray:
    if arm not in PREFIX:
        raise ValueError("Q3 reporting arm is outside frozen set")
    prefix = PREFIX[arm]
    p = oof[[f"{prefix}_p_cover", f"{prefix}_p_push", f"{prefix}_p_loss"]].to_numpy(
        dtype=float
    )
    if not np.isfinite(p).all() or (p < 0.0).any() or (p > 1.0).any():
        raise RuntimeError("Q3 reporting received invalid probabilities")
    if not np.allclose(p.sum(axis=1), 1.0, atol=1e-12, rtol=0.0):
        raise RuntimeError("Q3 reporting probability rows do not sum to one")
    return p


def _outcome_index(oof: pd.DataFrame) -> np.ndarray:
    mapping = {"HOME_COVER": 0, "PUSH": 1, "HOME_LOSS": 2}
    idx = oof["ats_outcome"].astype(str).map(mapping)
    if idx.isna().any():
        raise ValueError("Q3 reporting encountered unknown ATS outcome")
    return idx.to_numpy(dtype=int)


def _conditional_cover(p: np.ndarray) -> np.ndarray:
    denom = p[:, 0] + p[:, 2]
    if not np.isfinite(denom).all() or (denom <= 0.0).any():
        raise RuntimeError("Q3 conditional cover denominator is invalid")
    return p[:, 0] / denom


def _calibration_intercept_slope(prob: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    p = np.asarray(prob, dtype=float)
    y = np.asarray(actual, dtype=int)
    if len(p) < 2 or set(np.unique(y).tolist()) != {0, 1}:
        return float("nan"), float("nan")
    clipped = np.clip(p, LOGLOSS_FLOOR, 1.0 - LOGLOSS_FLOOR)
    logit = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
    model = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        fit_intercept=True,
        class_weight=None,
        max_iter=2000,
    )
    model.fit(logit, y)
    if int(model.n_iter_[0]) >= 2000:
        return float("nan"), float("nan")
    return float(model.intercept_[0]), float(model.coef_[0, 0])


def _metrics(oof: pd.DataFrame, arm: str) -> dict:
    p = _probabilities(oof, arm)
    outcome = _outcome_index(oof)
    row_loss = multinomial_log_loss(p, outcome)
    nonpush = outcome != 1
    q = _conditional_cover(p)
    cover_actual = (outcome == 0).astype(float)
    if nonpush.any():
        q_np = q[nonpush]
        y_np = cover_actual[nonpush]
        brier = float(np.mean(np.square(q_np - y_np)))
        binary_logloss = float(
            np.mean(
                -(
                    y_np * np.log(np.maximum(q_np, LOGLOSS_FLOOR))
                    + (1.0 - y_np) * np.log(np.maximum(1.0 - q_np, LOGLOSS_FLOOR))
                )
            )
        )
        intercept, slope = _calibration_intercept_slope(q_np, y_np.astype(int))
    else:
        brier = binary_logloss = intercept = slope = float("nan")
    push_actual = (outcome == 1).astype(float)
    return {
        "n": int(len(oof)),
        "nonpush_n": int(nonpush.sum()),
        "push_n": int((outcome == 1).sum()),
        "multinomial_cpl_logloss": float(np.mean(row_loss)),
        "cover_brier_nonpush": brier,
        "cover_logloss_nonpush": binary_logloss,
        "cover_calibration_intercept": intercept,
        "cover_calibration_slope": slope,
        "mean_predicted_push": float(np.mean(p[:, 1])),
        "empirical_push_rate": float(np.mean(push_actual)),
        "push_calibration_error": float(np.mean(p[:, 1]) - np.mean(push_actual)),
    }


def q3_metric_table(oof: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    groups: list[tuple[str, pd.DataFrame]] = [("ALL", oof)]
    for season, part in oof.groupby("season", sort=True):
        groups.append((str(int(season)), part))
    for season_label, part in groups:
        for arm in ARMS:
            rows.append({"season": season_label, "arm": arm, **_metrics(part, arm)})
    return pd.DataFrame(rows)


def q3_cover_reliability(oof: pd.DataFrame) -> pd.DataFrame:
    outcome = _outcome_index(oof)
    nonpush = outcome != 1
    actual = (outcome == 0).astype(float)
    rows: list[dict] = []
    for arm in ARMS:
        q = _conditional_cover(_probabilities(oof, arm))
        for b in range(10):
            lower = float(RELIABILITY_EDGES[b])
            upper = float(RELIABILITY_EDGES[b + 1])
            if b == 9:
                mask = nonpush & (q >= lower) & (q <= upper)
            else:
                mask = nonpush & (q >= lower) & (q < upper)
            n = int(mask.sum())
            rows.append(
                {
                    "arm": arm,
                    "bin": b,
                    "lower": lower,
                    "upper": upper,
                    "n": n,
                    "mean_predicted_cover": float(np.mean(q[mask])) if n else np.nan,
                    "empirical_cover_rate": float(np.mean(actual[mask])) if n else np.nan,
                }
            )
    return pd.DataFrame(rows)


def q3_push_calibration(oof: pd.DataFrame) -> pd.DataFrame:
    outcome = _outcome_index(oof)
    actual = (outcome == 1).astype(float)
    size = np.abs(pd.to_numeric(oof["home_spread"], errors="raise").to_numpy(dtype=float))
    season_values = pd.to_numeric(oof["season"], errors="raise").astype(int).to_numpy()
    groups: list[tuple[str, str, np.ndarray]] = [("overall", "ALL", np.ones(len(oof), dtype=bool))]
    for season in sorted(np.unique(season_values)):
        groups.append(("season", str(int(season)), season_values == season))
    for key in KEY_SPREADS:
        groups.append(
            (
                "key_number",
                f"K{int(key)}",
                np.isclose(size, float(key), atol=1e-9, rtol=0.0),
            )
        )
    rows: list[dict] = []
    for group_type, group, mask in groups:
        if not mask.any():
            continue
        for arm in ARMS:
            p = _probabilities(oof, arm)
            rows.append(
                {
                    "group_type": group_type,
                    "group": group,
                    "arm": arm,
                    "n": int(mask.sum()),
                    "mean_predicted_push": float(np.mean(p[mask, 1])),
                    "empirical_push_rate": float(np.mean(actual[mask])),
                    "push_calibration_error": float(np.mean(p[mask, 1]) - np.mean(actual[mask])),
                }
            )
    return pd.DataFrame(rows)


def q3_fixed_slice_metrics(oof: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for slice_type, slice_name, mask in fixed_slice_masks(oof):
        part = oof.loc[mask].copy()
        if part.empty:
            continue
        for arm in ARMS:
            rows.append(
                {
                    "slice_type": slice_type,
                    "slice": slice_name,
                    "arm": arm,
                    **_metrics(part, arm),
                }
            )
    return pd.DataFrame(rows)

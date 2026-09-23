from __future__ import annotations

"""Pre-result fixed-slice reporting for ATS NextGen Q1 Stage A."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_pinball_loss

from nfl_forecast.challenger_ats_nextgen_q1 import QUANTILES, QUANTILE_LABELS

KEY_NUMBER_BUCKETS = {
    "K3": (2.5, 3.0, 3.5),
    "K6": (5.5, 6.0, 6.5),
    "K7": (6.5, 7.0, 7.5),
    "K10": (9.5, 10.0, 10.5),
    "K14": (13.5, 14.0, 14.5),
}
FAVORITE_SIZE_BUCKETS = (
    ("FAV_LT3", 0.0, 3.0, False),
    ("FAV_3_LT7", 3.0, 7.0, False),
    ("FAV_7_LT10", 7.0, 10.0, False),
    ("FAV_10_LT14", 10.0, 14.0, False),
    ("FAV_GE14", 14.0, np.inf, True),
)
TOTAL_BUCKETS = (
    ("TOTAL_LT42", -np.inf, 42.0, False),
    ("TOTAL_42_LT45", 42.0, 45.0, False),
    ("TOTAL_45_LT48", 45.0, 48.0, False),
    ("TOTAL_GE48", 48.0, np.inf, True),
)


def _range_mask(values: pd.Series, lower: float, upper: float, last: bool) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if last:
        return numeric.ge(lower)
    return numeric.ge(lower) & numeric.lt(upper)


def fixed_slice_masks(oof: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    favorite = pd.to_numeric(oof["favorite_size"], errors="coerce")
    total = pd.to_numeric(oof["market_total"], errors="coerce")
    slices: list[tuple[str, str, pd.Series]] = []

    for name, values in KEY_NUMBER_BUCKETS.items():
        mask = favorite.isin(list(values))
        slices.append(("key_number", name, mask))
    for name, lower, upper, last in FAVORITE_SIZE_BUCKETS:
        slices.append(("favorite_size", name, _range_mask(favorite, lower, upper, last)))
    for name, lower, upper, last in TOTAL_BUCKETS:
        slices.append(("market_total", name, _range_mask(total, lower, upper, last)))
    return slices


def q1_fixed_slice_metrics(oof: pd.DataFrame) -> pd.DataFrame:
    """Report only the slices frozen in EVALUATION_PROTOCOL.md."""
    rows: list[dict] = []
    y_all = pd.to_numeric(oof["ats_residual"], errors="raise")
    for slice_type, slice_name, mask in fixed_slice_masks(oof):
        part = oof.loc[mask].copy()
        if part.empty:
            continue
        y = y_all.loc[mask].to_numpy(dtype=float)
        for arm, prefix in (("M0", "m0"), ("M2", "m2"), ("Q1", "q1")):
            for label, quantile in zip(QUANTILE_LABELS, QUANTILES, strict=True):
                pred = pd.to_numeric(
                    part[f"{prefix}_q_{label}"], errors="raise"
                ).to_numpy(dtype=float)
                coverage = float(np.mean(y <= pred))
                rows.append(
                    {
                        "slice_type": slice_type,
                        "slice": slice_name,
                        "arm": arm,
                        "quantile_label": label,
                        "quantile": float(quantile),
                        "n": int(len(part)),
                        "pinball_loss": float(
                            mean_pinball_loss(y, pred, alpha=float(quantile))
                        ),
                        "empirical_coverage": coverage,
                        "coverage_error": float(coverage - float(quantile)),
                    }
                )
    return pd.DataFrame(rows)

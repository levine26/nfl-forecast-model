from __future__ import annotations

"""Research-only statistical evaluation for paired LevLine forecasts.

This module deliberately has no production imports and no side effects.  It compares
predictions that refer to the same historical games, preserves chronology metadata, and
reports uncertainty instead of treating a small aggregate backtest edge as definitive.
"""

from dataclasses import dataclass
from math import erfc, sqrt
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

EPS = 1e-6
DEFAULT_SEED = 26


@dataclass(frozen=True)
class BootstrapResult:
    metric: str
    candidate: str
    reference: str
    block: str
    observed_delta: float
    ci_lower: float
    ci_upper: float
    probability_better: float
    samples: int


@dataclass(frozen=True)
class PairedTestResult:
    loss: str
    candidate: str
    reference: str
    block: str
    mean_loss_delta: float
    statistic: float
    p_value_two_sided: float
    blocks: int


def _clip(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _usable(frame: pd.DataFrame, target_col: str, *probability_cols: str) -> pd.DataFrame:
    columns = [target_col, *probability_cols]
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing forecast-comparison columns: {missing}")
    out = frame.copy()
    mask = out[target_col].notna()
    for column in probability_cols:
        mask &= pd.to_numeric(out[column], errors="coerce").notna()
    out = out.loc[mask].copy()
    if out.empty:
        raise ValueError("No paired forecast rows are usable")
    return out


def _metric_value(y: np.ndarray, p: np.ndarray, metric: str) -> float:
    p = _clip(p)
    y = np.asarray(y, dtype=int)
    if metric == "accuracy":
        return float(((p >= 0.5).astype(int) == y).mean())
    if metric == "brier":
        return float(brier_score_loss(y, p))
    if metric == "log_loss":
        return float(log_loss(y, p, labels=[0, 1]))
    raise ValueError("metric must be accuracy, brier, or log_loss")


def _point_losses(y: np.ndarray, p: np.ndarray, loss: str) -> np.ndarray:
    y = np.asarray(y, dtype=int)
    p = _clip(p)
    if loss == "brier":
        return (p - y) ** 2
    if loss == "log_loss":
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))
    if loss == "error":
        return ((p >= 0.5).astype(int) != y).astype(float)
    raise ValueError("loss must be brier, log_loss, or error")


def forecast_metrics(
    frame: pd.DataFrame,
    probability_col: str,
    *,
    target_col: str = "home_win",
) -> dict[str, float]:
    data = _usable(frame, target_col, probability_col)
    y = data[target_col].astype(int).to_numpy()
    p = _clip(pd.to_numeric(data[probability_col], errors="coerce"))
    return {
        "games": int(len(data)),
        "winner_pct": _metric_value(y, p, "accuracy"),
        "brier": _metric_value(y, p, "brier"),
        "log_loss": _metric_value(y, p, "log_loss"),
    }


def calibration_diagnostics(
    frame: pd.DataFrame,
    probability_col: str,
    *,
    target_col: str = "home_win",
    bins: int = 10,
) -> tuple[dict[str, float], pd.DataFrame]:
    """Return calibration intercept/slope plus fixed-width probability bins."""
    data = _usable(frame, target_col, probability_col)
    y = data[target_col].astype(int).to_numpy()
    p = _clip(pd.to_numeric(data[probability_col], errors="coerce"))
    logits = np.log(p / (1.0 - p)).reshape(-1, 1)

    intercept = np.nan
    slope = np.nan
    if len(np.unique(y)) == 2:
        model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=5000)
        model.fit(logits, y)
        intercept = float(model.intercept_[0])
        slope = float(model.coef_[0, 0])

    edges = np.linspace(0.0, 1.0, bins + 1)
    bucket = np.minimum(np.digitize(p, edges[1:-1], right=False), bins - 1)
    rows: list[dict] = []
    for idx in range(bins):
        mask = bucket == idx
        rows.append(
            {
                "bin": idx,
                "lower": float(edges[idx]),
                "upper": float(edges[idx + 1]),
                "games": int(mask.sum()),
                "mean_probability": float(p[mask].mean()) if mask.any() else np.nan,
                "observed_rate": float(y[mask].mean()) if mask.any() else np.nan,
            }
        )
    summary = {
        "games": int(len(data)),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }
    return summary, pd.DataFrame(rows)


def _block_keys(data: pd.DataFrame, block_cols: Sequence[str] | None) -> tuple[np.ndarray, str]:
    if not block_cols:
        return np.arange(len(data), dtype=int), "row"
    missing = [c for c in block_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Missing bootstrap block columns: {missing}")
    keys = data[list(block_cols)].astype("string").fillna("<NA>").agg("|".join, axis=1)
    codes, _ = pd.factorize(keys, sort=False)
    return codes.astype(int), "+".join(block_cols)


def paired_bootstrap(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    metric: str = "brier",
    target_col: str = "home_win",
    block_cols: Sequence[str] | None = None,
    samples: int = 2000,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> BootstrapResult:
    """Paired bootstrap candidate-minus-reference metric deltas.

    Lower deltas are better for Brier/log loss; higher deltas are better for accuracy.
    Blocking resamples whole weeks or seasons and therefore does not pretend every game
    is an independent draw.
    """
    if samples < 100:
        raise ValueError("samples must be at least 100")
    data = _usable(frame, target_col, candidate_col, reference_col).reset_index(drop=True)
    y = data[target_col].astype(int).to_numpy()
    candidate = _clip(pd.to_numeric(data[candidate_col], errors="coerce"))
    reference = _clip(pd.to_numeric(data[reference_col], errors="coerce"))
    codes, block_name = _block_keys(data, block_cols)
    unique_blocks = np.unique(codes)
    indices = {block: np.flatnonzero(codes == block) for block in unique_blocks}
    rng = np.random.default_rng(seed)

    observed = _metric_value(y, candidate, metric) - _metric_value(y, reference, metric)
    draws = np.empty(samples, dtype=float)
    for draw in range(samples):
        chosen = rng.choice(unique_blocks, size=len(unique_blocks), replace=True)
        sample_idx = np.concatenate([indices[int(block)] for block in chosen])
        draws[draw] = _metric_value(y[sample_idx], candidate[sample_idx], metric) - _metric_value(
            y[sample_idx], reference[sample_idx], metric
        )

    lower, upper = np.quantile(draws, [alpha / 2.0, 1.0 - alpha / 2.0])
    if metric == "accuracy":
        p_better = float((draws > 0.0).mean())
    else:
        p_better = float((draws < 0.0).mean())
    return BootstrapResult(
        metric=metric,
        candidate=candidate_col,
        reference=reference_col,
        block=block_name,
        observed_delta=float(observed),
        ci_lower=float(lower),
        ci_upper=float(upper),
        probability_better=p_better,
        samples=int(samples),
    )


def paired_loss_difference_test(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    loss: str = "brier",
    target_col: str = "home_win",
    block_cols: Sequence[str] = ("season", "week"),
) -> PairedTestResult:
    """Supplemental Diebold-Mariano-style paired loss-difference diagnostic.

    NFL games within a week share information shocks, so the default reduces point-loss
    differences to week blocks before estimating the standard error.  This is a simple
    large-sample diagnostic, not a substitute for the block bootstrap.
    """
    data = _usable(frame, target_col, candidate_col, reference_col).reset_index(drop=True)
    y = data[target_col].astype(int).to_numpy()
    candidate = _clip(pd.to_numeric(data[candidate_col], errors="coerce"))
    reference = _clip(pd.to_numeric(data[reference_col], errors="coerce"))
    diff = _point_losses(y, candidate, loss) - _point_losses(y, reference, loss)
    data = data.assign(_loss_diff=diff)
    missing = [c for c in block_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Missing paired-test block columns: {missing}")
    blocked = data.groupby(list(block_cols), dropna=False, sort=True)["_loss_diff"].mean()
    n = int(len(blocked))
    if n < 3:
        raise ValueError("Need at least three independent blocks for paired test")
    mean = float(blocked.mean())
    std = float(blocked.std(ddof=1))
    statistic = 0.0 if std == 0.0 else mean / (std / sqrt(n))
    p_value = float(erfc(abs(statistic) / sqrt(2.0)))
    return PairedTestResult(
        loss=loss,
        candidate=candidate_col,
        reference=reference_col,
        block="+".join(block_cols),
        mean_loss_delta=mean,
        statistic=float(statistic),
        p_value_two_sided=p_value,
        blocks=n,
    )


def standard_slices(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    target_col: str = "home_win",
    market_col: str = "market_prob",
) -> pd.DataFrame:
    """Evaluate stable, predeclared historical slices when the necessary fields exist."""
    data = _usable(frame, target_col, candidate_col, reference_col).copy()
    rows: list[dict] = []

    def add(slice_family: str, slice_value: str, subset: pd.DataFrame) -> None:
        if subset.empty:
            return
        c = forecast_metrics(subset, candidate_col, target_col=target_col)
        r = forecast_metrics(subset, reference_col, target_col=target_col)
        rows.append(
            {
                "slice_family": slice_family,
                "slice_value": slice_value,
                "games": c["games"],
                "candidate_winner_pct": c["winner_pct"],
                "reference_winner_pct": r["winner_pct"],
                "winner_delta": c["winner_pct"] - r["winner_pct"],
                "candidate_brier": c["brier"],
                "reference_brier": r["brier"],
                "brier_delta": c["brier"] - r["brier"],
                "candidate_log_loss": c["log_loss"],
                "reference_log_loss": r["log_loss"],
                "log_loss_delta": c["log_loss"] - r["log_loss"],
            }
        )

    if "season" in data.columns:
        for season, subset in data.groupby("season", sort=True):
            add("season", str(season), subset)
    if "week" in data.columns:
        week = pd.to_numeric(data.week, errors="coerce")
        phase = np.select([week <= 6, week <= 12], ["early", "mid"], default="late")
        for value in ("early", "mid", "late"):
            add("season_phase", value, data.loc[phase == value])
    if market_col in data.columns:
        market = pd.to_numeric(data[market_col], errors="coerce")
        add("market_side", "home_favorite", data.loc[market > 0.5])
        add("market_side", "home_underdog", data.loc[market < 0.5])
        disagreement = (pd.to_numeric(data[candidate_col], errors="coerce") - market).abs()
        usable = disagreement.notna()
        if int(usable.sum()) >= 20:
            q1, q2 = disagreement[usable].quantile([1 / 3, 2 / 3])
            add("market_disagreement", "low", data.loc[disagreement <= q1])
            add("market_disagreement", "mid", data.loc[(disagreement > q1) & (disagreement <= q2)])
            add("market_disagreement", "high", data.loc[disagreement > q2])
    if {"home_qb_starter_changed", "away_qb_starter_changed"}.issubset(data.columns):
        qb_change = (
            pd.to_numeric(data.home_qb_starter_changed, errors="coerce").fillna(0).gt(0)
            | pd.to_numeric(data.away_qb_starter_changed, errors="coerce").fillna(0).gt(0)
        )
        add("qb_change", "change", data.loc[qb_change])
        add("qb_change", "stable", data.loc[~qb_change])
    if "injury_availability_heavy" in data.columns:
        heavy = data.injury_availability_heavy.fillna(False).astype(bool)
        add("availability", "heavy", data.loc[heavy])
        add("availability", "ordinary", data.loc[~heavy])
    return pd.DataFrame(rows)


def compare_forecasts(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    target_col: str = "home_win",
    bootstrap_samples: int = 2000,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """Full paired comparison used by serious challenger candidates."""
    data = _usable(frame, target_col, candidate_col, reference_col)
    candidate = forecast_metrics(data, candidate_col, target_col=target_col)
    reference = forecast_metrics(data, reference_col, target_col=target_col)
    calibration, bins = calibration_diagnostics(data, candidate_col, target_col=target_col)

    bootstrap: list[dict] = []
    for metric in ("accuracy", "brier", "log_loss"):
        for blocks in (None, ("season", "week"), ("season",)):
            if blocks is not None and not set(blocks).issubset(data.columns):
                continue
            result = paired_bootstrap(
                data,
                candidate_col,
                reference_col,
                metric=metric,
                target_col=target_col,
                block_cols=blocks,
                samples=bootstrap_samples,
                seed=seed,
            )
            bootstrap.append(result.__dict__)

    paired_tests = []
    if {"season", "week"}.issubset(data.columns):
        for loss in ("brier", "log_loss", "error"):
            paired_tests.append(
                paired_loss_difference_test(
                    data,
                    candidate_col,
                    reference_col,
                    loss=loss,
                    target_col=target_col,
                ).__dict__
            )
    return {
        "candidate": candidate,
        "reference": reference,
        "metric_deltas": {
            "winner_pct": candidate["winner_pct"] - reference["winner_pct"],
            "brier": candidate["brier"] - reference["brier"],
            "log_loss": candidate["log_loss"] - reference["log_loss"],
        },
        "candidate_calibration": calibration,
        "calibration_bins": bins,
        "bootstrap": pd.DataFrame(bootstrap),
        "paired_tests": pd.DataFrame(paired_tests),
        "slices": standard_slices(data, candidate_col, reference_col, target_col=target_col),
    }


def confidence_set_approximation(
    frame: pd.DataFrame,
    model_cols: Sequence[str],
    *,
    target_col: str = "home_win",
    primary_metric: str = "brier",
    block_cols: Sequence[str] = ("season", "week"),
    bootstrap_samples: int = 2000,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Conservative multiple-model uncertainty set.

    The empirically best model is retained. Any other model is also retained unless a
    paired block-bootstrap confidence interval says it is strictly worse than the best.
    This is intentionally labeled an approximation rather than Hansen's formal MCS.
    """
    if len(model_cols) < 2:
        raise ValueError("Need at least two models for confidence-set comparison")
    data = _usable(frame, target_col, *model_cols)
    metrics = {
        column: _metric_value(
            data[target_col].astype(int).to_numpy(),
            pd.to_numeric(data[column], errors="coerce").to_numpy(),
            primary_metric,
        )
        for column in model_cols
    }
    best = max(metrics, key=metrics.get) if primary_metric == "accuracy" else min(metrics, key=metrics.get)
    rows = []
    for column in model_cols:
        if column == best:
            rows.append(
                {
                    "model": column,
                    "best_model": best,
                    "primary_metric": primary_metric,
                    "metric": metrics[column],
                    "delta_vs_best": 0.0,
                    "ci_lower": 0.0,
                    "ci_upper": 0.0,
                    "in_confidence_set": True,
                }
            )
            continue
        result = paired_bootstrap(
            data,
            column,
            best,
            metric=primary_metric,
            target_col=target_col,
            block_cols=block_cols,
            samples=bootstrap_samples,
            seed=seed,
            alpha=alpha,
        )
        strictly_worse = result.ci_upper < 0 if primary_metric == "accuracy" else result.ci_lower > 0
        rows.append(
            {
                "model": column,
                "best_model": best,
                "primary_metric": primary_metric,
                "metric": metrics[column],
                "delta_vs_best": result.observed_delta,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
                "in_confidence_set": not strictly_worse,
            }
        )
    return pd.DataFrame(rows).sort_values(["in_confidence_set", "metric"], ascending=[False, primary_metric != "accuracy"])

from __future__ import annotations

"""Shared scientific scaffold for Spread & Points Phase 3.

Research only. This module intentionally fails closed for 2025+ challenger targets.
All A0/B0/C0/D code imports chronology, identity, metric and bootstrap helpers from
this file so candidate implementations cannot silently define their own folds.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, mean_poisson_deviance

TRAINING_FLOOR = 2016
INNER_VALIDATION_START = 2019
DEVELOPMENT_SEASONS = (2022, 2023, 2024)
FORBIDDEN_PHASE3_SEASONS = frozenset({2025})
COMPLETED_2026_FLOOR = 2026
MARKET_HORIZON_LABEL = "historical_closing_late_benchmark_exact_horizon_opaque"
SOURCE_CONTRACT_VERSION = "phase3-feature-provenance-v1"
BASE_SEED = 2603

A0_ID = "A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1"
B0_ID = "B0-POSSESSION-DRIVE-SCORE-PROCESS-V1"
C0_ID = "C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1"
D_MARGIN_ID = "D-CONVEX-MARGIN-V1"
D_TOTAL_ID = "D-CONVEX-TOTAL-V1"

A0_ALPHA_GRID = (0.1, 1.0, 10.0, 100.0)
A0_HALF_LIFE_GRID = (4, 8, 16, 32)
A0_FALLBACK = (10.0, 16)
B0_DRIVE_ALPHA_GRID = (0.0, 0.1, 1.0, 10.0)
B0_DRIVE_ALPHA_FALLBACK = 1.0
B0_OUTCOME_C_GRID = (0.05, 0.2, 1.0, 5.0)
B0_OUTCOME_C_FALLBACK = 0.2
C0_ALPHA_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
C0_ALPHA_FALLBACK = 1.0
B0_SIMULATIONS = 10_000
RZ_PRIOR_STRENGTH = 20.0
EWMA_HALF_LIFE = 8.0


@dataclass(frozen=True)
class OuterFold:
    target_season: int
    train_start: int
    train_end: int
    inner_validation_seasons: tuple[int, ...]


class Phase3FirewallError(RuntimeError):
    pass


def guard_phase3_target_seasons(seasons: Iterable[int]) -> tuple[int, ...]:
    vals = tuple(int(s) for s in seasons)
    if not vals:
        raise Phase3FirewallError("Phase 3 requires at least one target season")
    bad_holdout = sorted(set(vals).intersection(FORBIDDEN_PHASE3_SEASONS))
    if bad_holdout:
        raise Phase3FirewallError(
            f"2025 challenger output is blocked in Phase 3: requested {bad_holdout}"
        )
    bad_future = sorted(s for s in vals if s >= COMPLETED_2026_FLOOR)
    if bad_future:
        raise Phase3FirewallError(
            f"completed-2026-or-later outcomes are blocked from Phase 3 selection: {bad_future}"
        )
    if any(s < TRAINING_FLOOR for s in vals):
        raise Phase3FirewallError("target season predates the frozen 2016 training floor")
    return vals


def assert_phase3_loaded_universe(frame: pd.DataFrame, *, season_col: str = "season") -> None:
    seasons = pd.to_numeric(frame[season_col], errors="coerce").dropna().astype(int)
    if seasons.empty:
        raise Phase3FirewallError("loaded universe has no seasons")
    if (seasons >= 2025).any():
        seen = sorted(seasons[seasons >= 2025].unique().tolist())
        raise Phase3FirewallError(
            f"Phase 3 loaded forbidden 2025+ outcomes/source rows: {seen}"
        )
    if int(seasons.min()) < TRAINING_FLOOR:
        raise Phase3FirewallError(
            f"Phase 3 loaded pre-{TRAINING_FLOOR} rows contrary to frozen floor"
        )


def inner_validation_seasons(outer_target: int) -> tuple[int, ...]:
    outer_target = int(outer_target)
    eligible = list(range(INNER_VALIDATION_START, outer_target))
    return tuple(eligible[-4:])


def outer_fold(target_season: int) -> OuterFold:
    target_season = guard_phase3_target_seasons([target_season])[0]
    if target_season <= TRAINING_FLOOR:
        raise Phase3FirewallError("outer target must have prior training history")
    return OuterFold(
        target_season=target_season,
        train_start=TRAINING_FLOOR,
        train_end=target_season - 1,
        inner_validation_seasons=inner_validation_seasons(target_season),
    )


def assert_prior_only(train: pd.DataFrame, valid: pd.DataFrame, *, season_col: str = "season") -> None:
    tr = pd.to_numeric(train[season_col], errors="coerce").dropna().astype(int)
    va = pd.to_numeric(valid[season_col], errors="coerce").dropna().astype(int)
    if tr.empty or va.empty:
        raise Phase3FirewallError("chronology check received empty train/validation season set")
    if int(tr.max()) >= int(va.min()):
        raise Phase3FirewallError(
            f"future/same-season leakage: train max={int(tr.max())}, validation min={int(va.min())}"
        )


def canonical_targets(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["actual_margin"] = (
        pd.to_numeric(out["home_score"], errors="coerce")
        - pd.to_numeric(out["away_score"], errors="coerce")
    )
    out["actual_total"] = (
        pd.to_numeric(out["home_score"], errors="coerce")
        + pd.to_numeric(out["away_score"], errors="coerce")
    )
    return out


def reconstruct_scores(total: np.ndarray | pd.Series, margin: np.ndarray | pd.Series) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray(total, dtype=float)
    m = np.asarray(margin, dtype=float)
    return (t + m) / 2.0, (t - m) / 2.0


def market_margin_from_schedule(frame: pd.DataFrame) -> pd.Series:
    # Canonical repository convention: positive spread_line means market-implied home margin.
    return pd.to_numeric(frame["spread_line"], errors="coerce")


def fixed_ewma_alpha(half_life: float = EWMA_HALF_LIFE) -> float:
    return float(1.0 - math.exp(math.log(0.5) / float(half_life)))


def shifted_ewma(series: pd.Series, half_life: float = EWMA_HALF_LIFE) -> pd.Series:
    return series.shift(1).ewm(halflife=float(half_life), adjust=False, min_periods=1).mean()


def stable_seed(candidate_id: str, game_id: str, *, base_seed: int = BASE_SEED) -> int:
    payload = f"{candidate_id}|{game_id}|{base_seed}".encode("utf-8")
    return int.from_bytes(sha256(payload).digest()[:4], "big", signed=False)


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def file_sha(paths: Sequence[str | Path]) -> str:
    h = sha256()
    for path in sorted(str(Path(p)) for p in paths):
        p = Path(path)
        h.update(path.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def finite_or_nan(value) -> float:
    try:
        value = float(value)
    except Exception:
        return float("nan")
    return value if np.isfinite(value) else float("nan")


def numeric_metrics(actual, pred) -> dict:
    a = pd.to_numeric(pd.Series(actual), errors="coerce")
    p = pd.to_numeric(pd.Series(pred), errors="coerce")
    mask = a.notna() & p.notna() & np.isfinite(a) & np.isfinite(p)
    a = a.loc[mask].to_numpy(dtype=float)
    p = p.loc[mask].to_numpy(dtype=float)
    if not len(a):
        return {"games": 0, "mae": None, "rmse": None, "bias_actual_minus_pred": None, "residual_sd": None}
    residual = a - p
    return {
        "games": int(len(a)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "bias_actual_minus_pred": float(np.mean(residual)),
        "residual_sd": float(np.std(residual, ddof=1)) if len(residual) > 1 else 0.0,
    }


def probability_metrics(actual_home_win, probability_home_win) -> dict:
    y = pd.to_numeric(pd.Series(actual_home_win), errors="coerce")
    p = pd.to_numeric(pd.Series(probability_home_win), errors="coerce")
    mask = y.notna() & p.notna() & y.isin([0, 1]) & np.isfinite(p)
    y = y.loc[mask].astype(int).to_numpy()
    p = np.clip(p.loc[mask].astype(float).to_numpy(), 1e-9, 1.0 - 1e-9)
    if not len(y):
        return {"games": 0, "winner_accuracy": None, "brier": None, "log_loss": None}
    return {
        "games": int(len(y)),
        "winner_accuracy": float(np.mean((p >= 0.5).astype(int) == y)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def poisson_deviance_safe(actual, pred) -> float:
    y = np.asarray(actual, dtype=float)
    mu = np.clip(np.asarray(pred, dtype=float), 1e-6, None)
    return float(mean_poisson_deviance(y, mu))


def gaussian_crps(actual, mean, sigma) -> float:
    """Mean Gaussian CRPS without scipy.stats dependency in the hot loop."""
    from scipy.special import erf

    y = np.asarray(actual, dtype=float)
    mu = np.asarray(mean, dtype=float)
    sig = np.asarray(sigma, dtype=float)
    mask = np.isfinite(y) & np.isfinite(mu) & np.isfinite(sig) & (sig > 0)
    if not mask.any():
        return float("nan")
    z = (y[mask] - mu[mask]) / sig[mask]
    phi = np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)
    Phi = 0.5 * (1.0 + erf(z / np.sqrt(2.0)))
    values = sig[mask] * (z * (2.0 * Phi - 1.0) + 2.0 * phi - 1.0 / np.sqrt(np.pi))
    return float(np.mean(values))


def empirical_crps(actual: float, samples: np.ndarray) -> float:
    s = np.asarray(samples, dtype=float)
    s = s[np.isfinite(s)]
    if not len(s):
        return float("nan")
    # CRPS(F,y) = E|X-y| - 0.5 E|X-X'|. The second term can be computed
    # exactly from sorted samples in O(n log n), avoiding an O(n^2) matrix.
    first = float(np.mean(np.abs(s - float(actual))))
    ss = np.sort(s)
    n = len(ss)
    coeff = 2.0 * np.arange(1, n + 1) - n - 1.0
    pair_mean = float(2.0 * np.sum(coeff * ss) / (n * n))
    return first - 0.5 * pair_mean


def empirical_energy_score(actual_home: float, actual_away: float, samples: np.ndarray, *, seed: int = BASE_SEED) -> float:
    sims = np.asarray(samples, dtype=float)
    if sims.ndim != 2 or sims.shape[1] != 2 or not len(sims):
        return float("nan")
    y = np.array([float(actual_home), float(actual_away)], dtype=float)
    first = float(np.mean(np.linalg.norm(sims - y, axis=1)))
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(sims))
    second = float(np.mean(np.linalg.norm(sims - sims[perm], axis=1)))
    return first - 0.5 * second


def interval_metrics(actual, lower, upper) -> dict:
    a = np.asarray(actual, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    mask = np.isfinite(a) & np.isfinite(lo) & np.isfinite(hi)
    if not mask.any():
        return {"games": 0, "coverage": None, "mean_width": None}
    return {
        "games": int(mask.sum()),
        "coverage": float(np.mean((a[mask] >= lo[mask]) & (a[mask] <= hi[mask]))),
        "mean_width": float(np.mean(hi[mask] - lo[mask])),
    }


def paired_market_metrics(actual, candidate, market) -> dict:
    a = np.asarray(actual, dtype=float)
    c = np.asarray(candidate, dtype=float)
    m = np.asarray(market, dtype=float)
    mask = np.isfinite(a) & np.isfinite(c) & np.isfinite(m)
    if not mask.any():
        return {"games": 0}
    ae_c = np.abs(a[mask] - c[mask])
    ae_m = np.abs(a[mask] - m[mask])
    delta = ae_c - ae_m
    return {
        "games": int(mask.sum()),
        "candidate_mae": float(ae_c.mean()),
        "market_mae": float(ae_m.mean()),
        "candidate_minus_market_mae": float(delta.mean()),
        "closer_rate_candidate": float(np.mean(ae_c < ae_m)),
        "tie_rate": float(np.mean(np.isclose(ae_c, ae_m))),
        "candidate_residual_mean": float(np.mean(a[mask] - c[mask])),
        "candidate_residual_variance": float(np.var(a[mask] - c[mask], ddof=1)),
        "market_residual_mean": float(np.mean(a[mask] - m[mask])),
        "market_residual_variance": float(np.var(a[mask] - m[mask], ddof=1)),
    }


def season_week_block_bootstrap(
    frame: pd.DataFrame,
    candidate_error: np.ndarray | pd.Series,
    reference_error: np.ndarray | pd.Series,
    *,
    samples: int = 10_000,
    seed: int = BASE_SEED,
) -> dict:
    work = pd.DataFrame(
        {
            "season": pd.to_numeric(frame["season"], errors="coerce"),
            "week": pd.to_numeric(frame["week"], errors="coerce"),
            "candidate": pd.to_numeric(pd.Series(candidate_error, index=frame.index), errors="coerce"),
            "reference": pd.to_numeric(pd.Series(reference_error, index=frame.index), errors="coerce"),
        }
    ).dropna()
    if work.empty:
        return {"games": 0, "blocks": 0, "samples": int(samples)}
    work["delta"] = work["candidate"] - work["reference"]
    work["block"] = work["season"].astype(int).astype(str) + "_" + work["week"].astype(int).astype(str)
    groups = {k: g["delta"].to_numpy(dtype=float) for k, g in work.groupby("block")}
    keys = np.array(sorted(groups), dtype=object)
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=float)
    for i in range(int(samples)):
        chosen = rng.choice(keys, size=len(keys), replace=True)
        vals = np.concatenate([groups[str(k)] for k in chosen])
        draws[i] = float(vals.mean())
    return {
        "games": int(len(work)),
        "blocks": int(len(keys)),
        "samples": int(samples),
        "candidate_minus_reference_mean": float(work["delta"].mean()),
        "ci95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "probability_candidate_lower": float(np.mean(draws < 0.0)),
        "block": "season+week",
        "seed": int(seed),
    }


def exact_common_rows(frames: Sequence[pd.DataFrame], *, key: str = "game_id") -> list[pd.DataFrame]:
    if not frames:
        return []
    common: set[str] | None = None
    for frame in frames:
        ids = set(frame[key].astype(str))
        common = ids if common is None else common.intersection(ids)
    common = common or set()
    ordered = sorted(common)
    out = []
    for frame in frames:
        idx = frame.assign(_key=frame[key].astype(str)).set_index("_key", drop=False)
        out.append(idx.loc[ordered].reset_index(drop=True).drop(columns=["_key"]))
    return out


def write_json(path: str | Path, payload: dict | list) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sanitize_json(value):
    if isinstance(value, dict):
        return {str(k): sanitize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        x = float(value)
        return x if np.isfinite(x) else None
    if isinstance(value, np.ndarray):
        return [sanitize_json(v) for v in value.tolist()]
    return value


def assert_prediction_receipt(frame: pd.DataFrame, candidate_id: str) -> None:
    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "candidate_id",
        "outer_target_season",
        "train_through_season",
        "source_contract_version",
        "code_sha",
        "config_sha",
        "fallback_state",
    }
    missing = required - set(frame.columns)
    if missing:
        raise Phase3FirewallError(f"{candidate_id}: prediction receipt missing {sorted(missing)}")
    if not frame["candidate_id"].eq(candidate_id).all():
        raise Phase3FirewallError(f"{candidate_id}: candidate identity drift")
    if pd.to_numeric(frame["season"], errors="coerce").ge(2025).any():
        raise Phase3FirewallError(f"{candidate_id}: forbidden 2025+ prediction row")
    target = pd.to_numeric(frame["outer_target_season"], errors="coerce")
    train_through = pd.to_numeric(frame["train_through_season"], errors="coerce")
    if not (train_through < target).all():
        raise Phase3FirewallError(f"{candidate_id}: OOF receipt has invalid training boundary")


def assert_unique_game_identity(frame: pd.DataFrame) -> None:
    cols = ["game_id", "season", "week", "home_team", "away_team"]
    if frame["game_id"].astype(str).duplicated().any():
        dupes = frame.loc[frame["game_id"].astype(str).duplicated(keep=False), cols]
        raise Phase3FirewallError(f"duplicate game identity rows:\n{dupes.head().to_string(index=False)}")
    if frame[["home_team", "away_team"]].isna().any().any():
        raise Phase3FirewallError("missing home/away team identity")
    if frame["home_team"].astype(str).eq(frame["away_team"].astype(str)).any():
        raise Phase3FirewallError("home team equals away team")


def d_gate_contract() -> dict:
    return {
        "abs_error_correlation_lt": 0.90,
        "pooled_mae_gain_gte": 0.10,
        "must_improve_seasons": [2023, 2024],
        "bootstrap_probability_gte": 0.75,
        "weights": "nonnegative_sum_to_one_prior_time_nested",
    }

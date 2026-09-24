from __future__ import annotations

"""Frozen numerical/statistical core for ATS Frontier V2 Phase 4.

Research only. This file contains no production imports other than standard scientific
Python dependencies. It implements the preregistered sign convention, exact integer
binning, M4 analytic tail-safe normalization, paired proper scores, deterministic
week-block bootstrap, and the scalar dynamic-state update used by M3.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import norm, t as student_t
from sklearn.linear_model import LogisticRegression, Ridge

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "phase4_config.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
BOOTSTRAP_SEED = int(CONFIG["bootstrap_seed"])
EPS = 1e-12


class Phase4ContractError(RuntimeError):
    pass


def sha256_file(path: str | Path) -> str:
    h = sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_files(paths: Sequence[str | Path]) -> str:
    h = sha256()
    for raw in sorted(str(Path(p)) for p in paths):
        p = Path(raw)
        h.update(raw.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def market_margin(spread_line: float | pd.Series) -> float | pd.Series:
    """Canonical repository sign: positive spread_line means expected home margin."""
    return pd.to_numeric(spread_line, errors="coerce") if isinstance(spread_line, pd.Series) else float(spread_line)


def actual_margin(home_score: float, away_score: float) -> int:
    value = float(home_score) - float(away_score)
    if not math.isclose(value, round(value), abs_tol=1e-9):
        raise Phase4ContractError("NFL final margin must be integer-valued")
    return int(round(value))


def observed_ats_class(margin: int | float, line: float) -> int:
    """0=home-cover, 1=push, 2=home-fail/away-cover."""
    d = float(margin) - float(line)
    if math.isclose(d, 0.0, abs_tol=1e-9):
        return 1
    return 0 if d > 0 else 2


def _integer_line(line: float) -> bool:
    return math.isclose(float(line), round(float(line)), abs_tol=1e-10)


def normal_cpl(mu: float, sigma: float, line: float) -> tuple[float, float, float]:
    sigma = max(float(sigma), 1e-6)
    line = float(line)
    if _integer_line(line):
        m = int(round(line))
        lo = norm.cdf((m - 0.5 - mu) / sigma)
        hi = norm.cdf((m + 0.5 - mu) / sigma)
        loss = float(lo)
        push = float(hi - lo)
        cover = float(1.0 - hi)
    else:
        # NFL margins are integers. A half-point market partitions bins at the line.
        cut = math.floor(line) + 0.5
        loss = float(norm.cdf((cut - mu) / sigma))
        push = 0.0
        cover = float(1.0 - loss)
    vals = np.clip(np.asarray([cover, push, loss], dtype=float), 0.0, 1.0)
    vals /= vals.sum()
    return tuple(float(x) for x in vals)


def multinomial_log_loss(classes: Sequence[int], probs: np.ndarray) -> float:
    y = np.asarray(classes, dtype=int)
    p = np.asarray(probs, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(y) != len(p):
        raise Phase4ContractError("invalid CPL shape")
    chosen = np.clip(p[np.arange(len(y)), y], EPS, 1.0)
    return float(np.mean(-np.log(chosen)))


def multiclass_brier(classes: Sequence[int], probs: np.ndarray) -> float:
    y = np.asarray(classes, dtype=int)
    p = np.asarray(probs, dtype=float)
    onehot = np.eye(3, dtype=float)[y]
    return float(np.mean(np.sum((p - onehot) ** 2, axis=1)))


def gaussian_crps(y: Sequence[float], mu: Sequence[float], sigma: Sequence[float]) -> float:
    from scipy.special import erf

    yy = np.asarray(y, dtype=float)
    mm = np.asarray(mu, dtype=float)
    ss = np.asarray(sigma, dtype=float)
    z = (yy - mm) / ss
    phi = np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)
    Phi = 0.5 * (1.0 + erf(z / np.sqrt(2.0)))
    vals = ss * (z * (2.0 * Phi - 1.0) + 2.0 * phi - 1.0 / np.sqrt(np.pi))
    return float(np.mean(vals))


@dataclass(frozen=True)
class ScalarState:
    mean: float = 0.0
    var: float = 1.0
    n: int = 0


def predict_state(state: ScalarState, q: float) -> ScalarState:
    return ScalarState(float(state.mean), float(state.var + q), int(state.n))


def update_state(state: ScalarState, observation: float, q: float, r: float = 1.0) -> ScalarState:
    pred = predict_state(state, q)
    if not np.isfinite(observation):
        return pred
    k = pred.var / (pred.var + float(r))
    mean = pred.mean + k * (float(observation) - pred.mean)
    var = (1.0 - k) * pred.var
    return ScalarState(float(mean), float(var), int(state.n + 1))


def season_transition(state: ScalarState, lam: float, q: float, league_mean: float = 0.0) -> ScalarState:
    mean = float(lam) * state.mean + (1.0 - float(lam)) * float(league_mean)
    var = float(lam) ** 2 * state.var + float(q)
    return ScalarState(mean, var, state.n)


def ridge_delta_fit(x: np.ndarray, residual: np.ndarray, alpha: float) -> np.ndarray:
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(residual, dtype=float)
    mask = np.isfinite(yy) & np.isfinite(xx).all(axis=1)
    if mask.sum() < max(20, xx.shape[1] * 5):
        return np.zeros(xx.shape[1], dtype=float)
    model = Ridge(alpha=float(alpha), fit_intercept=False)
    model.fit(xx[mask], yy[mask])
    return np.asarray(model.coef_, dtype=float)


KEY_MARGINS = (0, -3, 3, -7, 7)


def m4_base_cell(m: int, loc: float, sigma: float, nu: float) -> float:
    sigma = max(float(sigma), 1e-9)
    upper = student_t.cdf((float(m) + 0.5 - float(loc)) / sigma, df=float(nu))
    lower = student_t.cdf((float(m) - 0.5 - float(loc)) / sigma, df=float(nu))
    return float(max(0.0, upper - lower))


def _key_weight(m: int, gammas: Sequence[float]) -> float:
    g0, g3, g7 = (float(x) for x in gammas)
    if m == 0:
        return math.exp(g0)
    if abs(m) == 3:
        return math.exp(g3)
    if abs(m) == 7:
        return math.exp(g7)
    return 1.0


def m4_normalizer(loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    # Full Student-t integer lattice has total mass 1. Only five finite bins are reweighted.
    z = 1.0
    for m in KEY_MARGINS:
        p0 = m4_base_cell(m, loc, sigma, nu)
        z += (_key_weight(m, gammas) - 1.0) * p0
    if not np.isfinite(z) or z <= 0.0:
        raise Phase4ContractError("invalid analytic M4 normalizer")
    return float(z)


def m4_cell(m: int, loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    z = m4_normalizer(loc, sigma, nu, gammas)
    return float(m4_base_cell(int(m), loc, sigma, nu) * _key_weight(int(m), gammas) / z)


def _m4_base_leq(k: int, loc: float, sigma: float, nu: float) -> float:
    return float(student_t.cdf((float(k) + 0.5 - float(loc)) / float(sigma), df=float(nu)))


def m4_leq(k: int, loc: float, sigma: float, nu: float, gammas: Sequence[float]) -> float:
    base = _m4_base_leq(int(k), loc, sigma, nu)
    correction = 0.0
    for m in KEY_MARGINS:
        if m <= int(k):
            correction += (_key_weight(m, gammas) - 1.0) * m4_base_cell(m, loc, sigma, nu)
    z = m4_normalizer(loc, sigma, nu, gammas)
    return float(np.clip((base + correction) / z, 0.0, 1.0))


def m4_cpl(loc: float, sigma: float, nu: float, gammas: Sequence[float], line: float) -> tuple[float, float, float]:
    line = float(line)
    if _integer_line(line):
        m = int(round(line))
        loss = m4_leq(m - 1, loc, sigma, nu, gammas)
        push = m4_cell(m, loc, sigma, nu, gammas)
        cover = 1.0 - loss - push
    else:
        k = math.floor(line)
        loss = m4_leq(k, loc, sigma, nu, gammas)
        push = 0.0
        cover = 1.0 - loss
    vals = np.asarray([cover, push, loss], dtype=float)
    if not np.isfinite(vals).all() or (vals < -1e-13).any():
        raise Phase4ContractError("non-finite/negative M4 CPL probability")
    vals = np.clip(vals, 0.0, 1.0)
    if abs(float(vals.sum()) - 1.0) >= 1e-12:
        raise Phase4ContractError("M4 CPL probabilities do not normalize")
    vals /= vals.sum()
    return tuple(float(x) for x in vals)


def m4_sigma(params: Sequence[float], total: np.ndarray, spread: np.ndarray, conditional: bool) -> np.ndarray:
    p = np.asarray(params, dtype=float)
    total = np.asarray(total, dtype=float)
    spread = np.asarray(spread, dtype=float)
    if conditional:
        eta = p[0] + p[1] * np.log(np.clip(total, 1e-6, None) / 45.0) + p[2] * np.abs(spread) / 7.0
    else:
        eta = np.full(len(total), p[0], dtype=float)
    return np.exp(np.clip(eta, math.log(0.25), math.log(80.0)))


def fit_m4(
    train: pd.DataFrame,
    *,
    nu: int,
    lambda_scale: float,
    lambda_key: float,
    conditional: bool,
    use_key: bool,
) -> dict:
    if len(train) < 100:
        raise Phase4ContractError("M4 training set too small")
    margin = train["actual_margin"].to_numpy(dtype=int)
    loc = train["market_margin"].to_numpy(dtype=float)
    total = train["total_line"].to_numpy(dtype=float)
    spread = train["spread_line"].to_numpy(dtype=float)

    n_scale = 3 if conditional else 1
    n_key = 3 if use_key else 0
    residual = margin.astype(float) - loc
    init_sigma = max(float(np.std(residual, ddof=1)), 3.0)
    x0 = np.zeros(n_scale + n_key, dtype=float)
    x0[0] = math.log(init_sigma)

    def unpack(theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        scale = np.asarray(theta[:n_scale], dtype=float)
        key = np.asarray(theta[n_scale:], dtype=float) if use_key else np.zeros(3, dtype=float)
        return scale, key

    def objective(theta: np.ndarray) -> float:
        scale_p, key_p = unpack(theta)
        sig = m4_sigma(scale_p, total, spread, conditional)
        logp = np.empty(len(train), dtype=float)
        for i, m in enumerate(margin):
            p = m4_cell(int(m), loc[i], sig[i], float(nu), key_p)
            logp[i] = math.log(max(p, EPS))
        penalty = 0.0
        if conditional:
            penalty += float(lambda_scale) * float(np.dot(scale_p[1:], scale_p[1:])) / len(train)
        if use_key:
            penalty += float(lambda_key) * float(np.dot(key_p, key_p)) / len(train)
        return float(-np.mean(logp) + penalty)

    result = minimize(objective, x0, method="L-BFGS-B", options={"maxiter": 400, "ftol": 1e-11})
    if not result.success or not np.isfinite(result.fun):
        raise Phase4ContractError(f"M4 optimizer failed: {result.message}")
    scale_p, key_p = unpack(np.asarray(result.x, dtype=float))
    return {
        "nu": int(nu),
        "lambda_scale": float(lambda_scale),
        "lambda_key": float(lambda_key),
        "conditional": bool(conditional),
        "use_key": bool(use_key),
        "scale_params": scale_p.tolist(),
        "key_params": key_p.tolist(),
        "objective": float(result.fun),
    }


def predict_m4(frame: pd.DataFrame, fit: dict) -> pd.DataFrame:
    out = frame.copy()
    sig = m4_sigma(
        fit["scale_params"],
        out["total_line"].to_numpy(dtype=float),
        out["spread_line"].to_numpy(dtype=float),
        bool(fit["conditional"]),
    )
    nu = float(fit["nu"])
    key = fit["key_params"]
    pmass = []
    cpl = []
    for i, row in enumerate(out.itertuples(index=False)):
        loc = float(row.market_margin)
        m = int(row.actual_margin)
        pmass.append(m4_cell(m, loc, sig[i], nu, key))
        cpl.append(m4_cpl(loc, sig[i], nu, key, float(row.spread_line)))
    probs = np.asarray(cpl, dtype=float)
    out["sigma"] = sig
    out["observed_margin_mass"] = np.asarray(pmass, dtype=float)
    out["integer_log_score"] = -np.log(np.clip(out["observed_margin_mass"].to_numpy(dtype=float), EPS, 1.0))
    out["p_cover"] = probs[:, 0]
    out["p_push"] = probs[:, 1]
    out["p_loss"] = probs[:, 2]
    out["ats_class"] = [observed_ats_class(m, l) for m, l in zip(out["actual_margin"], out["spread_line"])]
    out["cpl_log_loss"] = -np.log(np.clip(probs[np.arange(len(out)), out["ats_class"].to_numpy(dtype=int)], EPS, 1.0))
    return out


def m4_ranked_probability_score(row: pd.Series, fit: dict, bound: int = 80) -> float:
    # Diagnostic only. The primary log score remains exact and untruncated. Tail outside
    # this diagnostic lattice is retained through analytic CDF values at the boundaries.
    loc = float(row["market_margin"])
    total = np.asarray([float(row["total_line"])])
    spread = np.asarray([float(row["spread_line"])])
    sig = float(m4_sigma(fit["scale_params"], total, spread, bool(fit["conditional"]))[0])
    nu = float(fit["nu"])
    key = fit["key_params"]
    y = int(row["actual_margin"])
    ks = np.arange(-bound, bound + 1)
    cdf = np.asarray([m4_leq(int(k), loc, sig, nu, key) for k in ks])
    obs = (ks >= y).astype(float)
    return float(np.sum((cdf - obs) ** 2))


def paired_week_bootstrap(
    frame: pd.DataFrame,
    delta_col: str,
    *,
    resamples: int = 10_000,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    data = frame[["season", "week", delta_col]].dropna().copy()
    if len(data) < 10:
        raise Phase4ContractError("paired bootstrap requires at least 10 rows")
    blocks = {
        int(season): [g[delta_col].to_numpy(dtype=float) for _, g in s.groupby("week", sort=True)]
        for season, s in data.groupby("season", sort=True)
    }
    rng = np.random.default_rng(int(seed))
    draws = np.empty(int(resamples), dtype=float)
    for b in range(int(resamples)):
        values: list[np.ndarray] = []
        for season in sorted(blocks):
            weeks = blocks[season]
            idx = rng.integers(0, len(weeks), size=len(weeks))
            values.extend(weeks[int(i)] for i in idx)
        draws[b] = float(np.mean(np.concatenate(values)))
    point = float(data[delta_col].mean())
    return {
        "n": int(len(data)),
        "weeks": int(data[["season", "week"]].drop_duplicates().shape[0]),
        "point_delta": point,
        "ci_2_5": float(np.percentile(draws, 2.5)),
        "ci_97_5": float(np.percentile(draws, 97.5)),
        "probability_favorable": float(np.mean(draws < 0.0)),
        "seed": int(seed),
        "resamples": int(resamples),
    }


def calibration_report(classes: Sequence[int], probs: np.ndarray) -> dict:
    # Binary home-cover calibration excludes pushes; this is a diagnostic, not a rescue.
    y3 = np.asarray(classes, dtype=int)
    p3 = np.asarray(probs, dtype=float)
    mask = y3 != 1
    if mask.sum() < 30:
        return {"n": int(mask.sum()), "intercept": None, "slope": None, "reliability": []}
    y = (y3[mask] == 0).astype(int)
    p = np.clip(p3[mask, 0] / np.clip(p3[mask, 0] + p3[mask, 2], EPS, None), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1.0 - p)).reshape(-1, 1)
    model = LogisticRegression(C=1e6, solver="lbfgs")
    try:
        model.fit(logit, y)
        intercept = float(model.intercept_[0])
        slope = float(model.coef_[0, 0])
    except Exception:
        intercept = None
        slope = None
    bins = pd.qcut(pd.Series(p), q=min(10, max(2, len(p) // 30)), duplicates="drop")
    rel = []
    for interval, idx in bins.groupby(bins, observed=True).groups.items():
        ii = np.asarray(list(idx), dtype=int)
        rel.append({
            "bin": str(interval),
            "n": int(len(ii)),
            "mean_pred": float(np.mean(p[ii])),
            "observed": float(np.mean(y[ii])),
        })
    return {"n": int(len(y)), "intercept": intercept, "slope": slope, "reliability": rel}


def full_slate_ats_diagnostic(frame: pd.DataFrame) -> dict:
    # No confidence threshold: every non-push row takes the higher-probability side.
    p_cover = frame["p_cover"].to_numpy(dtype=float)
    p_loss = frame["p_loss"].to_numpy(dtype=float)
    y = frame["ats_class"].to_numpy(dtype=int)
    side = np.where(p_cover >= p_loss, 0, 2)
    decisive = y != 1
    hits = side[decisive] == y[decisive]
    wins = int(hits.sum())
    losses = int((~hits).sum())
    pushes = int((~decisive).sum())
    n = wins + losses
    units = wins * (100.0 / 110.0) - losses if n else 0.0
    return {
        "games": int(len(frame)),
        "decisions": int(n),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_ex_push": float(wins / n) if n else None,
        "REFERENCE_MINUS110_units_per_1_risked": float(units),
        "REFERENCE_MINUS110_roi_on_risked_units": float(units / n) if n else None,
        "actual_historical_roi_claimed": False,
    }

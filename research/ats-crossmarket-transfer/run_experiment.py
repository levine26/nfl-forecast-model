from __future__ import annotations

"""Historical, chronology-clean ATS cross-market information-transfer experiment.

Research only. This runner reuses the canonical historical F-ST reconstruction and the
accepted ATS Frontier V2 constant-scale key-mass nuisance fits. It never loads completed
2026 outcomes and never writes production artifacts.
"""

import argparse
from collections import defaultdict
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
EPS = 1e-12


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v2 = _load_module("ats_frontier_v2_phase4_core", REPO_ROOT / "research" / "ats-frontier-v2" / "phase4_core.py")
hist = _load_module("ats_historical_challenger_runner", REPO_ROOT / "research" / "ats-historical-challenger" / "historical_challenger.py")

OUTER = tuple(int(x) for x in CONFIG["outer_test_seasons"])
ALPHAS = tuple(float(x) for x in CONFIG["alpha_grid"])
BETAS = tuple(float(x) for x in CONFIG["beta_grid"])
TAIL_TOL = float(CONFIG["tail_tolerance"])
BOOTSTRAP_SEED = int(CONFIG["bootstrap_seed"])
BOOTSTRAP_N = int(CONFIG["bootstrap_resamples"])


class CrossMarketError(RuntimeError):
    pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv_dump(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.17g")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _clip_prob(x) -> np.ndarray:
    return np.clip(np.asarray(x, dtype=float), 1e-6, 1.0 - 1e-6)


def _logit(x) -> np.ndarray:
    p = _clip_prob(x)
    return np.log(p / (1.0 - p))


def _binary_log_loss(y, p) -> float:
    yy = np.asarray(y, dtype=int)
    pp = _clip_prob(p)
    return float(np.mean(-(yy * np.log(pp) + (1 - yy) * np.log(1 - pp))))


def _binary_brier(y, p) -> float:
    yy = np.asarray(y, dtype=float)
    pp = np.asarray(p, dtype=float)
    return float(np.mean((pp - yy) ** 2))


def _accuracy(y, p) -> float:
    yy = np.asarray(y, dtype=int)
    pred = (np.asarray(p, dtype=float) >= 0.5).astype(int)
    return float(np.mean(pred == yy))


def _fit_for_season(season: int) -> dict:
    try:
        return hist.V2_FREEZE["outer_seasons"][str(int(season))]["CONSTANT_SCALE_KEY"]
    except KeyError as exc:
        raise CrossMarketError(f"missing frozen KMASS fit for {season}") from exc


def _base_parts(row: pd.Series, fit: dict) -> dict:
    loc = float(row["market_margin"])
    line = float(row["spread_line"])
    total = np.asarray([float(row["total_line"])])
    spread = np.asarray([line])
    sigma = float(v2.m4_sigma(fit["scale_params"], total, spread, bool(fit["conditional"]))[0])
    nu = float(fit["nu"])
    key = fit["key_params"]
    q0 = float(v2.m4_cell(0, loc, sigma, nu, key))
    qneg = float(v2.m4_leq(-1, loc, sigma, nu, key))
    qpos = float(1.0 - v2.m4_leq(0, loc, sigma, nu, key))
    if min(q0, qneg, qpos) < 0 or abs(q0 + qneg + qpos - 1.0) > 2e-10:
        raise CrossMarketError("invalid KMASS sign partition")
    c, p, l = v2.m4_cpl(loc, sigma, nu, key, line)
    observed_mass = float(v2.m4_cell(int(row["actual_margin"]), loc, sigma, nu, key))
    return {
        "loc": loc, "line": line, "sigma": sigma, "nu": nu, "key": key,
        "q0": q0, "qneg": qneg, "qpos": qpos,
        "p_cover": c, "p_push": p, "p_loss": l,
        "observed_mass": observed_mass,
    }


def _projected_leq(k: int, parts: dict, u: float) -> float:
    u = float(np.clip(u, 1e-9, 1 - 1e-9))
    q0, qneg, qpos = parts["q0"], parts["qneg"], parts["qpos"]
    target_pos = (1.0 - q0) * u
    target_neg = (1.0 - q0) * (1.0 - u)
    ps = target_pos / qpos
    ns = target_neg / qneg
    base = float(v2.m4_leq(int(k), parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
    if k < 0:
        return float(base * ns)
    if k == 0:
        return float(target_neg + q0)
    positive_through_k = base - qneg - q0
    return float(target_neg + q0 + positive_through_k * ps)


def _iproj_cpl(parts: dict, u: float) -> tuple[float, float, float]:
    line = parts["line"]
    if math.isclose(line, round(line), abs_tol=1e-10):
        m = int(round(line))
        loss = _projected_leq(m - 1, parts, u)
        leq_m = _projected_leq(m, parts, u)
        push = leq_m - loss
        cover = 1.0 - leq_m
    else:
        k = math.floor(line)
        loss = _projected_leq(k, parts, u)
        push = 0.0
        cover = 1.0 - loss
    vals = np.asarray([cover, push, loss], dtype=float)
    if not np.isfinite(vals).all() or (vals < -1e-10).any():
        raise CrossMarketError("invalid simple I-projection CPL")
    vals = np.clip(vals, 0.0, 1.0)
    vals /= vals.sum()
    return tuple(float(x) for x in vals)


def _iproj_observed_mass(parts: dict, margin: int, u: float) -> float:
    q = float(v2.m4_cell(int(margin), parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
    q0, qneg, qpos = parts["q0"], parts["qneg"], parts["qpos"]
    if margin == 0:
        return q
    if margin > 0:
        return float(q * ((1.0 - q0) * u / qpos))
    return float(q * ((1.0 - q0) * (1.0 - u) / qneg))


def _adaptive_support(parts: dict) -> tuple[np.ndarray, np.ndarray, float]:
    bound = int(CONFIG["initial_support_bound"])
    max_bound = int(CONFIG["maximum_support_bound"])
    while True:
        left = float(v2.m4_leq(-bound - 1, parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
        right = float(1.0 - v2.m4_leq(bound, parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
        tail = left + right
        if tail < TAIL_TOL:
            break
        bound *= 2
        if bound > max_bound:
            raise CrossMarketError(f"adaptive support failed tail tolerance: {tail}")
    margins = np.arange(-bound, bound + 1, dtype=int)
    q = np.asarray([
        v2.m4_cell(int(m), parts["loc"], parts["sigma"], parts["nu"], parts["key"])
        for m in margins
    ], dtype=float)
    if (q < 0).any() or not np.isfinite(q).all():
        raise CrossMarketError("invalid adaptive KMASS support")
    return margins, q, float(tail)


def _meanfix_pmf(parts: dict, u: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Minimum-KL PMF with fixed tie mass, sign mass, and baseline finite-support mean."""
    margins, q, tail = _adaptive_support(parts)
    zero = margins == 0
    pos = margins > 0
    neg = margins < 0
    q0 = float(q[zero][0])
    qpos = q[pos]
    qneg = q[neg]
    mpos = margins[pos].astype(float)
    mneg = margins[neg].astype(float)
    support_mass = float(q.sum())
    baseline_mean = float(np.dot(margins.astype(float), q) / support_mass)
    target_pos = (1.0 - q0) * float(u)
    target_neg = (1.0 - q0) * (1.0 - float(u))

    def weighted_region(base: np.ndarray, m: np.ndarray, lam: float, total: float) -> np.ndarray:
        zlog = np.log(np.clip(base, 1e-300, None)) + lam * m
        zlog -= float(np.max(zlog))
        w = np.exp(zlog)
        s = float(w.sum())
        if not np.isfinite(s) or s <= 0:
            raise CrossMarketError("meanfix exponential tilt underflow")
        return w * (total / s)

    def mean_at(lam: float) -> float:
        pp = weighted_region(qpos, mpos, lam, target_pos)
        pn = weighted_region(qneg, mneg, lam, target_neg)
        return float(np.dot(mpos, pp) + np.dot(mneg, pn))

    lo, hi = -0.25, 0.25
    flo = mean_at(lo) - baseline_mean
    fhi = mean_at(hi) - baseline_mean
    for _ in range(30):
        if flo <= 0 <= fhi:
            break
        if flo > 0:
            lo *= 2.0
            flo = mean_at(lo) - baseline_mean
        if fhi < 0:
            hi *= 2.0
            fhi = mean_at(hi) - baseline_mean
    else:
        raise CrossMarketError("mean-preserving I-projection infeasible on adaptive support")
    lam = float(brentq(lambda x: mean_at(x) - baseline_mean, lo, hi, xtol=1e-13, rtol=1e-13, maxiter=300))
    p = np.zeros_like(q)
    p[zero] = q0
    p[pos] = weighted_region(qpos, mpos, lam, target_pos)
    p[neg] = weighted_region(qneg, mneg, lam, target_neg)
    if abs(float(p.sum()) - 1.0) > 5e-11:
        raise CrossMarketError("meanfix PMF does not normalize")
    implied_mean = float(np.dot(margins.astype(float), p))
    if abs(implied_mean - baseline_mean) > 2e-9:
        raise CrossMarketError("meanfix mean constraint failed")
    if abs(float(p[zero][0]) - q0) > 1e-12:
        raise CrossMarketError("meanfix tie mass changed")
    if abs(float(p[pos].sum()) - target_pos) > 2e-11:
        raise CrossMarketError("meanfix positive-mass constraint failed")
    return margins, p, {
        "tail_mass": tail,
        "support_bound": int(max(abs(int(margins[0])), abs(int(margins[-1])))),
        "lambda": lam,
        "baseline_mean": baseline_mean,
        "implied_mean": implied_mean,
    }


def _pmf_cpl(margins: np.ndarray, p: np.ndarray, line: float) -> tuple[float, float, float]:
    if math.isclose(float(line), round(float(line)), abs_tol=1e-10):
        m = int(round(float(line)))
        push = float(p[margins == m].sum())
        cover = float(p[margins > m].sum())
        loss = float(p[margins < m].sum())
    else:
        cover = float(p[margins > float(line)].sum())
        push = 0.0
        loss = float(p[margins < float(line)].sum())
    vals = np.asarray([cover, push, loss], dtype=float)
    vals /= vals.sum()
    return tuple(float(x) for x in vals)


def _pmf_mass(margins: np.ndarray, p: np.ndarray, margin: int) -> float:
    hit = np.where(margins == int(margin))[0]
    if len(hit) != 1:
        raise CrossMarketError("observed margin outside adaptive support")
    return float(p[int(hit[0])])


def _target_prob(market: float, fst: float, alpha: float) -> float:
    d = float(_logit([fst])[0] - _logit([market])[0])
    return float(expit(float(_logit([market])[0]) + float(alpha) * d))


def _cpl_loss(cls: int, probs: tuple[float, float, float]) -> float:
    return float(-math.log(max(float(probs[int(cls)]), EPS)))


def _observed_class(margin: int, line: float) -> int:
    return int(v2.observed_ats_class(int(margin), float(line)))


def _select_alpha(train: pd.DataFrame, fit: dict) -> tuple[float, list[dict]]:
    rows = []
    for alpha in ALPHAS:
        losses = []
        for _, row in train.iterrows():
            parts = _base_parts(row, fit)
            u = _target_prob(float(row["market_prob"]), float(row["fst_home_prob"]), alpha)
            probs = _iproj_cpl(parts, u)
            losses.append(_cpl_loss(_observed_class(int(row["actual_margin"]), float(row["spread_line"])), probs))
        rows.append({"alpha": alpha, "n": len(losses), "cpl_log_loss": float(np.mean(losses))})
    best = min(rows, key=lambda r: (r["cpl_log_loss"], r["alpha"]))
    return float(best["alpha"]), rows


def _select_beta(train: pd.DataFrame, fit: dict) -> tuple[float, list[dict]]:
    rows = []
    for beta in BETAS:
        losses = []
        for _, row in train.iterrows():
            parts = _base_parts(row, fit)
            c0 = parts["p_cover"] / max(parts["p_cover"] + parts["p_loss"], EPS)
            d = float(_logit([row["fst_home_prob"]])[0] - _logit([row["market_prob"]])[0])
            c = float(expit(float(_logit([c0])[0]) + beta * d))
            probs = ((1 - parts["p_push"]) * c, parts["p_push"], (1 - parts["p_push"]) * (1 - c))
            losses.append(_cpl_loss(_observed_class(int(row["actual_margin"]), float(row["spread_line"])), probs))
        rows.append({"beta": beta, "n": len(losses), "cpl_log_loss": float(np.mean(losses))})
    best = min(rows, key=lambda r: (r["cpl_log_loss"], r["beta"]))
    return float(best["beta"]), rows


def _score_fold(test: pd.DataFrame, fit: dict, alpha: float, beta: float) -> tuple[pd.DataFrame, dict]:
    out_rows: list[dict] = []
    meanfix_meta: list[dict] = []
    for _, row in test.iterrows():
        parts = _base_parts(row, fit)
        cls = _observed_class(int(row["actual_margin"]), float(row["spread_line"]))
        market = float(row["market_prob"])
        fstp = float(row["fst_home_prob"])
        delta = float(_logit([fstp])[0] - _logit([market])[0])
        u_fst = _target_prob(market, fstp, alpha)

        base_probs = (parts["p_cover"], parts["p_push"], parts["p_loss"])
        mkt_probs = _iproj_cpl(parts, market)
        fst_probs = _iproj_cpl(parts, u_fst)
        full_fst_probs = _iproj_cpl(parts, fstp)

        mm, pm, meta_m = _meanfix_pmf(parts, market)
        mf, pf, meta_f = _meanfix_pmf(parts, u_fst)
        mkt_mf_probs = _pmf_cpl(mm, pm, parts["line"])
        fst_mf_probs = _pmf_cpl(mf, pf, parts["line"])

        c0 = parts["p_cover"] / max(parts["p_cover"] + parts["p_loss"], EPS)
        c = float(expit(float(_logit([c0])[0]) + beta * delta))
        off_probs = ((1 - parts["p_push"]) * c, parts["p_push"], (1 - parts["p_push"]) * (1 - c))

        rec = {
            "game_id": str(row["game_id"]), "season": int(row["season"]), "week": int(row["week"]),
            "gameday": str(row.get("gameday", "")), "home_team": str(row.get("home_team", "")),
            "away_team": str(row.get("away_team", "")), "actual_margin": int(row["actual_margin"]),
            "spread_line": float(row["spread_line"]), "total_line": float(row["total_line"]),
            "market_prob": market, "fst_home_prob": fstp, "delta_fst": delta,
            "alpha_selected": float(alpha), "beta_selected": float(beta), "ats_class": cls,
        }
        models = {
            "kmass_market": (base_probs, parts["observed_mass"]),
            "marketml_iproj": (mkt_probs, _iproj_observed_mass(parts, int(row["actual_margin"]), market)),
            "fst_iproj": (fst_probs, _iproj_observed_mass(parts, int(row["actual_margin"]), u_fst)),
            "fst_iproj_alpha1": (full_fst_probs, _iproj_observed_mass(parts, int(row["actual_margin"]), fstp)),
            "marketml_meanfix": (mkt_mf_probs, _pmf_mass(mm, pm, int(row["actual_margin"]))),
            "fst_meanfix": (fst_mf_probs, _pmf_mass(mf, pf, int(row["actual_margin"]))),
            "cpl_offset": (off_probs, None),
        }
        for name, (probs, mass) in models.items():
            rec[f"{name}_p_cover"] = probs[0]
            rec[f"{name}_p_push"] = probs[1]
            rec[f"{name}_p_loss"] = probs[2]
            rec[f"{name}_cpl_log_loss"] = _cpl_loss(cls, probs)
            rec[f"{name}_conditional_cover"] = probs[0] / max(probs[0] + probs[2], EPS)
            if mass is not None:
                rec[f"{name}_integer_log_score"] = -math.log(max(float(mass), EPS))
        rec["kmass_market_expected_margin"] = meta_m["baseline_mean"]
        rec["marketml_meanfix_expected_margin"] = meta_m["implied_mean"]
        rec["fst_meanfix_expected_margin"] = meta_f["implied_mean"]
        out_rows.append(rec)
        meanfix_meta.extend([meta_m, meta_f])
    scored = pd.DataFrame(out_rows)
    diagnostics = {
        "max_meanfix_tail_mass": float(max(x["tail_mass"] for x in meanfix_meta)),
        "max_meanfix_support_bound": int(max(x["support_bound"] for x in meanfix_meta)),
        "max_mean_constraint_error": float(max(abs(x["implied_mean"] - x["baseline_mean"]) for x in meanfix_meta)),
    }
    return scored, diagnostics


def _calibration(frame: pd.DataFrame, prefix: str) -> dict:
    probs = frame[[f"{prefix}_p_cover", f"{prefix}_p_push", f"{prefix}_p_loss"]].to_numpy(dtype=float)
    return v2.calibration_report(frame["ats_class"].to_numpy(dtype=int), probs)


def _conditional_metrics(frame: pd.DataFrame, prefix: str) -> dict:
    mask = frame["ats_class"] != 1
    y = (frame.loc[mask, "ats_class"].to_numpy(dtype=int) == 0).astype(int)
    p = np.clip(frame.loc[mask, f"{prefix}_conditional_cover"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
    return {
        "n": int(mask.sum()),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(np.mean(-(y * np.log(p) + (1-y) * np.log(1-p)))),
        "sharpness_variance": float(np.var(p)),
    }


def _cpl_brier(frame: pd.DataFrame, prefix: str) -> dict:
    probs = frame[[f"{prefix}_p_cover", f"{prefix}_p_push", f"{prefix}_p_loss"]].to_numpy(dtype=float)
    y = np.eye(3)[frame["ats_class"].to_numpy(dtype=int)]
    comp = np.mean((probs - y) ** 2, axis=0)
    return {"cover": float(comp[0]), "push": float(comp[1]), "loss": float(comp[2]), "sum": float(comp.sum())}


def _ats(frame: pd.DataFrame, prefix: str, base_prefix: str = "kmass_market") -> dict:
    y = frame["ats_class"].to_numpy(dtype=int)
    side = np.where(frame[f"{prefix}_p_cover"].to_numpy(dtype=float) >= frame[f"{prefix}_p_loss"].to_numpy(dtype=float), 0, 2)
    base = np.where(frame[f"{base_prefix}_p_cover"].to_numpy(dtype=float) >= frame[f"{base_prefix}_p_loss"].to_numpy(dtype=float), 0, 2)
    decisive = y != 1
    hits = side[decisive] == y[decisive]
    wins = int(hits.sum()); losses = int((~hits).sum()); pushes = int((~decisive).sum())
    sw = side != base
    sw_dec = sw & decisive
    sw_hits = side[sw_dec] == y[sw_dec]
    sw_push = int(np.sum(sw & ~decisive))
    units = wins * (100.0/110.0) - losses
    return {
        "wins": wins, "losses": losses, "pushes": pushes,
        "hit_rate_ex_push": float(wins / (wins + losses)) if wins + losses else None,
        "REFERENCE_MINUS110_units_per_1_risked": float(units),
        "REFERENCE_MINUS110_roi_on_risked_units": float(units / (wins + losses)) if wins + losses else None,
        "actual_historical_roi_claimed": False,
        "side_switches_vs_kmass_market": int(sw.sum()),
        "switch_wins": int(sw_hits.sum()), "switch_losses": int((~sw_hits).sum()), "switch_pushes": sw_push,
    }


def _bootstrap(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    col = f"delta__{candidate}__vs__{null}"
    temp = frame[["season", "week"]].copy()
    temp[col] = frame[f"{candidate}_cpl_log_loss"] - frame[f"{null}_cpl_log_loss"]
    return v2.paired_week_bootstrap(temp, col, resamples=BOOTSTRAP_N, seed=BOOTSTRAP_SEED)


def _per_season(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    rows = []
    for season, g in frame.groupby("season", sort=True):
        delta = g[f"{candidate}_cpl_log_loss"] - g[f"{null}_cpl_log_loss"]
        rows.append({"season": int(season), "n": int(len(g)), "candidate_log_loss": float(g[f"{candidate}_cpl_log_loss"].mean()), "null_log_loss": float(g[f"{null}_cpl_log_loss"].mean()), "delta": float(delta.mean())})
    return rows


def _leave_one_season_out(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    out=[]
    for season in sorted(frame["season"].unique()):
        g=frame[frame["season"] != season]
        d=g[f"{candidate}_cpl_log_loss"]-g[f"{null}_cpl_log_loss"]
        out.append({"left_out_season":int(season),"n":int(len(g)),"delta":float(d.mean())})
    return out


def _leave_one_week_out(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    full = float((frame[f"{candidate}_cpl_log_loss"]-frame[f"{null}_cpl_log_loss"]).mean())
    vals=[]
    for (s,w), _ in frame.groupby(["season","week"],sort=True):
        g=frame[~((frame["season"]==s)&(frame["week"]==w))]
        vals.append(float((g[f"{candidate}_cpl_log_loss"]-g[f"{null}_cpl_log_loss"]).mean()))
    return {"full_delta":full,"min_loo_delta":float(min(vals)),"max_loo_delta":float(max(vals)),"sign_flips":int(sum(np.sign(x)!=np.sign(full) for x in vals if x != 0 and full != 0))}


def _exact_wilson(w: int, l: int, z: float = 1.959963984540054) -> tuple[float,float]:
    n=w+l
    if n==0: return (float("nan"),float("nan"))
    p=w/n; den=1+z*z/n
    ctr=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return float(ctr-half),float(ctr+half)


def _diagnostic_buckets(frame: pd.DataFrame, candidate: str, null: str) -> pd.DataFrame:
    work=frame.copy()
    a=np.abs(work["spread_line"].to_numpy(dtype=float))
    conds=[a<=2,(a>2)&(a<=3.5),(a>3.5)&(a<=6.5),(a>6.5)&(a<=7.5),a>7.5]
    labels=["|spread| <= 2","2 < |spread| <= 3.5","3.5 < |spread| <= 6.5","6.5 < |spread| <= 7.5","|spread| > 7.5"]
    work["spread_bucket"]=np.select(conds,labels,default="UNKNOWN")
    tol=float(CONFIG["key_near_tolerance"])
    work["key_bucket"]=np.where(np.abs(a-3)<=tol,"near_3",np.where(np.abs(a-7)<=tol,"near_7","other"))
    dabs=np.abs(work["delta_fst"].to_numpy(dtype=float))
    bins=np.asarray(CONFIG["delta_abs_bins"],dtype=float)
    work["delta_bucket"]=pd.cut(dabs,bins=bins,right=True,include_lowest=True).astype(str)
    out=[]
    for dim in ["spread_bucket","key_bucket","delta_bucket"]:
        for bucket,g in work.groupby(dim,sort=False,observed=True):
            out.append({"dimension":dim,"bucket":str(bucket),"candidate":candidate,"null":null,"n":int(len(g)),"candidate_cpl_log_loss":float(g[f"{candidate}_cpl_log_loss"].mean()),"null_cpl_log_loss":float(g[f"{null}_cpl_log_loss"].mean()),"delta":float((g[f"{candidate}_cpl_log_loss"]-g[f"{null}_cpl_log_loss"]).mean())})
    return pd.DataFrame(out)


def _holm(results: dict[str, dict]) -> dict:
    # Bootstrap one-sided empirical p ~= P(delta >= 0). Holm controls the three-candidate family.
    items=[]
    for name,r in results.items():
        p=max(1.0/BOOTSTRAP_N,1.0-float(r["probability_favorable"]))
        items.append((name,p))
    ordered=sorted(items,key=lambda x:x[1])
    adj={}
    running=0.0
    m=len(ordered)
    for i,(name,p) in enumerate(ordered):
        val=min(1.0,(m-i)*p)
        running=max(running,val)
        adj[name]={"raw_one_sided_bootstrap_p":p,"holm_adjusted_p":running}
    return adj


def _source_signal(frame: pd.DataFrame) -> dict:
    y=frame["home_win"].astype(int).to_numpy()
    out={"common_n":int(len(frame)),"outer_seasons":sorted(int(x) for x in frame["season"].unique())}
    for label,col in [("market","market_prob"),("fst","fst_home_prob")]:
        p=frame[col].to_numpy(dtype=float)
        out[label]={"accuracy":_accuracy(y,p),"brier":_binary_brier(y,p),"log_loss":_binary_log_loss(y,p)}
    out["fst_minus_market"]={"accuracy_pp":100*(out["fst"]["accuracy"]-out["market"]["accuracy"]),"brier":out["fst"]["brier"]-out["market"]["brier"],"log_loss":out["fst"]["log_loss"]-out["market"]["log_loss"]}
    out["by_season"]=[]
    for season,g in frame.groupby("season",sort=True):
        yy=g["home_win"].astype(int).to_numpy()
        rec={"season":int(season),"n":int(len(g))}
        for label,col in [("market","market_prob"),("fst","fst_home_prob")]:
            pp=g[col].to_numpy(dtype=float)
            rec[label]={"accuracy":_accuracy(yy,pp),"brier":_binary_brier(yy,pp),"log_loss":_binary_log_loss(yy,pp)}
        out["by_season"].append(rec)
    return out


def _numerical_pretests(archive: pd.DataFrame) -> dict:
    sample=archive[archive["season"].isin(OUTER)].head(12)
    max_norm=0.0; max_mean=0.0; max_tail=0.0; alpha0=0.0; beta0=0.0
    for _,row in sample.iterrows():
        fit=_fit_for_season(int(row["season"]))
        parts=_base_parts(row,fit)
        probs=_iproj_cpl(parts,float(row["market_prob"]))
        max_norm=max(max_norm,abs(sum(probs)-1.0))
        # alpha=0 must reproduce market ML I-projection exactly
        u0=_target_prob(float(row["market_prob"]),float(row["fst_home_prob"]),0.0)
        alpha0=max(alpha0,max(abs(a-b) for a,b in zip(probs,_iproj_cpl(parts,u0))))
        mm,pm,meta=_meanfix_pmf(parts,float(row["market_prob"]))
        max_mean=max(max_mean,abs(meta["implied_mean"]-meta["baseline_mean"]))
        max_tail=max(max_tail,meta["tail_mass"])
        c0=parts["p_cover"]/max(parts["p_cover"]+parts["p_loss"],EPS)
        c=float(expit(float(_logit([c0])[0])))
        bp=((1-parts["p_push"])*c,parts["p_push"],(1-parts["p_push"])*(1-c))
        beta0=max(beta0,max(abs(a-b) for a,b in zip(bp,(parts["p_cover"],parts["p_push"],parts["p_loss"]))))
    if max_norm>1e-11 or max_mean>2e-9 or max_tail>=TAIL_TOL or alpha0>1e-12 or beta0>1e-12:
        raise CrossMarketError("numerical preregistration tests failed")
    return {"sample_rows":int(len(sample)),"max_probability_normalization_error":max_norm,"max_mean_constraint_error":max_mean,"max_tail_mass":max_tail,"alpha0_market_null_max_abs_error":alpha0,"beta0_kmass_baseline_max_abs_error":beta0,"pass":True}


def run(output_dir: Path) -> dict:
    games, game_identity = hist.build_historical_games()
    archive, coverage, fst_receipts = hist.build_center_archive(games)
    if int((archive["season"]>=2026).sum()) != 0:
        raise CrossMarketError("completed-2026 outcome firewall violated")
    required=["market_prob","fst_home_prob","home_win","actual_margin","spread_line","total_line","market_margin"]
    archive=archive.dropna(subset=required).copy()
    if archive["game_id"].astype(str).duplicated().any():
        raise CrossMarketError("duplicate archive game identity")
    numerical=_numerical_pretests(archive)

    selections=[]; scored_parts=[]; numerical_folds=[]
    for season in OUTER:
        fit=_fit_for_season(season)
        train=archive[archive["season"]<season].copy()
        test=archive[archive["season"]==season].copy()
        if train.empty or test.empty or train["season"].ge(season).any():
            raise CrossMarketError(f"invalid chronology for {season}")
        alpha,alpha_grid=_select_alpha(train,fit)
        beta,beta_grid=_select_beta(train,fit)
        scored,meta=_score_fold(test,fit,alpha,beta)
        scored["home_win"]=test["home_win"].astype(int).to_numpy()
        scored_parts.append(scored)
        numerical_folds.append({"season":season,**meta})
        selections.append({"season":season,"inner_training_n":int(len(train)),"inner_training_seasons":sorted(int(x) for x in train["season"].unique()),"alpha_selected":alpha,"beta_selected":beta,"alpha_grid":alpha_grid,"beta_grid":beta_grid})
    oof=pd.concat(scored_parts,ignore_index=True).sort_values(["season","week","game_id"]).reset_index(drop=True)
    if len(oof) != len(set(oof["game_id"])):
        raise CrossMarketError("OOF game identity not unique")
    if oof["season"].ge(2026).any():
        raise CrossMarketError("2026 entered OOF predictions")

    source=_source_signal(oof)
    prefixes=["kmass_market","marketml_iproj","fst_iproj","fst_iproj_alpha1","marketml_meanfix","fst_meanfix","cpl_offset"]
    overall={}
    for p in prefixes:
        overall[p]={
            "n":int(len(oof)),
            "cpl_log_loss":float(oof[f"{p}_cpl_log_loss"].mean()),
            "conditional":_conditional_metrics(oof,p),
            "cpl_brier_components":_cpl_brier(oof,p),
            "calibration":_calibration(oof,p),
            "ats":_ats(oof,p),
        }
        if f"{p}_integer_log_score" in oof:
            overall[p]["integer_margin_log_score"]=float(oof[f"{p}_integer_log_score"].mean())
    comparisons={
        "fst_iproj_vs_marketml_iproj":("fst_iproj","marketml_iproj"),
        "fst_meanfix_vs_marketml_meanfix":("fst_meanfix","marketml_meanfix"),
        "cpl_offset_vs_kmass_market":("cpl_offset","kmass_market"),
    }
    boots={}; season_results={}; loo={}; bucket_parts=[]
    for label,(cand,null) in comparisons.items():
        boots[label]=_bootstrap(oof,cand,null)
        season_results[label]=_per_season(oof,cand,null)
        loo[label]={"leave_one_season_out":_leave_one_season_out(oof,cand,null),"leave_one_week_out":_leave_one_week_out(oof,cand,null)}
        bucket_parts.append(_diagnostic_buckets(oof,cand,null))
    holm=_holm({
        "ATS-XM-IPROJ-FST-V1":boots["fst_iproj_vs_marketml_iproj"],
        "ATS-XM-IPROJ-MEANFIX-V1":boots["fst_meanfix_vs_marketml_meanfix"],
        "ATS-XM-CPL-OFFSET-V1":boots["cpl_offset_vs_kmass_market"],
    })

    # Diagnostic expected-margin MAE for full PMF candidates whose mean is available.
    center_diag={
        "kmass_market_expected_margin_mae":float(np.mean(np.abs(oof["actual_margin"]-oof["kmass_market_expected_margin"]))),
        "marketml_meanfix_expected_margin_mae":float(np.mean(np.abs(oof["actual_margin"]-oof["marketml_meanfix_expected_margin"]))),
        "fst_meanfix_expected_margin_mae":float(np.mean(np.abs(oof["actual_margin"]-oof["fst_meanfix_expected_margin"]))),
    }

    decisions={}
    mapping={
        "ATS-XM-IPROJ-FST-V1":("fst_iproj","marketml_iproj","fst_iproj_vs_marketml_iproj"),
        "ATS-XM-IPROJ-MEANFIX-V1":("fst_meanfix","marketml_meanfix","fst_meanfix_vs_marketml_meanfix"),
        "ATS-XM-CPL-OFFSET-V1":("cpl_offset","kmass_market","cpl_offset_vs_kmass_market"),
    }
    for cid,(cand,null,label) in mapping.items():
        b=boots[label]; ps=season_results[label]
        favorable_seasons=sum(1 for x in ps if x["delta"]<0)
        switches=overall[cand]["ats"]["side_switches_vs_kmass_market"]
        ats_delta=overall[cand]["ats"]["hit_rate_ex_push"]-overall[null]["ats"]["hit_rate_ex_push"]
        cal_c=overall[cand]["calibration"]; cal_n=overall[null]["calibration"]
        material_cal=False
        if cal_c.get("slope") is not None and cal_n.get("slope") is not None:
            material_cal |= abs(cal_c["slope"]-1)>abs(cal_n["slope"]-1)+float(CONFIG["calibration_material_slope_worsening"])
        if cal_c.get("intercept") is not None and cal_n.get("intercept") is not None:
            material_cal |= abs(cal_c["intercept"])>abs(cal_n["intercept"])+float(CONFIG["calibration_material_intercept_worsening"])
        primary_better=b["point_delta"]<0
        interval_support=b["ci_97_5"]<0
        holm_support=holm[cid]["holm_adjusted_p"]<0.05
        gates={"primary_better":primary_better,"paired_95_interval_entirely_favorable":interval_support,"favorable_seasons_at_least_3":favorable_seasons>=3,"no_material_calibration_degradation":not material_cal,"switches_at_least_10":switches>=int(CONFIG["minimum_switches_for_advancement"]),"ats_not_materially_adverse":ats_delta>=-float(CONFIG["ats_material_adverse_pp"]),"holm_adjusted_support":holm_support,"no_numerical_or_leakage_failure":True}
        if all(gates.values()): cls="IMPLEMENTATION_CANDIDATE"
        elif primary_better and favorable_seasons>=3: cls="HISTORICALLY_PROMISING"
        else: cls="NO_MATERIAL_IMPROVEMENT"
        decisions[cid]={"classification":cls,"gates":gates,"candidate_minus_null_delta":b["point_delta"],"favorable_seasons":favorable_seasons,"ats_hit_rate_delta":ats_delta,"switches":switches}

    implementation=[k for k,v in decisions.items() if v["classification"]=="IMPLEMENTATION_CANDIDATE"]
    best_mechanism=min(mapping,key=lambda k: decisions[k]["candidate_minus_null_delta"])
    result={
        "program":"LEVLINE_ATS_CROSSMARKET_TRANSFER_V1",
        "execution_sha":_git_sha(),
        "outer_test_seasons":list(OUTER),
        "common_rows":int(len(oof)),
        "common_rows_by_season":{str(int(s)):int(len(g)) for s,g in oof.groupby("season")},
        "completed_2026_outcomes_used":0,
        "production_changed":False,
        "market_probability_semantic_class":CONFIG["market_probability_semantic_class"],
        "source_signal":source,
        "chronology_selection":selections,
        "overall":overall,
        "bootstrap":boots,
        "holm":holm,
        "per_season":season_results,
        "robustness":loo,
        "center_mae_diagnostic":center_diag,
        "numerical_tests":numerical,
        "numerical_fold_diagnostics":numerical_folds,
        "coverage":coverage,
        "fst_reconstruction_receipts":fst_receipts,
        "historical_game_identity":game_identity,
        "decisions":decisions,
        "implementation_candidates":implementation,
        "best_point_estimate_mechanism":best_mechanism,
    }

    output_dir.mkdir(parents=True,exist_ok=True)
    _csv_dump(output_dir/"OOF_PREDICTIONS.csv",oof)
    _csv_dump(output_dir/"TRANSFER_DIAGNOSTICS.csv",pd.concat(bucket_parts,ignore_index=True))
    _json_dump(output_dir/"RESULTS.json",result)
    _json_dump(output_dir/"SOURCE_SIGNAL_AUDIT.json",source)
    _json_dump(output_dir/"BOOTSTRAP_RESULTS.json",{"bootstrap":boots,"holm":holm,"robustness":loo})
    _json_dump(output_dir/"NUMERICAL_TEST_RECEIPT.json",{"pretests":numerical,"folds":numerical_folds})
    _json_dump(output_dir/"PER_SEASON_RESULTS.json",season_results)
    _json_dump(output_dir/"ATS_RESULTS.json",{p:overall[p]["ats"] for p in prefixes})
    _json_dump(output_dir/"CALIBRATION_RESULTS.json",{p:overall[p]["calibration"] for p in prefixes})
    _json_dump(output_dir/"IMPLEMENTATION_DECISION.json",{"decisions":decisions,"implementation_candidates":implementation,"best_point_estimate_mechanism":best_mechanism})
    manifest={p.name:_sha(p) for p in sorted(output_dir.iterdir()) if p.is_file()}
    _json_dump(output_dir/"MANIFEST.json",manifest)
    return result


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",default=str(ROOT/"results"))
    args=parser.parse_args()
    result=run(Path(args.output_dir))
    print(json.dumps({"common_rows":result["common_rows"],"source_signal":result["source_signal"],"decisions":result["decisions"],"implementation_candidates":result["implementation_candidates"]},indent=2,sort_keys=True))


if __name__ == "__main__":
    main()

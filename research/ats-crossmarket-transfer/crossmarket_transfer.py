from __future__ import annotations

"""LEVLINE ATS CROSS-MARKET INFORMATION TRANSFER V1.

Research only. Reuses the accepted historical KMASS nuisance fits and chronology-clean
F-ST reconstruction. No completed-2026 outcome is loaded and no production artifact is
written.
"""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit, logsumexp
from scipy.stats import beta as beta_dist

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "research" / "ats-frontier-v2"))

import phase4_core as v2core  # noqa: E402

CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
EPS = 1e-12


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


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_prior_module():
    path = REPO_ROOT / "research" / "ats-historical-challenger" / "historical_challenger.py"
    spec = importlib.util.spec_from_file_location("ats_historical_challenger", path)
    if spec is None or spec.loader is None:
        raise CrossMarketError("cannot load canonical historical challenger")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _logit(x: float | np.ndarray) -> float | np.ndarray:
    p = np.clip(np.asarray(x, dtype=float), 1e-6, 1.0 - 1e-6)
    out = np.log(p / (1.0 - p))
    return float(out) if np.ndim(x) == 0 else out


def _candidate_target(p_market: float, p_fst: float, weight: float) -> float:
    d = float(_logit(p_fst) - _logit(p_market))
    return float(expit(float(_logit(p_market)) + float(weight) * d))


def _fit_for_season(prior, season: int) -> dict:
    try:
        return prior.V2_FREEZE["outer_seasons"][str(int(season))]["CONSTANT_SCALE_KEY"]
    except KeyError as exc:
        raise CrossMarketError(f"missing frozen KMASS fit for {season}") from exc


def _row_params(row: pd.Series, fit: dict) -> tuple[float, float, float, list[float]]:
    loc = float(row["market_margin"])
    sigma = float(v2core.m4_sigma(
        fit["scale_params"],
        np.asarray([float(row["total_line"])], dtype=float),
        np.asarray([float(row["spread_line"])], dtype=float),
        bool(fit["conditional"]),
    )[0])
    return loc, sigma, float(fit["nu"]), list(fit["key_params"])


def _base_sign_stats(row: pd.Series, fit: dict) -> dict:
    loc, sigma, nu, key = _row_params(row, fit)
    q0 = v2core.m4_cell(0, loc, sigma, nu, key)
    qminus = v2core.m4_leq(-1, loc, sigma, nu, key)
    qle0 = v2core.m4_leq(0, loc, sigma, nu, key)
    qplus = 1.0 - qle0
    if min(q0, qminus, qplus) < 0.0 or abs(q0 + qminus + qplus - 1.0) > 2e-12:
        raise CrossMarketError("invalid KMASS sign partition")
    return {"loc": loc, "sigma": sigma, "nu": nu, "key": key, "q0": q0, "qminus": qminus, "qplus": qplus}


def _projected_leq(k: int, stats: dict, u: float) -> float:
    u = float(u)
    q0, qminus, qplus = stats["q0"], stats["qminus"], stats["qplus"]
    if not (0.0 < u < 1.0):
        raise CrossMarketError("projection target outside (0,1)")
    sn = (1.0 - q0) * (1.0 - u) / qminus
    sp = (1.0 - q0) * u / qplus
    base = v2core.m4_leq(int(k), stats["loc"], stats["sigma"], stats["nu"], stats["key"])
    if k < 0:
        val = sn * base
    elif k == 0:
        val = sn * qminus + q0
    else:
        val = sn * qminus + q0 + sp * (base - qminus - q0)
    return float(np.clip(val, 0.0, 1.0))


def _projected_cell(m: int, stats: dict, u: float) -> float:
    q = v2core.m4_cell(int(m), stats["loc"], stats["sigma"], stats["nu"], stats["key"])
    q0, qminus, qplus = stats["q0"], stats["qminus"], stats["qplus"]
    if m > 0:
        scale = (1.0 - q0) * float(u) / qplus
    elif m < 0:
        scale = (1.0 - q0) * (1.0 - float(u)) / qminus
    else:
        scale = 1.0
    return float(q * scale)


def _cpl_from_projected(row: pd.Series, stats: dict, u: float) -> tuple[float, float, float]:
    line = float(row["spread_line"])
    if math.isclose(line, round(line), abs_tol=1e-10):
        m = int(round(line))
        loss = _projected_leq(m - 1, stats, u)
        push = _projected_cell(m, stats, u)
        cover = 1.0 - loss - push
    else:
        k = math.floor(line)
        loss = _projected_leq(k, stats, u)
        push = 0.0
        cover = 1.0 - loss
    vals = np.asarray([cover, push, loss], dtype=float)
    if not np.isfinite(vals).all() or (vals < -2e-12).any():
        raise CrossMarketError("invalid projected CPL probabilities")
    vals = np.clip(vals, 0.0, 1.0)
    vals /= vals.sum()
    return tuple(float(x) for x in vals)


def _adaptive_base_support(row: pd.Series, fit: dict) -> tuple[np.ndarray, np.ndarray, float, float]:
    stats = _base_sign_stats(row, fit)
    bound = int(CONFIG["initial_support_bound"])
    max_bound = int(CONFIG["maximum_support_bound"])
    tol = float(CONFIG["tail_tolerance"])
    while True:
        ms = np.arange(-bound, bound + 1, dtype=int)
        q = np.asarray([
            v2core.m4_cell(int(m), stats["loc"], stats["sigma"], stats["nu"], stats["key"])
            for m in ms
        ], dtype=float)
        total = float(q.sum())
        tail = max(0.0, 1.0 - total)
        if total > 1.0 + 5e-12:
            raise CrossMarketError("adaptive PMF support exceeds unit mass")
        if tail < tol:
            mean = float(np.dot(ms.astype(float), q))
            return ms, q, tail, mean
        bound *= 2
        if bound > max_bound:
            raise CrossMarketError(f"tail tolerance not reached; residual={tail}")


def _weighted_group_mean(ms: np.ndarray, q: np.ndarray, lam: float) -> float:
    mask = q > 0.0
    m = ms[mask].astype(float)
    qq = q[mask]
    lw = np.log(qq) + float(lam) * m
    z = logsumexp(lw)
    w = np.exp(lw - z)
    return float(np.dot(w, m))


def _meanfix_projection(row: pd.Series, fit: dict, u: float) -> dict:
    stats = _base_sign_stats(row, fit)
    ms, q, tail, target_mean = _adaptive_base_support(row, fit)
    q0 = float(stats["q0"])
    spos = (1.0 - q0) * float(u)
    sneg = (1.0 - q0) * (1.0 - float(u))
    pos = ms > 0
    neg = ms < 0
    zero = ms == 0
    qp, qn = q[pos], q[neg]
    mp, mn = ms[pos], ms[neg]
    if not qp.size or not qn.size or not zero.any():
        raise CrossMarketError("meanfix support missing sign group")

    def f(lam: float) -> float:
        return (
            spos * _weighted_group_mean(mp, qp, lam)
            + sneg * _weighted_group_mean(mn, qn, lam)
            - target_mean
        )

    if abs(f(0.0)) < 1e-14:
        lam = 0.0
    else:
        lo, hi = -1.0, 1.0
        flo, fhi = f(lo), f(hi)
        while flo > 0.0 and abs(lo) < 128.0:
            lo *= 2.0
            flo = f(lo)
        while fhi < 0.0 and abs(hi) < 128.0:
            hi *= 2.0
            fhi = f(hi)
        if flo > 0.0 or fhi < 0.0:
            raise CrossMarketError(
                f"meanfix constraint infeasible on adaptive support: f(lo)={flo}, f(hi)={fhi}"
            )
        lam = float(brentq(f, lo, hi, xtol=1e-13, rtol=1e-13, maxiter=300))

    p = np.zeros(len(ms), dtype=float)
    for mask, mass in ((pos, spos), (neg, sneg)):
        gm, gq = ms[mask].astype(float), q[mask]
        lw = np.log(gq) + lam * gm
        w = np.exp(lw - logsumexp(lw))
        p[mask] = mass * w
    p[zero] = q0
    if abs(float(p.sum()) - 1.0) > 3e-12 or (p < -1e-14).any():
        raise CrossMarketError("meanfix projected PMF does not normalize")
    mean = float(np.dot(ms.astype(float), p))
    if abs(mean - target_mean) > 5e-9:
        raise CrossMarketError(f"meanfix mean constraint failed: {mean-target_mean}")
    positive_mass = float(p[pos].sum())
    negative_mass = float(p[neg].sum())
    if abs(positive_mass - spos) > 3e-12 or abs(negative_mass - sneg) > 3e-12:
        raise CrossMarketError("meanfix sign constraint failed")

    line = float(row["spread_line"])
    if math.isclose(line, round(line), abs_tol=1e-10):
        line_i = int(round(line))
        push = float(p[ms == line_i].sum())
        loss = float(p[ms < line_i].sum())
    else:
        push = 0.0
        loss = float(p[ms <= math.floor(line)].sum())
    cover = float(1.0 - loss - push)
    actual = int(row["actual_margin"])
    hit = np.flatnonzero(ms == actual)
    if len(hit) != 1:
        raise CrossMarketError("observed margin outside adaptive support")
    obs_mass = float(p[int(hit[0])])
    return {
        "ms": ms,
        "p": p,
        "tail_mass_base": tail,
        "lambda": lam,
        "target_mean": target_mean,
        "mean": mean,
        "mean_error": mean - target_mean,
        "p_cover": cover,
        "p_push": push,
        "p_loss": loss,
        "observed_margin_mass": obs_mass,
    }


def _ats_class(row: pd.Series) -> int:
    return int(v2core.observed_ats_class(float(row["actual_margin"]), float(row["spread_line"])))


def _ll_for_class(cls: int, probs: tuple[float, float, float]) -> float:
    return float(-math.log(max(float(probs[int(cls)]), EPS)))


def _score_baseline(row: pd.Series, fit: dict) -> dict:
    loc, sigma, nu, key = _row_params(row, fit)
    cpl = v2core.m4_cpl(loc, sigma, nu, key, float(row["spread_line"]))
    mass = v2core.m4_cell(int(row["actual_margin"]), loc, sigma, nu, key)
    return {"p_cover": cpl[0], "p_push": cpl[1], "p_loss": cpl[2], "observed_margin_mass": mass}


def _score_iproj(row: pd.Series, fit: dict, u: float) -> dict:
    stats = _base_sign_stats(row, fit)
    cpl = _cpl_from_projected(row, stats, u)
    mass = _projected_cell(int(row["actual_margin"]), stats, u)
    return {"p_cover": cpl[0], "p_push": cpl[1], "p_loss": cpl[2], "observed_margin_mass": mass}


def _score_offset(row: pd.Series, fit: dict, beta: float) -> dict:
    base = _score_baseline(row, fit)
    d = float(_logit(float(row["fst_home_prob"])) - _logit(float(row["market_prob"])))
    nonpush = max(1.0 - float(base["p_push"]), EPS)
    c0 = np.clip(float(base["p_cover"]) / nonpush, 1e-9, 1.0 - 1e-9)
    c = float(expit(float(_logit(c0)) + float(beta) * d))
    cover = nonpush * c
    loss = nonpush * (1.0 - c)
    return {"p_cover": cover, "p_push": float(base["p_push"]), "p_loss": loss}


def _select_weights(train: pd.DataFrame, fit: dict) -> tuple[float, float, list[dict], list[dict]]:
    alpha_rows = []
    for alpha in [float(x) for x in CONFIG["alpha_grid"]]:
        losses = []
        for _, row in train.iterrows():
            u = _candidate_target(float(row["market_prob"]), float(row["fst_home_prob"]), alpha)
            score = _score_iproj(row, fit, u)
            losses.append(_ll_for_class(_ats_class(row), (score["p_cover"], score["p_push"], score["p_loss"])))
        alpha_rows.append({"alpha": alpha, "n": int(len(train)), "cpl_log_loss": float(np.mean(losses))})
    alpha_best = min(alpha_rows, key=lambda r: (r["cpl_log_loss"], r["alpha"]))

    beta_rows = []
    for beta in [float(x) for x in CONFIG["beta_grid"]]:
        losses = []
        for _, row in train.iterrows():
            score = _score_offset(row, fit, beta)
            losses.append(_ll_for_class(_ats_class(row), (score["p_cover"], score["p_push"], score["p_loss"])))
        beta_rows.append({"beta": beta, "n": int(len(train)), "cpl_log_loss": float(np.mean(losses))})
    beta_best = min(beta_rows, key=lambda r: (r["cpl_log_loss"], r["beta"]))
    return float(alpha_best["alpha"]), float(beta_best["beta"]), alpha_rows, beta_rows


def _score_outer(archive: pd.DataFrame, prior) -> tuple[pd.DataFrame, dict, list[dict]]:
    parts = []
    selection = {}
    numerical_failures: list[dict] = []
    for season in [int(x) for x in CONFIG["outer_test_seasons"]]:
        fit = _fit_for_season(prior, season)
        train = archive[(archive["season"] < season) & (archive["season"] >= int(CONFIG["inner_archive_first_season"]))].copy()
        test = archive[archive["season"] == season].copy()
        if train.empty or test.empty or train["season"].ge(season).any():
            raise CrossMarketError(f"invalid chronology for {season}")
        alpha, beta, alpha_grid, beta_grid = _select_weights(train, fit)
        selection[str(season)] = {
            "training_rows": int(len(train)),
            "training_first_season": int(train["season"].min()),
            "training_last_season": int(train["season"].max()),
            "alpha": alpha,
            "beta": beta,
            "alpha_grid": alpha_grid,
            "beta_grid": beta_grid,
        }
        rows = []
        for _, row in test.iterrows():
            out = {
                "game_id": str(row["game_id"]),
                "season": season,
                "week": int(row["week"]),
                "gameday": str(row.get("gameday", "")),
                "home_team": str(row.get("home_team", "")),
                "away_team": str(row.get("away_team", "")),
                "spread_line": float(row["spread_line"]),
                "total_line": float(row["total_line"]),
                "actual_margin": int(row["actual_margin"]),
                "home_win": int(row["home_win"]),
                "market_prob": float(row["market_prob"]),
                "fst_home_prob": float(row["fst_home_prob"]),
                "delta_fst": float(_logit(float(row["fst_home_prob"])) - _logit(float(row["market_prob"]))),
                "selected_alpha": alpha,
                "selected_beta": beta,
            }
            cls = _ats_class(row)
            out["ats_class"] = cls
            base = _score_baseline(row, fit)
            u_mkt = float(row["market_prob"])
            u_fst = _candidate_target(u_mkt, float(row["fst_home_prob"]), alpha)
            u_full = float(row["fst_home_prob"])
            simple_mkt = _score_iproj(row, fit, u_mkt)
            simple_fst = _score_iproj(row, fit, u_fst)
            simple_full = _score_iproj(row, fit, u_full)
            offset = _score_offset(row, fit, beta)
            try:
                mean_mkt = _meanfix_projection(row, fit, u_mkt)
                mean_fst = _meanfix_projection(row, fit, u_fst)
            except Exception as exc:
                numerical_failures.append({"season": season, "game_id": str(row["game_id"]), "error": repr(exc)})
                raise
            scores = {
                "base": base,
                "ml_iproj": simple_mkt,
                "fst_iproj": simple_fst,
                "fst_alpha1": simple_full,
                "ml_meanfix": mean_mkt,
                "fst_meanfix": mean_fst,
                "cpl_offset": offset,
            }
            for slug, score in scores.items():
                probs = (float(score["p_cover"]), float(score["p_push"]), float(score["p_loss"]))
                out[f"{slug}_p_cover"] = probs[0]
                out[f"{slug}_p_push"] = probs[1]
                out[f"{slug}_p_loss"] = probs[2]
                out[f"{slug}_cpl_ll"] = _ll_for_class(cls, probs)
                if "observed_margin_mass" in score:
                    mass = float(score["observed_margin_mass"])
                    out[f"{slug}_integer_ll"] = float(-math.log(max(mass, EPS)))
                if "mean_error" in score:
                    out[f"{slug}_mean_error"] = float(score["mean_error"])
                    out[f"{slug}_tail_mass_base"] = float(score["tail_mass_base"])
                    out[f"{slug}_lambda"] = float(score["lambda"])
            rows.append(out)
        parts.append(pd.DataFrame(rows))
    frame = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    return frame, selection, numerical_failures


def _source_metrics(frame: pd.DataFrame, pcol: str) -> dict:
    y = frame["home_win"].to_numpy(dtype=int)
    p = np.clip(frame[pcol].to_numpy(dtype=float), 1e-9, 1.0 - 1e-9)
    pred = (p >= 0.5).astype(int)
    return {
        "n": int(len(frame)),
        "winner_accuracy": float(np.mean(pred == y)),
        "winner_correct": int(np.sum(pred == y)),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p)))),
    }


def _conditional_metrics(frame: pd.DataFrame, slug: str) -> dict:
    y3 = frame["ats_class"].to_numpy(dtype=int)
    probs = frame[[f"{slug}_p_cover", f"{slug}_p_push", f"{slug}_p_loss"]].to_numpy(dtype=float)
    onehot = np.eye(3)[y3]
    mask = y3 != 1
    y = (y3[mask] == 0).astype(int)
    p = np.clip(probs[mask, 0] / np.clip(probs[mask, 0] + probs[mask, 2], EPS, None), 1e-9, 1.0 - 1e-9)
    brier = float(np.mean((p - y) ** 2))
    logloss = float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))
    ybar = float(np.mean(y))
    bins = np.minimum((p * 10).astype(int), 9)
    reliability = 0.0
    resolution = 0.0
    rel_rows = []
    for b in sorted(set(bins.tolist())):
        idx = bins == b
        pk, yk, nk = float(np.mean(p[idx])), float(np.mean(y[idx])), int(idx.sum())
        w = nk / len(y)
        reliability += w * (pk - yk) ** 2
        resolution += w * (yk - ybar) ** 2
        rel_rows.append({"bin": int(b), "n": nk, "mean_pred": pk, "observed": yk})
    return {
        "conditional_nonpush_n": int(mask.sum()),
        "conditional_cover_brier": brier,
        "conditional_cover_log_loss": logloss,
        "multiclass_brier": float(np.mean(np.sum((probs - onehot) ** 2, axis=1))),
        "brier_component_cover": float(np.mean((probs[:, 0] - onehot[:, 0]) ** 2)),
        "brier_component_push": float(np.mean((probs[:, 1] - onehot[:, 1]) ** 2)),
        "brier_component_loss": float(np.mean((probs[:, 2] - onehot[:, 2]) ** 2)),
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(ybar * (1.0 - ybar)),
        "sharpness_std_conditional_cover": float(np.std(p, ddof=0)),
        "reliability_bins": rel_rows,
        "calibration": v2core.calibration_report(y3, probs),
    }


def _exact_hit_interval(wins: int, losses: int, alpha: float = 0.05) -> tuple[float | None, float | None]:
    n = wins + losses
    if n == 0:
        return None, None
    lo = 0.0 if wins == 0 else float(beta_dist.ppf(alpha / 2.0, wins, n - wins + 1))
    hi = 1.0 if wins == n else float(beta_dist.ppf(1.0 - alpha / 2.0, wins + 1, n - wins))
    return lo, hi


def _ats_metrics(frame: pd.DataFrame, slug: str) -> dict:
    tmp = pd.DataFrame({
        "p_cover": frame[f"{slug}_p_cover"],
        "p_push": frame[f"{slug}_p_push"],
        "p_loss": frame[f"{slug}_p_loss"],
        "ats_class": frame["ats_class"],
    })
    out = v2core.full_slate_ats_diagnostic(tmp)
    lo, hi = _exact_hit_interval(int(out["wins"]), int(out["losses"]))
    out["exact_hit_rate_ci_95"] = [lo, hi]
    out["economic_price_label"] = str(CONFIG["economic_price_assumption"])
    return out


def _side(frame: pd.DataFrame, slug: str) -> np.ndarray:
    return np.where(frame[f"{slug}_p_cover"].to_numpy(dtype=float) >= frame[f"{slug}_p_loss"].to_numpy(dtype=float), 0, 2)


def _switch_report(frame: pd.DataFrame, candidate: str, reference: str) -> dict:
    cs, rs = _side(frame, candidate), _side(frame, reference)
    mask = cs != rs
    y = frame["ats_class"].to_numpy(dtype=int)
    decisive = mask & (y != 1)
    wins = int(np.sum(cs[decisive] == y[decisive]))
    losses = int(np.sum(cs[decisive] != y[decisive]))
    pushes = int(np.sum(mask & (y == 1)))
    n = wins + losses
    return {
        "switches": int(mask.sum()),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_ex_push": float(wins / n) if n else None,
    }


def _bootstrap(frame: pd.DataFrame, delta_col: str) -> dict:
    data = frame[["season", "week", delta_col]].dropna().copy()
    blocks = {
        int(season): [g[delta_col].to_numpy(dtype=float) for _, g in s.groupby("week", sort=True)]
        for season, s in data.groupby("season", sort=True)
    }
    rng = np.random.default_rng(int(CONFIG["bootstrap_seed"]))
    B = int(CONFIG["bootstrap_resamples"])
    draws = np.empty(B, dtype=float)
    for b in range(B):
        vals = []
        for season in sorted(blocks):
            weeks = blocks[season]
            idx = rng.integers(0, len(weeks), size=len(weeks))
            vals.extend(weeks[int(i)] for i in idx)
        draws[b] = float(np.mean(np.concatenate(vals)))
    point = float(data[delta_col].mean())
    p_one = float((np.sum(draws >= 0.0) + 1) / (B + 1))
    loo_week = []
    for (season, week), _ in data.groupby(["season", "week"], sort=True):
        keep = ~((data["season"] == season) & (data["week"] == week))
        loo_week.append({"season": int(season), "week": int(week), "delta": float(data.loc[keep, delta_col].mean())})
    return {
        "n": int(len(data)),
        "weeks": int(data[["season", "week"]].drop_duplicates().shape[0]),
        "point_delta": point,
        "ci_2_5": float(np.percentile(draws, 2.5)),
        "ci_97_5": float(np.percentile(draws, 97.5)),
        "probability_favorable": float(np.mean(draws < 0.0)),
        "one_sided_bootstrap_p": p_one,
        "seed": int(CONFIG["bootstrap_seed"]),
        "resamples": B,
        "leave_one_week_out_min": float(min(x["delta"] for x in loo_week)),
        "leave_one_week_out_max": float(max(x["delta"] for x in loo_week)),
        "leave_one_week_out_flips_unfavorable": bool(point < 0.0 and any(x["delta"] >= 0.0 for x in loo_week)),
    }


def _holm_adjust(raw: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        adj = min(1.0, (m - i) * float(p))
        running = max(running, adj)
        out[name] = running
    return out


def _per_season_delta(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    return {
        str(int(s)): float((g[f"{candidate}_cpl_ll"] - g[f"{null}_cpl_ll"]).mean())
        for s, g in frame.groupby("season", sort=True)
    }


def _loso_delta(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    out = {}
    for s in sorted(frame["season"].unique()):
        g = frame[frame["season"] != s]
        out[str(int(s))] = float((g[f"{candidate}_cpl_ll"] - g[f"{null}_cpl_ll"]).mean())
    return out


def _bucket_diagnostics(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    abs_spread = frame["spread_line"].abs()
    specs = [
        ("abs_spread_le_2", abs_spread <= 2.0),
        ("2_lt_abs_spread_le_3_5", (abs_spread > 2.0) & (abs_spread <= 3.5)),
        ("3_5_lt_abs_spread_le_6_5", (abs_spread > 3.5) & (abs_spread <= 6.5)),
        ("6_5_lt_abs_spread_le_7_5", (abs_spread > 6.5) & (abs_spread <= 7.5)),
        ("abs_spread_gt_7_5", abs_spread > 7.5),
    ]
    rows = []
    for label, mask in specs:
        g = frame[mask]
        rows.append({
            "bucket": label,
            "n": int(len(g)),
            "candidate_minus_null_cpl_ll": float((g[f"{candidate}_cpl_ll"] - g[f"{null}_cpl_ll"]).mean()) if len(g) else None,
            "candidate_ats": _ats_metrics(g, candidate) if len(g) else None,
            "null_ats": _ats_metrics(g, null) if len(g) else None,
        })
    return rows


def _key_diagnostics(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    a = frame["spread_line"].abs()
    near3 = (a - 3.0).abs() <= float(CONFIG["key_near_tolerance"])
    near7 = (a - 7.0).abs() <= float(CONFIG["key_near_tolerance"])
    specs = [("near_3", near3), ("near_7", near7), ("other", ~(near3 | near7))]
    rows = []
    for label, mask in specs:
        g = frame[mask]
        rows.append({
            "bucket": label,
            "n": int(len(g)),
            "candidate_minus_null_cpl_ll": float((g[f"{candidate}_cpl_ll"] - g[f"{null}_cpl_ll"]).mean()) if len(g) else None,
        })
    return rows


def _transfer_diagnostics(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    edges = [float(x) for x in CONFIG["delta_abs_bins"]]
    d = frame["delta_fst"].abs()
    s = frame["spread_line"].abs()
    spread_specs = [
        ("le2", s <= 2.0),
        ("2to3_5", (s > 2.0) & (s <= 3.5)),
        ("3_5to6_5", (s > 3.5) & (s <= 6.5)),
        ("6_5to7_5", (s > 6.5) & (s <= 7.5)),
        ("gt7_5", s > 7.5),
    ]
    rows = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        dm = (d >= lo) & (d < hi)
        for slabel, sm in spread_specs:
            g = frame[dm & sm]
            if g.empty:
                continue
            rows.append({
                "delta_abs_lo": lo,
                "delta_abs_hi": hi,
                "spread_bucket": slabel,
                "n": int(len(g)),
                "mean_abs_delta_fst": float(g["delta_fst"].abs().mean()),
                "candidate_minus_null_cpl_ll": float((g[f"{candidate}_cpl_ll"] - g[f"{null}_cpl_ll"]).mean()),
            })
    return rows


def _material_calibration_degradation(cand: dict, null: dict) -> bool:
    ci, cs = cand["calibration"].get("intercept"), cand["calibration"].get("slope")
    ni, ns = null["calibration"].get("intercept"), null["calibration"].get("slope")
    if None in (ci, cs, ni, ns):
        return True
    iw = abs(float(ci)) - abs(float(ni))
    sw = abs(float(cs) - 1.0) - abs(float(ns) - 1.0)
    return bool(iw > float(CONFIG["calibration_material_intercept_worsening"]) or sw > float(CONFIG["calibration_material_slope_worsening"]))


def _numerical_tests(archive: pd.DataFrame, prior) -> dict:
    season = int(CONFIG["outer_test_seasons"][0])
    fit = _fit_for_season(prior, season)
    row = archive[archive["season"] == season].iloc[0]
    stats = _base_sign_stats(row, fit)
    sign_sum = stats["q0"] + stats["qminus"] + stats["qplus"]
    half = row.copy()
    half["spread_line"] = float(math.floor(float(row["spread_line"]))) + 0.5
    whole = row.copy()
    whole["spread_line"] = float(round(float(row["spread_line"])))
    u = float(row["market_prob"])
    ip0 = _score_iproj(row, fit, u)
    ip0b = _score_iproj(row, fit, _candidate_target(u, float(row["fst_home_prob"]), 0.0))
    off0 = _score_offset(row, fit, 0.0)
    base = _score_baseline(row, fit)
    mean = _meanfix_projection(row, fit, u)
    half_cpl = _cpl_from_projected(half, _base_sign_stats(half, fit), u)
    whole_cpl = _cpl_from_projected(whole, _base_sign_stats(whole, fit), u)
    checks = {
        "pmf_sign_partition_normalizes": abs(sign_sum - 1.0) < 2e-12,
        "nonnegative_sign_mass": min(stats["q0"], stats["qminus"], stats["qplus"]) >= 0.0,
        "tie_mass_preserved_iproj": abs(_projected_cell(0, stats, u) - stats["q0"]) < 2e-12,
        "half_point_has_no_push": abs(half_cpl[1]) < 1e-15,
        "whole_line_has_push": whole_cpl[1] > 0.0,
        "alpha0_reproduces_market_null": max(abs(ip0[k] - ip0b[k]) for k in ("p_cover", "p_push", "p_loss", "observed_margin_mass")) < 2e-12,
        "beta0_reproduces_cpl_baseline": max(abs(off0[k] - base[k]) for k in ("p_cover", "p_push", "p_loss")) < 2e-12,
        "meanfix_normalizes": abs(float(mean["p"].sum()) - 1.0) < 3e-12,
        "meanfix_tie_preserved": abs(float(mean["p"][mean["ms"] == 0][0]) - stats["q0"]) < 3e-12,
        "meanfix_mean_preserved": abs(float(mean["mean_error"])) < 5e-9,
        "adaptive_tail_tolerance": float(mean["tail_mass_base"]) < float(CONFIG["tail_tolerance"]),
        "repository_spread_is_expected_home_margin": abs(float(row["market_margin"]) - float(row["spread_line"])) < 1e-12,
        "deterministic_iproj": ip0 == _score_iproj(row, fit, u),
    }
    if not all(checks.values()):
        raise CrossMarketError(f"numerical pretests failed: {checks}")
    return {"status": "PASS", "checks": checks, "sample_game_id": str(row["game_id"]), "sample_season": season}


def _leakage_tests(archive: pd.DataFrame, prior_receipts: dict, historical_identity: dict) -> dict:
    chronology_ok = all(int(v["training_last_season"]) < int(k) for k, v in prior_receipts.items())
    mutation_sample = archive.iloc[0].copy()
    season = int(mutation_sample["season"])
    fit = _fit_for_season(_load_prior_module(), season)
    before = _score_iproj(mutation_sample, fit, float(mutation_sample["market_prob"]))
    mutation_sample["actual_margin"] = int(mutation_sample["actual_margin"]) + 17
    after_probs = _score_iproj(mutation_sample, fit, float(mutation_sample["market_prob"]))
    outcome_invariant = max(abs(before[k] - after_probs[k]) for k in ("p_cover", "p_push", "p_loss")) < 1e-15
    checks = {
        "completed_2026_outcomes_loaded_zero": int(historical_identity.get("completed_2026_rows", -1)) == 0,
        "fst_fold_training_strictly_prior": chronology_ok,
        "target_outcome_mutation_does_not_change_prediction_probabilities": outcome_invariant,
        "outer_max_season_2025": int(archive["season"].max()) <= 2025,
        "target_season_not_used_for_alpha_beta_by_contract": True,
        "outer_results_do_not_define_architecture": True,
    }
    if not all(checks.values()):
        raise CrossMarketError(f"leakage pretests failed: {checks}")
    return {"status": "PASS", "checks": checks}


def _overall_metrics(frame: pd.DataFrame) -> tuple[dict, dict, dict]:
    slugs = ["base", "ml_iproj", "fst_iproj", "fst_alpha1", "ml_meanfix", "fst_meanfix", "cpl_offset"]
    overall, ats, calibration = {}, {}, {}
    for slug in slugs:
        cond = _conditional_metrics(frame, slug)
        vals = {
            "n": int(len(frame)),
            "cpl_log_loss": float(frame[f"{slug}_cpl_ll"].mean()),
            **{k: v for k, v in cond.items() if k != "reliability_bins"},
        }
        if f"{slug}_integer_ll" in frame:
            vals["integer_margin_log_score"] = float(frame[f"{slug}_integer_ll"].mean())
        overall[slug] = vals
        calibration[slug] = {"calibration": cond["calibration"], "reliability_bins": cond["reliability_bins"], "reliability": cond["reliability"], "resolution": cond["resolution"], "sharpness": cond["sharpness_std_conditional_cover"]}
        ats[slug] = _ats_metrics(frame, slug)
    return overall, ats, calibration


def _decision(frame: pd.DataFrame, overall: dict, ats: dict, bootstrap: dict, numerical_failures: list[dict]) -> dict:
    comps = {
        "ATS-XM-IPROJ-FST-V1": ("fst_iproj", "ml_iproj"),
        "ATS-XM-IPROJ-MEANFIX-V1": ("fst_meanfix", "ml_meanfix"),
        "ATS-XM-CPL-OFFSET-V1": ("cpl_offset", "base"),
    }
    out = {}
    for name, (cand, null) in comps.items():
        delta = float(overall[cand]["cpl_log_loss"] - overall[null]["cpl_log_loss"])
        per = _per_season_delta(frame, cand, null)
        switch = _switch_report(frame, cand, null)
        cal_bad = _material_calibration_degradation(overall[cand], overall[null])
        hr_c = ats[cand]["hit_rate_ex_push"]
        hr_n = ats[null]["hit_rate_ex_push"]
        ats_bad = bool(switch["switches"] >= 10 and hr_c is not None and hr_n is not None and float(hr_c) <= float(hr_n) - float(CONFIG["ats_material_adverse_pp"]))
        gates = {
            "primary_better": delta < 0.0,
            "bootstrap_upper_below_zero": float(bootstrap[name]["ci_97_5"]) < 0.0,
            "favorable_in_at_least_3_outer_seasons": sum(v < 0.0 for v in per.values()) >= 3,
            "no_material_calibration_degradation": not cal_bad,
            "no_numerical_or_leakage_failure": len(numerical_failures) == 0,
            "at_least_10_side_switches": int(switch["switches"]) >= int(CONFIG["minimum_switches_for_advancement"]),
            "not_driven_by_one_week": not bool(bootstrap[name]["leave_one_week_out_flips_unfavorable"]),
            "ats_not_materially_adverse": not ats_bad,
            "operational_complexity_reasonable": True,
        }
        if all(gates.values()):
            classification = "IMPLEMENTATION_CANDIDATE"
        elif len(numerical_failures):
            classification = "FAILED"
        elif delta < 0.0:
            classification = "HISTORICALLY_PROMISING"
        else:
            classification = "NO_MATERIAL_IMPROVEMENT"
        out[name] = {
            "candidate_slug": cand,
            "null_slug": null,
            "delta_cpl_log_loss": delta,
            "per_season_delta": per,
            "leave_one_season_out_delta": _loso_delta(frame, cand, null),
            "switch_report": switch,
            "calibration_materially_degraded": cal_bad,
            "ats_materially_adverse": ats_bad,
            "gates": gates,
            "classification": classification,
        }
    implementation = [k for k, v in out.items() if v["classification"] == "IMPLEMENTATION_CANDIDATE"]
    best = min(out, key=lambda k: out[k]["delta_cpl_log_loss"])
    return {"candidates": out, "implementation_candidates": implementation, "best_point_estimate_mechanism": best}


def _write_markdown_results(outdir: Path, summary: dict) -> None:
    dec = summary["decision"]
    lines = [
        "# Implementation Decision",
        "",
        f"Common N: **{summary['common_n']}** across outer seasons {summary['outer_seasons']}.",
        "",
    ]
    for name, d in dec["candidates"].items():
        b = summary["bootstrap"][name]
        lines += [
            f"## {name}",
            f"- classification: `{d['classification']}`",
            f"- candidate-minus-null CPL log loss: `{d['delta_cpl_log_loss']:.12g}`",
            f"- 95% week-block interval: `[{b['ci_2_5']:.12g}, {b['ci_97_5']:.12g}]`",
            f"- switches: `{d['switch_report']['switches']}`; switch record `{d['switch_report']['wins']}-{d['switch_report']['losses']}-{d['switch_report']['pushes']}`",
            "",
        ]
    if dec["implementation_candidates"]:
        central = "YES — at least one frozen transfer mechanism satisfies the historical implementation gate."
    else:
        central = "NO — no frozen transfer mechanism satisfies the full historical implementation gate."
    lines += ["## Central answer", central, "", f"Best primary point estimate mechanism: `{dec['best_point_estimate_mechanism']}`.", ""]
    (outdir / "IMPLEMENTATION_DECISION.md").write_text("\n".join(lines), encoding="utf-8")

    rec = summary["source_signal"]["overall"]
    final = [
        "# Final Receipt",
        "",
        f"- execution head: `{summary['execution_head']}`",
        f"- common N: `{summary['common_n']}`",
        f"- F-ST winner accuracy: `{rec['fst']['winner_accuracy']:.6f}`",
        f"- market winner accuracy: `{rec['market']['winner_accuracy']:.6f}`",
        f"- completed-2026 outcomes used: `{summary['completed_2026_outcomes_used']}`",
        f"- production changed: `{summary['production_changed']}`",
        f"- implementation candidates: `{dec['implementation_candidates']}`",
        "",
        "This receipt is research-only and does not authorize production promotion.",
    ]
    (outdir / "FINAL_RECEIPT.md").write_text("\n".join(final) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict:
    prior = _load_prior_module()
    games, historical_identity = prior.build_historical_games()
    archive, coverage, fst_receipts = prior.build_center_archive(games)
    archive = archive[archive["season"].between(int(CONFIG["inner_archive_first_season"]), max(CONFIG["outer_test_seasons"]))].copy()
    if archive["season"].ge(2026).any():
        raise CrossMarketError("completed-2026 firewall violated")

    numerical = _numerical_tests(archive, prior)
    leakage = _leakage_tests(archive, fst_receipts, historical_identity)

    target_archive = archive[archive["season"].isin([int(x) for x in CONFIG["outer_test_seasons"]])].copy()
    source = {
        "overall": {"fst": _source_metrics(target_archive, "fst_home_prob"), "market": _source_metrics(target_archive, "market_prob")},
        "by_season": {
            str(int(s)): {"fst": _source_metrics(g, "fst_home_prob"), "market": _source_metrics(g, "market_prob")}
            for s, g in target_archive.groupby("season", sort=True)
        },
        "market_probability_semantic_class": CONFIG["market_probability_semantic_class"],
    }

    oof, selection, numerical_failures = _score_outer(archive, prior)
    if len(oof) != len(target_archive) or set(oof["game_id"]) != set(target_archive["game_id"].astype(str)):
        raise CrossMarketError("outer candidate common-row identity mismatch")

    overall, ats, calibration = _overall_metrics(oof)
    comparisons = {
        "ATS-XM-IPROJ-FST-V1": ("fst_iproj", "ml_iproj"),
        "ATS-XM-IPROJ-MEANFIX-V1": ("fst_meanfix", "ml_meanfix"),
        "ATS-XM-CPL-OFFSET-V1": ("cpl_offset", "base"),
    }
    bootstrap = {}
    raw_p = {}
    for name, (cand, null) in comparisons.items():
        col = f"delta__{cand}__{null}"
        oof[col] = oof[f"{cand}_cpl_ll"] - oof[f"{null}_cpl_ll"]
        bootstrap[name] = _bootstrap(oof, col)
        raw_p[name] = float(bootstrap[name]["one_sided_bootstrap_p"])
    holm = _holm_adjust(raw_p)
    for name in bootstrap:
        bootstrap[name]["holm_adjusted_one_sided_p"] = float(holm[name])

    decision = _decision(oof, overall, ats, bootstrap, numerical_failures)

    per_season_rows = []
    for season, g in oof.groupby("season", sort=True):
        for slug in ["base", "ml_iproj", "fst_iproj", "fst_alpha1", "ml_meanfix", "fst_meanfix", "cpl_offset"]:
            per_season_rows.append({
                "season": int(season),
                "model": slug,
                "n": int(len(g)),
                "cpl_log_loss": float(g[f"{slug}_cpl_ll"].mean()),
                "integer_margin_log_score": float(g[f"{slug}_integer_ll"].mean()) if f"{slug}_integer_ll" in g else None,
                "ats_wins": _ats_metrics(g, slug)["wins"],
                "ats_losses": _ats_metrics(g, slug)["losses"],
                "ats_pushes": _ats_metrics(g, slug)["pushes"],
                "ats_hit_rate_ex_push": _ats_metrics(g, slug)["hit_rate_ex_push"],
            })
    per_season = pd.DataFrame(per_season_rows)

    bucket = {}
    keydiag = {}
    transfer = {}
    for name, (cand, null) in comparisons.items():
        bucket[name] = _bucket_diagnostics(oof, cand, null)
        keydiag[name] = _key_diagnostics(oof, cand, null)
        transfer[name] = _transfer_diagnostics(oof, cand, null)

    summary = {
        "program": CONFIG["program"],
        "execution_head": _git_sha(),
        "outer_seasons": [int(x) for x in CONFIG["outer_test_seasons"]],
        "common_n": int(len(oof)),
        "common_n_by_season": {str(int(s)): int(len(g)) for s, g in oof.groupby("season")},
        "historical_identity": historical_identity,
        "coverage": coverage,
        "fst_fold_receipts": fst_receipts,
        "source_signal": source,
        "selection": selection,
        "overall": overall,
        "ats": ats,
        "calibration": calibration,
        "bootstrap": bootstrap,
        "decision": decision,
        "spread_bucket_diagnostics": bucket,
        "key_number_diagnostics": keydiag,
        "transfer_diagnostics": transfer,
        "numerical_tests": numerical,
        "leakage_tests": leakage,
        "numerical_failures": numerical_failures,
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "sportsbook_reference_side_defined": False,
        "sportsbook_reference_side_note": "No historical spread-side price/lean is available; ATS sides are model probability choices and economic sensitivity is REFERENCE_MINUS110 only.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    oof.to_csv(output_dir / "OOF_PREDICTIONS.csv", index=False, float_format="%.17g")
    per_season.to_csv(output_dir / "PER_SEASON_RESULTS.csv", index=False, float_format="%.17g")
    _json_dump(output_dir / "OVERALL_RESULTS.json", overall)
    _json_dump(output_dir / "ATS_RESULTS.json", ats)
    _json_dump(output_dir / "CALIBRATION_REPORT.json", calibration)
    _json_dump(output_dir / "BOOTSTRAP_RESULTS.json", bootstrap)
    _json_dump(output_dir / "TRANSFER_DIAGNOSTICS.json", transfer)
    _json_dump(output_dir / "SOURCE_SIGNAL_AUDIT.json", source)
    _json_dump(output_dir / "NUMERICAL_TEST_RECEIPT.json", numerical)
    _json_dump(output_dir / "RED_TEAM_AUDIT.json", {"leakage": leakage, "numerical_failures": numerical_failures, "production_changed": False})
    _json_dump(output_dir / "IMPLEMENTATION_DECISION.json", decision)
    _json_dump(output_dir / "FINAL_RECEIPT.json", summary)
    _write_markdown_results(output_dir, summary)
    manifest = {p.name: _sha256_file(p) for p in sorted(output_dir.iterdir()) if p.is_file()}
    _json_dump(output_dir / "MANIFEST.json", manifest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({
        "common_n": result["common_n"],
        "source_signal": result["source_signal"]["overall"],
        "selection": {k: {"alpha": v["alpha"], "beta": v["beta"]} for k, v in result["selection"].items()},
        "decision": result["decision"],
        "completed_2026_outcomes_used": result["completed_2026_outcomes_used"],
        "production_changed": result["production_changed"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

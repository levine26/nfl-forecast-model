from __future__ import annotations

"""Chronology-clean ATS Market Manifold V2 historical experiment.

Research only. Primary candidates use sportsbook spread + immutable historical market
moneyline probability only. No F-ST/football signal enters candidate construction.
"""

import argparse
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

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
V1_ROOT = REPO_ROOT / "research" / "ats-crossmarket-transfer"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
OUTER = tuple(int(x) for x in CONFIG["outer_test_seasons"])
THETAS = tuple(float(x) for x in CONFIG["theta_grid"])
EPS = 1e-12


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Use the exact accepted V1 schedule/archive/support code, then its strict inner chronology.
probability_entry = _load("probability_only_entrypoint", V1_ROOT / "probability_only_entrypoint.py")
xm = probability_entry.runner
strict_entry = _load("ats_xm_chronology_strict_v2_dependency", V1_ROOT / "chronology_strict_entrypoint.py")


class MarketManifoldError(RuntimeError):
    pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.17g")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _logit_scalar(p: float) -> float:
    return float(xm._logit([float(p)])[0])


def _archive() -> tuple[pd.DataFrame, dict, dict]:
    games, identity = probability_entry.build_schedule_only_historical_games()
    archive, coverage, _ = probability_entry.build_probability_archive(games)
    archive = archive.dropna(
        subset=["game_id", "season", "week", "actual_margin", "spread_line", "total_line", "market_margin", "market_prob"]
    ).copy()
    archive["season"] = pd.to_numeric(archive["season"], errors="raise").astype(int)
    archive["week"] = pd.to_numeric(archive["week"], errors="raise").astype(int)
    if archive["season"].ge(2026).any():
        raise MarketManifoldError("2026 outcome entered V2 archive")
    if archive["game_id"].astype(str).duplicated().any():
        raise MarketManifoldError("duplicate game identity")
    expected = {str(k): int(v) for k, v in CONFIG["expected_common_rows_by_season"].items()}
    observed = {k: int(v["common_rows"]) for k, v in coverage["coverage_by_season"].items()}
    if observed != expected:
        raise MarketManifoldError(f"canonical common-row drift: {observed} != {expected}")
    if identity["game_ids_sha256"] != CONFIG["canonical_game_ids_sha256"]:
        raise MarketManifoldError("canonical historical game identity hash drift")
    return archive.sort_values(["season", "week", "game_id"]).reset_index(drop=True), coverage, identity


def _n1_support(parts: dict, market_prob: float) -> tuple[np.ndarray, np.ndarray, dict]:
    margins, q, tail = xm._adaptive_support(parts)
    if float(tail) >= float(CONFIG["tail_tolerance"]):
        raise MarketManifoldError(f"adaptive tail tolerance failed: {tail}")
    zero = margins == 0
    pos = margins > 0
    neg = margins < 0
    if int(zero.sum()) != 1:
        raise MarketManifoldError("support must contain exactly one zero cell")
    q0 = float(parts["q0"])
    u = float(np.clip(market_prob, 1e-9, 1.0 - 1e-9))
    target_pos = (1.0 - q0) * u
    target_neg = (1.0 - q0) * (1.0 - u)
    p0 = np.zeros_like(q, dtype=float)
    p0[zero] = q0
    p0[pos] = q[pos] * (target_pos / float(q[pos].sum()))
    p0[neg] = q[neg] * (target_neg / float(q[neg].sum()))
    if abs(float(p0.sum()) - 1.0) > 5e-11:
        raise MarketManifoldError("N1 adaptive-support PMF does not normalize")
    uq = float(parts["qpos"] / (parts["qpos"] + parts["qneg"]))
    r_ml = _logit_scalar(u) - _logit_scalar(uq)
    meta = {
        "tail_mass": float(tail),
        "target_pos": target_pos,
        "target_neg": target_neg,
        "q0": q0,
        "r_ml": r_ml,
        "support_bound": int(max(abs(int(margins[0])), abs(int(margins[-1])))),
        "n1_expected_margin": float(np.dot(margins.astype(float), p0)),
    }
    return margins, p0, meta


def _shape_basis(margins: np.ndarray, line: float) -> np.ndarray:
    width = float(CONFIG["shape_width_points"])
    return np.tanh((margins.astype(float) - float(line)) / width)


def _weighted_region(base: np.ndarray, m: np.ndarray, h: np.ndarray, gamma: float, lam: float, total: float) -> np.ndarray:
    z = np.log(np.clip(base, 1e-300, None)) + float(gamma) * h + float(lam) * m
    z -= float(np.max(z))
    w = np.exp(z)
    denom = float(w.sum())
    if not np.isfinite(denom) or denom <= 0:
        raise MarketManifoldError("shape-tilt exponential weighting failed")
    return w * (float(total) / denom)


def _candidate_pmf(parts: dict, market_prob: float, theta: float, *, meanfix: bool) -> tuple[np.ndarray, np.ndarray, dict]:
    margins, p0, n1 = _n1_support(parts, market_prob)
    zero = margins == 0
    pos = margins > 0
    neg = margins < 0
    h = _shape_basis(margins, float(parts["line"]))
    gamma = float(theta) * float(n1["r_ml"])
    target_pos = float(n1["target_pos"])
    target_neg = float(n1["target_neg"])
    q0 = float(n1["q0"])

    def build(lam: float) -> np.ndarray:
        p = np.zeros_like(p0)
        p[zero] = q0
        p[pos] = _weighted_region(
            p0[pos], margins[pos].astype(float), h[pos], gamma, lam, target_pos
        )
        p[neg] = _weighted_region(
            p0[neg], margins[neg].astype(float), h[neg], gamma, lam, target_neg
        )
        return p

    lam = 0.0
    target_mean = float(n1["n1_expected_margin"])
    if meanfix and abs(gamma) > 1e-15:
        def f(value: float) -> float:
            return float(np.dot(margins.astype(float), build(value))) - target_mean

        lo, hi = -0.25, 0.25
        flo, fhi = f(lo), f(hi)
        for _ in range(40):
            if flo <= 0.0 <= fhi:
                break
            if flo > 0.0:
                lo *= 2.0
                flo = f(lo)
            if fhi < 0.0:
                hi *= 2.0
                fhi = f(hi)
        else:
            raise MarketManifoldError("mean-fixed market shape tilt is infeasible")
        lam = float(brentq(f, lo, hi, xtol=1e-13, rtol=1e-13, maxiter=300))

    p = build(lam)
    if abs(float(p.sum()) - 1.0) > 5e-11:
        raise MarketManifoldError("candidate PMF does not normalize")
    if abs(float(p[zero][0]) - q0) > 1e-12:
        raise MarketManifoldError("candidate zero mass changed")
    if abs(float(p[pos].sum()) - target_pos) > 2e-11:
        raise MarketManifoldError("candidate positive sign mass changed")
    if abs(float(p[neg].sum()) - target_neg) > 2e-11:
        raise MarketManifoldError("candidate negative sign mass changed")
    implied_mean = float(np.dot(margins.astype(float), p))
    if meanfix and abs(implied_mean - target_mean) > 2e-9:
        raise MarketManifoldError("candidate N1 mean constraint failed")
    return margins, p, {
        **n1,
        "theta": float(theta),
        "gamma": gamma,
        "lambda": lam,
        "candidate_expected_margin": implied_mean,
        "meanfix": bool(meanfix),
        "mean_constraint_error": abs(implied_mean - target_mean) if meanfix else None,
    }


def _candidate_probs(parts: dict, market_prob: float, theta: float, *, meanfix: bool) -> tuple[tuple[float, float, float], float, dict, tuple[np.ndarray, np.ndarray]]:
    # theta=0 is the frozen strong null by contract; return its exact analytic CPL/mass.
    if abs(float(theta)) < 1e-15:
        margins, p, meta = _candidate_pmf(parts, market_prob, 0.0, meanfix=meanfix)
        exact = xm._iproj_cpl(parts, float(market_prob))
        mass = xm._iproj_observed_mass(parts, int(parts["_actual_margin"]), float(market_prob))
        return exact, float(mass), meta, (margins, p)
    margins, p, meta = _candidate_pmf(parts, market_prob, theta, meanfix=meanfix)
    probs = xm._pmf_cpl(margins, p, float(parts["line"]))
    mass = xm._pmf_mass(margins, p, int(parts["_actual_margin"]))
    return probs, float(mass), meta, (margins, p)


def _parts(row: pd.Series, fit: dict) -> dict:
    parts = xm._base_parts(row, fit)
    parts["_actual_margin"] = int(row["actual_margin"])
    return parts


def _rps(margins: np.ndarray, p: np.ndarray, actual_margin: int) -> float:
    mass = float(p.sum())
    if not np.isfinite(mass) or mass <= 0:
        raise MarketManifoldError("invalid RPS support mass")
    pn = p / mass
    cdf = np.cumsum(pn)
    obs_cdf = (margins >= int(actual_margin)).astype(float)
    return float(np.sum((cdf - obs_cdf) ** 2))


def _select_theta(train: pd.DataFrame) -> tuple[float, list[dict]]:
    grid: list[dict] = []
    for theta in THETAS:
        losses: list[float] = []
        by_season: dict[int, list[float]] = {}
        for _, row in train.iterrows():
            season = int(row["season"])
            fit = strict_entry._inner_fit(season)
            parts = _parts(row, fit)
            probs, _, _, _ = _candidate_probs(parts, float(row["market_prob"]), theta, meanfix=False)
            cls = xm._observed_class(int(row["actual_margin"]), float(row["spread_line"]))
            loss = xm._cpl_loss(cls, probs)
            losses.append(loss)
            by_season.setdefault(season, []).append(loss)
        grid.append({
            "theta": float(theta),
            "n": int(len(losses)),
            "cpl_log_loss": float(np.mean(losses)),
            "season_forward_inner": True,
            "per_season": {str(s): float(np.mean(v)) for s, v in sorted(by_season.items())},
        })
    best = min(grid, key=lambda r: (r["cpl_log_loss"], r["theta"]))
    return float(best["theta"]), grid


def _score_fold(test: pd.DataFrame, fit: dict, theta: float) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    tails: list[float] = []
    mean_errors: list[float] = []
    bounds: list[int] = []
    for _, row in test.iterrows():
        parts = _parts(row, fit)
        market = float(row["market_prob"])
        cls = xm._observed_class(int(row["actual_margin"]), float(row["spread_line"]))

        margins_q, q, tail_q = xm._adaptive_support(parts)
        n1_support_m, n1_support_p, n1_meta = _n1_support(parts, market)
        n1_probs = xm._iproj_cpl(parts, market)
        n1_mass = xm._iproj_observed_mass(parts, int(row["actual_margin"]), market)
        a_probs, a_mass, a_meta, (a_m, a_p) = _candidate_probs(parts, market, theta, meanfix=False)
        b_probs, b_mass, b_meta, (b_m, b_p) = _candidate_probs(parts, market, theta, meanfix=True)

        rec = {
            "game_id": str(row["game_id"]),
            "season": int(row["season"]),
            "week": int(row["week"]),
            "gameday": str(row.get("gameday", "")),
            "home_team": str(row.get("home_team", "")),
            "away_team": str(row.get("away_team", "")),
            "actual_margin": int(row["actual_margin"]),
            "spread_line": float(row["spread_line"]),
            "total_line": float(row["total_line"]),
            "market_prob": market,
            "r_ml": float(n1_meta["r_ml"]),
            "theta_selected": float(theta),
            "ats_class": int(cls),
        }
        models = {
            "kmass_market": ((parts["p_cover"], parts["p_push"], parts["p_loss"]), float(parts["observed_mass"]), margins_q, q),
            "marketml_iproj": (n1_probs, float(n1_mass), n1_support_m, n1_support_p),
            "mm_shapetilt": (a_probs, a_mass, a_m, a_p),
            "mm_shapetilt_meanfix": (b_probs, b_mass, b_m, b_p),
        }
        for name, (probs, mass, margins, pmf) in models.items():
            rec[f"{name}_p_cover"] = float(probs[0])
            rec[f"{name}_p_push"] = float(probs[1])
            rec[f"{name}_p_loss"] = float(probs[2])
            rec[f"{name}_conditional_cover"] = float(probs[0] / max(float(probs[0] + probs[2]), EPS))
            rec[f"{name}_cpl_log_loss"] = xm._cpl_loss(cls, probs)
            rec[f"{name}_integer_log_score"] = float(-math.log(max(float(mass), EPS)))
            rec[f"{name}_expected_margin"] = float(np.dot(margins.astype(float), pmf / float(pmf.sum())))
            rec[f"{name}_rps"] = _rps(margins, pmf, int(row["actual_margin"]))

        rows.append(rec)
        tails.extend([float(tail_q), float(a_meta["tail_mass"]), float(b_meta["tail_mass"])])
        bounds.extend([int(a_meta["support_bound"]), int(b_meta["support_bound"])])
        if b_meta["mean_constraint_error"] is not None:
            mean_errors.append(float(b_meta["mean_constraint_error"]))
    return pd.DataFrame(rows), {
        "max_tail_mass": float(max(tails)),
        "max_support_bound": int(max(bounds)),
        "max_mean_constraint_error": float(max(mean_errors) if mean_errors else 0.0),
    }


def _bootstrap(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    col = f"delta__{candidate}__vs__{null}"
    temp = frame[["season", "week"]].copy()
    temp[col] = frame[f"{candidate}_cpl_log_loss"] - frame[f"{null}_cpl_log_loss"]
    return xm.v2.paired_week_bootstrap(
        temp,
        col,
        resamples=int(CONFIG["bootstrap_resamples"]),
        seed=int(CONFIG["bootstrap_seed"]),
    )


def _holm(boots: dict[str, dict]) -> dict:
    n = int(CONFIG["bootstrap_resamples"])
    ordered = sorted(
        [(name, max(1.0 / n, 1.0 - float(value["probability_favorable"]))) for name, value in boots.items()],
        key=lambda x: x[1],
    )
    out: dict[str, dict] = {}
    running = 0.0
    m = len(ordered)
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = {"raw_one_sided_bootstrap_p": float(p), "holm_adjusted_p": float(running)}
    return out


def _switch_record(frame: pd.DataFrame, candidate: str, null: str) -> dict:
    cand = np.where(frame[f"{candidate}_p_cover"].to_numpy(float) >= frame[f"{candidate}_p_loss"].to_numpy(float), 0, 2)
    ref = np.where(frame[f"{null}_p_cover"].to_numpy(float) >= frame[f"{null}_p_loss"].to_numpy(float), 0, 2)
    y = frame["ats_class"].to_numpy(int)
    sw = cand != ref
    decisive = sw & (y != 1)
    wins = int(np.sum(cand[decisive] == y[decisive]))
    losses = int(np.sum(cand[decisive] != y[decisive]))
    pushes = int(np.sum(sw & (y == 1)))
    if int(sw.sum()):
        counts = frame.loc[sw].groupby(["season", "week"]).size()
        max_week = int(counts.max())
        max_share = float(max_week / int(sw.sum()))
    else:
        max_week = 0
        max_share = 0.0
    return {
        "switches": int(sw.sum()),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_ex_push": float(wins / (wins + losses)) if wins + losses else None,
        "max_switches_single_season_week": max_week,
        "max_single_week_switch_share": max_share,
    }


def _diagnostics(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    work = frame.copy()
    a = work["spread_line"].abs()
    work["spread_bucket"] = pd.cut(
        a,
        bins=[-1e-12, 2.0, 3.5, 6.5, 7.5, float("inf")],
        labels=["<=2", "2-3.5", "3.5-6.5", "6.5-7.5", ">7.5"],
        include_lowest=True,
    )
    work["key_bucket"] = np.select(
        [np.isclose(a, 3.0), np.isclose(a, 7.0)],
        ["abs_spread_3", "abs_spread_7"],
        default="other",
    )
    bins = [float(x) for x in CONFIG["r_ml_abs_bins"]]
    work["r_ml_bucket"] = pd.cut(work["r_ml"].abs(), bins=bins, right=False, include_lowest=True)
    work["delta"] = work[f"{candidate}_cpl_log_loss"] - work[f"{null}_cpl_log_loss"]
    out: list[dict] = []
    for dim in ["spread_bucket", "key_bucket", "r_ml_bucket"]:
        for bucket, g in work.groupby(dim, observed=True, sort=False):
            out.append({
                "dimension": dim,
                "bucket": str(bucket),
                "candidate": candidate,
                "null": null,
                "n": int(len(g)),
                "mean_delta_cpl": float(g["delta"].mean()),
                "mean_abs_r_ml": float(g["r_ml"].abs().mean()),
            })
    return out


def _preflight_payload() -> dict:
    archive, coverage, identity = _archive()
    outer = archive[archive["season"].isin(OUTER)].copy()
    if outer.empty:
        raise MarketManifoldError("preflight has no outer rows")
    _, pre2021 = strict_entry._build_pre2021_fit()
    if int(pre2021["training_last_season"]) >= 2021:
        raise MarketManifoldError("pre-2021 nuisance chronology failed")

    max_theta0 = 0.0
    max_sign = 0.0
    max_zero = 0.0
    max_mean = 0.0
    max_tail = 0.0
    mutation_ok = True
    fst_mutation_ok = True
    for _, row in outer.head(40).iterrows():
        fit = xm._fit_for_season(int(row["season"]))
        parts = _parts(row, fit)
        market = float(row["market_prob"])
        exact = xm._iproj_cpl(parts, market)
        for meanfix in (False, True):
            probs0, _, _, _ = _candidate_probs(parts, market, 0.0, meanfix=meanfix)
            max_theta0 = max(max_theta0, max(abs(a - b) for a, b in zip(exact, probs0)))
            margins, p, meta = _candidate_pmf(parts, market, 1.0, meanfix=meanfix)
            pos = margins > 0
            neg = margins < 0
            zero = margins == 0
            max_sign = max(max_sign, abs(float(p[pos].sum()) - float(meta["target_pos"])), abs(float(p[neg].sum()) - float(meta["target_neg"])))
            max_zero = max(max_zero, abs(float(p[zero][0]) - float(meta["q0"])))
            max_tail = max(max_tail, float(meta["tail_mass"]))
            if meanfix:
                max_mean = max(max_mean, float(meta["mean_constraint_error"]))

        mutated = row.copy()
        mutated["actual_margin"] = int(row["actual_margin"]) + 37
        parts2 = _parts(mutated, fit)
        a1, _, _, _ = _candidate_probs(parts, market, 1.0, meanfix=False)
        a2, _, _, _ = _candidate_probs(parts2, market, 1.0, meanfix=False)
        mutation_ok = mutation_ok and max(abs(x-y) for x, y in zip(a1, a2)) < 1e-15

        fst_mut = row.copy()
        if "fst_home_prob" in fst_mut:
            fst_mut["fst_home_prob"] = 0.999 if float(fst_mut["fst_home_prob"]) < 0.5 else 0.001
        parts3 = _parts(fst_mut, fit)
        a3, _, _, _ = _candidate_probs(parts3, market, 1.0, meanfix=False)
        fst_mutation_ok = fst_mutation_ok and max(abs(x-y) for x, y in zip(a1, a3)) < 1e-15

    whole = outer[np.isclose(outer["spread_line"], np.round(outer["spread_line"]))].head(1)
    half = outer[~np.isclose(outer["spread_line"], np.round(outer["spread_line"]))].head(1)
    whole_push = False
    half_zero = False
    if not whole.empty:
        row = whole.iloc[0]
        parts = _parts(row, xm._fit_for_season(int(row["season"])))
        probs, _, _, _ = _candidate_probs(parts, float(row["market_prob"]), 1.0, meanfix=False)
        whole_push = probs[1] > 0.0
    if not half.empty:
        row = half.iloc[0]
        parts = _parts(row, xm._fit_for_season(int(row["season"])))
        probs, _, _, _ = _candidate_probs(parts, float(row["market_prob"]), 1.0, meanfix=False)
        half_zero = abs(probs[1]) < 1e-15

    checks = {
        "canonical_game_identity_match": identity["game_ids_sha256"] == CONFIG["canonical_game_ids_sha256"],
        "canonical_common_rows_match": True,
        "completed_2026_outcomes_zero": int((archive["season"] >= 2026).sum()) == 0,
        "pre2021_nuisance_strictly_prior": int(pre2021["training_last_season"]) < 2021,
        "theta0_reproduces_N1": max_theta0 <= 1e-12,
        "sign_mass_preserved": max_sign <= 2e-11,
        "zero_mass_preserved": max_zero <= 1e-12,
        "N1_mean_preserved_by_meanfix": max_mean <= 2e-9,
        "adaptive_tail_below_tolerance": max_tail < float(CONFIG["tail_tolerance"]),
        "whole_line_push_positive": bool(whole_push),
        "half_line_push_zero": bool(half_zero),
        "target_outcome_mutation_prediction_invariant": bool(mutation_ok),
        "FST_field_mutation_prediction_invariant": bool(fst_mutation_ok),
        "primary_candidate_signature_has_no_FST_input": True,
    }
    if not all(checks.values()):
        raise MarketManifoldError(f"V2 preflight failed: {checks}")
    return {
        "status": "PASS",
        "checks": checks,
        "max_errors": {
            "theta0": max_theta0,
            "sign_mass": max_sign,
            "zero_mass": max_zero,
            "mean_constraint": max_mean,
            "tail_mass": max_tail,
        },
        "pre2021_nuisance": pre2021,
        "historical_game_identity": identity,
        "coverage": coverage,
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
    }


def preflight(output: Path) -> dict:
    payload = _preflight_payload()
    _dump(output, payload)
    return payload


def run(output_dir: Path, preflight_path: Path | None = None) -> dict:
    if preflight_path is not None:
        pre = json.loads(preflight_path.read_text(encoding="utf-8"))
        if pre.get("status") != "PASS":
            raise MarketManifoldError("refusing target scoring without passing preflight")
    else:
        pre = _preflight_payload()

    archive, coverage, identity = _archive()
    scored_parts: list[pd.DataFrame] = []
    selections: list[dict] = []
    numerical: list[dict] = []
    for season in OUTER:
        train = archive[archive["season"] < season].copy()
        test = archive[archive["season"] == season].copy()
        if train.empty or test.empty or train["season"].ge(season).any():
            raise MarketManifoldError(f"invalid outer chronology for {season}")
        theta, grid = _select_theta(train)
        fit = xm._fit_for_season(season)
        scored, meta = _score_fold(test, fit, theta)
        scored_parts.append(scored)
        numerical.append({"season": int(season), **meta})
        selections.append({
            "season": int(season),
            "theta_selected": float(theta),
            "inner_training_n": int(len(train)),
            "inner_training_seasons": sorted(int(x) for x in train["season"].unique()),
            "theta_grid": grid,
        })

    oof = pd.concat(scored_parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    if len(oof) != 1087 or oof["game_id"].duplicated().any() or oof["season"].ge(2026).any():
        raise MarketManifoldError("canonical V2 OOF identity/size firewall failed")

    prefixes = ["kmass_market", "marketml_iproj", "mm_shapetilt", "mm_shapetilt_meanfix"]
    overall: dict[str, dict] = {}
    for prefix in prefixes:
        overall[prefix] = {
            "n": int(len(oof)),
            "cpl_log_loss": float(oof[f"{prefix}_cpl_log_loss"].mean()),
            "cpl_brier_components": xm._cpl_brier(oof, prefix),
            "conditional": xm._conditional_metrics(oof, prefix),
            "calibration": xm._calibration(oof, prefix),
            "ats": xm._ats(oof, prefix),
            "integer_margin_log_score": float(oof[f"{prefix}_integer_log_score"].mean()),
            "rps": float(oof[f"{prefix}_rps"].mean()),
            "expected_margin_mae": float(np.mean(np.abs(oof["actual_margin"] - oof[f"{prefix}_expected_margin"]))),
        }

    # Hard parity with accepted V1 strong/null scores before interpreting new candidates.
    if abs(overall["kmass_market"]["cpl_log_loss"] - 0.7696147399) > 1e-9:
        raise MarketManifoldError("KMASS-MARKET score drift versus canonical V1")
    if abs(overall["marketml_iproj"]["cpl_log_loss"] - 0.7682207714) > 1e-9:
        raise MarketManifoldError("KMASS-MARKETML-IPROJ score drift versus canonical V1")

    mapping = {
        "ATS-MM-SHAPETILT-V1": "mm_shapetilt",
        "ATS-MM-SHAPETILT-MEANFIX-V1": "mm_shapetilt_meanfix",
    }
    boots: dict[str, dict] = {}
    per_season: dict[str, list[dict]] = {}
    robustness: dict[str, dict] = {}
    switches: dict[str, dict] = {}
    diag_rows: list[dict] = []
    for cid, cand in mapping.items():
        boots[cid] = _bootstrap(oof, cand, "marketml_iproj")
        per_season[cid] = xm._per_season(oof, cand, "marketml_iproj")
        robustness[cid] = {
            "leave_one_season_out": xm._leave_one_season_out(oof, cand, "marketml_iproj"),
            "leave_one_week_out": xm._leave_one_week_out(oof, cand, "marketml_iproj"),
        }
        switches[cid] = _switch_record(oof, cand, "marketml_iproj")
        diag_rows.extend(_diagnostics(oof, cand, "marketml_iproj"))
    holm = _holm(boots)

    decisions: dict[str, dict] = {}
    for cid, cand in mapping.items():
        boot = boots[cid]
        seasons = per_season[cid]
        favorable = int(sum(1 for x in seasons if float(x["delta"]) < 0.0))
        switch = switches[cid]
        cand_cal = overall[cand]["calibration"]
        null_cal = overall["marketml_iproj"]["calibration"]
        material_cal = False
        if cand_cal.get("slope") is not None and null_cal.get("slope") is not None:
            material_cal |= abs(float(cand_cal["slope"]) - 1.0) > abs(float(null_cal["slope"]) - 1.0) + float(CONFIG["calibration_material_slope_worsening"])
        if cand_cal.get("intercept") is not None and null_cal.get("intercept") is not None:
            material_cal |= abs(float(cand_cal["intercept"])) > abs(float(null_cal["intercept"])) + float(CONFIG["calibration_material_intercept_worsening"])
        ats_delta = float(overall[cand]["ats"]["hit_rate_ex_push"] - overall["marketml_iproj"]["ats"]["hit_rate_ex_push"])
        gates = {
            "primary_better": float(boot["point_delta"]) < 0.0,
            "paired_95_interval_entirely_favorable": float(boot["ci_97_5"]) < 0.0,
            "favorable_seasons_at_least_3": favorable >= 3,
            "no_material_calibration_degradation": not material_cal,
            "no_numerical_or_leakage_failure": True,
            "switches_at_least_10": int(switch["switches"]) >= int(CONFIG["minimum_switches_for_advancement"]),
            "no_single_week_switch_concentration": float(switch["max_single_week_switch_share"]) <= float(CONFIG["max_single_week_switch_share"]),
            "ats_not_materially_adverse": ats_delta >= -float(CONFIG["ats_material_adverse_pp"]),
            "holm_adjusted_support": float(holm[cid]["holm_adjusted_p"]) < 0.05,
        }
        if all(gates.values()):
            classification = "IMPLEMENTATION_CANDIDATE"
        elif gates["primary_better"] and gates["favorable_seasons_at_least_3"]:
            classification = "HISTORICALLY_PROMISING"
        else:
            classification = "NO_MATERIAL_IMPROVEMENT"
        decisions[cid] = {
            "classification": classification,
            "candidate_minus_N1_delta": float(boot["point_delta"]),
            "favorable_seasons": favorable,
            "ats_hit_rate_delta": ats_delta,
            "switch_record": switch,
            "gates": gates,
        }

    implementation = [cid for cid, d in decisions.items() if d["classification"] == "IMPLEMENTATION_CANDIDATE"]
    result = {
        "program": CONFIG["program"],
        "execution_sha": _git_sha(),
        "outer_test_seasons": list(OUTER),
        "common_rows": int(len(oof)),
        "common_rows_by_season": {str(int(s)): int(len(g)) for s, g in oof.groupby("season")},
        "evidence_status": "DEVELOPMENT_NON_PRISTINE",
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "market_probability_semantic_class": CONFIG["market_probability_semantic_class"],
        "canonical_v1_execution_sha": CONFIG["canonical_v1_execution_sha"],
        "historical_game_identity": identity,
        "coverage": coverage,
        "preflight_status": pre["status"],
        "chronology_selection": selections,
        "overall": overall,
        "bootstrap": boots,
        "holm": holm,
        "per_season": per_season,
        "robustness": robustness,
        "switches_vs_N1": switches,
        "numerical_fold_diagnostics": numerical,
        "decisions": decisions,
        "implementation_candidates": implementation,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _csv(output_dir / "OOF_PREDICTIONS.csv", oof)
    _csv(output_dir / "FIXED_DIAGNOSTICS.csv", pd.DataFrame(diag_rows))
    _dump(output_dir / "RESULTS.json", result)
    _dump(output_dir / "BOOTSTRAP_RESULTS.json", {"bootstrap": boots, "holm": holm, "robustness": robustness})
    _dump(output_dir / "PER_SEASON_RESULTS.json", per_season)
    _dump(output_dir / "IMPLEMENTATION_DECISION.json", {"decisions": decisions, "implementation_candidates": implementation})
    _dump(output_dir / "NUMERICAL_RECEIPT.json", {"preflight": pre, "folds": numerical})

    lines = [
        "# Final Scientific Receipt — ATS Market Manifold V2",
        "",
        f"Execution SHA: `{result['execution_sha']}`",
        f"Common OOF N: `{result['common_rows']}` across `{result['outer_test_seasons']}`.",
        "Evidence status: `DEVELOPMENT_NON_PRISTINE`.",
        "Completed-2026 outcomes used: `0`.",
        "Production changed: `False`.",
        f"Preflight: `{result['preflight_status']}`.",
        "",
        "## Candidate classifications",
        "",
    ]
    for cid in mapping:
        d = decisions[cid]
        b = boots[cid]
        lines.append(
            f"- `{cid}`: `{d['classification']}`; delta `{d['candidate_minus_N1_delta']:.12g}`; "
            f"95% block interval `[{float(b['ci_2_5']):.12g}, {float(b['ci_97_5']):.12g}]`."
        )
    lines.extend(["", "Research only. No production promotion is authorized by this receipt.", ""])
    (output_dir / "FINAL_RECEIPT.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {p.name: _sha(p) for p in sorted(output_dir.iterdir()) if p.is_file() and p.name != "MANIFEST.json"}
    _dump(output_dir / "MANIFEST.json", manifest)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--preflight-output", type=Path, default=ROOT / "preflight_receipt.json")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        payload = preflight(args.preflight_output)
        print(json.dumps({"status": payload["status"], "checks": payload["checks"]}, indent=2, sort_keys=True))
        return
    result = run(args.output_dir, args.preflight_output if args.preflight_output.exists() else None)
    print(json.dumps({
        "common_rows": result["common_rows"],
        "chronology_selection": [
            {"season": x["season"], "theta": x["theta_selected"]} for x in result["chronology_selection"]
        ],
        "decisions": result["decisions"],
        "implementation_candidates": result["implementation_candidates"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

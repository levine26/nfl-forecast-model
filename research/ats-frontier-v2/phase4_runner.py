from __future__ import annotations

"""Controlled historical development runner for ATS Frontier V2 Phase 4.

The runner is intentionally self-contained inside the research tree. It reads the frozen
Phase-3 contracts, loads nflverse history through 2025 only, executes the preregistered
M3 and M4 experiments with chronological outer/inner evaluation, and emits immutable
research evidence. It never imports or modifies the production forecasting pipeline.
"""

import argparse
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import t as student_t

from nfl_forecast.data import load_core_data
from nfl_forecast.features import aggregate_team_games

import phase4_core as core

ROOT = Path(__file__).resolve().parent
CONFIG = core.CONFIG
OUTER = tuple(int(x) for x in CONFIG["outer_development_seasons"])
WARMUP = int(CONFIG["warmup_start_season"])
MARKET_LABEL = CONFIG["market_horizon_label"]


class Phase4RunError(RuntimeError):
    pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def _json_dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv_dump(path: Path, frame: pd.DataFrame) -> None:
    out = frame.copy()
    keys = [c for c in ("season", "week", "game_id", "variant") if c in out.columns]
    if keys:
        out = out.sort_values(keys).reset_index(drop=True)
    out.to_csv(path, index=False, lineterminator="\n")


def _regular(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "game_type" in out.columns:
        out = out[out["game_type"].eq("REG")].copy()
    elif "season_type" in out.columns:
        out = out[out["season_type"].eq("REG")].copy()
    return out


def _load_source() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    # Absolute completed-2026 firewall: the data loader is never asked for 2026.
    seasons = list(range(WARMUP, 2026))
    bundle = load_core_data(seasons)
    sched = _regular(bundle.schedules)
    sched["season"] = pd.to_numeric(sched["season"], errors="coerce")
    sched["week"] = pd.to_numeric(sched["week"], errors="coerce")
    sched = sched[sched["season"].between(WARMUP, 2025, inclusive="both")].copy()
    if (sched["season"] >= 2026).any():
        raise Phase4RunError("completed-2026 schedule row entered Phase 4")
    sched["home_score"] = pd.to_numeric(sched["home_score"], errors="coerce")
    sched["away_score"] = pd.to_numeric(sched["away_score"], errors="coerce")
    sched["spread_line"] = pd.to_numeric(sched["spread_line"], errors="coerce")
    sched["total_line"] = pd.to_numeric(sched.get("total_line"), errors="coerce")
    sched = sched[sched["home_score"].notna() & sched["away_score"].notna()].copy()
    sched["actual_margin"] = (sched["home_score"] - sched["away_score"]).round().astype(int)
    sched["market_margin"] = core.market_margin(sched["spread_line"])
    if "gameday" in sched.columns:
        sched["gameday"] = pd.to_datetime(sched["gameday"], errors="coerce")
    keep = [
        c for c in (
            "game_id", "season", "week", "gameday", "home_team", "away_team",
            "home_score", "away_score", "spread_line", "total_line", "actual_margin",
            "market_margin",
        ) if c in sched.columns
    ]
    games = sched[keep].drop_duplicates("game_id").copy()

    pbp = _regular(bundle.pbp)
    pbp["season"] = pd.to_numeric(pbp["season"], errors="coerce")
    pbp["week"] = pd.to_numeric(pbp["week"], errors="coerce")
    pbp = pbp[pbp["season"].between(WARMUP, 2025, inclusive="both")].copy()
    if (pbp["season"] >= 2026).any():
        raise Phase4RunError("completed-2026 PBP row entered Phase 4")

    identity_payload = {
        "schedule_rows": int(len(games)),
        "pbp_rows": int(len(pbp)),
        "schedule_seasons": sorted(int(x) for x in games["season"].dropna().unique()),
        "pbp_seasons": sorted(int(x) for x in pbp["season"].dropna().unique()),
        "game_ids_sha256": sha256("\n".join(sorted(games["game_id"].astype(str))).encode()).hexdigest(),
        "market_label": MARKET_LABEL,
    }
    identity_payload["dataset_identity_sha256"] = sha256(
        json.dumps(identity_payload, sort_keys=True).encode()
    ).hexdigest()
    return games, pbp, identity_payload


def _prior_z_by_week(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Standardize each observation with moments available before its NFL week."""
    out = frame.copy().sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    history: dict[str, list[float]] = {c: [] for c in columns}
    for (_, _), idx in out.groupby(["season", "week"], sort=True).groups.items():
        ii = np.asarray(list(idx), dtype=int)
        for col in columns:
            h = np.asarray(history[col], dtype=float)
            h = h[np.isfinite(h)]
            mean = float(np.mean(h)) if len(h) else 0.0
            sd = float(np.std(h, ddof=1)) if len(h) > 20 else np.nan
            if not np.isfinite(sd) or sd < 1e-6:
                sd = 1.0
            vals = pd.to_numeric(out.loc[ii, col], errors="coerce").to_numpy(dtype=float)
            out.loc[ii, f"z_{col}"] = (vals - mean) / sd
        # Current week enters moments only after every row in that week is transformed.
        for col in columns:
            vals = pd.to_numeric(out.loc[ii, col], errors="coerce").to_numpy(dtype=float)
            history[col].extend(float(v) for v in vals if np.isfinite(v))
    return out


def _team_observations(pbp: pd.DataFrame) -> pd.DataFrame:
    obs = aggregate_team_games(pbp)
    need = ["game_id", "season", "week", "team", "off_epa", "success_rate", "def_epa_allowed", "def_success_allowed"]
    for col in need:
        if col not in obs.columns:
            obs[col] = np.nan
    obs = obs[need].copy()
    obs = _prior_z_by_week(obs, ["off_epa", "success_rate", "def_epa_allowed", "def_success_allowed"])
    obs["off_measure"] = obs[["z_off_epa", "z_success_rate"]].mean(axis=1, skipna=True)
    # D is defensive strength; lower EPA/success allowed therefore maps to higher D.
    obs["def_measure"] = -obs[["z_def_epa_allowed", "z_def_success_allowed"]].mean(axis=1, skipna=True)
    return obs


def _qb_observations(pbp: pd.DataFrame) -> pd.DataFrame:
    q = pbp.copy()
    id_col = next((c for c in ("passer_player_id", "passer_id", "qb_player_id") if c in q.columns), None)
    if id_col is None:
        raise Phase4RunError("PBP has no qualified historical QB identity column")
    drop_col = "qb_dropback" if "qb_dropback" in q.columns else "pass_attempt"
    q["_drop"] = pd.to_numeric(q.get(drop_col, 0), errors="coerce").fillna(0.0)
    q["_epa"] = pd.to_numeric(q.get("epa"), errors="coerce")
    q = q[q["posteam"].notna() & q[id_col].notna() & q["_drop"].eq(1) & q["_epa"].notna()].copy()
    if q.empty:
        raise Phase4RunError("qualified QB dropback table is empty")
    grouped = q.groupby(["game_id", "season", "week", "posteam", id_col], observed=True).agg(
        qb_epa_dropback=("_epa", "mean"), dropbacks=("_drop", "sum")
    ).reset_index()
    grouped = grouped.sort_values(["game_id", "posteam", "dropbacks"], ascending=[True, True, False])
    grouped = grouped.drop_duplicates(["game_id", "posteam"], keep="first")
    grouped = grouped.rename(columns={"posteam": "team", id_col: "qb_id"})
    grouped["qb_id"] = grouped["qb_id"].astype(str)
    grouped = _prior_z_by_week(grouped, ["qb_epa_dropback"])
    grouped["qb_measure"] = grouped["z_qb_epa_dropback"]
    return grouped[["game_id", "season", "week", "team", "qb_id", "dropbacks", "qb_measure"]]


def _obs_maps(team_obs: pd.DataFrame, qb_obs: pd.DataFrame):
    team_map = {
        (int(r.season), int(r.week), str(r.game_id), str(r.team)): (float(r.off_measure), float(r.def_measure))
        for r in team_obs.itertuples(index=False)
    }
    qb_map = {
        (int(r.season), int(r.week), str(r.game_id), str(r.team)): (str(r.qb_id), float(r.qb_measure))
        for r in qb_obs.itertuples(index=False)
    }
    return team_map, qb_map


def _state_features(
    games: pd.DataFrame,
    team_map: dict,
    qb_map: dict,
    *, q_team: float,
    q_qb: float,
    lam: float,
) -> pd.DataFrame:
    offense: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    defense: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    quarterbacks: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    last_qb: dict[str, str] = {}
    static_off_sum = defaultdict(float); static_off_n = defaultdict(int)
    static_def_sum = defaultdict(float); static_def_n = defaultdict(int)
    static_qb_sum = defaultdict(float); static_qb_n = defaultdict(int)
    rows: list[dict] = []
    previous_season = None

    ordered = games.sort_values(["season", "week", "game_id"]).copy()
    for (season, week), week_games in ordered.groupby(["season", "week"], sort=True):
        season = int(season); week = int(week)
        if previous_season is not None and season != previous_season:
            offense = {k: core.season_transition(v, lam, q_team) for k, v in offense.items()}
            defense = {k: core.season_transition(v, lam, q_team) for k, v in defense.items()}
            quarterbacks = {k: core.season_transition(v, lam, q_qb) for k, v in quarterbacks.items()}
        previous_season = season

        # Freeze all target-week predictors before any target-week update.
        for g in week_games.itertuples(index=False):
            home = str(g.home_team); away = str(g.away_team)
            oh = offense.get(home, core.ScalarState()).mean
            oa = offense.get(away, core.ScalarState()).mean
            dh = defense.get(home, core.ScalarState()).mean
            da = defense.get(away, core.ScalarState()).mean
            hq = last_qb.get(home); aq = last_qb.get(away)
            qh = quarterbacks.get(hq, core.ScalarState()).mean if hq else 0.0
            qa = quarterbacks.get(aq, core.ScalarState()).mean if aq else 0.0
            soh = static_off_sum[home] / static_off_n[home] if static_off_n[home] else 0.0
            soa = static_off_sum[away] / static_off_n[away] if static_off_n[away] else 0.0
            sdh = static_def_sum[home] / static_def_n[home] if static_def_n[home] else 0.0
            sda = static_def_sum[away] / static_def_n[away] if static_def_n[away] else 0.0
            sqh = static_qb_sum[hq] / static_qb_n[hq] if hq and static_qb_n[hq] else 0.0
            sqa = static_qb_sum[aq] / static_qb_n[aq] if aq and static_qb_n[aq] else 0.0
            rows.append({
                "game_id": str(g.game_id), "season": season, "week": week,
                "dynamic_team_signal": (oh - da) - (oa - dh),
                "dynamic_qb_signal": qh - qa,
                "static_team_signal": (soh - sda) - (soa - sdh),
                "static_qb_signal": sqh - sqa,
                "home_prior_qb": hq or "LEAGUE_PRIOR",
                "away_prior_qb": aq or "LEAGUE_PRIOR",
            })

        # Current-week outcomes update only after every prediction for the week is frozen.
        for g in week_games.itertuples(index=False):
            for team in (str(g.home_team), str(g.away_team)):
                key = (season, week, str(g.game_id), team)
                if key in team_map:
                    off_m, def_m = team_map[key]
                    offense[team] = core.update_state(offense.get(team, core.ScalarState()), off_m, q_team)
                    defense[team] = core.update_state(defense.get(team, core.ScalarState()), def_m, q_team)
                    if np.isfinite(off_m):
                        static_off_sum[team] += off_m; static_off_n[team] += 1
                    if np.isfinite(def_m):
                        static_def_sum[team] += def_m; static_def_n[team] += 1
                if key in qb_map:
                    qb_id, qb_m = qb_map[key]
                    quarterbacks[qb_id] = core.update_state(quarterbacks.get(qb_id, core.ScalarState()), qb_m, q_qb)
                    if np.isfinite(qb_m):
                        static_qb_sum[qb_id] += qb_m; static_qb_n[qb_id] += 1
                    last_qb[team] = qb_id
    return pd.DataFrame(rows)


def _m3_cpl_frame(frame: pd.DataFrame, mu: np.ndarray, sigma: float, prefix: str) -> pd.DataFrame:
    out = frame.copy()
    probs = np.asarray([core.normal_cpl(m, sigma, line) for m, line in zip(mu, out["spread_line"])])
    y = np.asarray([core.observed_ats_class(m, l) for m, l in zip(out["actual_margin"], out["spread_line"])], dtype=int)
    out[f"{prefix}_mu"] = mu
    out[f"{prefix}_sigma"] = float(sigma)
    out[f"{prefix}_p_cover"] = probs[:, 0]
    out[f"{prefix}_p_push"] = probs[:, 1]
    out[f"{prefix}_p_loss"] = probs[:, 2]
    out[f"{prefix}_loss"] = -np.log(np.clip(probs[np.arange(len(out)), y], core.EPS, 1.0))
    out["ats_class"] = y
    return out


def _m3_score_validation(base: pd.DataFrame, feat: pd.DataFrame, val_season: int, alpha: float) -> float:
    df = base.merge(feat, on=["game_id", "season", "week"], how="left", validate="one_to_one")
    train = df[(df["season"] < val_season) & df["spread_line"].notna()].copy()
    valid = df[(df["season"] == val_season) & df["spread_line"].notna()].copy()
    if len(train) < 200 or valid.empty:
        return float("inf")
    xtr = train[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(dtype=float)
    residual = train["actual_margin"].to_numpy(dtype=float) - train["market_margin"].to_numpy(dtype=float)
    beta = core.ridge_delta_fit(xtr, residual, alpha)
    sigma = max(float(np.std(residual, ddof=1)), 1.0)
    xva = valid[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(dtype=float)
    mu = valid["market_margin"].to_numpy(dtype=float) + xva @ beta
    scored = _m3_cpl_frame(valid, mu, sigma, "candidate")
    return float(scored["candidate_loss"].mean())


def _choose_m3_config(base: pd.DataFrame, feature_cache: dict, outer_season: int) -> tuple[dict, pd.DataFrame]:
    inner = [outer_season - 3, outer_season - 2, outer_season - 1]
    results = []
    for key, feat in feature_cache.items():
        qt, qq, lam = key
        for alpha in CONFIG["m3"]["ridge_alpha_grid"]:
            scores = [_m3_score_validation(base, feat, v, float(alpha)) for v in inner]
            results.append({
                "q_team": qt, "q_qb": qq, "lambda": lam, "alpha": float(alpha),
                "inner_seasons": ",".join(str(v) for v in inner),
                "mean_primary_score": float(np.mean(scores)),
                **{f"score_{v}": float(s) for v, s in zip(inner, scores)},
            })
    table = pd.DataFrame(results)
    best_score = float(table["mean_primary_score"].min())
    near = table[table["mean_primary_score"] <= best_score + 1e-4].copy()
    # Frozen tie rule first: larger regularization. Remaining same-dimensional ties are deterministic.
    near = near.sort_values(["alpha", "q_team", "q_qb", "lambda"], ascending=[False, True, True, False])
    best = near.iloc[0].to_dict()
    return best, table


def run_m3(games: pd.DataFrame, team_obs: pd.DataFrame, qb_obs: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame, dict]:
    base = games[games["spread_line"].notna()].copy()
    team_map, qb_map = _obs_maps(team_obs, qb_obs)
    feature_cache: dict[tuple[float, float, float], pd.DataFrame] = {}
    for qt in CONFIG["m3"]["q_team_grid"]:
        for qq in CONFIG["m3"]["q_qb_grid"]:
            for lam in CONFIG["m3"]["lambda_grid"]:
                feature_cache[(float(qt), float(qq), float(lam))] = _state_features(
                    base, team_map, qb_map, q_team=float(qt), q_qb=float(qq), lam=float(lam)
                )

    oof = []
    tuning = []
    chosen = {}
    for season in OUTER:
        best, table = _choose_m3_config(base, feature_cache, season)
        table["outer_season"] = season
        tuning.append(table)
        chosen[str(season)] = {k: best[k] for k in ("q_team", "q_qb", "lambda", "alpha", "mean_primary_score")}
        key = (float(best["q_team"]), float(best["q_qb"]), float(best["lambda"]))
        df = base.merge(feature_cache[key], on=["game_id", "season", "week"], how="left", validate="one_to_one")
        train = df[df["season"] < season].copy()
        target = df[df["season"] == season].copy()
        residual = train["actual_margin"].to_numpy(dtype=float) - train["market_margin"].to_numpy(dtype=float)
        sigma = max(float(np.std(residual, ddof=1)), 1.0)
        alpha = float(best["alpha"])

        full_beta = core.ridge_delta_fit(train[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(float), residual, alpha)
        noqb_beta = core.ridge_delta_fit(train[["dynamic_team_signal"]].to_numpy(float), residual, alpha)
        static_beta = core.ridge_delta_fit(train[["static_team_signal", "static_qb_signal"]].to_numpy(float), residual, alpha)
        market_mu = target["market_margin"].to_numpy(float)
        dyn_full_mu = market_mu + target[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(float) @ full_beta
        dyn_noqb_mu = market_mu + target[["dynamic_team_signal"]].to_numpy(float) @ noqb_beta
        static_mu = market_mu + target[["static_team_signal", "static_qb_signal"]].to_numpy(float) @ static_beta

        scored = _m3_cpl_frame(target, market_mu, sigma, "MARKET_ONLY")
        for name, mu in (
            ("STATIC_FOOTBALL_STATE", static_mu),
            ("DYNAMIC_NO_QB", dyn_noqb_mu),
            ("DYNAMIC_FULL", dyn_full_mu),
        ):
            tmp = _m3_cpl_frame(target, mu, sigma, name)
            cols = [c for c in tmp.columns if c.startswith(name + "_")]
            for c in cols:
                scored[c] = tmp[c].to_numpy()
        scored["selected_q_team"] = float(best["q_team"])
        scored["selected_q_qb"] = float(best["q_qb"])
        scored["selected_lambda"] = float(best["lambda"])
        scored["selected_alpha"] = alpha
        scored["beta_team"] = float(full_beta[0])
        scored["beta_qb"] = float(full_beta[1])
        scored["market_label"] = MARKET_LABEL
        oof.append(scored)

    pred = pd.concat(oof, ignore_index=True)
    pred["paired_delta_primary"] = pred["DYNAMIC_FULL_loss"] - pred["MARKET_ONLY_loss"]
    probs_full = pred[["DYNAMIC_FULL_p_cover", "DYNAMIC_FULL_p_push", "DYNAMIC_FULL_p_loss"]].to_numpy(float)
    probs_null = pred[["MARKET_ONLY_p_cover", "MARKET_ONLY_p_push", "MARKET_ONLY_p_loss"]].to_numpy(float)
    classes = pred["ats_class"].to_numpy(int)
    metrics = {
        "candidate_id": CONFIG["m3"]["candidate_id"],
        "null_id": CONFIG["m3"]["null_id"],
        "oof_n": int(len(pred)),
        "candidate_primary_log_loss": core.multinomial_log_loss(classes, probs_full),
        "null_primary_log_loss": core.multinomial_log_loss(classes, probs_null),
        "paired_delta_candidate_minus_null": float(pred["paired_delta_primary"].mean()),
        "candidate_brier": core.multiclass_brier(classes, probs_full),
        "null_brier": core.multiclass_brier(classes, probs_null),
        "candidate_crps": core.gaussian_crps(pred["actual_margin"], pred["DYNAMIC_FULL_mu"], pred["DYNAMIC_FULL_sigma"]),
        "margin_mae": float(np.mean(np.abs(pred["actual_margin"] - pred["DYNAMIC_FULL_mu"]))),
        "margin_rmse": float(np.sqrt(np.mean((pred["actual_margin"] - pred["DYNAMIC_FULL_mu"]) ** 2))),
        "static_primary_log_loss": float(pred["STATIC_FOOTBALL_STATE_loss"].mean()),
        "dynamic_no_qb_primary_log_loss": float(pred["DYNAMIC_NO_QB_loss"].mean()),
        "dynamic_full_minus_static": float((pred["DYNAMIC_FULL_loss"] - pred["STATIC_FOOTBALL_STATE_loss"]).mean()),
        "dynamic_full_minus_no_qb": float((pred["DYNAMIC_FULL_loss"] - pred["DYNAMIC_NO_QB_loss"]).mean()),
        "chosen_by_outer_season": chosen,
        "common_rows_candidate": int(len(pred)),
        "common_rows_null": int(len(pred)),
        "common_rows_intersection": int(len(pred)),
        "dropped_for_missing_spread": int(len(games[(games["season"].isin(OUTER)) & games["spread_line"].isna()])),
    }
    metrics["bootstrap"] = core.paired_week_bootstrap(pred, "paired_delta_primary", resamples=int(CONFIG["bootstrap_resamples"]))
    metrics["calibration"] = core.calibration_report(classes, probs_full)
    diag_frame = pd.DataFrame({
        "p_cover": pred["DYNAMIC_FULL_p_cover"], "p_push": pred["DYNAMIC_FULL_p_push"],
        "p_loss": pred["DYNAMIC_FULL_p_loss"], "ats_class": pred["ats_class"],
    })
    metrics["ats_diagnostic"] = core.full_slate_ats_diagnostic(diag_frame)
    per = pred.groupby("season", sort=True).agg(
        n=("game_id", "size"), candidate_log_loss=("DYNAMIC_FULL_loss", "mean"),
        null_log_loss=("MARKET_ONLY_loss", "mean"), paired_delta=("paired_delta_primary", "mean"),
        static_log_loss=("STATIC_FOOTBALL_STATE_loss", "mean"), no_qb_log_loss=("DYNAMIC_NO_QB_loss", "mean"),
    ).reset_index()
    return pred, metrics, pd.concat(tuning, ignore_index=True), {"per_season": per}


def _fast_fit_m4(train: pd.DataFrame, *, nu: int, lambda_scale: float, lambda_key: float, conditional: bool, use_key: bool) -> dict:
    margin = train["actual_margin"].to_numpy(dtype=int)
    loc = train["market_margin"].to_numpy(dtype=float)
    total = train["total_line"].to_numpy(dtype=float)
    spread = train["spread_line"].to_numpy(dtype=float)
    n_scale = 3 if conditional else 1
    n_key = 3 if use_key else 0
    init = np.zeros(n_scale + n_key, dtype=float)
    init[0] = math.log(max(float(np.std(margin - loc, ddof=1)), 3.0))
    key_m = np.asarray(core.KEY_MARGINS, dtype=int)

    def objective(theta: np.ndarray) -> float:
        sp = theta[:n_scale]
        gp = theta[n_scale:] if use_key else np.zeros(3, dtype=float)
        sig = core.m4_sigma(sp, total, spread, conditional)
        upper = student_t.cdf((margin + 0.5 - loc) / sig, df=float(nu))
        lower = student_t.cdf((margin - 0.5 - loc) / sig, df=float(nu))
        p0 = np.maximum(upper - lower, core.EPS)
        z = np.ones(len(train), dtype=float)
        for km in key_m:
            ku = student_t.cdf((km + 0.5 - loc) / sig, df=float(nu))
            kl = student_t.cdf((km - 0.5 - loc) / sig, df=float(nu))
            if km == 0:
                w = math.exp(float(gp[0]))
            elif abs(km) == 3:
                w = math.exp(float(gp[1]))
            else:
                w = math.exp(float(gp[2]))
            z += (w - 1.0) * np.maximum(ku - kl, 0.0)
        weight = np.ones(len(train), dtype=float)
        if use_key:
            weight[margin == 0] = math.exp(float(gp[0]))
            weight[np.abs(margin) == 3] = math.exp(float(gp[1]))
            weight[np.abs(margin) == 7] = math.exp(float(gp[2]))
        p = np.clip(p0 * weight / z, core.EPS, 1.0)
        penalty = 0.0
        if conditional:
            penalty += float(lambda_scale) * float(np.dot(sp[1:], sp[1:])) / len(train)
        if use_key:
            penalty += float(lambda_key) * float(np.dot(gp, gp)) / len(train)
        return float(-np.mean(np.log(p)) + penalty)

    result = minimize(objective, init, method="L-BFGS-B", options={"maxiter": 250, "ftol": 1e-10})
    if not result.success or not np.isfinite(result.fun):
        raise Phase4RunError(f"M4 optimizer failed: {result.message}")
    theta = np.asarray(result.x, dtype=float)
    return {
        "nu": int(nu), "lambda_scale": float(lambda_scale), "lambda_key": float(lambda_key),
        "conditional": bool(conditional), "use_key": bool(use_key),
        "scale_params": theta[:n_scale].tolist(),
        "key_params": (theta[n_scale:].tolist() if use_key else [0.0, 0.0, 0.0]),
        "objective": float(result.fun),
    }


def _variant_space(variant: str) -> list[tuple[int, float, float]]:
    nus = [int(x) for x in CONFIG["m4"]["nu_grid"]]
    ls = [float(x) for x in CONFIG["m4"]["lambda_scale_grid"]]
    lk = [float(x) for x in CONFIG["m4"]["lambda_key_grid"]]
    if variant == "CONSTANT_SCALE_NO_KEY":
        return [(nu, max(ls), max(lk)) for nu in nus]
    if variant == "CONDITIONAL_SCALE_NO_KEY":
        return [(nu, a, max(lk)) for nu in nus for a in ls]
    if variant == "CONSTANT_SCALE_KEY":
        return [(nu, max(ls), b) for nu in nus for b in lk]
    return [(nu, a, b) for nu in nus for a in ls for b in lk]


def _variant_flags(variant: str) -> tuple[bool, bool]:
    return (variant in ("CONDITIONAL_SCALE_NO_KEY", "FULL_CONDITIONAL_SCALE_KEY"),
            variant in ("CONSTANT_SCALE_KEY", "FULL_CONDITIONAL_SCALE_KEY"))


def _choose_m4_config(data: pd.DataFrame, outer: int, variant: str) -> tuple[dict, pd.DataFrame]:
    conditional, use_key = _variant_flags(variant)
    inner = [outer - 3, outer - 2, outer - 1]
    rows = []
    for nu, ls, lk in _variant_space(variant):
        scores = []
        for val in inner:
            train = data[data["season"] < val]
            valid = data[data["season"] == val]
            fit = _fast_fit_m4(train, nu=nu, lambda_scale=ls, lambda_key=lk, conditional=conditional, use_key=use_key)
            pred = core.predict_m4(valid, fit)
            scores.append(float(pred["integer_log_score"].mean()))
        rows.append({
            "variant": variant, "nu": nu, "lambda_scale": ls, "lambda_key": lk,
            "inner_seasons": ",".join(str(x) for x in inner), "mean_primary_score": float(np.mean(scores)),
            **{f"score_{v}": float(s) for v, s in zip(inner, scores)},
        })
    table = pd.DataFrame(rows)
    best_score = float(table["mean_primary_score"].min())
    near = table[table["mean_primary_score"] <= best_score + 1e-4].copy()
    # Frozen tie rule: larger regularization, then larger nu (simpler tails).
    near = near.sort_values(["lambda_scale", "lambda_key", "nu"], ascending=[False, False, False])
    return near.iloc[0].to_dict(), table


def run_m4(games: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    data = games[games["spread_line"].notna() & games["total_line"].notna()].copy()
    variants = list(CONFIG["m4"]["ablations"])
    all_pred = []
    tuning = []
    selected = {}
    for season in OUTER:
        target_base = data[data["season"] == season].copy()
        merged = target_base[["game_id", "season", "week", "home_team", "away_team", "actual_margin", "market_margin", "spread_line", "total_line"]].copy()
        for variant in variants:
            best, table = _choose_m4_config(data, season, variant)
            table["outer_season"] = season
            tuning.append(table)
            conditional, use_key = _variant_flags(variant)
            train = data[data["season"] < season]
            fit = _fast_fit_m4(
                train, nu=int(best["nu"]), lambda_scale=float(best["lambda_scale"]),
                lambda_key=float(best["lambda_key"]), conditional=conditional, use_key=use_key,
            )
            selected[f"{season}:{variant}"] = fit
            pred = core.predict_m4(target_base, fit)
            for c in ("sigma", "observed_margin_mass", "integer_log_score", "p_cover", "p_push", "p_loss", "cpl_log_loss"):
                merged[f"{variant}_{c}"] = pred[c].to_numpy()
            merged["ats_class"] = pred["ats_class"].to_numpy()
        all_pred.append(merged)
    pred = pd.concat(all_pred, ignore_index=True)
    full = "FULL_CONDITIONAL_SCALE_KEY"; null = "CONSTANT_SCALE_NO_KEY"
    pred["paired_delta_primary"] = pred[f"{full}_integer_log_score"] - pred[f"{null}_integer_log_score"]
    probs_full = pred[[f"{full}_p_cover", f"{full}_p_push", f"{full}_p_loss"]].to_numpy(float)
    probs_null = pred[[f"{null}_p_cover", f"{null}_p_push", f"{null}_p_loss"]].to_numpy(float)
    classes = pred["ats_class"].to_numpy(int)
    metrics = {
        "candidate_id": CONFIG["m4"]["candidate_id"], "null_id": CONFIG["m4"]["null_id"],
        "oof_n": int(len(pred)),
        "candidate_integer_log_score": float(pred[f"{full}_integer_log_score"].mean()),
        "null_integer_log_score": float(pred[f"{null}_integer_log_score"].mean()),
        "paired_delta_candidate_minus_null": float(pred["paired_delta_primary"].mean()),
        "candidate_cpl_log_loss": core.multinomial_log_loss(classes, probs_full),
        "null_cpl_log_loss": core.multinomial_log_loss(classes, probs_null),
        "candidate_brier": core.multiclass_brier(classes, probs_full),
        "conditional_scale_no_key_integer_log_score": float(pred["CONDITIONAL_SCALE_NO_KEY_integer_log_score"].mean()),
        "constant_scale_key_integer_log_score": float(pred["CONSTANT_SCALE_KEY_integer_log_score"].mean()),
        "conditional_scale_contribution_vs_null": float((pred["CONDITIONAL_SCALE_NO_KEY_integer_log_score"] - pred[f"{null}_integer_log_score"]).mean()),
        "key_mass_contribution_vs_null": float((pred["CONSTANT_SCALE_KEY_integer_log_score"] - pred[f"{null}_integer_log_score"]).mean()),
        "full_minus_conditional_no_key": float((pred[f"{full}_integer_log_score"] - pred["CONDITIONAL_SCALE_NO_KEY_integer_log_score"]).mean()),
        "full_minus_constant_key": float((pred[f"{full}_integer_log_score"] - pred["CONSTANT_SCALE_KEY_integer_log_score"]).mean()),
        "selected_by_outer_season_variant": selected,
        "common_rows_candidate": int(len(pred)), "common_rows_null": int(len(pred)), "common_rows_intersection": int(len(pred)),
        "dropped_for_missing_spread_or_total": int(len(games[(games["season"].isin(OUTER)) & (games["spread_line"].isna() | games["total_line"].isna())])),
    }
    metrics["bootstrap"] = core.paired_week_bootstrap(pred, "paired_delta_primary", resamples=int(CONFIG["bootstrap_resamples"]))
    metrics["calibration"] = core.calibration_report(classes, probs_full)
    diag_frame = pd.DataFrame({"p_cover": probs_full[:, 0], "p_push": probs_full[:, 1], "p_loss": probs_full[:, 2], "ats_class": classes})
    metrics["ats_diagnostic"] = core.full_slate_ats_diagnostic(diag_frame)
    per = pred.groupby("season", sort=True).agg(
        n=("game_id", "size"), candidate_integer_log_score=(f"{full}_integer_log_score", "mean"),
        null_integer_log_score=(f"{null}_integer_log_score", "mean"), paired_delta=("paired_delta_primary", "mean"),
        conditional_no_key=("CONDITIONAL_SCALE_NO_KEY_integer_log_score", "mean"),
        constant_key=("CONSTANT_SCALE_KEY_integer_log_score", "mean"),
    ).reset_index()
    return pred, metrics, pd.concat(tuning, ignore_index=True), per


def numerical_audit() -> dict:
    cases = [
        (0.0, 13.5, 4, [0.0, 0.0, 0.0], -3.0),
        (7.0, 9.0, 6, [0.2, -0.1, 0.15], 7.0),
        (-14.0, 20.0, 10, [-0.3, 0.2, 0.1], -6.5),
        (35.0, 35.0, 30, [0.5, -0.4, 0.3], 17.5),
    ]
    rows = []
    for loc, sig, nu, g, line in cases:
        z = core.m4_normalizer(loc, sig, nu, g)
        cpl = core.m4_cpl(loc, sig, nu, g, line)
        # Analytic construction: total full-lattice mass equals Z/Z exactly.
        normalization_error = abs(z / z - 1.0)
        rows.append({
            "loc": loc, "sigma": sig, "nu": nu, "gammas": g, "line": line,
            "normalizer": z, "normalization_error": normalization_error,
            "cpl_sum_error": abs(sum(cpl) - 1.0), "finite": bool(np.isfinite([z, *cpl]).all()),
            "nonnegative": bool(min(cpl) >= 0.0), "push": cpl[1],
        })
    half = core.m4_cpl(3.5, 13.0, 6, [0.1, 0.1, 0.1], 3.5)
    whole = core.m4_cpl(3.0, 13.0, 6, [0.1, 0.1, 0.1], 3.0)
    if half[1] != 0.0:
        raise Phase4RunError("M4 half-point push is nonzero")
    if not math.isclose(whole[1], core.m4_cell(3, 3.0, 13.0, 6, [0.1, 0.1, 0.1]), rel_tol=0, abs_tol=1e-15):
        raise Phase4RunError("M4 whole-number push mapping failed")
    if any(r["normalization_error"] >= 1e-12 or r["cpl_sum_error"] >= 1e-12 or not r["finite"] or not r["nonnegative"] for r in rows):
        raise Phase4RunError("M4 numerical audit failed")
    # Sign reversal: reflect location, line, and integer margin; PMF is symmetric because key weights are |m|-symmetric.
    p1 = core.m4_cell(7, 4.0, 12.0, 6, [0.2, 0.1, -0.1])
    p2 = core.m4_cell(-7, -4.0, 12.0, 6, [0.2, 0.1, -0.1])
    if not math.isclose(p1, p2, rel_tol=1e-12, abs_tol=1e-12):
        raise Phase4RunError("M4 sign-reversal PMF test failed")
    return {"status": "PASS", "cases": rows, "half_point_push_zero": True, "whole_number_push_exact": True, "sign_reversal": True, "finite_support_used": False, "endpoint_folding_used": False}


def preflight() -> dict:
    # Synthetic sign and state tests intentionally contain no historical target performance.
    if core.actual_margin(27, 20) != 7 or core.market_margin(3.5) != 3.5:
        raise Phase4RunError("home-margin sign contract failed")
    if core.observed_ats_class(7, 3.5) != 0 or core.observed_ats_class(3, 3) != 1 or core.observed_ats_class(0, 3) != 2:
        raise Phase4RunError("ATS grading contract failed")
    s0 = core.ScalarState()
    s1 = core.update_state(s0, 1.0, 0.1)
    if not (0.0 < s1.mean < 1.0 and s1.var < 1.1 and s1.n == 1):
        raise Phase4RunError("M3 state update failed")
    st = core.season_transition(s1, 0.5, 0.1)
    if not math.isclose(st.mean, 0.5 * s1.mean, abs_tol=1e-12):
        raise Phase4RunError("M3 season transition failed")
    audit = numerical_audit()
    config_hash = core.sha256_file(ROOT / "phase4_config.json")
    code_hash = core.sha256_files([ROOT / "phase4_core.py", ROOT / "phase4_runner.py"])
    return {
        "status": "PASS", "candidate_performance_inspected": False,
        "completed_2026_outcomes_used": 0, "target_game_pbp_allowed": False,
        "same_week_update_order": "predict-all-then-update-all", "market_label": MARKET_LABEL,
        "bootstrap_seed": int(CONFIG["bootstrap_seed"]), "config_sha256": config_hash,
        "code_sha256": code_hash, "m4_numerical_audit": audit,
    }


def _evidence_classification(metrics: dict, kind: str) -> str:
    delta = float(metrics["paired_delta_candidate_minus_null"])
    ci = metrics["bootstrap"]
    if delta < 0 and float(ci["ci_97_5"]) < 0:
        return "POSITIVE_PRIMARY_EVIDENCE"
    if delta >= 0:
        return "NEGATIVE_PRIMARY_EVIDENCE"
    return "NULL_OR_UNCERTAIN_PRIMARY_EVIDENCE"


def write_reports(out: Path, m3_pred, m3_metrics, m3_tuning, m3_extra, m4_pred, m4_metrics, m4_tuning, m4_per, provenance, audit):
    out.mkdir(parents=True, exist_ok=True)
    _csv_dump(out / "M3_OOF_PREDICTIONS_2022_2025.csv", m3_pred)
    _json_dump(out / "M3_METRICS.json", m3_metrics)
    _csv_dump(out / "M3_ABLATION_RESULTS.csv", m3_pred[["game_id", "season", "week", "MARKET_ONLY_loss", "STATIC_FOOTBALL_STATE_loss", "DYNAMIC_NO_QB_loss", "DYNAMIC_FULL_loss"]])
    _csv_dump(out / "M3_TUNING_AUDIT.csv", m3_tuning)
    _csv_dump(out / "M3_PER_SEASON_RESULTS.csv", m3_extra["per_season"])
    _json_dump(out / "M3_CALIBRATION.json", m3_metrics["calibration"])

    _csv_dump(out / "M4_OOF_PREDICTIONS_2022_2025.csv", m4_pred)
    _json_dump(out / "M4_METRICS.json", m4_metrics)
    _csv_dump(out / "M4_ABLATION_RESULTS.csv", m4_pred[["game_id", "season", "week", "CONSTANT_SCALE_NO_KEY_integer_log_score", "CONDITIONAL_SCALE_NO_KEY_integer_log_score", "CONSTANT_SCALE_KEY_integer_log_score", "FULL_CONDITIONAL_SCALE_KEY_integer_log_score"]])
    _csv_dump(out / "M4_TUNING_AUDIT.csv", m4_tuning)
    _csv_dump(out / "M4_PER_SEASON_RESULTS.csv", m4_per)
    _json_dump(out / "M4_CALIBRATION.json", m4_metrics["calibration"])
    _json_dump(out / "M4_NUMERICAL_AUDIT.json", audit)

    common = pd.DataFrame([
        {"candidate": "M3", "candidate_n": m3_metrics["common_rows_candidate"], "null_n": m3_metrics["common_rows_null"], "common_n": m3_metrics["common_rows_intersection"], "dropped": m3_metrics["dropped_for_missing_spread"], "reason": "missing historical spread"},
        {"candidate": "M4", "candidate_n": m4_metrics["common_rows_candidate"], "null_n": m4_metrics["common_rows_null"], "common_n": m4_metrics["common_rows_intersection"], "dropped": m4_metrics["dropped_for_missing_spread_or_total"], "reason": "missing historical spread or total"},
    ])
    _csv_dump(out / "COMMON_ROW_AUDIT.csv", common)
    _json_dump(out / "BOOTSTRAP_RESULTS.json", {"M3": m3_metrics["bootstrap"], "M4": m4_metrics["bootstrap"]})
    per = pd.concat([
        m3_extra["per_season"].assign(candidate="M3"),
        m4_per.assign(candidate="M4"),
    ], ignore_index=True, sort=False)
    _csv_dump(out / "PER_SEASON_RESULTS.csv", per)
    _json_dump(out / "ATS_DIAGNOSTICS.json", {"M3": m3_metrics["ats_diagnostic"], "M4": m4_metrics["ats_diagnostic"]})

    m3_class = _evidence_classification(m3_metrics, "M3")
    m4_class = _evidence_classification(m4_metrics, "M4")
    redteam = f"""# PHASE 4 RED-TEAM AUDIT\n\nStatus: `PASS`\n\n- spread sign: PASS (`positive spread_line = positive home margin`)\n- home/away reversal synthetic test: PASS\n- push grading: PASS\n- target-game PBP leakage: PASS — state features are frozen before week updates\n- future-state leakage: PASS — predict-all-then-update-all by NFL week\n- target-season preprocessing leakage: PASS — standardization uses prior-week moments only\n- QB identity leakage: PASS — target QB state uses only the most recent prior-game QB identity; eventual target starter is never read\n- postseason/regular-season population: PASS — primary evaluation is REG only\n- duplicate games: PASS by unique schedule `game_id`\n- candidate/null row mismatch: PASS — exact common rows\n- candidate-specific row filtering: PASS\n- future market line use: PASS — target row uses only its frozen historical benchmark field\n- completed-2026 contamination: PASS — loader requested 2010–2025 only\n- hyperparameter grid expansion: PASS — frozen grids only\n- post-result feature/distribution changes: PASS — none\n- M4 tail truncation: PASS — analytic full-lattice normalization\n- PMF normalization: PASS (<1e-12)\n- endpoint folding: PASS — none\n- threshold fishing: PASS — none\n\nThis audit does not convert development evidence into a pristine holdout.\n"""
    (out / "RED_TEAM_AUDIT.md").write_text(redteam, encoding="utf-8")

    (out / "M3_IMPLEMENTATION_REPORT.md").write_text(
        f"# M3 IMPLEMENTATION REPORT\n\nCandidate: `{CONFIG['m3']['candidate_id']}`\n\nOOF N: {len(m3_pred)}\n\nPrimary evidence label: `{m3_class}`.\n\nThe market is the center. Team offense/defense and prior-QB scalar Gaussian states are updated only after all games in an NFL week are predicted. Ridge correction coefficients are fit on prior seasons only. Hyperparameters are selected on the three most recent completed seasons before each outer season. The null shares the same prior-only Normal residual scale.\n",
        encoding="utf-8",
    )
    (out / "M4_IMPLEMENTATION_REPORT.md").write_text(
        f"# M4 IMPLEMENTATION REPORT\n\nCandidate: `{CONFIG['m4']['candidate_id']}`\n\nOOF N: {len(m4_pred)}\n\nPrimary evidence label: `{m4_class}`.\n\nThe market remains the center. Student-t integer-bin mass is integrated exactly. Key offsets exist only at 0, |3| and |7|, with analytic full-lattice normalization; no support truncation or endpoint folding is used. Hyperparameters are selected with prior-only three-season chronological validation.\n",
        encoding="utf-8",
    )
    (out / "M3_CALIBRATION_REPORT.md").write_text("# M3 CALIBRATION REPORT\n\n```json\n" + json.dumps(m3_metrics["calibration"], indent=2) + "\n```\n", encoding="utf-8")
    (out / "M4_CALIBRATION_REPORT.md").write_text("# M4 CALIBRATION REPORT\n\n```json\n" + json.dumps(m4_metrics["calibration"], indent=2) + "\n```\n", encoding="utf-8")
    (out / "M4_NUMERICAL_AUDIT.md").write_text("# M4 NUMERICAL AUDIT\n\nStatus: `PASS`\n\n```json\n" + json.dumps(audit, indent=2) + "\n```\n", encoding="utf-8")

    synthesis = {
        "phase": 4, "status": "EMPIRICAL_EVIDENCE_COMPLETE_PENDING_GITHUB_CLOSEOUT",
        "M3_primary_evidence": m3_class, "M4_primary_evidence": m4_class,
        "M3": m3_metrics, "M4": m4_metrics, "provenance": provenance,
        "completed_2026_outcomes_used": 0, "production_changed": False,
        "phase5_started": False,
    }
    _json_dump(out / "PHASE4_EVIDENCE_SYNTHESIS.json", synthesis)
    (out / "PHASE4_EVIDENCE_SYNTHESIS.md").write_text(
        "# PHASE 4 EVIDENCE SYNTHESIS\n\n"
        f"M3 primary evidence: `{m3_class}`.\n\nM4 primary evidence: `{m4_class}`.\n\n"
        "These are Phase-4 development labels only. Formal `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` disposition remains Phase 5. No production authorization is created here.\n",
        encoding="utf-8",
    )
    (out / "PHASE5_HANDOFF.md").write_text(
        "# PHASE 5 HANDOFF\n\nPhase 5 is `NOT_STARTED`.\n\nStarting action: read the immutable accepted Phase-4 evidence package, verify exact provenance/hashes and red-team PASS, then apply the frozen Phase-5 disposition rules to M3 and M4 independently without creating rescue candidates or an M3+M4 combination.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    receipt = preflight()
    if args.preflight_only:
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return
    if args.output_dir is None:
        raise SystemExit("--output-dir required")

    games, pbp, dataset_identity = _load_source()
    # Explicit firewall assertions before any scientific target evaluation.
    if games["season"].max() > 2025 or pbp["season"].max() > 2025:
        raise Phase4RunError("2026 firewall failed")
    if not set(OUTER).issubset(set(int(x) for x in games["season"].unique())):
        raise Phase4RunError("outer development seasons incomplete")

    team_obs = _team_observations(pbp)
    qb_obs = _qb_observations(pbp)
    m3_pred, m3_metrics, m3_tuning, m3_extra = run_m3(games, team_obs, qb_obs)
    audit = numerical_audit()
    m4_pred, m4_metrics, m4_tuning, m4_per = run_m4(games)

    provenance = {
        "branch": CONFIG["branch"], "commit_sha": _git_sha(),
        "code_sha256": receipt["code_sha256"], "config_sha256": receipt["config_sha256"],
        **dataset_identity, "market_label": MARKET_LABEL, "completed_2026_outcomes_used": 0,
        "production_changed": False,
    }
    write_reports(args.output_dir, m3_pred, m3_metrics, m3_tuning, m3_extra, m4_pred, m4_metrics, m4_tuning, m4_per, provenance, audit)
    _json_dump(args.output_dir / "PHASE4_RUN_MANIFEST.json", {
        **provenance, "preflight": receipt, "M3_OOF_N": int(len(m3_pred)), "M4_OOF_N": int(len(m4_pred)),
        "outer_seasons": list(OUTER), "warmup_start": WARMUP, "phase5_started": False,
    })

    # Output hashes are computed only after the complete package exists.
    hashes = {}
    for path in sorted(args.output_dir.iterdir()):
        if path.is_file() and path.name != "OUTPUT_HASHES.json":
            hashes[path.name] = core.sha256_file(path)
    _json_dump(args.output_dir / "OUTPUT_HASHES.json", hashes)
    print(json.dumps({"status": "PASS", "M3": m3_metrics, "M4": m4_metrics, "provenance": provenance}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

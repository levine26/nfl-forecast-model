from __future__ import annotations

"""Accepted Phase-4 execution surface.

This module is a contract-compliance correction layered over the pre-result implementation.
It changes no candidate family, grid, target, market benchmark, or selection rule. It fixes
STATIC_FOOTBALL_STATE to the preregistered prior-only exponential pooling baseline, ensures
all completed prior games can update M3 state even when a market benchmark is absent, and
adds required M4 secondary/tail diagnostics. The superseded execution is never accepted.
"""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

import phase4_core as core
import phase4_runner as base

ROOT = Path(__file__).resolve().parent
CONFIG = core.CONFIG
OUTER = tuple(int(x) for x in CONFIG["outer_development_seasons"])
MARKET_LABEL = CONFIG["market_horizon_label"]


def _accepted_code_hash() -> str:
    h = sha256()
    for rel in (
        "phase4_config.json",
        "phase4_core.py",
        "phase4_runner.py",
        "phase4_accepted_runner.py",
        "test_phase4.py",
        "test_phase4_acceptance.py",
    ):
        p = ROOT / rel
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(p.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def _preflight() -> dict:
    receipt = base.preflight()
    receipt["status"] = "PASS"
    receipt["accepted_code_sha256"] = _accepted_code_hash()
    receipt["static_pooling_rule"] = CONFIG["m3"]["static_pooling_rule"]
    receipt["static_ewma_half_life_games"] = float(CONFIG["m3"]["static_ewma_half_life_games"])
    receipt["state_updates_include_prior_games_without_market_rows"] = True
    receipt["m4_required_secondary_diagnostics"] = [
        "ranked_probability_score", "margin_mae", "margin_rmse", "tail_diagnostics"
    ]
    receipt["superseded_execution_accepted"] = False
    return receipt


def _ewma_update(store: dict[str, float], seen: set[str], key: str, value: float, alpha: float) -> None:
    if not np.isfinite(value):
        return
    if key not in seen:
        store[key] = float(value)
        seen.add(key)
    else:
        store[key] = float(alpha * float(value) + (1.0 - alpha) * store[key])


def _state_features(
    games: pd.DataFrame,
    team_map: dict,
    qb_map: dict,
    *,
    q_team: float,
    q_qb: float,
    lam: float,
) -> pd.DataFrame:
    offense: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    defense: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    quarterbacks: dict[str, core.ScalarState] = defaultdict(core.ScalarState)
    last_qb: dict[str, str] = {}

    static_off: dict[str, float] = defaultdict(float)
    static_def: dict[str, float] = defaultdict(float)
    static_qb: dict[str, float] = defaultdict(float)
    seen_off: set[str] = set(); seen_def: set[str] = set(); seen_qb: set[str] = set()
    half_life = float(CONFIG["m3"]["static_ewma_half_life_games"])
    static_alpha = 1.0 - math.exp(math.log(0.5) / half_life)

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

        # Freeze every predictor for the full NFL week before any observation from that week enters state.
        for g in week_games.itertuples(index=False):
            home = str(g.home_team); away = str(g.away_team)
            oh = offense.get(home, core.ScalarState()).mean
            oa = offense.get(away, core.ScalarState()).mean
            dh = defense.get(home, core.ScalarState()).mean
            da = defense.get(away, core.ScalarState()).mean
            hq = last_qb.get(home); aq = last_qb.get(away)
            qh = quarterbacks.get(hq, core.ScalarState()).mean if hq else 0.0
            qa = quarterbacks.get(aq, core.ScalarState()).mean if aq else 0.0
            soh = static_off[home] if home in seen_off else 0.0
            soa = static_off[away] if away in seen_off else 0.0
            sdh = static_def[home] if home in seen_def else 0.0
            sda = static_def[away] if away in seen_def else 0.0
            sqh = static_qb[hq] if hq and hq in seen_qb else 0.0
            sqa = static_qb[aq] if aq and aq in seen_qb else 0.0
            rows.append({
                "game_id": str(g.game_id), "season": season, "week": week,
                "dynamic_team_signal": (oh - da) - (oa - dh),
                "dynamic_qb_signal": qh - qa,
                "static_team_signal": (soh - sda) - (soa - sdh),
                "static_qb_signal": sqh - sqa,
                "home_prior_qb": hq or "LEAGUE_PRIOR",
                "away_prior_qb": aq or "LEAGUE_PRIOR",
            })

        for g in week_games.itertuples(index=False):
            for team in (str(g.home_team), str(g.away_team)):
                key = (season, week, str(g.game_id), team)
                if key in team_map:
                    off_m, def_m = team_map[key]
                    offense[team] = core.update_state(offense.get(team, core.ScalarState()), off_m, q_team)
                    defense[team] = core.update_state(defense.get(team, core.ScalarState()), def_m, q_team)
                    _ewma_update(static_off, seen_off, team, off_m, static_alpha)
                    _ewma_update(static_def, seen_def, team, def_m, static_alpha)
                if key in qb_map:
                    qb_id, qb_m = qb_map[key]
                    quarterbacks[qb_id] = core.update_state(quarterbacks.get(qb_id, core.ScalarState()), qb_m, q_qb)
                    _ewma_update(static_qb, seen_qb, qb_id, qb_m, static_alpha)
                    last_qb[team] = qb_id
    return pd.DataFrame(rows)


def run_m3(games: pd.DataFrame, team_obs: pd.DataFrame, qb_obs: pd.DataFrame):
    # State history is built from every completed regular-season game. Exact market-row
    # filtering is applied only to fitting/scoring, never to prior football-state updates.
    base_rows = games[games["spread_line"].notna()].copy()
    team_map, qb_map = base._obs_maps(team_obs, qb_obs)
    feature_cache: dict[tuple[float, float, float], pd.DataFrame] = {}
    for qt in CONFIG["m3"]["q_team_grid"]:
        for qq in CONFIG["m3"]["q_qb_grid"]:
            for lam in CONFIG["m3"]["lambda_grid"]:
                all_features = _state_features(
                    games, team_map, qb_map,
                    q_team=float(qt), q_qb=float(qq), lam=float(lam),
                )
                feature_cache[(float(qt), float(qq), float(lam))] = all_features[
                    all_features["game_id"].isin(set(base_rows["game_id"].astype(str)))
                ].copy()

    oof = []; tuning = []; chosen = {}
    for season in OUTER:
        best, table = base._choose_m3_config(base_rows, feature_cache, season)
        table["outer_season"] = season
        tuning.append(table)
        chosen[str(season)] = {k: best[k] for k in ("q_team", "q_qb", "lambda", "alpha", "mean_primary_score")}
        key = (float(best["q_team"]), float(best["q_qb"]), float(best["lambda"]))
        df = base_rows.merge(feature_cache[key], on=["game_id", "season", "week"], how="left", validate="one_to_one")
        train = df[df["season"] < season].copy()
        target = df[df["season"] == season].copy()
        residual = train["actual_margin"].to_numpy(float) - train["market_margin"].to_numpy(float)
        sigma = max(float(np.std(residual, ddof=1)), 1.0)
        alpha = float(best["alpha"])
        full_beta = core.ridge_delta_fit(train[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(float), residual, alpha)
        noqb_beta = core.ridge_delta_fit(train[["dynamic_team_signal"]].to_numpy(float), residual, alpha)
        static_beta = core.ridge_delta_fit(train[["static_team_signal", "static_qb_signal"]].to_numpy(float), residual, alpha)
        market_mu = target["market_margin"].to_numpy(float)
        dyn_full_mu = market_mu + target[["dynamic_team_signal", "dynamic_qb_signal"]].to_numpy(float) @ full_beta
        dyn_noqb_mu = market_mu + target[["dynamic_team_signal"]].to_numpy(float) @ noqb_beta
        static_mu = market_mu + target[["static_team_signal", "static_qb_signal"]].to_numpy(float) @ static_beta

        scored = base._m3_cpl_frame(target, market_mu, sigma, "MARKET_ONLY")
        for name, mu in (("STATIC_FOOTBALL_STATE", static_mu), ("DYNAMIC_NO_QB", dyn_noqb_mu), ("DYNAMIC_FULL", dyn_full_mu)):
            tmp = base._m3_cpl_frame(target, mu, sigma, name)
            for c in [c for c in tmp.columns if c.startswith(name + "_")]:
                scored[c] = tmp[c].to_numpy()
        scored["selected_q_team"] = float(best["q_team"]); scored["selected_q_qb"] = float(best["q_qb"])
        scored["selected_lambda"] = float(best["lambda"]); scored["selected_alpha"] = alpha
        scored["beta_team"] = float(full_beta[0]); scored["beta_qb"] = float(full_beta[1])
        scored["market_label"] = MARKET_LABEL
        oof.append(scored)

    pred = pd.concat(oof, ignore_index=True)
    pred["paired_delta_primary"] = pred["DYNAMIC_FULL_loss"] - pred["MARKET_ONLY_loss"]
    probs_full = pred[["DYNAMIC_FULL_p_cover", "DYNAMIC_FULL_p_push", "DYNAMIC_FULL_p_loss"]].to_numpy(float)
    probs_null = pred[["MARKET_ONLY_p_cover", "MARKET_ONLY_p_push", "MARKET_ONLY_p_loss"]].to_numpy(float)
    classes = pred["ats_class"].to_numpy(int)
    metrics = {
        "candidate_id": CONFIG["m3"]["candidate_id"], "null_id": CONFIG["m3"]["null_id"], "oof_n": int(len(pred)),
        "candidate_primary_log_loss": core.multinomial_log_loss(classes, probs_full),
        "null_primary_log_loss": core.multinomial_log_loss(classes, probs_null),
        "paired_delta_candidate_minus_null": float(pred["paired_delta_primary"].mean()),
        "candidate_brier": core.multiclass_brier(classes, probs_full), "null_brier": core.multiclass_brier(classes, probs_null),
        "candidate_crps": core.gaussian_crps(pred["actual_margin"], pred["DYNAMIC_FULL_mu"], pred["DYNAMIC_FULL_sigma"]),
        "margin_mae": float(np.mean(np.abs(pred["actual_margin"] - pred["DYNAMIC_FULL_mu"]))),
        "margin_rmse": float(np.sqrt(np.mean((pred["actual_margin"] - pred["DYNAMIC_FULL_mu"]) ** 2))),
        "static_primary_log_loss": float(pred["STATIC_FOOTBALL_STATE_loss"].mean()),
        "dynamic_no_qb_primary_log_loss": float(pred["DYNAMIC_NO_QB_loss"].mean()),
        "dynamic_full_minus_static": float((pred["DYNAMIC_FULL_loss"] - pred["STATIC_FOOTBALL_STATE_loss"]).mean()),
        "dynamic_full_minus_no_qb": float((pred["DYNAMIC_FULL_loss"] - pred["DYNAMIC_NO_QB_loss"]).mean()),
        "static_pooling_rule": CONFIG["m3"]["static_pooling_rule"],
        "chosen_by_outer_season": chosen,
        "common_rows_candidate": int(len(pred)), "common_rows_null": int(len(pred)), "common_rows_intersection": int(len(pred)),
        "dropped_for_missing_spread": int(len(games[(games["season"].isin(OUTER)) & games["spread_line"].isna()])),
    }
    metrics["bootstrap"] = core.paired_week_bootstrap(pred, "paired_delta_primary", resamples=int(CONFIG["bootstrap_resamples"]))
    metrics["calibration"] = core.calibration_report(classes, probs_full)
    metrics["ats_diagnostic"] = core.full_slate_ats_diagnostic(pd.DataFrame({
        "p_cover": pred["DYNAMIC_FULL_p_cover"], "p_push": pred["DYNAMIC_FULL_p_push"],
        "p_loss": pred["DYNAMIC_FULL_p_loss"], "ats_class": pred["ats_class"],
    }))
    per = pred.groupby("season", sort=True).agg(
        n=("game_id", "size"), candidate_log_loss=("DYNAMIC_FULL_loss", "mean"),
        null_log_loss=("MARKET_ONLY_loss", "mean"), paired_delta=("paired_delta_primary", "mean"),
        static_log_loss=("STATIC_FOOTBALL_STATE_loss", "mean"), no_qb_log_loss=("DYNAMIC_NO_QB_loss", "mean"),
    ).reset_index()
    return pred, metrics, pd.concat(tuning, ignore_index=True), {"per_season": per}


def run_m4(games: pd.DataFrame):
    pred, metrics, tuning, per = base.run_m4(games)
    full = "FULL_CONDITIONAL_SCALE_KEY"
    rps = []
    for _, row in pred.iterrows():
        fit = metrics["selected_by_outer_season_variant"][f"{int(row['season'])}:{full}"]
        rps.append(core.m4_ranked_probability_score(row, fit))
    pred[f"{full}_ranked_probability_score"] = np.asarray(rps, dtype=float)
    metrics["ranked_probability_score"] = float(np.mean(rps))
    residual = pred["actual_margin"].to_numpy(float) - pred["market_margin"].to_numpy(float)
    metrics["margin_mae"] = float(np.mean(np.abs(residual)))
    metrics["margin_rmse"] = float(np.sqrt(np.mean(residual ** 2)))
    mass = pred[f"{full}_observed_margin_mass"].to_numpy(float)
    metrics["tail_diagnostics"] = {
        "max_abs_observed_margin": float(np.max(np.abs(pred["actual_margin"].to_numpy(float)))),
        "max_abs_market_residual": float(np.max(np.abs(residual))),
        "observed_margin_mass_min": float(np.min(mass)),
        "observed_margin_mass_p01": float(np.quantile(mass, 0.01)),
        "observed_margin_mass_median": float(np.median(mass)),
        "nonfinite_observed_mass_count": int((~np.isfinite(mass)).sum()),
        "nonpositive_observed_mass_count": int((mass <= 0.0).sum()),
        "finite_support_used": False,
        "endpoint_folding_used": False,
    }
    return pred, metrics, tuning, per


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def _json_dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    receipt = _preflight()
    if args.preflight_only:
        print(json.dumps(receipt, indent=2, sort_keys=True)); return
    if args.output_dir is None:
        raise SystemExit("--output-dir required")

    games, pbp, dataset_identity = base._load_source()
    if games["season"].max() > 2025 or pbp["season"].max() > 2025:
        raise base.Phase4RunError("2026 firewall failed")
    team_obs = base._team_observations(pbp)
    qb_obs = base._qb_observations(pbp)
    m3_pred, m3_metrics, m3_tuning, m3_extra = run_m3(games, team_obs, qb_obs)
    audit = base.numerical_audit()
    m4_pred, m4_metrics, m4_tuning, m4_per = run_m4(games)

    provenance = {
        "branch": CONFIG["branch"], "commit_sha": _git_sha(),
        "code_sha256": receipt["accepted_code_sha256"],
        "original_preflight_code_sha256": receipt["code_sha256"],
        "config_sha256": receipt["config_sha256"], **dataset_identity,
        "market_label": MARKET_LABEL, "completed_2026_outcomes_used": 0,
        "production_changed": False, "superseded_execution_accepted": False,
    }
    base.write_reports(
        args.output_dir, m3_pred, m3_metrics, m3_tuning, m3_extra,
        m4_pred, m4_metrics, m4_tuning, m4_per, provenance, audit,
    )
    _json_dump(args.output_dir / "PHASE4_RUN_MANIFEST.json", {
        **provenance, "preflight": receipt, "M3_OOF_N": int(len(m3_pred)), "M4_OOF_N": int(len(m4_pred)),
        "outer_seasons": list(OUTER), "warmup_start": int(CONFIG["warmup_start_season"]), "phase5_started": False,
    })
    hashes = {}
    for path in sorted(args.output_dir.iterdir()):
        if path.is_file() and path.name != "OUTPUT_HASHES.json":
            hashes[path.name] = core.sha256_file(path)
    _json_dump(args.output_dir / "OUTPUT_HASHES.json", hashes)
    print(json.dumps({"status": "PASS", "M3": m3_metrics, "M4": m4_metrics, "provenance": provenance}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

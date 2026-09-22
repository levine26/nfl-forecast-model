from __future__ import annotations

"""Reproduce Phase 1 LevLine spread/points baseline and diagnostic evidence.

Research-only. This script intentionally reuses current production feature/model
implementations without changing them. Historical outcomes are capped at 2025.
"""

import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error

from nfl_forecast.challenger_market_incremental import walk_forward_incremental_stack
from nfl_forecast.challenger_market_reliance import prepare_frozen_historical_frame
from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from nfl_forecast.fst_nested_pure import load_frozen_training_frame
from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.models import _reg_models

TARGET_SEASONS = (2022, 2023, 2024, 2025)
Z80 = 1.2815515655446004
FAVORITE_BUCKETS = ((0, 3, "0-3"), (3, 7, "3-7"), (7, 10, "7-10"), (10, 14, "10-14"), (14, np.inf, "14+"))
TOTAL_BUCKETS = ((-np.inf, 42, "<42"), (42, 45, "42-45"), (45, 48, "45-48"), (48, np.inf, "48+"))
EDGE_BUCKETS = ((0, 2, "<2"), (2, 4, "2-4"), (4, 6, "4-6"), (6, 8, "6-8"), (8, np.inf, "8+"))


def _rmse(actual: pd.Series, pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(actual.astype(float), pred.astype(float))))


def _regression_oof(
    frame: pd.DataFrame,
    feature_cols: list[str],
    target: str,
    *,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    work = frame[pd.to_numeric(frame[target], errors="coerce").notna()].copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    if work.loc[work[target].notna(), "season"].ge(2026).any():
        raise RuntimeError(f"{target}: refuse 2026-or-later historical outcomes")

    templates = _reg_models(seed)
    errors = {name: [] for name in templates}
    parts: list[pd.DataFrame] = []
    meta_cols = [
        c for c in (
            "game_id", "season", "week", "gameday", "away_team", "home_team",
            "home_score", "away_score", "margin", "game_total", "spread_line",
            "total_line", "home_moneyline", "away_moneyline", "market_home_prob",
            "rest_diff", "home_elo", "away_elo", "elo_home_prob",
            "diff_win_ewma", "diff_off_epa_ewma", "diff_def_epa_allowed_ewma",
            "diff_pass_epa_ewma", "diff_rush_epa_ewma", "diff_success_rate_ewma",
            "diff_off_epa_l3", "diff_off_epa_l8", "diff_pass_epa_l3", "diff_pass_epa_l8",
            "diff_rush_epa_l3", "diff_rush_epa_l8", "diff_success_rate_l3",
            "diff_success_rate_l8", "diff_win_l3", "diff_win_l8",
        ) if c in work.columns
    ]

    for season in TARGET_SEASONS:
        tr = work[work["season"] < season]
        va = work[work["season"] == season]
        if va.empty:
            continue
        if len(tr) < 100:
            raise RuntimeError(f"{target}: insufficient pre-{season} history")
        part = va[meta_cols].copy()
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target].astype(float))
            pred = model.predict(va[feature_cols])
            part[name] = pred
            errors[name].append(float(mean_absolute_error(va[target], pred)))
        parts.append(part)

    if not parts:
        raise RuntimeError(f"{target}: no target-season OOF rows")

    oof = pd.concat(parts).sort_index()
    base_mae = {name: float(np.mean(vals)) for name, vals in errors.items()}
    inv = {name: 1.0 / max(value, 1e-9) for name, value in base_mae.items()}
    denom = sum(inv.values())
    weights = {name: value / denom for name, value in inv.items()}
    pred_col = f"model_{target}"
    oof[pred_col] = sum(weights[name] * oof[name].to_numpy(dtype=float) for name in weights)
    residual = pd.to_numeric(oof[target], errors="coerce") - oof[pred_col]
    sigma = float(residual.std(ddof=1))
    return oof, {
        "target": target,
        "base_mean_oof_mae": base_mae,
        "descriptive_weights": weights,
        "residual_std": sigma,
        "ensemble_mae": float(residual.abs().mean()),
        "methodology": "season-held-out base predictions; inverse-MAE weights estimated across same 2022-2025 OOF block",
    }


def _numeric_metrics(actual: pd.Series, pred: pd.Series) -> dict:
    a = pd.to_numeric(actual, errors="coerce")
    p = pd.to_numeric(pred, errors="coerce")
    mask = a.notna() & p.notna()
    a, p = a[mask].astype(float), p[mask].astype(float)
    resid = a - p
    return {
        "games": int(len(a)),
        "mae": float(resid.abs().mean()),
        "rmse": _rmse(a, p),
        "mean_signed_error_actual_minus_pred": float(resid.mean()),
        "residual_std": float(resid.std(ddof=1)),
        "actual_std": float(a.std(ddof=1)),
        "predicted_std": float(p.std(ddof=1)),
        "actual_variance": float(a.var(ddof=1)),
        "predicted_variance": float(p.var(ddof=1)),
    }


def _interval_coverage(actual: pd.Series, pred: pd.Series, sigma: float) -> float:
    a = pd.to_numeric(actual, errors="coerce")
    p = pd.to_numeric(pred, errors="coerce")
    mask = a.notna() & p.notna()
    a, p = a[mask].astype(float), p[mask].astype(float)
    return float(((a >= p - Z80 * sigma) & (a <= p + Z80 * sigma)).mean())


def _probability_metrics(y: pd.Series, p: pd.Series) -> dict:
    yy = pd.to_numeric(y, errors="coerce")
    pp = pd.to_numeric(p, errors="coerce")
    mask = yy.notna() & pp.notna()
    yy = yy[mask].astype(int)
    pp = pp[mask].astype(float).clip(1e-6, 1 - 1e-6)
    return {
        "games": int(len(yy)),
        "winner_accuracy": float(((pp >= 0.5).astype(int) == yy).mean()),
        "brier": float(brier_score_loss(yy, pp)),
        "log_loss": float(log_loss(yy, pp)),
    }


def _cover_probability(mean: float, sigma: float, threshold: float) -> float:
    if not np.isfinite(mean) or not np.isfinite(sigma) or sigma <= 0 or not np.isfinite(threshold):
        return np.nan
    return float(1.0 - NormalDist(mu=float(mean), sigma=float(sigma)).cdf(float(threshold)))


def _bucket(value: float, defs) -> str | None:
    if pd.isna(value):
        return None
    value = float(value)
    for lo, hi, label in defs:
        if value >= lo and value < hi:
            return label
    return None


def _block_bootstrap_error_delta(
    frame: pd.DataFrame,
    model_error: pd.Series,
    market_error: pd.Series,
    *,
    samples: int = 5000,
    seed: int = 26,
) -> dict:
    work = pd.DataFrame({
        "season": pd.to_numeric(frame["season"], errors="coerce"),
        "week": pd.to_numeric(frame["week"], errors="coerce"),
        "delta": pd.to_numeric(model_error, errors="coerce") - pd.to_numeric(market_error, errors="coerce"),
    }).dropna()
    work["_block"] = work["season"].astype(int).astype(str) + "_" + work["week"].astype(int).astype(str)
    blocks = sorted(work["_block"].unique())
    values = {block: work.loc[work["_block"].eq(block), "delta"].to_numpy(dtype=float) for block in blocks}
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=float)
    for i in range(int(samples)):
        chosen = rng.choice(blocks, size=len(blocks), replace=True)
        draws[i] = float(np.concatenate([values[block] for block in chosen]).mean())
    return {
        "games": int(len(work)),
        "blocks": int(len(blocks)),
        "model_minus_market_mae": float(work["delta"].mean()),
        "ci95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "bootstrap_probability_model_better": float(np.mean(draws < 0.0)),
        "samples": int(samples),
        "block": "season+week",
    }


def _error_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    def add(dimension: str, bucket: str, part: pd.DataFrame) -> None:
        if part.empty:
            return
        margin_resid = part["actual_margin"] - part["model_margin"]
        total_resid = part["actual_total"] - part["model_total"]
        rows.append({
            "dimension": dimension,
            "bucket": str(bucket),
            "games": int(len(part)),
            "margin_mae": float(margin_resid.abs().mean()),
            "margin_rmse": float(np.sqrt(np.mean(np.square(margin_resid)))),
            "margin_bias_actual_minus_pred": float(margin_resid.mean()),
            "total_mae": float(total_resid.abs().mean()),
            "total_rmse": float(np.sqrt(np.mean(np.square(total_resid)))),
            "total_bias_actual_minus_pred": float(total_resid.mean()),
            "market_spread_mae": float(part["market_margin_error_abs"].dropna().mean()) if part["market_margin_error_abs"].notna().any() else np.nan,
            "market_total_mae": float(part["market_total_error_abs"].dropna().mean()) if part["market_total_error_abs"].notna().any() else np.nan,
        })

    for season, part in frame.groupby("season"):
        add("season", str(int(season)), part)

    frame = frame.copy()
    frame["week_bucket"] = pd.cut(
        pd.to_numeric(frame["week"], errors="coerce"),
        bins=[0, 4, 9, 14, np.inf],
        labels=["weeks_1_4", "weeks_5_9", "weeks_10_14", "weeks_15_plus"],
        include_lowest=True,
    )
    for label, part in frame.groupby("week_bucket", observed=True):
        add("season_segment", str(label), part)

    frame["market_favorite_size"] = frame["market_margin"].abs().map(lambda x: _bucket(x, FAVORITE_BUCKETS))
    for label, part in frame.groupby("market_favorite_size", dropna=True):
        add("market_favorite_size_abs_points", label, part)

    frame["market_total_bucket"] = frame["total_line"].map(lambda x: _bucket(x, TOTAL_BUCKETS))
    for label, part in frame.groupby("market_total_bucket", dropna=True):
        add("market_total_line", label, part)

    frame["edge_bucket"] = frame["model_market_gap"].abs().map(lambda x: _bucket(x, EDGE_BUCKETS))
    for label, part in frame.groupby("edge_bucket", dropna=True):
        add("model_market_margin_disagreement", label, part)

    frame["result_class"] = np.where(frame["actual_margin"].abs() <= 8, "one_score_8_or_less", "non_one_score")
    for label, part in frame.groupby("result_class"):
        add("result_class", label, part)

    for threshold in (14, 21, 28):
        add("realized_blowout_threshold", f"abs_margin_ge_{threshold}", frame[frame["actual_margin"].abs() >= threshold])

    if "rest_diff" in frame.columns:
        rd = pd.to_numeric(frame["rest_diff"], errors="coerce")
        frame["rest_bucket"] = np.select(
            [rd <= -3, rd >= 3],
            ["home_rest_disadvantage_3plus", "home_rest_advantage_3plus"],
            default="rest_diff_within_2",
        )
        for label, part in frame.groupby("rest_bucket"):
            add("rest_differential", label, part)

    frame["market_favorite_side"] = np.select(
        [frame["market_margin"] > 0, frame["market_margin"] < 0],
        ["home_favorite", "away_favorite"],
        default="pickem",
    )
    for label, part in frame.groupby("market_favorite_side"):
        add("market_favorite_side", label, part)

    if "div_game" in frame.columns:
        div = pd.to_numeric(frame["div_game"], errors="coerce")
        for label, part in frame.groupby(np.where(div.eq(1), "division", "non_division")):
            add("division_game", label, part)

    if "roof" in frame.columns:
        roof = frame["roof"].fillna("unknown").astype(str).str.lower()
        frame["roof_bucket"] = np.where(
            roof.str.contains("dome|closed", regex=True),
            "enclosed",
            np.where(roof.str.contains("outdoor|open", regex=True), "open_air_or_open_roof", "other_or_unknown"),
        )
        for label, part in frame.groupby("roof_bucket"):
            add("roof_state", label, part)

    if {"home_elo", "away_elo"}.issubset(frame.columns):
        elo_gap = (pd.to_numeric(frame["home_elo"], errors="coerce") - pd.to_numeric(frame["away_elo"], errors="coerce")).abs()
        frame["elo_strength_gap"] = pd.cut(
            elo_gap, bins=[-np.inf, 50, 100, np.inf], labels=["<50", "50-100", "100+"], right=False
        )
        for label, part in frame.groupby("elo_strength_gap", observed=True):
            add("pregame_elo_gap", str(label), part)

    for side in ("home_team", "away_team"):
        if side in frame.columns:
            for team, part in frame.groupby(side):
                add(side, team, part)

    return pd.DataFrame(rows)


def _process_diagnostics(pbp: pd.DataFrame) -> pd.DataFrame:
    if pbp is None or pbp.empty or "game_id" not in pbp.columns:
        return pd.DataFrame()
    work = pbp.copy()
    if "season" in work.columns:
        work = work[pd.to_numeric(work["season"], errors="coerce").isin(TARGET_SEASONS)]
    if "season_type" in work.columns:
        work = work[work["season_type"].eq("REG")]
    if work.empty:
        return pd.DataFrame()

    rows = []
    for game_id, g in work.groupby("game_id", sort=False):
        valid = g[g.get("posteam", pd.Series(index=g.index, dtype=object)).notna()].copy()
        pass_attempts = float(pd.to_numeric(valid.get("pass_attempt", 0), errors="coerce").fillna(0).sum())
        rush_attempts = float(pd.to_numeric(valid.get("rush_attempt", 0), errors="coerce").fillna(0).sum())
        denom = pass_attempts + rush_attempts
        epa = pd.to_numeric(valid.get("epa", np.nan), errors="coerce")
        success = pd.to_numeric(valid.get("success", np.nan), errors="coerce")
        yards = pd.to_numeric(valid.get("yards_gained", np.nan), errors="coerce")
        interceptions = pd.to_numeric(valid.get("interception", 0), errors="coerce").fillna(0)
        fumbles_lost = pd.to_numeric(valid.get("fumble_lost", 0), errors="coerce").fillna(0)
        sacks = pd.to_numeric(valid.get("sack", 0), errors="coerce").fillna(0)
        qb_hits = pd.to_numeric(valid.get("qb_hit", 0), errors="coerce").fillna(0)
        possessions = np.nan
        red_zone_opportunities = np.nan
        red_zone_td_rate = np.nan
        if "drive" in valid.columns and "posteam" in valid.columns:
            drive_keys = valid[["posteam", "drive"]].dropna().drop_duplicates()
            possessions = float(drive_keys.shape[0])
            if "yardline_100" in valid.columns and "touchdown" in valid.columns:
                drive = valid[["posteam", "drive", "yardline_100", "touchdown"]].dropna(subset=["posteam", "drive"]).copy()
                drive["yardline_100"] = pd.to_numeric(drive["yardline_100"], errors="coerce")
                drive["touchdown"] = pd.to_numeric(drive["touchdown"], errors="coerce").fillna(0)
                drive_summary = drive.groupby(["posteam", "drive"], observed=True).agg(
                    reached_red_zone=("yardline_100", lambda s: bool((s <= 20).any())),
                    touchdown=("touchdown", "max"),
                )
                rz = drive_summary[drive_summary["reached_red_zone"]]
                red_zone_opportunities = float(len(rz))
                red_zone_td_rate = float(rz["touchdown"].mean()) if len(rz) else np.nan
        fg_result = valid.get("field_goal_result", pd.Series(index=valid.index, dtype=object)).astype(str).str.lower()
        made_field_goals = float(fg_result.eq("made").sum())
        special = pd.to_numeric(valid.get("special_teams_play", 0), errors="coerce")
        if not isinstance(special, pd.Series):
            special = pd.Series(float(special), index=valid.index)
        special = special.fillna(0).eq(1)
        touchdowns = pd.to_numeric(valid.get("touchdown", 0), errors="coerce")
        if not isinstance(touchdowns, pd.Series):
            touchdowns = pd.Series(float(touchdowns), index=valid.index)
        special_teams_tds = float((special & touchdowns.fillna(0).eq(1)).sum())
        rows.append({
            "game_id": game_id,
            "realized_offensive_plays": int(len(valid)),
            "realized_pass_rate": float(pass_attempts / denom) if denom else np.nan,
            "realized_rush_rate": float(rush_attempts / denom) if denom else np.nan,
            "realized_mean_epa": float(epa.mean()) if epa.notna().any() else np.nan,
            "realized_success_rate": float(success.mean()) if success.notna().any() else np.nan,
            "realized_explosive_20plus_rate": float((yards >= 20).mean()) if yards.notna().any() else np.nan,
            "realized_turnovers": float(interceptions.sum() + fumbles_lost.sum()),
            "realized_sacks": float(sacks.sum()),
            "realized_qb_hits": float(qb_hits.sum()),
            "realized_possessions_proxy": possessions,
            "realized_red_zone_opportunities": red_zone_opportunities,
            "realized_red_zone_td_rate": red_zone_td_rate,
            "realized_made_field_goals": made_field_goals,
            "realized_special_teams_tds": special_teams_tds,
        })
    return pd.DataFrame(rows)


def _correlations(frame: pd.DataFrame) -> dict:
    out = {}
    abs_margin_error = (frame["actual_margin"] - frame["model_margin"]).abs()
    abs_total_error = (frame["actual_total"] - frame["model_total"]).abs()
    for col in (
        "realized_offensive_plays", "realized_pass_rate", "realized_mean_epa",
        "realized_success_rate", "realized_explosive_20plus_rate",
        "realized_turnovers", "realized_sacks", "realized_qb_hits",
        "realized_possessions_proxy", "realized_rush_rate",
        "realized_red_zone_opportunities", "realized_red_zone_td_rate",
        "realized_made_field_goals", "realized_special_teams_tds",
    ):
        if col not in frame.columns:
            continue
        x = pd.to_numeric(frame[col], errors="coerce")
        mask_m = x.notna() & abs_margin_error.notna()
        mask_t = x.notna() & abs_total_error.notna()
        out[col] = {
            "games_margin": int(mask_m.sum()),
            "corr_with_abs_margin_error": float(x[mask_m].corr(abs_margin_error[mask_m])) if mask_m.sum() >= 3 else np.nan,
            "games_total": int(mask_t.sum()),
            "corr_with_abs_total_error": float(x[mask_t].corr(abs_total_error[mask_t])) if mask_t.sum() >= 3 else np.nan,
        }
    return out


def run(output_dir: str = "research_outputs/spread_points_phase1", config_path: str = "config/model.yaml") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    bundle = load_core_data(range(start, 2026), cfg["data"]["cache_dir"])
    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, 2026))

    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(bundle.pbp, cfg["data"]["neutral_wp_lower"], cfg["data"]["neutral_wp_upper"])
    team_games = add_game_results(team_games, bundle.schedules)
    games = build_matchup_features(team_games, bundle.schedules, elo)
    games = add_vig_free_market_prob(games)
    historical = games[
        pd.to_numeric(games["season"], errors="coerce").le(2025)
        & pd.to_numeric(games["margin"], errors="coerce").notna()
    ].copy()

    features = core_columns(historical)
    margin_oof, margin_fit = _regression_oof(historical, features, "margin", seed=int(cfg["model"]["random_state"]))
    total_oof, total_fit = _regression_oof(historical, features, "game_total", seed=int(cfg["model"]["random_state"]))

    keep_total = ["game_id", "model_game_total"]
    merged = margin_oof.merge(total_oof[keep_total], on="game_id", how="inner")
    merged = merged.rename(columns={
        "model_margin": "model_margin",
        "model_game_total": "model_total",
        "margin": "actual_margin",
        "game_total": "actual_total",
    })
    merged["actual_home_score"] = pd.to_numeric(merged["home_score"], errors="coerce")
    merged["actual_away_score"] = pd.to_numeric(merged["away_score"], errors="coerce")
    merged["model_home_score"] = (merged["model_total"] + merged["model_margin"]) / 2.0
    merged["model_away_score"] = (merged["model_total"] - merged["model_margin"]) / 2.0
    merged["market_margin"] = pd.to_numeric(merged["spread_line"], errors="coerce")
    merged["market_margin_error_abs"] = (merged["actual_margin"] - merged["market_margin"]).abs()
    merged["market_total_error_abs"] = (merged["actual_total"] - pd.to_numeric(merged["total_line"], errors="coerce")).abs()
    merged["model_market_gap"] = merged["model_margin"] - merged["market_margin"]

    diagnostic_schedule_cols = [
        c for c in ["game_id", "div_game", "roof", "location", "stadium"]
        if c in bundle.schedules.columns
    ]
    if len(diagnostic_schedule_cols) > 1:
        schedule_diag = bundle.schedules[diagnostic_schedule_cols].drop_duplicates("game_id", keep="last")
        merged = merged.merge(schedule_diag, on="game_id", how="left", validate="one_to_one")

    margin_sigma = float(margin_fit["residual_std"])
    total_sigma = float(total_fit["residual_std"])

    # Exact chronology-clean winner analogue already used by the current F-ST audit.
    frozen = prepare_frozen_historical_frame(load_frozen_training_frame())
    winner_pred, winner_coeff = walk_forward_incremental_stack(frozen)
    winner_pred = winner_pred[winner_pred["season"].isin(TARGET_SEASONS)].copy()
    merged = merged.merge(
        winner_pred[["game_id", "home_win", "market_prob", "pure_prob", "market_calibrated_prob", "market_plus_pure_prob"]],
        on="game_id",
        how="left",
    )

    # ATS and probabilistic cover diagnostics.
    edge = merged["model_margin"] - merged["market_margin"]
    market_residual = merged["actual_margin"] - merged["market_margin"]
    merged["ats_push"] = np.isclose(market_residual, 0.0)
    merged["model_no_edge"] = np.isclose(edge, 0.0)
    merged["ats_hit"] = np.where(
        merged["ats_push"] | merged["model_no_edge"] | edge.isna() | market_residual.isna(),
        np.nan,
        np.sign(edge) == np.sign(market_residual),
    )
    merged["cover_home_prob"] = [
        _cover_probability(m, margin_sigma, s)
        for m, s in zip(merged["model_margin"], merged["market_margin"])
    ]
    merged["actual_home_cover"] = np.where(
        merged["ats_push"] | merged["market_margin"].isna(),
        np.nan,
        (merged["actual_margin"] > merged["market_margin"]).astype(float),
    )
    merged["over_prob"] = [
        _cover_probability(m, total_sigma, s)
        for m, s in zip(merged["model_total"], pd.to_numeric(merged["total_line"], errors="coerce"))
    ]
    total_push = np.isclose(merged["actual_total"] - pd.to_numeric(merged["total_line"], errors="coerce"), 0.0)
    merged["actual_over"] = np.where(
        total_push | pd.to_numeric(merged["total_line"], errors="coerce").isna(),
        np.nan,
        (merged["actual_total"] > pd.to_numeric(merged["total_line"], errors="coerce")).astype(float),
    )

    # Coherence with the chronology-clean historical F-ST analogue.
    merged["probability_implied_margin"] = pd.to_numeric(merged["market_plus_pure_prob"], errors="coerce").clip(1e-6, 1 - 1e-6).map(
        lambda p: NormalDist().inv_cdf(float(p)) * margin_sigma if pd.notna(p) else np.nan
    )
    merged["winner_margin_sign_split"] = (
        np.sign(merged["market_plus_pure_prob"] - 0.5) != np.sign(merged["model_margin"])
    ) & ~np.isclose(merged["market_plus_pure_prob"], 0.5) & ~np.isclose(merged["model_margin"], 0.0)

    process = _process_diagnostics(bundle.pbp)
    if not process.empty:
        merged = merged.merge(process, on="game_id", how="left")

    baseline = {
        "sample": {
            "seasons": list(TARGET_SEASONS),
            "games": int(len(merged)),
            "ties": int(np.isclose(merged["actual_margin"], 0.0).sum()),
            "postseason_included": False,
            "oos_label": "current-validation descriptive ensemble; base predictions season-held-out",
        },
        "model_fit": {"margin": margin_fit, "total": total_fit},
        "team_points": {
            "home": _numeric_metrics(merged["actual_home_score"], merged["model_home_score"]),
            "away": _numeric_metrics(merged["actual_away_score"], merged["model_away_score"]),
        },
        "margin": _numeric_metrics(merged["actual_margin"], merged["model_margin"]),
        "total": _numeric_metrics(merged["actual_total"], merged["model_total"]),
        "interval_coverage": {
            "margin_nominal_80": _interval_coverage(merged["actual_margin"], merged["model_margin"], margin_sigma),
            "total_nominal_80": _interval_coverage(merged["actual_total"], merged["model_total"], total_sigma),
            "margin_sigma": margin_sigma,
            "total_sigma": total_sigma,
        },
        "market": {
            "spread": _numeric_metrics(merged["actual_margin"], merged["market_margin"]),
            "total": _numeric_metrics(merged["actual_total"], pd.to_numeric(merged["total_line"], errors="coerce")),
            "timing": "historical schedule/closing-line benchmark; exact capture timing opaque",
        },
        "winner": {
            "chronology_clean_fst_analogue": _probability_metrics(merged["home_win"], merged["market_plus_pure_prob"]),
            "raw_market": _probability_metrics(merged["home_win"], merged["market_prob"]),
            "football_only": _probability_metrics(merged["home_win"], merged["pure_prob"]),
        },
    }

    modern = merged[pd.to_numeric(merged["season"], errors="coerce").ge(2023)].copy()
    baseline["modern_2023_2025"] = {
        "games": int(len(modern)),
        "home_points": _numeric_metrics(modern["actual_home_score"], modern["model_home_score"]),
        "away_points": _numeric_metrics(modern["actual_away_score"], modern["model_away_score"]),
        "margin": _numeric_metrics(modern["actual_margin"], modern["model_margin"]),
        "market_spread": _numeric_metrics(modern["actual_margin"], modern["market_margin"]),
        "total": _numeric_metrics(modern["actual_total"], modern["model_total"]),
        "market_total": _numeric_metrics(modern["actual_total"], pd.to_numeric(modern["total_line"], errors="coerce")),
    }
    baseline["paired_model_vs_market_uncertainty"] = {
        "margin_mae": _block_bootstrap_error_delta(
            merged,
            (merged["actual_margin"] - merged["model_margin"]).abs(),
            (merged["actual_margin"] - merged["market_margin"]).abs(),
            samples=5000,
            seed=426,
        ),
        "total_mae": _block_bootstrap_error_delta(
            merged,
            (merged["actual_total"] - merged["model_total"]).abs(),
            (merged["actual_total"] - pd.to_numeric(merged["total_line"], errors="coerce")).abs(),
            samples=5000,
            seed=427,
        ),
    }

    non_ties = ~np.isclose(merged["actual_margin"], 0.0)
    baseline["winner"]["tie_excluded_sensitivity"] = {
        "games": int(non_ties.sum()),
        "chronology_clean_fst_accuracy": float(
            ((merged.loc[non_ties, "market_plus_pure_prob"] >= 0.5).astype(int) == merged.loc[non_ties, "home_win"].astype(int)).mean()
        ),
        "market_accuracy": float(
            ((merged.loc[non_ties, "market_prob"] >= 0.5).astype(int) == merged.loc[non_ties, "home_win"].astype(int)).mean()
        ),
    }

    ats = pd.to_numeric(merged["ats_hit"], errors="coerce").dropna()
    cover_mask = pd.to_numeric(merged["actual_home_cover"], errors="coerce").notna() & pd.to_numeric(merged["cover_home_prob"], errors="coerce").notna()
    over_mask = pd.to_numeric(merged["actual_over"], errors="coerce").notna() & pd.to_numeric(merged["over_prob"], errors="coerce").notna()
    baseline["ats"] = {
        "market_covered_games": int(merged["market_margin"].notna().sum()),
        "pushes": int(merged["ats_push"].sum()),
        "model_no_edge_games": int(merged["model_no_edge"].sum()),
        "decisions": int(len(ats)),
        "model_ats_accuracy": float(ats.mean()) if len(ats) else np.nan,
        "cover_probability_brier": float(brier_score_loss(merged.loc[cover_mask, "actual_home_cover"].astype(int), merged.loc[cover_mask, "cover_home_prob"])) if cover_mask.any() else np.nan,
        "over_probability_brier": float(brier_score_loss(merged.loc[over_mask, "actual_over"].astype(int), merged.loc[over_mask, "over_prob"])) if over_mask.any() else np.nan,
    }

    # Fixed ATS edge buckets.
    ats_buckets = []
    for lo, hi, label in EDGE_BUCKETS:
        part = merged[(edge.abs() >= lo) & (edge.abs() < hi)]
        decisions = pd.to_numeric(part["ats_hit"], errors="coerce").dropna()
        ats_buckets.append({
            "edge_bucket": label,
            "games": int(len(part)),
            "decisions": int(len(decisions)),
            "ats_accuracy": float(decisions.mean()) if len(decisions) else np.nan,
            "margin_mae": float((part["actual_margin"] - part["model_margin"]).abs().mean()) if len(part) else np.nan,
            "market_spread_mae": float(part["market_margin_error_abs"].mean()) if len(part) else np.nan,
        })
    baseline["ats"]["edge_buckets"] = ats_buckets

    # Compression/favorite diagnostics.
    compression = {
        "actual_margin_std": float(merged["actual_margin"].std(ddof=1)),
        "model_margin_std": float(merged["model_margin"].std(ddof=1)),
        "market_margin_std": float(merged["market_margin"].std(ddof=1)),
        "model_to_actual_sd_ratio": float(merged["model_margin"].std(ddof=1) / merged["actual_margin"].std(ddof=1)),
        "market_to_actual_sd_ratio": float(merged["market_margin"].std(ddof=1) / merged["actual_margin"].std(ddof=1)),
        "favorite_size": [],
        "realized_blowouts": [],
    }
    for lo, hi, label in FAVORITE_BUCKETS:
        part = merged[(merged["market_margin"].abs() >= lo) & (merged["market_margin"].abs() < hi) & ~np.isclose(merged["market_margin"], 0.0)]
        sign = np.sign(part["market_margin"])
        compression["favorite_size"].append({
            "bucket": label,
            "games": int(len(part)),
            "market_favorite_expected_margin": float((part["market_margin"] * sign).mean()) if len(part) else np.nan,
            "model_favorite_expected_margin": float((part["model_margin"] * sign).mean()) if len(part) else np.nan,
            "realized_favorite_margin": float((part["actual_margin"] * sign).mean()) if len(part) else np.nan,
            "realized_minus_model_favorite_margin": float(((part["actual_margin"] - part["model_margin"]) * sign).mean()) if len(part) else np.nan,
        })
    for threshold in (14, 21, 28):
        part = merged[merged["actual_margin"].abs() >= threshold]
        sign = np.sign(part["actual_margin"])
        compression["realized_blowouts"].append({
            "threshold": threshold,
            "games": int(len(part)),
            "mean_realized_abs_margin": float(part["actual_margin"].abs().mean()) if len(part) else np.nan,
            "mean_model_margin_oriented_to_actual_winner": float((part["model_margin"] * sign).mean()) if len(part) else np.nan,
            "mean_market_margin_oriented_to_actual_winner": float((part["market_margin"] * sign).mean()) if len(part) else np.nan,
        })

    coherence_mask = merged["market_plus_pure_prob"].notna() & merged["probability_implied_margin"].notna()
    coherence = {
        "games": int(coherence_mask.sum()),
        "winner_vs_independent_margin_sign_splits": int(merged.loc[coherence_mask, "winner_margin_sign_split"].sum()),
        "winner_vs_independent_margin_sign_split_rate": float(merged.loc[coherence_mask, "winner_margin_sign_split"].mean()),
        "independent_vs_probability_implied_margin_mae": float(
            (merged.loc[coherence_mask, "model_margin"] - merged.loc[coherence_mask, "probability_implied_margin"]).abs().mean()
        ),
        "independent_vs_probability_implied_margin_correlation": float(
            merged.loc[coherence_mask, "model_margin"].corr(merged.loc[coherence_mask, "probability_implied_margin"])
        ),
        "note": "uses chronology-clean historical F-ST analogue; public production bridge uses official frozen probability plus margin sigma",
    }

    window_pairs = [
        ("diff_off_epa_l3", "diff_off_epa_l8"),
        ("diff_pass_epa_l3", "diff_pass_epa_l8"),
        ("diff_rush_epa_l3", "diff_rush_epa_l8"),
        ("diff_success_rate_l3", "diff_success_rate_l8"),
        ("diff_win_l3", "diff_win_l8"),
    ]
    standardized_parts = []
    for short_col, long_col in window_pairs:
        if short_col not in merged.columns or long_col not in merged.columns:
            continue
        diff = (pd.to_numeric(merged[short_col], errors="coerce") - pd.to_numeric(merged[long_col], errors="coerce")).abs()
        scale = float(pd.to_numeric(merged[long_col], errors="coerce").std(ddof=1))
        if np.isfinite(scale) and scale > 0:
            standardized_parts.append(diff / scale)
    if standardized_parts:
        merged["recent_form_window_disagreement"] = pd.concat(standardized_parts, axis=1).mean(axis=1)
        q25, q75 = merged["recent_form_window_disagreement"].quantile([0.25, 0.75])
        low = merged[merged["recent_form_window_disagreement"] <= q25]
        high = merged[merged["recent_form_window_disagreement"] >= q75]
        recent_form_instability = {
            "definition": "mean standardized absolute L3-vs-L8 disagreement across offense/pass/rush/success/win pregame features",
            "corr_with_abs_margin_error": float(merged["recent_form_window_disagreement"].corr((merged["actual_margin"] - merged["model_margin"]).abs())),
            "corr_with_abs_total_error": float(merged["recent_form_window_disagreement"].corr((merged["actual_total"] - merged["model_total"]).abs())),
            "bottom_quartile_games": int(len(low)),
            "bottom_quartile_margin_mae": float((low["actual_margin"] - low["model_margin"]).abs().mean()),
            "top_quartile_games": int(len(high)),
            "top_quartile_margin_mae": float((high["actual_margin"] - high["model_margin"]).abs().mean()),
            "diagnostic_only": True,
        }
    else:
        recent_form_instability = {"status": "unavailable"}

    market_signal_overlap = {
        "independent_margin_vs_market_margin_correlation": float(merged["model_margin"].corr(merged["market_margin"])),
        "independent_total_vs_market_total_correlation": float(merged["model_total"].corr(pd.to_numeric(merged["total_line"], errors="coerce"))),
        "football_probability_vs_market_probability_correlation": float(merged["pure_prob"].corr(merged["market_prob"])),
        "direct_market_feature_in_independent_margin_total_models": False,
    }

    decomposition = _error_rows(merged)
    process_corr = _correlations(merged)

    team_point_rows = []
    for team in sorted(set(merged["home_team"].astype(str)) | set(merged["away_team"].astype(str))):
        home = merged[merged["home_team"].astype(str).eq(team)]
        away = merged[merged["away_team"].astype(str).eq(team)]
        actual_for = pd.concat([home["actual_home_score"], away["actual_away_score"]], ignore_index=True)
        pred_for = pd.concat([home["model_home_score"], away["model_away_score"]], ignore_index=True)
        actual_against = pd.concat([home["actual_away_score"], away["actual_home_score"]], ignore_index=True)
        pred_against = pd.concat([home["model_away_score"], away["model_home_score"]], ignore_index=True)
        team_point_rows.append({
            "team": team,
            "games": int(len(actual_for)),
            "offense_points_mae": float((actual_for - pred_for).abs().mean()),
            "offense_points_bias_actual_minus_pred": float((actual_for - pred_for).mean()),
            "defense_points_allowed_mae": float((actual_against - pred_against).abs().mean()),
            "defense_points_allowed_bias_actual_minus_pred": float((actual_against - pred_against).mean()),
        })
    team_points = pd.DataFrame(team_point_rows)

    summary = {
        "status": "research_only",
        "production_changed": False,
        "historical_outcomes_after_2025_used_for_model_selection": 0,
        "evaluation_contract": "research/spread-points-nextgen/phase1/EVALUATION_CONTRACT.md",
        "baseline": baseline,
        "compression": compression,
        "coherence": coherence,
        "market_signal_overlap": market_signal_overlap,
        "recent_form_instability": recent_form_instability,
        "realized_process_diagnostics": {
            "warning": "postgame diagnostic associations only; never pregame features in this audit",
            "correlations": process_corr,
        },
        "limitations": [
            "Historical nflverse schedule market lines have opaque exact capture timing and are treated as a closing/historical benchmark.",
            "QB transition, injury, inactive, weather, travel, and personnel subgroup labels require separately qualified point-in-time histories; missing state is not treated as healthy/stable.",
            "The regression ensemble weights reproduce current validation semantics and are descriptive across the same OOF block, not chronology-clean candidate-selection evidence.",
        ],
    }

    merged.to_csv(out / "baseline_predictions_2022_2025.csv", index=False)
    decomposition.to_csv(out / "error_decomposition.csv", index=False)
    team_points.to_csv(out / "team_points_decomposition.csv", index=False)
    winner_coeff.to_csv(out / "chronology_clean_winner_coefficients.csv", index=False)
    (out / "baseline_metrics.json").write_text(json.dumps(baseline, indent=2, allow_nan=True), encoding="utf-8")
    (out / "phase1_machine_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/spread_points_phase1")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    result = run(args.output_dir, args.config)
    print(json.dumps(result, indent=2, allow_nan=True))

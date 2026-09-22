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
            "rest_diff",
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
        if "drive" in valid.columns and "posteam" in valid.columns:
            possessions = float(valid[["posteam", "drive"]].dropna().drop_duplicates().shape[0])
        rows.append({
            "game_id": game_id,
            "realized_offensive_plays": int(len(valid)),
            "realized_pass_rate": float(pass_attempts / denom) if denom else np.nan,
            "realized_mean_epa": float(epa.mean()) if epa.notna().any() else np.nan,
            "realized_success_rate": float(success.mean()) if success.notna().any() else np.nan,
            "realized_explosive_20plus_rate": float((yards >= 20).mean()) if yards.notna().any() else np.nan,
            "realized_turnovers": float(interceptions.sum() + fumbles_lost.sum()),
            "realized_sacks": float(sacks.sum()),
            "realized_qb_hits": float(qb_hits.sum()),
            "realized_possessions_proxy": possessions,
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
        "realized_possessions_proxy",
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

    decomposition = _error_rows(merged)
    process_corr = _correlations(merged)

    summary = {
        "status": "research_only",
        "production_changed": False,
        "historical_outcomes_after_2025_used_for_model_selection": 0,
        "evaluation_contract": "research/spread-points-nextgen/phase1/EVALUATION_CONTRACT.md",
        "baseline": baseline,
        "compression": compression,
        "coherence": coherence,
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

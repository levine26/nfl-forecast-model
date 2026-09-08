from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import NormalDist
import numpy as np
import pandas as pd

from .config import load_config
from .data import load_core_data, load_advanced_data
from .elo import build_pregame_elo
from .features import aggregate_team_games, add_game_results, build_matchup_features, sujar_baseline_columns, core_columns
from .market import add_vig_free_market_prob
from .models import fit_season_stacked_classifier, fit_weighted_regression
from .publish import write_outputs


@dataclass
class PipelineArtifacts:
    games: pd.DataFrame
    predictions: pd.DataFrame


def projected_score(margin: pd.Series, total: pd.Series) -> tuple[pd.Series, pd.Series]:
    home = (total + margin) / 2.0
    away = (total - margin) / 2.0
    return home, away


def fair_american_odds(prob: float) -> float:
    p = float(np.clip(prob, 1e-6, 1 - 1e-6))
    if p >= 0.5:
        return -100.0 * p / (1.0 - p)
    return 100.0 * (1.0 - p) / p


def probability_above(threshold, mean, sigma) -> float:
    if pd.isna(threshold) or pd.isna(mean) or pd.isna(sigma) or float(sigma) <= 0:
        return np.nan
    return float(1.0 - NormalDist(mu=float(mean), sigma=float(sigma)).cdf(float(threshold)))


def consistency_flag(prob: float, margin: float) -> str:
    # Tiny near-50/near-zero differences are noise, not a meaningful conflict.
    if abs(float(prob) - 0.5) < 0.02 or abs(float(margin)) < 1.0:
        return "NEUTRAL"
    return "ALIGNED" if (float(prob) - 0.5) * float(margin) > 0 else "WIN-MARGIN SPLIT"


def confidence_label(prob: float, disagreement: float = 0.0, consistency: str = "ALIGNED") -> str:
    q = max(float(prob), 1.0 - float(prob))
    level = 3 if q >= 0.70 else 2 if q >= 0.60 else 1 if q >= 0.55 else 0
    if float(disagreement) >= 0.10:
        level -= 1
    if consistency == "WIN-MARGIN SPLIT":
        level -= 1
    return ["Coin Flip", "Lean", "Solid", "High"][max(0, min(3, level))]


def run(config_path="config/model.yaml", season_to_predict=2026, snapshot_type="EARLY") -> PipelineArtifacts:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, season_to_predict + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])

    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, season_to_predict + 1))

    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    tg = aggregate_team_games(bundle.pbp, cfg["data"]["neutral_wp_lower"], cfg["data"]["neutral_wp_upper"])
    tg = add_game_results(tg, bundle.schedules)
    games = build_matchup_features(tg, bundle.schedules, elo)
    games = add_vig_free_market_prob(games)

    historical = games[games["home_win"].notna()].copy()
    unresolved = games[(games["season"] == season_to_predict) & games["home_win"].isna()].copy()
    if unresolved.empty:
        raise RuntimeError(f"No upcoming games found for {season_to_predict}.")
    next_week = int(unresolved["week"].min())
    current = unresolved[unresolved["week"] == next_week].copy()

    baseline_cols = sujar_baseline_columns(historical)
    core_cols = core_columns(historical)
    if len(baseline_cols) < 4:
        raise RuntimeError(f"Baseline feature build incomplete: {baseline_cols}")

    validation_start = max(start + 1, season_to_predict - 4)
    validation_end = season_to_predict - 1
    seed = cfg["model"]["random_state"]
    baseline = fit_season_stacked_classifier(historical, baseline_cols, seed=seed, validation_start=validation_start, validation_end=validation_end)
    core = fit_season_stacked_classifier(historical, core_cols, seed=seed, validation_start=validation_start, validation_end=validation_end)
    margin = fit_weighted_regression(historical, core_cols, "margin", seed=seed, validation_start=validation_start, validation_end=validation_end)
    total = fit_weighted_regression(historical, core_cols, "game_total", seed=seed, validation_start=validation_start, validation_end=validation_end)

    current["sujar_home_prob"] = baseline.predict_proba(current)[:, 1]
    current["pure_home_prob"] = core.predict_proba(current)[:, 1]
    current["expected_margin"] = margin.predict(current)
    current["expected_total"] = total.predict(current)
    current["margin_sigma"] = float(margin.residual_std)
    current["total_sigma"] = float(total.residual_std)

    has_market = current["market_home_prob"].notna()
    current["market_available"] = has_market
    current["final_home_prob"] = current["pure_home_prob"]
    current.loc[has_market, "final_home_prob"] = (
        0.75 * current.loc[has_market, "pure_home_prob"]
        + 0.25 * current.loc[has_market, "market_home_prob"]
    )

    current["fair_home_moneyline"] = current["final_home_prob"].map(fair_american_odds)
    current["model_edge"] = np.where(
        current["spread_line"].notna(), current["expected_margin"] - current["spread_line"], np.nan
    )
    current["cover_home_prob"] = current.apply(
        lambda r: probability_above(r.get("spread_line"), r.get("expected_margin"), r.get("margin_sigma")), axis=1
    )
    current["over_prob"] = current.apply(
        lambda r: probability_above(r.get("total_line"), r.get("expected_total"), r.get("total_sigma")), axis=1
    )
    z80 = 1.2815515655446004
    current["margin_low_80"] = current["expected_margin"] - z80 * current["margin_sigma"]
    current["margin_high_80"] = current["expected_margin"] + z80 * current["margin_sigma"]
    current["total_low_80"] = current["expected_total"] - z80 * current["total_sigma"]
    current["total_high_80"] = current["expected_total"] + z80 * current["total_sigma"]

    hp, ap = projected_score(current["expected_margin"], current["expected_total"])
    current["projected_home_score"] = hp
    current["projected_away_score"] = ap
    current["projected_score"] = current.apply(
        lambda r: f"{r.home_team} {r.projected_home_score:.1f} – {r.away_team} {r.projected_away_score:.1f}", axis=1
    )
    current["pick"] = np.where(current["final_home_prob"] >= 0.5, current["home_team"], current["away_team"])

    base_probs = core.base_predict(current)
    current["model_disagreement"] = base_probs.std(axis=1)
    current["consistency_flag"] = current.apply(
        lambda r: consistency_flag(r["final_home_prob"], r["expected_margin"]), axis=1
    )
    current["confidence"] = current.apply(
        lambda r: confidence_label(r["final_home_prob"], r["model_disagreement"], r["consistency_flag"]), axis=1
    )

    pbp_max = int(pd.to_numeric(bundle.pbp.get("season"), errors="coerce").max()) if len(bundle.pbp) else start
    if pbp_max >= season_to_predict:
        data_state = f"{season_to_predict} schedule/results/Elo + PBP/EPA live"
    else:
        data_state = f"{season_to_predict} schedule/results/Elo live; EPA/form through {pbp_max}"
    current["data_state"] = data_state
    current["model_version"] = "0.2.0-locks-uncertainty"
    current["snapshot_type"] = snapshot_type
    current["prediction_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    return PipelineArtifacts(games=games, predictions=current)

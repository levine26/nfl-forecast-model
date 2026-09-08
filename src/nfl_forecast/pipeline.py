from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .config import load_config
from .data import load_core_data, load_advanced_data
from .elo import build_pregame_elo
from .features import aggregate_team_games, add_game_results, build_matchup_features, sujar_baseline_columns, core_columns
from .market import add_vig_free_market_prob
from .models import fit_season_stacked_classifier, fit_weighted_regression


@dataclass
class PipelineArtifacts:
    games: pd.DataFrame
    predictions: pd.DataFrame


def projected_score(margin: pd.Series, total: pd.Series) -> tuple[pd.Series, pd.Series]:
    home = (total + margin) / 2.0
    away = (total - margin) / 2.0
    return home, away


def confidence_label(prob: float) -> str:
    q = max(prob, 1 - prob)
    if q >= 0.70: return "High"
    if q >= 0.60: return "Solid"
    if q >= 0.55: return "Lean"
    return "Coin Flip"


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

    # Use recent, fully completed seasons to learn ensemble weights while retaining
    # the full historical sample for the final fitted models. The live test season
    # is therefore never used to tune stacker/weight parameters.
    validation_start = max(start + 1, season_to_predict - 4)
    validation_end = season_to_predict - 1
    baseline = fit_season_stacked_classifier(historical, baseline_cols, seed=cfg["model"]["random_state"], validation_start=validation_start, validation_end=validation_end)
    core = fit_season_stacked_classifier(historical, core_cols, seed=cfg["model"]["random_state"], validation_start=validation_start, validation_end=validation_end)
    margin = fit_weighted_regression(historical, core_cols, "margin", seed=cfg["model"]["random_state"], validation_start=validation_start, validation_end=validation_end)
    total = fit_weighted_regression(historical, core_cols, "game_total", seed=cfg["model"]["random_state"], validation_start=validation_start, validation_end=validation_end)

    current["sujar_home_prob"] = baseline.predict_proba(current)[:, 1]
    current["pure_home_prob"] = core.predict_proba(current)[:, 1]
    current["expected_margin"] = margin.predict(current)
    current["expected_total"] = total.predict(current)

    has_market = current["market_home_prob"].notna()
    current["final_home_prob"] = current["pure_home_prob"]
    current.loc[has_market, "final_home_prob"] = (
        0.75 * current.loc[has_market, "pure_home_prob"] + 0.25 * current.loc[has_market, "market_home_prob"]
    )

    hp, ap = projected_score(current["expected_margin"], current["expected_total"])
    current["projected_home_score"] = hp
    current["projected_away_score"] = ap
    current["projected_score"] = current.apply(lambda r: f"{r.home_team} {r.projected_home_score:.1f} – {r.away_team} {r.projected_away_score:.1f}", axis=1)
    current["pick"] = np.where(current["final_home_prob"] >= 0.5, current["home_team"], current["away_team"])
    current["confidence"] = current["final_home_prob"].map(confidence_label)
    current["model_version"] = "0.1.0-core"
    current["snapshot_type"] = snapshot_type
    current["prediction_timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    base_probs = core.base_predict(current)
    current["model_disagreement"] = base_probs.std(axis=1)
    return PipelineArtifacts(games=games, predictions=current)


def write_outputs(artifacts: PipelineArtifacts, output_dir="outputs") -> None:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    p = artifacts.predictions.copy()
    cols = [c for c in [
        "game_id","season","week","gameday","gametime","away_team","home_team",
        "sujar_home_prob","pure_home_prob","market_home_prob","final_home_prob","pick",
        "expected_margin","expected_total","projected_score","spread_line","total_line",
        "confidence","model_disagreement","snapshot_type","model_version","prediction_timestamp_utc"
    ] if c in p.columns]
    p[cols].to_csv(out / "this_week.csv", index=False)

    hist_path = out / "prediction_history.csv"
    hist = p[cols].copy()
    hist["prediction_id"] = hist["game_id"].astype(str) + "__" + hist["snapshot_type"] + "__" + hist["prediction_timestamp_utc"]
    if hist_path.exists():
        old = pd.read_csv(hist_path)
        hist = pd.concat([old, hist], ignore_index=True).drop_duplicates("prediction_id")
    hist.to_csv(hist_path, index=False)

    status = {
        "status": "healthy",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "games": int(len(p)),
        "model_version": str(p["model_version"].iloc[0]) if len(p) else None,
    }
    (out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

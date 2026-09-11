from __future__ import annotations

"""Run PHASE3B-PROB-MARGIN-BRIDGE-001 without touching production surfaces."""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_market_incremental import walk_forward_incremental_stack
from nfl_forecast.challenger_probability_margin_bridge import (
    blocked_margin_bootstrap,
    chronological_probability_margin_bridge,
    margin_metrics,
    result_dict,
    six_plus_disagreement_slice,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features
from nfl_forecast.fst_nested_pure import load_frozen_training_frame


def run(
    output_dir: str = "research_outputs/phase3b_probability_margin_bridge",
    *,
    config_path: str = "config/model.yaml",
    bootstrap_samples: int = 2000,
) -> dict:
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
    team_games = aggregate_team_games(
        bundle.pbp,
        cfg["data"]["neutral_wp_lower"],
        cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, bundle.schedules)
    games = build_matchup_features(team_games, bundle.schedules, elo)
    games = games[pd.to_numeric(games.season, errors="coerce").le(2025)].copy()
    if pd.to_numeric(games.season, errors="coerce").dropna().ge(2026).any():
        raise RuntimeError("Phase 3B loaded post-2025 outcomes")

    frozen = load_frozen_training_frame()
    incremental, coefficients = walk_forward_incremental_stack(frozen)
    predictions, diagnostics = chronological_probability_margin_bridge(
        games,
        incremental,
        probability_cols=("market_prob", "market_plus_pure_prob"),
    )

    market_bridge_col = "market_prob_bridge_margin"
    football_bridge_col = "market_plus_pure_prob_bridge_margin"
    metrics = {
        "market_spread": margin_metrics(predictions, "spread_line"),
        "raw_market_probability_bridge": margin_metrics(predictions, market_bridge_col),
        "market_plus_football_probability_bridge": margin_metrics(predictions, football_bridge_col),
    }
    uncertainty = {
        "raw_market_bridge_vs_market_spread": result_dict(
            blocked_margin_bootstrap(
                predictions,
                market_bridge_col,
                "spread_line",
                samples=bootstrap_samples,
                seed=331,
            )
        ),
        "market_plus_football_bridge_vs_market_spread": result_dict(
            blocked_margin_bootstrap(
                predictions,
                football_bridge_col,
                "spread_line",
                samples=bootstrap_samples,
                seed=332,
            )
        ),
        "market_plus_football_bridge_vs_raw_market_bridge": result_dict(
            blocked_margin_bootstrap(
                predictions,
                football_bridge_col,
                market_bridge_col,
                samples=bootstrap_samples,
                seed=333,
            )
        ),
    }
    large_gap = {
        "raw_market_probability_bridge": six_plus_disagreement_slice(predictions, market_bridge_col),
        "market_plus_football_probability_bridge": six_plus_disagreement_slice(predictions, football_bridge_col),
    }

    raw_vs_spread = uncertainty["raw_market_bridge_vs_market_spread"]
    football_vs_spread = uncertainty["market_plus_football_bridge_vs_market_spread"]
    football_vs_raw = uncertainty["market_plus_football_bridge_vs_raw_market_bridge"]
    raw_predictive = raw_vs_spread["ci_upper"] <= 0.0
    football_predictive = football_vs_spread["ci_upper"] <= 0.0
    football_incremental = football_vs_raw["ci_upper"] < 0.0
    interpretation = (
        "validated_predictive_margin_model"
        if football_predictive and football_incremental
        else "presentation_transform_not_validated_margin_forecast"
    )

    predictions.to_csv(out / "phase3b_bridge_predictions_2022_2025.csv", index=False)
    diagnostics.to_csv(out / "phase3b_sigma_diagnostics.csv", index=False)
    coefficients.to_csv(out / "phase3b_incremental_probability_coefficients.csv", index=False)
    report = {
        "status": "research_only",
        "experiment_id": "PHASE3B-PROB-MARGIN-BRIDGE-001",
        "candidate_version": "chronological-probability-margin-bridge-v1",
        "production_changed": False,
        "promotion_authorized": False,
        "2026_outcomes_used": 0,
        "games": int(len(predictions)),
        "metrics": metrics,
        "uncertainty": uncertainty,
        "six_plus_point_disagreement": large_gap,
        "qualification": {
            "raw_market_bridge_not_worse_than_spread_with_support": raw_predictive,
            "market_plus_football_bridge_not_worse_than_spread_with_support": football_predictive,
            "market_plus_football_bridge_improves_raw_bridge_with_support": football_incremental,
            "public_interpretation": interpretation,
        },
        "decision_rule": (
            "Do not tune sigma after observing this result. If the bridge fails, keep it only as an explicitly labeled probability-consistent presentation transform rather than a validated expected-margin forecast."
        ),
    }
    (out / "phase3b_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/phase3b_probability_margin_bridge")
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config, bootstrap_samples=args.bootstrap_samples)


if __name__ == "__main__":
    main()

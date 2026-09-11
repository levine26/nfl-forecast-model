from __future__ import annotations

"""Run research-only historical forensics for large margin-vs-market disagreements."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_margin_forensics import (
    bootstrap_dict,
    bootstrap_large_gap_error_delta,
    current_large_gap_probes,
    summarize_margin_disagreements,
    walk_forward_margin_predictions,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import (
    add_game_results,
    aggregate_team_games,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.market import add_vig_free_market_prob


def _records(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    clean = frame.replace({np.nan: None})
    return json.loads(clean.to_json(orient="records"))


def run(
    output_dir: str = "research_outputs/margin_forensics",
    *,
    config_path: str = "config/model.yaml",
    bootstrap_samples: int = 3000,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, 2026))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
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
    games = add_vig_free_market_prob(games)
    historical = games[
        pd.to_numeric(games.season, errors="coerce").le(2025)
        & games.margin.notna()
        & games.spread_line.notna()
    ].copy()
    if historical.empty:
        raise RuntimeError("No historical margin rows available")
    if pd.to_numeric(historical.season, errors="coerce").max() > 2025:
        raise RuntimeError("Margin forensic historical cutoff failed")

    features = core_columns(historical)
    predictions, weights = walk_forward_margin_predictions(
        historical,
        features,
        seed=int(cfg["model"]["random_state"]),
    )
    buckets = summarize_margin_disagreements(predictions)
    large_gap = predictions[predictions.abs_model_market_gap >= 6.0].copy()
    season_large_gap = (
        large_gap.groupby("season", as_index=False)
        .agg(
            games=("game_id", "size") if "game_id" in large_gap.columns else ("actual_margin", "size"),
            mean_abs_gap_points=("abs_model_market_gap", "mean"),
            model_margin_mae=("model_abs_error", "mean"),
            market_spread_mae=("market_abs_error", "mean"),
            model_minus_market_mae=("model_minus_market_abs_error", "mean"),
            model_closer_rate=("model_closer", "mean"),
        )
        if not large_gap.empty
        else pd.DataFrame()
    )
    uncertainty = bootstrap_large_gap_error_delta(
        predictions,
        minimum_gap_points=6.0,
        samples=bootstrap_samples,
        seed=626,
    )

    predictions.to_csv(out / "margin_oof_predictions_2022_2025.csv", index=False)
    weights.to_csv(out / "margin_descriptive_weights.csv", index=False)
    buckets.to_csv(out / "margin_gap_buckets.csv", index=False)
    season_large_gap.to_csv(out / "margin_6plus_by_season.csv", index=False)

    current_probes = pd.DataFrame()
    slate_path = Path("outputs/this_week.csv")
    if slate_path.exists():
        current_probes = current_large_gap_probes(pd.read_csv(slate_path), minimum_gap_points=6.0)
        current_probes.to_csv(out / "current_large_margin_disagreements.csv", index=False)

    overall = {
        "games": int(len(predictions)),
        "model_margin_mae": float(predictions.model_abs_error.mean()),
        "market_spread_mae": float(predictions.market_abs_error.mean()),
        "model_minus_market_mae": float(predictions.model_minus_market_abs_error.mean()),
        "model_closer_rate": float(predictions.model_closer.mean()),
    }
    report = {
        "status": "research_only",
        "study": "margin_disagreement_forensics",
        "production_changed": False,
        "promotion_authorized": False,
        "historical_outcomes_after_2025_used": 0,
        "historical_target_seasons": [2022, 2023, 2024, 2025],
        "methodology_caveat": (
            "Base margin predictions are season-held-out. The final inverse-MAE ensemble weights are descriptive current-production-style weights estimated across the same 2022-25 OOF block; this audit diagnoses large disagreement behavior and is not a chronology-clean candidate-selection test."
        ),
        "overall": overall,
        "gap_buckets": _records(buckets),
        "six_plus_point_gap_uncertainty": bootstrap_dict(uncertainty),
        "six_plus_by_season": _records(season_large_gap),
        "current_ungraded_large_gap_probes": _records(current_probes),
        "kc_probe_game_id": "2026_01_DEN_KC",
        "decision_rule": (
            "Do not treat a large margin-vs-market disagreement as an edge merely because it is large. Require historical error improvement and uncertainty support; current 2026 probes remain ungraded and cannot tune the model."
        ),
    }
    (out / "margin_forensics_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/margin_forensics")
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--bootstrap-samples", type=int, default=3000)
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config, bootstrap_samples=args.bootstrap_samples)


if __name__ == "__main__":
    main()

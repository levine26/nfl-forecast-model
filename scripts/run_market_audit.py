from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data, load_advanced_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import aggregate_team_games, add_game_results, build_matchup_features, core_columns
from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.market_diagnostics import build_market_diagnostics
from nfl_forecast.models import fit_season_stacked_classifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    cfg = load_config(args.config)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, args.season + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, args.season + 1))

    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(bundle.pbp, cfg["data"]["neutral_wp_lower"], cfg["data"]["neutral_wp_upper"])
    team_games = add_game_results(team_games, bundle.schedules)
    games = add_vig_free_market_prob(build_matchup_features(team_games, bundle.schedules, elo))
    historical = games[games["home_win"].notna()].copy()

    validation_start = max(start + 1, args.season - 4)
    validation_end = args.season - 1
    core = fit_season_stacked_classifier(
        historical,
        core_columns(historical),
        seed=cfg["model"]["random_state"],
        validation_start=validation_start,
        validation_end=validation_end,
    )

    current_path = Path(args.output_dir) / "this_week.csv"
    current = pd.read_csv(current_path) if current_path.exists() else pd.DataFrame()
    audit, grid, walk = build_market_diagnostics(historical, core.oof_predictions, current)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "market_independence.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    grid.to_csv(out / "market_weight_grid.csv", index=False)
    walk.to_csv(out / "market_weight_walk_forward.csv", index=False)

    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Reusable historical-only challenger feature assembly.

Unlike live challenger runners, this helper never needs a current/future schedule row. It
is intended for orthogonal historical experiments that must hard-cap their data horizon.
Production forecasting code does not import this module.
"""

from dataclasses import dataclass

import pandas as pd

from .challenger_v07 import build_opponent_adjusted_matchup_features, opponent_adjusted_feature_columns
from .challenger_v08 import build_qb_matchup_features, qb_feature_columns
from .config import load_config
from .data import load_core_data
from .elo import build_pregame_elo
from .features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from .market import add_vig_free_market_prob


@dataclass(frozen=True)
class HistoricalChallengerFrame:
    config: dict
    games: pd.DataFrame
    feature_sets: dict[str, list[str]]


def build_historical_challenger_frame(
    config_path: str = "config/model.yaml",
    *,
    end_season: int = 2025,
) -> HistoricalChallengerFrame:
    if end_season > 2025:
        raise ValueError("Historical model-selection data horizon may not exceed 2025")
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, int(end_season) + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
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
    base_games = build_matchup_features(team_games, bundle.schedules, elo)
    opponent_games = build_opponent_adjusted_matchup_features(team_games, bundle.schedules, base_games)
    games = build_qb_matchup_features(bundle.pbp, bundle.schedules, opponent_games)
    games = add_vig_free_market_prob(games)

    season = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season.le(end_season)].copy()
    if historical.empty:
        raise RuntimeError("Historical challenger frame is empty")
    if int(pd.to_numeric(historical["season"], errors="coerce").max()) > end_season:
        raise RuntimeError("Historical challenger frame violated its data horizon")

    opponent = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    core = core_columns(historical)
    base = [column for column in core if column not in set(opponent) | set(qb)]
    if not base or len(opponent) != 32 or not qb:
        raise RuntimeError("Historical challenger feature construction failed")
    feature_sets = {
        "production_compatible": sorted(base),
        "opponent_adjusted_qb": sorted(set(base + opponent + qb)),
    }
    return HistoricalChallengerFrame(cfg, historical, feature_sets)

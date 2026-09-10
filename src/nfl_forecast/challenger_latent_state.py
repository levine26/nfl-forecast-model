from __future__ import annotations

"""Historical-only assembly for the pre-registered F-LS-01 latent-state challenger."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .challenger_v07 import build_opponent_adjusted_matchup_features, opponent_adjusted_feature_columns
from .challenger_v08 import build_qb_matchup_features, qb_feature_columns
from .config import load_config
from .data import load_core_data
from .elo import build_pregame_elo
from .features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from .latent_state_research import build_game_latent_features, build_latent_team_state, latent_feature_columns
from .market import add_vig_free_market_prob

HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)


@dataclass(frozen=True)
class LatentResearchFrame:
    historical: pd.DataFrame
    feature_sets: dict[str, list[str]]
    latent_features: list[str]
    latent_audit: dict[str, Any]
    counts: dict[str, int]


def build_latent_research_frame(config_path: str = "config/model.yaml") -> LatentResearchFrame:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, HISTORICAL_END + 1))
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

    latent_build = build_latent_team_state(team_games)
    games = build_game_latent_features(games, latent_build.pregame_state)

    season = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season.le(HISTORICAL_END)].copy()
    if historical.empty or pd.to_numeric(historical["season"], errors="coerce").gt(HISTORICAL_END).any():
        raise RuntimeError("F-LS-01 historical horizon was violated")

    opponent = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    latent = latent_feature_columns(historical)
    core = core_columns(historical)
    blocked = set(opponent) | set(qb)
    base = [column for column in core if column not in blocked]
    if not base or len(opponent) != 32 or not qb or len(latent) != 2:
        raise RuntimeError("F-LS-01 feature construction is incomplete")

    feature_sets = {
        "production_compatible": sorted(base),
        "v08": sorted(set(base + opponent + qb)),
        "v08_plus_latent": sorted(set(base + opponent + qb + latent)),
    }
    return LatentResearchFrame(
        historical=historical,
        feature_sets=feature_sets,
        latent_features=latent,
        latent_audit=latent_build.audit,
        counts={
            "historical_games": int(len(historical)),
            "pbp_rows": int(len(bundle.pbp)),
            "team_game_rows": int(len(team_games)),
            "latent_pregame_rows": int(len(latent_build.pregame_state)),
            "latent_terminal_rows": int(len(latent_build.terminal_state)),
        },
    )

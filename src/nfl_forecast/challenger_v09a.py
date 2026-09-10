from __future__ import annotations

"""Leakage-safe v0.9A player-value challenger assembly.

This module is research-only. It builds historical game-level player-state features from
completed 2012-2025 play data and joins them to the existing v0.8 football feature stack.
It never reads 2026 outcomes, never writes production outputs, and is not imported by the
production forecasting path.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .challenger_v07 import build_opponent_adjusted_matchup_features, opponent_adjusted_feature_columns
from .challenger_v08 import build_qb_matchup_features, qb_feature_columns
from .config import load_config
from .data import load_advanced_data, load_core_data
from .elo import build_pregame_elo
from .features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from .market import add_vig_free_market_prob
from .player_state_research import build_game_player_features, build_player_state, v09a_feature_columns

HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)


@dataclass(frozen=True)
class V09AResearchFrame:
    historical: pd.DataFrame
    feature_sets: dict[str, list[str]]
    player_feature_columns: list[str]
    player_audit: dict[str, Any]
    counts: dict[str, int]


def _historical_source(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Restrict an advanced source to <=2025 when it exposes a season field."""
    if frame is None or frame.empty:
        return frame
    if "season" not in frame.columns:
        return frame
    season = pd.to_numeric(frame["season"], errors="coerce")
    return frame[season.le(HISTORICAL_END)].copy()


def _assert_selection_data_contract(frame: pd.DataFrame) -> None:
    season = pd.to_numeric(frame["season"], errors="coerce")
    if season.gt(HISTORICAL_END).any():
        raise ValueError("v0.9A historical selection frame contains post-2025 rows")
    if "home_win" in frame.columns and frame.loc[season.gt(HISTORICAL_END), "home_win"].notna().any():
        raise ValueError("2026 outcomes are prohibited from v0.9A selection")


def build_v09a_research_frame(config_path: str = "config/model.yaml") -> V09AResearchFrame:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    bundle = load_advanced_data(bundle, seasons)

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
    opp_games = build_opponent_adjusted_matchup_features(team_games, bundle.schedules, base_games)
    games = build_qb_matchup_features(bundle.pbp, bundle.schedules, opp_games)
    games = add_vig_free_market_prob(games)

    player_build = build_player_state(
        bundle.pbp,
        snap_counts=_historical_source(bundle.snap_counts),
        depth_charts=_historical_source(bundle.depth_charts),
        ngs_passing=_historical_source(bundle.ngs_passing),
    )
    games = build_game_player_features(games, player_build.team_pregame_state)

    season_num = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season_num.le(HISTORICAL_END)].copy()
    _assert_selection_data_contract(historical)

    opp = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    player = v09a_feature_columns(historical)
    all_core = core_columns(historical)
    blocked = set(opp) | set(qb) | set(player)
    base = [column for column in all_core if column not in blocked]
    if not base or len(opp) != 32 or not qb or not player:
        raise RuntimeError("v0.9A feature construction is incomplete")

    feature_sets = {
        "production_compatible": sorted(base),
        "opponent_adjusted_qb": sorted(set(base + opp + qb)),
        "production_plus_player": sorted(set(base + player)),
        "opponent_adjusted_qb_plus_player": sorted(set(base + opp + qb + player)),
    }
    return V09AResearchFrame(
        historical=historical,
        feature_sets=feature_sets,
        player_feature_columns=player,
        player_audit=player_build.audit,
        counts={
            "games": int(len(historical)),
            "plays": int(len(bundle.pbp)),
            "player_game_roles": int(len(player_build.player_game_roles)),
            "player_state_rows": int(len(player_build.player_state)),
            "team_pregame_state_rows": int(len(player_build.team_pregame_state)),
        },
    )

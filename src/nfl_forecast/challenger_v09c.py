from __future__ import annotations

"""Historical-only LevLine v0.9C unit-continuity challenger assembly.

This research module hard-caps all model-selection data at 2025. Unit state for game G
comes only from completed G-1/G-2 snap distributions. It is never imported by the
production forecast path.
"""

from dataclasses import dataclass
from typing import Any

import nflreadpy as nfl
import pandas as pd

from .challenger_v07 import build_opponent_adjusted_matchup_features, opponent_adjusted_feature_columns
from .challenger_v08 import build_qb_matchup_features, qb_feature_columns
from .config import load_config
from .data import load_advanced_data, load_core_data
from .elo import build_pregame_elo
from .features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from .market import add_vig_free_market_prob
from .unit_state_research import build_game_unit_features, build_unit_state, v09c_feature_columns

HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)


@dataclass(frozen=True)
class V09CResearchFrame:
    historical: pd.DataFrame
    feature_sets: dict[str, list[str]]
    unit_features: list[str]
    unit_audit: dict[str, Any]
    counts: dict[str, int]


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def build_v09c_research_frame(config_path: str = "config/model.yaml") -> V09CResearchFrame:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    bundle = load_advanced_data(bundle, seasons)
    if bundle.snap_counts is None or bundle.snap_counts.empty:
        raise RuntimeError("v0.9C requires historical snap-count data")

    players = _pandas(nfl.load_players())
    if players is None or players.empty:
        raise RuntimeError("v0.9C requires the nflverse player ID crosswalk")

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

    snap_season = pd.to_numeric(bundle.snap_counts["season"], errors="coerce")
    historical_snaps = bundle.snap_counts[snap_season.le(HISTORICAL_END)].copy()
    unit_build = build_unit_state(historical_snaps, players)
    games = build_game_unit_features(games, unit_build.team_pregame_state)

    season = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season.le(HISTORICAL_END)].copy()
    if historical.empty or pd.to_numeric(historical.season, errors="coerce").gt(HISTORICAL_END).any():
        raise RuntimeError("v0.9C historical selection horizon was violated")

    opponent = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    unit = v09c_feature_columns(historical)
    core = core_columns(historical)
    blocked = set(opponent) | set(qb) | set(unit)
    base = [column for column in core if column not in blocked]
    if not base or len(opponent) != 32 or not qb or len(unit) != 11:
        raise RuntimeError("v0.9C feature construction is incomplete")

    feature_sets = {
        "production_compatible": sorted(base),
        "opponent_adjusted_qb": sorted(set(base + opponent + qb)),
        "opponent_adjusted_qb_plus_unit": sorted(set(base + opponent + qb + unit)),
    }
    return V09CResearchFrame(
        historical=historical,
        feature_sets=feature_sets,
        unit_features=unit,
        unit_audit=unit_build.audit,
        counts={
            "historical_games": int(len(historical)),
            "pbp_rows": int(len(bundle.pbp)),
            "snap_rows": int(len(unit_build.snap_rows)),
            "team_game_unit_rows": int(len(unit_build.team_game_unit_state)),
            "team_pregame_unit_rows": int(len(unit_build.team_pregame_state)),
        },
    )

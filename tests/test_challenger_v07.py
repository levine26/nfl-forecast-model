import numpy as np
import pandas as pd

from nfl_forecast.challenger_v07 import (
    add_opponent_adjusted_game_residuals,
    build_opponent_adjusted_matchup_features,
    opponent_adjusted_feature_columns,
)


def _row(game_id, week, home, away, team, off, opp_off):
    return {
        "game_id": game_id,
        "season": 2025,
        "week": week,
        "gameday": f"2025-09-{week:02d}",
        "home_team": home,
        "away_team": away,
        "team": team,
        "off_epa": off,
        "pass_epa": off + 0.02,
        "rush_epa": off - 0.02,
        "success_rate": 0.50 + off / 5.0,
        "neutral_epa": off,
        "def_epa_allowed": opp_off,
        "def_pass_epa_allowed": opp_off + 0.02,
        "def_rush_epa_allowed": opp_off - 0.02,
        "def_success_allowed": 0.50 + opp_off / 5.0,
        "win": float(off > opp_off),
    }


def _fixture():
    games = [
        ("g1", 1, "A", "B", 0.20, -0.10),
        ("g2", 1, "C", "D", 0.05, 0.10),
        ("g3", 2, "A", "D", 0.30, 0.00),
        ("g4", 2, "C", "B", 0.15, -0.05),
        ("g5", 3, "A", "C", 0.40, 0.10),
    ]
    rows = []
    for game_id, week, home, away, home_off, away_off in games:
        rows.append(_row(game_id, week, home, away, home, home_off, away_off))
        rows.append(_row(game_id, week, home, away, away, away_off, home_off))
    team_games = pd.DataFrame(rows)

    schedules = pd.DataFrame([
        {"game_id": "g1", "season": 2025, "week": 1, "gameday": "2025-09-01", "gametime": "13:00", "home_team": "A", "away_team": "B", "game_type": "REG"},
        {"game_id": "g2", "season": 2025, "week": 1, "gameday": "2025-09-01", "gametime": "16:00", "home_team": "C", "away_team": "D", "game_type": "REG"},
        {"game_id": "g3", "season": 2025, "week": 2, "gameday": "2025-09-02", "gametime": "13:00", "home_team": "A", "away_team": "D", "game_type": "REG"},
        {"game_id": "g4", "season": 2025, "week": 2, "gameday": "2025-09-02", "gametime": "16:00", "home_team": "C", "away_team": "B", "game_type": "REG"},
        {"game_id": "g5", "season": 2025, "week": 3, "gameday": "2025-09-03", "gametime": "13:00", "home_team": "A", "away_team": "C", "game_type": "REG"},
        {"game_id": "g6", "season": 2025, "week": 4, "gameday": "2025-09-04", "gametime": "13:00", "home_team": "A", "away_team": "B", "game_type": "REG"},
    ])
    base_games = schedules[["game_id", "season", "week", "home_team", "away_team"]].copy()
    return team_games, schedules, base_games


def test_game_residual_uses_opponent_pregame_strength():
    team_games, _, _ = _fixture()
    adjusted = add_opponent_adjusted_game_residuals(team_games)

    # In g3, A produced 0.30 EPA/play. D entered g3 having allowed 0.05
    # EPA/play in g2, so A's opponent-adjusted residual is +0.25.
    row = adjusted[(adjusted.game_id == "g3") & (adjusted.team == "A")].iloc[0]
    assert np.isclose(row.opp_adj_off_epa, 0.25)

    # A allowed 0.00 EPA/play in g3. D entered with +0.10 offensive EPA,
    # so A's defensive residual is -0.10 (lower remains better).
    assert np.isclose(row.opp_adj_def_epa_allowed, -0.10)


def test_same_game_performance_cannot_change_its_pregame_features():
    team_games, schedules, base_games = _fixture()
    before = build_opponent_adjusted_matchup_features(team_games, schedules, base_games)

    mutated = team_games.copy()
    mask = (mutated.game_id == "g5") & (mutated.team == "A")
    mutated.loc[mask, "off_epa"] = 5.0
    mutated.loc[mask, "pass_epa"] = 5.0
    mutated.loc[mask, "rush_epa"] = 5.0
    mutated.loc[mask, "success_rate"] = 1.0
    after = build_opponent_adjusted_matchup_features(mutated, schedules, base_games)

    feature = "diff_opp_adj_off_epa_ewma"
    g5_before = before.loc[before.game_id.eq("g5"), feature].iloc[0]
    g5_after = after.loc[after.game_id.eq("g5"), feature].iloc[0]
    assert np.isfinite(g5_before)
    assert np.isclose(g5_before, g5_after)

    # The g5 performance is allowed to affect the following game's pregame state.
    g6_before = before.loc[before.game_id.eq("g6"), feature].iloc[0]
    g6_after = after.loc[after.game_id.eq("g6"), feature].iloc[0]
    assert np.isfinite(g6_before)
    assert not np.isclose(g6_before, g6_after)


def test_opponent_adjusted_columns_are_research_only_and_explicit():
    team_games, schedules, base_games = _fixture()
    out = build_opponent_adjusted_matchup_features(team_games, schedules, base_games)
    columns = opponent_adjusted_feature_columns(out)

    assert len(columns) == 32  # 8 residual metrics x EWMA/L3/L5/L8
    assert all(c.startswith("diff_opp_adj_") for c in columns)
    assert set(base_games.columns).issubset(out.columns)

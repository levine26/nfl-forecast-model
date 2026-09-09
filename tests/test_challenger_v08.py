import numpy as np
import pandas as pd

from nfl_forecast.challenger_v08 import (
    build_qb_matchup_features,
    build_qb_starter_team_features,
    qb_feature_columns,
)


def _schedule():
    return pd.DataFrame([
        {"game_id": "c1", "season": 2025, "week": 1, "gameday": "2025-09-01", "gametime": "10:00", "game_type": "REG", "home_team": "C", "away_team": "D", "home_qb_id": "Q3", "away_qb_id": "Q4", "home_qb_name": "Three", "away_qb_name": "Four", "home_score": 24, "away_score": 17},
        {"game_id": "g1", "season": 2025, "week": 1, "gameday": "2025-09-01", "gametime": "13:00", "game_type": "REG", "home_team": "A", "away_team": "B", "home_qb_id": "Q1", "away_qb_id": "Q2", "home_qb_name": "One", "away_qb_name": "Two", "home_score": 20, "away_score": 14},
        {"game_id": "g2", "season": 2025, "week": 2, "gameday": "2025-09-08", "gametime": "13:00", "game_type": "REG", "home_team": "A", "away_team": "B", "home_qb_id": "Q1", "away_qb_id": "Q2", "home_qb_name": "One", "away_qb_name": "Two", "home_score": 17, "away_score": 21},
        {"game_id": "g3", "season": 2025, "week": 3, "gameday": "2025-09-15", "gametime": "13:00", "game_type": "REG", "home_team": "A", "away_team": "B", "home_qb_id": "Q3", "away_qb_id": "Q2", "home_qb_name": "Three", "away_qb_name": "Two", "home_score": 27, "away_score": 23},
        {"game_id": "g4", "season": 2025, "week": 4, "gameday": "2025-09-22", "gametime": "13:00", "game_type": "REG", "home_team": "A", "away_team": "B", "home_qb_id": "Q3", "away_qb_id": "Q2", "home_qb_name": "Three", "away_qb_name": "Two", "home_score": np.nan, "away_score": np.nan},
        {"game_id": "g5", "season": 2025, "week": 5, "gameday": "2025-09-29", "gametime": "13:00", "game_type": "REG", "home_team": "A", "away_team": "B", "home_qb_id": "Q3", "away_qb_id": "Q2", "home_qb_name": "Three", "away_qb_name": "Two", "home_score": np.nan, "away_score": np.nan},
    ])


def _add_dropbacks(rows, game_id, season, week, team, qb, epa):
    for i in range(4):
        rows.append({
            "game_id": game_id,
            "season": season,
            "week": week,
            "season_type": "REG",
            "posteam": team,
            "passer_player_id": qb,
            "passer_player_name": qb,
            "epa": epa + (i - 1.5) * 0.01,
            "pass_attempt": 1,
            "sack": 0,
            "success": float(epa > 0),
            "cpoe": epa * 10,
        })


def _pbp():
    rows = []
    # Q3 establishes strong prior quality with team C before joining A.
    _add_dropbacks(rows, "c1", 2025, 1, "C", "Q3", 0.40)
    _add_dropbacks(rows, "c1", 2025, 1, "D", "Q4", -0.05)
    _add_dropbacks(rows, "g1", 2025, 1, "A", "Q1", 0.10)
    _add_dropbacks(rows, "g1", 2025, 1, "B", "Q2", 0.00)
    _add_dropbacks(rows, "g2", 2025, 2, "A", "Q1", 0.20)
    _add_dropbacks(rows, "g2", 2025, 2, "B", "Q2", 0.05)
    _add_dropbacks(rows, "g3", 2025, 3, "A", "Q3", 0.30)
    _add_dropbacks(rows, "g3", 2025, 3, "B", "Q2", 0.10)
    return pd.DataFrame(rows)


def test_new_team_starter_carries_only_prior_career_quality_and_flags_change():
    team = build_qb_starter_team_features(_pbp(), _schedule())
    row = team[(team.game_id == "g3") & (team.team == "A")].iloc[0]

    # Q3's g3 pregame quality comes from his completed C start, not g3 itself.
    assert np.isclose(float(row.qb_epa_ewma), 0.40)
    assert int(round(float(np.expm1(row.qb_log_prior_starts)))) == 1
    assert float(row.qb_starter_changed) == 1.0
    assert float(row.qb_continuity_starts_prior) == 0.0
    assert float(row.qb_new_starter) == 0.0


def test_same_game_qb_performance_cannot_change_same_game_pregame_feature():
    schedules = _schedule()
    base = schedules[["game_id", "season", "week", "home_team", "away_team"]].copy()
    pbp = _pbp()
    before = build_qb_matchup_features(pbp, schedules, base)

    mutated = pbp.copy()
    mask = (mutated.game_id == "g3") & (mutated.passer_player_id == "Q3")
    mutated.loc[mask, "epa"] = 5.0
    after = build_qb_matchup_features(mutated, schedules, base)

    feature = "diff_qb_epa_ewma"
    g3_before = before.loc[before.game_id.eq("g3"), feature].iloc[0]
    g3_after = after.loc[after.game_id.eq("g3"), feature].iloc[0]
    assert np.isclose(g3_before, g3_after)

    # Once g3 is completed, its QB performance is legitimate prior information for g4.
    g4_before = before.loc[before.game_id.eq("g4"), feature].iloc[0]
    g4_after = after.loc[after.game_id.eq("g4"), feature].iloc[0]
    assert not np.isclose(g4_before, g4_after)


def test_unplayed_future_starts_do_not_manufacture_continuity_or_experience():
    team = build_qb_starter_team_features(_pbp(), _schedule())
    g4 = team[(team.game_id == "g4") & (team.team == "A")].iloc[0]
    g5 = team[(team.game_id == "g5") & (team.team == "A")].iloc[0]

    # Q3 completed one prior start for A (g3). The unplayed g4 row cannot make g5
    # look like two consecutive completed A starts.
    assert float(g4.qb_continuity_starts_prior) == 1.0
    assert float(g5.qb_continuity_starts_prior) == 1.0
    assert np.isclose(float(g4.qb_log_prior_starts), float(g5.qb_log_prior_starts))
    assert float(g4.qb_starter_changed) == 0.0
    assert float(g5.qb_starter_changed) == 0.0


def test_qb_feature_contract_keeps_binary_side_information():
    schedules = _schedule()
    base = schedules[["game_id"]].copy()
    out = build_qb_matchup_features(_pbp(), schedules, base)
    cols = qb_feature_columns(out)

    assert "diff_qb_epa_ewma" in cols
    assert "diff_qb_continuity_starts_prior" in cols
    assert "home_qb_starter_changed" in cols
    assert "away_qb_starter_changed" in cols
    assert "home_qb_quality_missing" in cols
    assert "away_qb_new_starter" in cols

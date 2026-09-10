from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_forecast.player_state_research import (
    add_chronological_player_values,
    audit_player_data,
    build_game_player_features,
    build_player_game_roles,
    build_team_pregame_state,
    normalize_team_code,
    v09a_feature_columns,
)


def _target_pbp(game2_epa: float = -2.0) -> pd.DataFrame:
    rows = []
    for week, epa in ((1, 2.0), (2, game2_epa), (3, 1.0)):
        for play in range(10):
            rows.append(
                {
                    "game_id": f"2022_0{week}_AAA_BBB",
                    "season": 2022,
                    "week": week,
                    "posteam": "AAA",
                    "receiver_player_id": "00-1111111",
                    "receiver_player_name": "A. Receiver",
                    "pass_attempt": 1,
                    "rush_attempt": 0,
                    "epa": epa / 10.0,
                    "success": float(epa > 0),
                    "air_yards": 8.0,
                }
            )
    return pd.DataFrame(rows)


def _state(game2_epa: float = -2.0) -> pd.DataFrame:
    roles = build_player_game_roles(_target_pbp(game2_epa))
    player = add_chronological_player_values(roles, shrinkage={"target": 10.0})
    return build_team_pregame_state(player)


def test_current_game_performance_cannot_change_its_own_pregame_state():
    normal = _state(-2.0).query("role == 'target'").set_index("game_id")
    altered = _state(50.0).query("role == 'target'").set_index("game_id")

    game2 = "2022_02_AAA_BBB"
    game3 = "2022_03_AAA_BBB"
    assert normal.loc[game2, "pregame_player_value"] == altered.loc[game2, "pregame_player_value"]
    assert normal.loc[game3, "pregame_player_value"] != altered.loc[game3, "pregame_player_value"]


def test_first_game_is_explicitly_unknown_and_state_is_lagged():
    state = _state().query("role == 'target'").sort_values("week")
    assert bool(state.iloc[0].state_missing)
    assert np.isnan(state.iloc[0].pregame_player_value)
    assert not bool(state.iloc[1].state_missing)
    assert state.iloc[1].pregame_known_players == 1


def test_same_week_role_prior_does_not_leak_across_games():
    pbp = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2022, "week": 1, "posteam": "A", "receiver_player_id": "p1", "receiver_player_name": "One", "epa": 10.0, "success": 1.0},
            {"game_id": "g2", "season": 2022, "week": 1, "posteam": "B", "receiver_player_id": "p2", "receiver_player_name": "Two", "epa": -10.0, "success": 0.0},
            {"game_id": "g3", "season": 2022, "week": 2, "posteam": "A", "receiver_player_id": "p1", "receiver_player_name": "One", "epa": 0.0, "success": 0.0},
        ]
    )
    state = add_chronological_player_values(build_player_game_roles(pbp), shrinkage={"target": 1.0})
    week1 = state[(state.role == "target") & (state.week == 1)]
    assert set(week1.role_epa_prior) == {0.0}
    week2 = state[(state.role == "target") & (state.week == 2)]
    assert np.isclose(float(week2.iloc[0].role_epa_prior), 0.0)


def test_v09a_game_features_are_compact_skill_state_and_not_qb_double_count():
    state = _state()
    schedules = pd.DataFrame(
        [
            {"game_id": "2022_01_AAA_BBB", "season": 2022, "week": 1, "away_team": "BBB", "home_team": "AAA"},
            {"game_id": "2022_02_AAA_BBB", "season": 2022, "week": 2, "away_team": "BBB", "home_team": "AAA"},
            {"game_id": "2022_03_AAA_BBB", "season": 2022, "week": 3, "away_team": "BBB", "home_team": "AAA"},
        ]
    )
    features = build_game_player_features(schedules, state)
    columns = v09a_feature_columns(features)
    assert columns
    assert all("qb" not in column for column in columns)
    assert len(columns) <= 10


def test_identity_and_data_quality_audit_fail_closed():
    pbp = _target_pbp()
    pbp.loc[pbp.index[0], "posteam"] = "JAC"
    pbp.loc[pbp.index[0], "receiver_player_name"] = "Alpha Receiver"
    pbp.loc[pbp.index[1], "receiver_player_name"] = "Different Person"
    audit = audit_player_data(pbp)
    assert normalize_team_code("JAC") == "JAX"
    assert audit["jax_jac_rows_normalized"] == 1
    assert audit["player_id_name_conflicts"] >= 1
    assert audit["fail_closed_identity_policy"] is True
    assert audit["snap_counts"]["status"] == "missing"
    assert "prohibited" in audit["injury_uncertainty"]

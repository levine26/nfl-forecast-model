import math

import pandas as pd
import pytest

from nfl_forecast.props_role_state import (
    RoleStateError,
    SnapRoleConfig,
    build_snap_trend_role_adjustments,
)


def _snaps():
    return pd.DataFrame(
        [
            {"season": 2024, "week": 1, "game_id": "g1", "team": "LAR", "player_id": "wr1", "offense_pct": 40.0, "game_type": "REG"},
            {"season": 2024, "week": 2, "game_id": "g2", "team": "LAR", "player_id": "wr1", "offense_pct": 50.0, "game_type": "REG"},
            {"season": 2024, "week": 3, "game_id": "g3", "team": "LAR", "player_id": "wr1", "offense_pct": 80.0, "game_type": "REG"},
            {"season": 2024, "week": 4, "game_id": "g4", "team": "LAR", "player_id": "wr1", "offense_pct": 90.0, "game_type": "REG"},
            {"season": 2024, "week": 5, "game_id": "TARGET", "team": "LAR", "player_id": "wr1", "offense_pct": 5.0, "game_type": "REG"},
            {"season": 2024, "week": 1, "game_id": "g1", "team": "LAR", "player_id": "rb1", "offense_pct": 65.0, "game_type": "REG"},
            {"season": 2024, "week": 2, "game_id": "g2", "team": "LAR", "player_id": "rb1", "offense_pct": 60.0, "game_type": "REG"},
            {"season": 2024, "week": 3, "game_id": "g3", "team": "LAR", "player_id": "rb1", "offense_pct": 55.0, "game_type": "REG"},
            {"season": 2024, "week": 4, "game_id": "g4", "team": "LAR", "player_id": "rb1", "offense_pct": 50.0, "game_type": "REG"},
        ]
    )


def _players():
    return pd.DataFrame(
        [
            {"player_id": "wr1", "position": "WR", "team": "LAR"},
            {"player_id": "rb1", "position": "RB", "team": "LAR"},
            {"player_id": "qb1", "position": "QB", "team": "LAR"},
        ]
    )


def test_snap_role_uses_only_prior_weeks():
    adjustments, audit = build_snap_trend_role_adjustments(
        _snaps(), _players(), season=2024, week=5, team="LAR"
    )
    assert audit["target_or_future_rows_used"] == 0
    assert audit["historical_max_period_used"] == {"season": 2024, "week": 4}
    assert audit["players"]["wr1"]["recent_snap_share"] > audit["players"]["wr1"]["baseline_snap_share"]
    assert adjustments["wr1"]["role_multiplier"] > 1.0


def test_future_target_row_cannot_change_multiplier():
    first, _ = build_snap_trend_role_adjustments(
        _snaps(), _players(), season=2024, week=5, team="LAR"
    )
    changed = _snaps()
    changed.loc[changed["game_id"].eq("TARGET"), "offense_pct"] = 100.0
    second, _ = build_snap_trend_role_adjustments(
        changed, _players(), season=2024, week=5, team="LAR"
    )
    assert first == second


def test_percentage_and_fraction_snap_formats_match():
    fraction = _snaps().copy()
    fraction["offense_pct"] = fraction["offense_pct"] / 100.0
    a, _ = build_snap_trend_role_adjustments(
        _snaps(), _players(), season=2024, week=5, team="LAR"
    )
    b, _ = build_snap_trend_role_adjustments(
        fraction, _players(), season=2024, week=5, team="LAR"
    )
    assert math.isclose(a["wr1"]["role_multiplier"], b["wr1"]["role_multiplier"], rel_tol=1e-12)


def test_unknown_or_unsupported_players_remain_neutral():
    adjustments, audit = build_snap_trend_role_adjustments(
        _snaps(), _players(), season=2024, week=5, team="LAR"
    )
    assert "qb1" not in adjustments
    assert "qb1" not in audit["players"]


def test_config_requires_shorter_recent_half_life():
    with pytest.raises(RoleStateError):
        SnapRoleConfig(recent_half_life_games=8.0, baseline_half_life_games=8.0).validate()

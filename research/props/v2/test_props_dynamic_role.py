import pandas as pd
import pytest

from research.props.v2.props_dynamic_role import (
    DynamicRoleError,
    build_dynamic_role_adjustments,
    normalize_lagged_snap_history,
)


def _snaps():
    return pd.DataFrame(
        [
            {"game_id": "g1", "season": 2024, "week": 1, "team": "ARI", "player_id": "wr1", "position": "WR", "offense_pct": 95.0, "offense_snaps": 60},
            {"game_id": "g1", "season": 2024, "week": 1, "team": "ARI", "player_id": "wr3", "position": "WR", "offense_pct": 35.0, "offense_snaps": 22},
            {"game_id": "g2", "season": 2024, "week": 2, "team": "ARI", "player_id": "wr1", "position": "WR", "offense_pct": 92.0, "offense_snaps": 58},
            {"game_id": "g2", "season": 2024, "week": 2, "team": "ARI", "player_id": "wr3", "position": "WR", "offense_pct": 42.0, "offense_snaps": 26},
            {"game_id": "g3", "season": 2024, "week": 3, "team": "ARI", "player_id": "wr1", "position": "WR", "offense_pct": 88.0, "offense_snaps": 55},
            {"game_id": "g3", "season": 2024, "week": 3, "team": "ARI", "player_id": "wr3", "position": "WR", "offense_pct": 70.0, "offense_snaps": 44},
            # Target week must never enter state.
            {"game_id": "target", "season": 2024, "week": 4, "team": "ARI", "player_id": "wr3", "position": "WR", "offense_pct": 100.0, "offense_snaps": 65},
        ]
    )


def _current():
    return pd.DataFrame(
        [
            {"player_id": "wr1", "position": "WR", "team": "ARI"},
            {"player_id": "wr3", "position": "WR", "team": "ARI"},
            {"player_id": "rookie", "position": "WR", "team": "ARI"},
        ]
    )


def test_snap_history_is_strictly_lagged():
    history, audit = normalize_lagged_snap_history(_snaps(), season=2024, week=4)
    assert "target" not in set(history["game_id"])
    assert history["week"].max() == 3
    assert audit["target_week"] == 4
    assert audit["strictly_lagged"] is True


def test_dynamic_role_differentiates_player_participation():
    adjustments, audit = build_dynamic_role_adjustments(
        _snaps(),
        _current(),
        season=2024,
        week=4,
        team="ARI",
    )
    assert adjustments["wr1"]["route_role_multiplier"] > adjustments["wr3"]["route_role_multiplier"]
    assert adjustments["wr3"]["target_role_multiplier"] > 1.0
    assert "rookie" not in adjustments
    assert "rookie" in audit["fallback_player_ids"]
    assert audit["target_game_rows_used"] == 0


def test_snap_share_can_be_derived_when_pct_missing():
    frame = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2024, "week": 1, "team": "ARI", "player_id": "a", "offense_snaps": 60},
            {"game_id": "g1", "season": 2024, "week": 1, "team": "ARI", "player_id": "b", "offense_snaps": 30},
        ]
    )
    history, audit = normalize_lagged_snap_history(frame, season=2024, week=2)
    shares = dict(zip(history["player_id"], history["snap_share"]))
    assert shares["a"] == pytest.approx(1.0)
    assert shares["b"] == pytest.approx(0.5)
    assert audit["derived_share_rows"] == 2


def test_missing_required_horizon_fields_fail_closed():
    with pytest.raises(DynamicRoleError):
        normalize_lagged_snap_history(
            pd.DataFrame([{"game_id": "g1", "player_id": "p1"}]),
            season=2024,
            week=2,
        )


def test_route_only_ablation_does_not_change_target_or_carry_channels():
    adjustments, audit = build_dynamic_role_adjustments(
        _snaps(),
        _current(),
        season=2024,
        week=4,
        team="ARI",
        mode="route_only",
    )
    assert audit["mode"] == "route_only"
    assert adjustments["wr1"]
    assert set(adjustments["wr1"]) == {"route_role_multiplier"}
    assert set(adjustments["wr3"]) == {"route_role_multiplier"}


def test_unknown_ablation_mode_fails_closed():
    with pytest.raises(DynamicRoleError):
        build_dynamic_role_adjustments(
            _snaps(),
            _current(),
            season=2024,
            week=4,
            team="ARI",
            mode="posthoc_magic",
        )

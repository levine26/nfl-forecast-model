import pandas as pd

from nfl_forecast.props_role_state import (
    build_lagged_snap_route_adjustments,
)


PRIORS = {"RB": 0.55, "WR": 0.90, "TE": 0.75}


def _state():
    return pd.DataFrame(
        [
            {"player_id": "wr1", "position": "WR", "team": "ARI"},
            {"player_id": "rb1", "position": "RB", "team": "ARI"},
            {"player_id": "te1", "position": "TE", "team": "ARI"},
            {"player_id": "qb1", "position": "QB", "team": "ARI"},
        ]
    )


def test_route_adjustment_uses_only_strictly_prior_games():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2026, "week": 1, "player_id": "wr1", "team": "ARI", "offense_pct": 0.80},
            {"game_id": "g2", "season": 2026, "week": 2, "player_id": "wr1", "team": "ARI", "offense_pct": 0.90},
            {"game_id": "g3", "season": 2026, "week": 3, "player_id": "wr1", "team": "ARI", "offense_pct": 0.95},
            {"game_id": "target", "season": 2026, "week": 4, "player_id": "wr1", "team": "ARI", "offense_pct": 0.01},
        ]
    )
    result = build_lagged_snap_route_adjustments(
        snaps,
        _state(),
        season=2026,
        week=4,
        route_prior_means=PRIORS,
    )
    audit = result.audit["players"]["wr1"]
    assert audit["last_evidence_week"] == 3
    assert audit["lagged_games_used"] == 3
    assert abs(audit["mean_lagged_snap_share"] - (0.80 + 0.90 + 0.95) / 3) < 1e-12
    assert result.audit["target_week_rows_used"] == 0


def test_requires_two_positive_prior_games_before_adjusting():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2025, "week": 18, "player_id": "rb1", "team": "ARI", "offense_pct": 0.40},
        ]
    )
    result = build_lagged_snap_route_adjustments(
        snaps,
        _state(),
        season=2026,
        week=1,
        route_prior_means=PRIORS,
    )
    assert "ARI" not in result.adjustments_by_team or "rb1" not in result.adjustments_by_team["ARI"]
    assert result.audit["players"]["rb1"]["status"] == "insufficient_positive_prior_games"


def test_percent_scale_is_normalized_and_only_route_multiplier_changes():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2025, "week": 16, "player_id": "te1", "team": "ARI", "offense_pct": 60.0},
            {"game_id": "g2", "season": 2025, "week": 17, "player_id": "te1", "team": "ARI", "offense_pct": 70.0},
            {"game_id": "g3", "season": 2025, "week": 18, "player_id": "te1", "team": "ARI", "offense_pct": 80.0},
        ]
    )
    result = build_lagged_snap_route_adjustments(
        snaps,
        _state(),
        season=2026,
        week=1,
        route_prior_means=PRIORS,
    )
    adjustment = result.adjustments_by_team["ARI"]["te1"]
    assert set(adjustment) == {"route_role_multiplier"}
    assert abs(adjustment["route_role_multiplier"] - (0.70 / 0.75)) < 1e-12


def test_qb_is_not_route_adjusted():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2025, "week": 17, "player_id": "qb1", "team": "ARI", "offense_pct": 1.0},
            {"game_id": "g2", "season": 2025, "week": 18, "player_id": "qb1", "team": "ARI", "offense_pct": 1.0},
        ]
    )
    result = build_lagged_snap_route_adjustments(
        snaps,
        _state(),
        season=2026,
        week=1,
        route_prior_means=PRIORS,
    )
    assert all("qb1" not in players for players in result.adjustments_by_team.values())

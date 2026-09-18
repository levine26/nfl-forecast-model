import pandas as pd
import pytest

from nfl_forecast.props_opportunity import OpportunityProjection
from nfl_forecast.props_opportunity_handoff import (
    attach_scoring_opportunity_allocations,
    normalize_player_opportunity_history,
)


def _projection():
    return OpportunityProjection(
        metadata={},
        hierarchy={},
        marginals={},
        players=[
            {"player_id": "QB1", "position": "QB"},
            {"player_id": "RB1", "position": "RB"},
            {"player_id": "WR1", "position": "WR"},
            {"player_id": "TE1", "position": "TE"},
        ],
        redistribution={},
        audit={},
    )


def _current_players():
    return pd.DataFrame(
        [
            {"player_id": "QB1", "position": "QB", "availability_probability": 1.0, "availability_uncertainty": 0.0, "role_multiplier": 1.0, "carry_role_multiplier": 1.0, "target_role_multiplier": 1.0},
            {"player_id": "RB1", "position": "RB", "availability_probability": 1.0, "availability_uncertainty": 0.0, "role_multiplier": 1.0, "carry_role_multiplier": 1.0, "target_role_multiplier": 1.0},
            {"player_id": "WR1", "position": "WR", "availability_probability": 1.0, "availability_uncertainty": 0.0, "role_multiplier": 1.0, "carry_role_multiplier": 1.0, "target_role_multiplier": 1.0},
            {"player_id": "TE1", "position": "TE", "availability_probability": 1.0, "availability_uncertainty": 0.0, "role_multiplier": 1.0, "carry_role_multiplier": 1.0, "target_role_multiplier": 1.0},
        ]
    )


def _history():
    rows = []
    for week in (1, 2, 3):
        for player_id, position, rz_carry, gl_carry, rz_target, ez_target in (
            ("QB1", "QB", 1, 1, 0, 0),
            ("RB1", "RB", 4, 2, 1, 0),
            ("WR1", "WR", 0, 0, 3, 2),
            ("TE1", "TE", 0, 0, 2, 1),
        ):
            rows.append(
                {
                    "game_id": f"g{week}",
                    "season": 2025,
                    "week": week,
                    "team": "ARI",
                    "player_id": player_id,
                    "position": position,
                    "red_zone_carries": rz_carry,
                    "goal_line_carries": gl_carry,
                    "red_zone_targets": rz_target,
                    "end_zone_targets": ez_target,
                }
            )
    return pd.DataFrame(rows)


def test_rush_attempt_alias_is_normalized_without_touching_missing_routes():
    history = pd.DataFrame(
        [{"player_id": "RB1", "rush_attempts": 12, "routes": None}]
    )
    history["position"] = "RB"
    out = normalize_player_opportunity_history(history)
    assert out.loc[0, "designed_carries"] == 12
    assert out.loc[0, "designed_carry_source"] == "rush_attempts:non_qb_direct"
    assert pd.isna(out.loc[0, "routes"])


def test_scoring_allocations_include_qb_carries_and_receiver_target_channels():
    projection = attach_scoring_opportunity_allocations(
        _projection(),
        _history(),
        _current_players(),
        half_life_games=8.0,
    )

    goal_line = projection.hierarchy["goal_line_carry_share"]
    assert "QB1" in goal_line["player_ids"]
    assert "RB1" in goal_line["player_ids"]
    assert goal_line["mean_share"]["RB1"] > goal_line["mean_share"]["QB1"]

    end_zone = projection.hierarchy["end_zone_target_share"]
    assert "QB1" not in end_zone["player_ids"]
    assert {"RB1", "WR1", "TE1"}.issubset(end_zone["player_ids"])
    assert projection.players[2]["end_zone_target_share_mean"] > 0

    assert projection.audit["scoring_opportunity_channels"]["goal_line_carry_share"]["status"] == "available"
    assert projection.audit["scoring_opportunity_channels"]["first_read_target_share"]["status"] == "unavailable"


def test_simulation_ready_handoff_runs_end_to_end_with_missing_routes():
    from nfl_forecast.props_opportunity import ForecastContext
    from nfl_forecast.props_opportunity_handoff import build_simulation_ready_opportunity_projection

    team_rows = []
    player_rows = []
    for week in range(1, 7):
        gid = f"2025_{week:02d}_ARI_LA"
        team_rows.append(
            {
                "game_id": gid,
                "season": 2025,
                "week": week,
                "team": "ARI",
                "offensive_plays": 64,
                "dropbacks": 39,
                "pass_attempts": 35,
                "sacks": 2,
                "qb_scrambles": 2,
                "designed_rush_attempts": 25,
                "team_targets": 33,
            }
        )
        for pid, pos, rush, targets, rec, rz_c, gl_c, rz_t, ez_t in (
            ("QB1", "QB", 3, 0, 0, 1, 1, 0, 0),
            ("RB1", "RB", 17, 4, 3, 4, 2, 1, 0),
            ("WR1", "WR", 0, 11, 7, 0, 0, 4, 2),
            ("TE1", "TE", 0, 7, 5, 0, 0, 2, 1),
        ):
            player_rows.append(
                {
                    "game_id": gid,
                    "season": 2025,
                    "week": week,
                    "team": "ARI",
                    "player_id": pid,
                    "position": pos,
                    "rush_attempts": rush,
                    "routes": None,
                    "targets": targets,
                    "receptions": rec,
                    "red_zone_carries": rz_c,
                    "goal_line_carries": gl_c,
                    "red_zone_targets": rz_t,
                    "end_zone_targets": ez_t,
                }
            )

    player_state = pd.DataFrame(
        [
            {"schema_version": "levline_props_player_state.v1", "game_id": "2026_03_LA_ARI", "player_id": "QB1", "player_name": "Quarterback", "position": "QB", "team": "ARI", "expected_active_state": "AVAILABLE", "availability_source_status": "CURRENT_TIMESTAMPED", "expected_role": "QB_PRIMARY"},
            {"schema_version": "levline_props_player_state.v1", "game_id": "2026_03_LA_ARI", "player_id": "RB1", "player_name": "Back", "position": "RB", "team": "ARI", "expected_active_state": "AVAILABLE", "availability_source_status": "CURRENT_TIMESTAMPED", "expected_role": "RB_LEAD"},
            {"schema_version": "levline_props_player_state.v1", "game_id": "2026_03_LA_ARI", "player_id": "WR1", "player_name": "Wide", "position": "WR", "team": "ARI", "expected_active_state": "AVAILABLE", "availability_source_status": "CURRENT_TIMESTAMPED", "expected_role": "WR_PRIMARY"},
            {"schema_version": "levline_props_player_state.v1", "game_id": "2026_03_LA_ARI", "player_id": "TE1", "player_name": "Tight", "position": "TE", "team": "ARI", "expected_active_state": "AVAILABLE", "availability_source_status": "CURRENT_TIMESTAMPED", "expected_role": "TE_PRIMARY"},
        ]
    )
    context = ForecastContext(
        game_id="2026_03_LA_ARI",
        season=2026,
        week=3,
        team="ARI",
        opponent="LA",
        forecast_timestamp="2026-09-17T22:00:00+00:00",
        data_horizon="2026-09-17T22:00:00+00:00",
    )
    projection = build_simulation_ready_opportunity_projection(
        pd.DataFrame(team_rows),
        pd.DataFrame(player_rows),
        player_state,
        context,
        route_prior_means={"RB": 0.55, "WR": 0.90, "TE": 0.70},
    )
    assert projection.marginals["qb_pass_attempts"]["mean"] > 0
    assert projection.hierarchy["goal_line_carry_share"]["mean_share"]["QB1"] > 0
    assert projection.hierarchy["end_zone_target_share"]["mean_share"]["WR1"] > 0
    route_audit = projection.audit["canonical_player_state_adapter"]["route_history"]
    assert set(route_audit["route_prior_only_player_ids"]) == {"RB1", "WR1", "TE1"}
    assert projection.audit["scoring_opportunity_channels"]["end_zone_target_share"]["status"] == "available"


def test_qb_rush_alias_subtracts_team_scrambles():
    history = pd.DataFrame(
        [{"game_id": "g1", "team": "ARI", "player_id": "QB1", "position": "QB", "rush_attempts": 6}]
    )
    team_history = pd.DataFrame(
        [{"game_id": "g1", "team": "ARI", "qb_scrambles": 4}]
    )
    out = normalize_player_opportunity_history(history, team_history=team_history)
    assert out.loc[0, "designed_carries"] == 2
    assert out.loc[0, "designed_carry_source"] == "rush_attempts_minus_team_qb_scrambles"


def test_qb_rush_alias_without_scramble_evidence_fails_closed():
    history = pd.DataFrame(
        [{"game_id": "g1", "team": "ARI", "player_id": "QB1", "position": "QB", "rush_attempts": 3}]
    )
    with pytest.raises(ValueError, match="require qb_scrambles"):
        normalize_player_opportunity_history(history)

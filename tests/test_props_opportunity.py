import math

import pandas as pd
import pytest

from nfl_forecast.props_opportunity import (
    ForecastContext,
    build_opportunity_projection,
    diagnostics_summary,
    rolling_origin_team_diagnostics,
)


def _team_history():
    rows = []
    for week in range(1, 7):
        rows.extend(
            [
                {
                    "game_id": f"2025_{week:02d}_ARI_LA",
                    "season": 2025,
                    "week": week,
                    "team": "ARI",
                    "offensive_plays": 62 + (week % 3),
                    "dropbacks": 37 + (week % 2),
                    "pass_attempts": 34 + (week % 2),
                    "sacks": 2,
                    "qb_scrambles": 1,
                    "designed_rush_attempts": 25,
                    "team_targets": 32 + (week % 2),
                },
                {
                    "game_id": f"2025_{week:02d}_LA_ARI",
                    "season": 2025,
                    "week": week,
                    "team": "LA",
                    "offensive_plays": 64,
                    "dropbacks": 39,
                    "pass_attempts": 36,
                    "sacks": 2,
                    "qb_scrambles": 1,
                    "designed_rush_attempts": 25,
                    "team_targets": 34,
                },
            ]
        )
    rows.extend(
        [
            {
                "game_id": "2026_01_ARI_X",
                "season": 2026,
                "week": 1,
                "team": "ARI",
                "offensive_plays": 66,
                "dropbacks": 40,
                "pass_attempts": 35,
                "sacks": 2,
                "qb_scrambles": 3,
                "designed_rush_attempts": 26,
                "team_targets": 33,
            },
            {
                "game_id": "2026_02_ARI_X",
                "season": 2026,
                "week": 2,
                "team": "ARI",
                "offensive_plays": 65,
                "dropbacks": 39,
                "pass_attempts": 34,
                "sacks": 2,
                "qb_scrambles": 3,
                "designed_rush_attempts": 26,
                "team_targets": 32,
            },
        ]
    )
    return pd.DataFrame(rows)


def _player_history():
    rows = []
    for week in range(1, 7):
        gid = f"2025_{week:02d}_ARI_LA"
        rows.extend(
            [
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "QB1", "position": "QB", "designed_carries": 4, "routes": 0, "targets": 0, "receptions": 0},
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "RB1", "position": "RB", "designed_carries": 15, "routes": 20, "targets": 4, "receptions": 3},
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "RB2", "position": "RB", "designed_carries": 6, "routes": 8, "targets": 2, "receptions": 1},
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "WR1", "position": "WR", "designed_carries": 0, "routes": 35, "targets": 10, "receptions": 7},
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "WR2", "position": "WR", "designed_carries": 0, "routes": 30, "targets": 8, "receptions": 5},
                {"game_id": gid, "season": 2025, "week": week, "team": "ARI", "player_id": "TE1", "position": "TE", "designed_carries": 0, "routes": 24, "targets": 8, "receptions": 6},
            ]
        )
    for week in range(1, 7):
        gid = f"2025_{week:02d}_LA_ARI"
        rows.extend(
            [
                {"game_id": gid, "season": 2025, "week": week, "team": "LA", "player_id": "LARB", "position": "RB", "designed_carries": 18, "routes": 18, "targets": 4, "receptions": 3},
                {"game_id": gid, "season": 2025, "week": week, "team": "LA", "player_id": "LAWR", "position": "WR", "designed_carries": 0, "routes": 36, "targets": 11, "receptions": 7},
                {"game_id": gid, "season": 2025, "week": week, "team": "LA", "player_id": "LATE", "position": "TE", "designed_carries": 0, "routes": 26, "targets": 7, "receptions": 5},
            ]
        )
    return pd.DataFrame(rows)


def _players(wr1_availability=1.0):
    return pd.DataFrame(
        [
            {"player_id": "QB1", "player_name": "Quarterback", "position": "QB", "availability_probability": 1.0, "is_primary_qb": True},
            {"player_id": "RB1", "player_name": "Back One", "position": "RB", "availability_probability": 1.0},
            {"player_id": "RB2", "player_name": "Back Two", "position": "RB", "availability_probability": 1.0},
            {"player_id": "WR1", "player_name": "Wide One", "position": "WR", "availability_probability": wr1_availability},
            {"player_id": "WR2", "player_name": "Wide Two", "position": "WR", "availability_probability": 1.0},
            {"player_id": "TE1", "player_name": "Tight End", "position": "TE", "availability_probability": 1.0},
        ]
    )


def _context():
    return ForecastContext(
        game_id="2026_03_LA_ARI",
        season=2026,
        week=3,
        team="ARI",
        opponent="LA",
        forecast_timestamp="2026-09-17T22:00:00+00:00",
        data_horizon="2026-09-17T22:00:00+00:00",
    )


def test_projection_exposes_required_hierarchy_and_uncertainty():
    projection = build_opportunity_projection(_team_history(), _player_history(), _players(), _context())
    hierarchy = projection.hierarchy
    for key in (
        "team_offensive_plays",
        "dropback_rate_given_team_plays",
        "dropback_outcome_given_dropback",
        "designed_carry_share_given_designed_rush",
        "route_participation_given_dropback",
        "target_share_given_team_target",
        "reception_probability_given_target",
    ):
        assert key in hierarchy

    for key in (
        "team_offensive_plays",
        "qb_dropbacks",
        "qb_pass_attempts",
        "qb_rushing_opportunities",
        "team_rush_attempts",
    ):
        assert projection.marginals[key]["mean"] >= 0
        assert projection.marginals[key]["variance"] >= 0

    assert projection.audit["official_winner_probabilities_modified"] is False
    assert projection.audit["current_game_rows_used"] == 0
    assert projection.marginals["primary_qb_player_id"] == "QB1"


def test_absent_wr_volume_redistributes_across_multiple_receivers_and_routes():
    healthy = build_opportunity_projection(_team_history(), _player_history(), _players(1.0), _context())
    absent = build_opportunity_projection(_team_history(), _player_history(), _players(0.0), _context())

    base = healthy.redistribution["targets"]["post_availability_share"]
    after = absent.redistribution["targets"]["post_availability_share"]
    assert after["WR1"] == 0.0
    gainers = [pid for pid in ("WR2", "TE1", "RB1", "RB2") if after[pid] > base[pid]]
    assert len(gainers) >= 2

    route_before = healthy.redistribution["routes"]["post_availability_participation"]
    route_after = absent.redistribution["routes"]["post_availability_participation"]
    assert route_after["WR1"] == 0.0
    assert route_after["WR2"] >= route_before["WR2"]
    assert route_after["TE1"] >= route_before["TE1"]


def test_leakage_guard_rejects_same_week_history():
    team = _team_history()
    team.loc[len(team)] = {
        "game_id": "2026_03_OTHER",
        "season": 2026,
        "week": 3,
        "team": "ARI",
        "offensive_plays": 60,
        "dropbacks": 35,
        "pass_attempts": 31,
        "sacks": 2,
        "qb_scrambles": 2,
        "designed_rush_attempts": 25,
        "team_targets": 29,
    }
    with pytest.raises(ValueError, match="forecast horizon"):
        build_opportunity_projection(team, _player_history(), _players(), _context())


def test_ambiguous_qb_identity_fails_closed():
    players = _players()
    players.loc[len(players)] = {
        "player_id": "QB2",
        "player_name": "Other QB",
        "position": "QB",
        "availability_probability": 1.0,
        "is_primary_qb": True,
    }
    with pytest.raises(ValueError, match="Multiple players marked"):
        build_opportunity_projection(_team_history(), _player_history(), players, _context())


def test_roll_forward_diagnostics_exclude_2026_by_default():
    diagnostics = rolling_origin_team_diagnostics(
        _team_history(),
        _player_history(),
        minimum_prior_games=2,
    )
    assert not diagnostics.empty
    assert not (diagnostics["season"] == 2026).any()
    summary = diagnostics_summary(diagnostics)
    assert summary["rows"] == len(diagnostics)
    assert math.isfinite(summary["team_plays_mae"])
    assert summary["excluded_2026_for_selection_safety"] is True


def test_non_neutral_context_adjustment_requires_provenance():
    context = _context()
    context = ForecastContext(**{**context.__dict__, "dropback_logit_delta": 0.1})
    with pytest.raises(ValueError, match="adjustments_provenance"):
        build_opportunity_projection(_team_history(), _player_history(), _players(), context)


def test_play_volume_uncertainty_changes_sampling_parameters():
    base = build_opportunity_projection(
        _team_history(), _player_history(), _players(), _context()
    )
    context = ForecastContext(
        **{
            **_context().__dict__,
            "play_volume_uncertainty_multiplier": 2.0,
            "adjustments_provenance": "preregistered uncertainty stress test",
        }
    )
    wider = build_opportunity_projection(
        _team_history(), _player_history(), _players(), context
    )
    base_plays = base.hierarchy["team_offensive_plays"]
    wide_plays = wider.hierarchy["team_offensive_plays"]
    assert wide_plays["mean"] == pytest.approx(base_plays["mean"])
    assert wide_plays["variance"] > base_plays["variance"]
    assert wide_plays["gamma_shape"] < base_plays["gamma_shape"]
    assert wide_plays["gamma_rate"] < base_plays["gamma_rate"]


def test_generic_carries_are_rejected_to_prevent_qb_scramble_double_count():
    unsafe = _player_history().rename(columns={"designed_carries": "carries"})
    with pytest.raises(ValueError, match="designed_carries"):
        build_opportunity_projection(_team_history(), unsafe, _players(), _context())

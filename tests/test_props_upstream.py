from __future__ import annotations

import pandas as pd
import pytest

from nfl_forecast.props_upstream import (
    EFFICIENCY_PRIOR_FIELDS,
    PropsUpstreamError,
    build_efficiency_baselines,
    build_game_upstream_package,
    build_lagged_props_history,
)


GAME_ID = "2026_03_LAR_ARI"
KICKOFF = "2026-09-20T20:05:00Z"
FORECAST = "2026-09-17T22:00:00Z"


def _identity():
    return pd.DataFrame(
        [
            {"gsis_id": "A-QB", "position": "QB"},
            {"gsis_id": "A-RB", "position": "RB"},
            {"gsis_id": "A-WR", "position": "WR"},
            {"gsis_id": "A-TE", "position": "TE"},
            {"gsis_id": "L-QB", "position": "QB"},
            {"gsis_id": "L-RB", "position": "RB"},
            {"gsis_id": "L-WR", "position": "WR"},
            {"gsis_id": "L-TE", "position": "TE"},
        ]
    )


def _play(
    *,
    game_id,
    season,
    week,
    team,
    passer="",
    rusher="",
    receiver="",
    pass_attempt=0,
    rush_attempt=0,
    qb_scramble=0,
    complete_pass=0,
    sack=0,
    passing_yards=0,
    rushing_yards=0,
    receiving_yards=0,
    yardline_100=50,
    air_yards=0,
):
    return {
        "game_id": game_id,
        "season": season,
        "week": week,
        "posteam": team,
        "passer_player_id": passer,
        "rusher_player_id": rusher,
        "receiver_player_id": receiver,
        "pass_attempt": pass_attempt,
        "rush_attempt": rush_attempt,
        "qb_scramble": qb_scramble,
        "complete_pass": complete_pass,
        "sack": sack,
        "passing_yards": passing_yards,
        "rushing_yards": rushing_yards,
        "receiving_yards": receiving_yards,
        "yardline_100": yardline_100,
        "air_yards": air_yards,
    }


def _pbp():
    rows = []
    for week in (1, 2):
        for team, qb, rb, wr, te, opponent in (
            ("ARI", "A-QB", "A-RB", "A-WR", "A-TE", "LAR"),
            ("LAR", "L-QB", "L-RB", "L-WR", "L-TE", "ARI"),
        ):
            gid = f"2026_{week:02d}_{team}_{opponent}"
            rows.extend(
                [
                    _play(
                        game_id=gid, season=2026, week=week, team=team,
                        passer=qb, receiver=wr, pass_attempt=1, complete_pass=1,
                        passing_yards=18, receiving_yards=18, yardline_100=18, air_yards=9,
                    ),
                    _play(
                        game_id=gid, season=2026, week=week, team=team,
                        passer=qb, receiver=te, pass_attempt=1, complete_pass=1,
                        passing_yards=12, receiving_yards=12, yardline_100=8, air_yards=9,
                    ),
                    _play(
                        game_id=gid, season=2026, week=week, team=team,
                        passer=qb, receiver=rb, pass_attempt=1, complete_pass=0,
                        passing_yards=0, receiving_yards=0, yardline_100=35, air_yards=2,
                    ),
                    _play(
                        game_id=gid, season=2026, week=week, team=team,
                        rusher=rb, rush_attempt=1, rushing_yards=7, yardline_100=4,
                    ),
                    _play(
                        game_id=gid, season=2026, week=week, team=team,
                        rusher=qb, rush_attempt=1, qb_scramble=1, rushing_yards=6, yardline_100=30,
                    ),
                ]
            )
    # Target-week rows are poison-pill data: they must never enter a Week 3 build.
    rows.append(
        _play(
            game_id=GAME_ID, season=2026, week=3, team="ARI",
            passer="A-QB", receiver="A-WR", pass_attempt=1, complete_pass=1,
            passing_yards=99, receiving_yards=99,
        )
    )
    return pd.DataFrame(rows)


def _player_state():
    rows = []
    for team, opponent, prefix in (("ARI", "LAR", "A"), ("LAR", "ARI", "L")):
        for suffix, position in (("QB", "QB"), ("RB", "RB"), ("WR", "WR"), ("TE", "TE")):
            rows.append(
                {
                    "schema_version": "levline_props_player_state.v1",
                    "game_id": GAME_ID,
                    "player_id": f"{prefix}-{suffix}",
                    "player_name": f"{team} {suffix}",
                    "position": position,
                    "team": team,
                    "opponent": opponent,
                    "kickoff_timestamp": KICKOFF,
                    "expected_active_state": "AVAILABLE",
                    "availability_source_status": "PROSPECTIVE",
                    "expected_role": "UNKNOWN",
                }
            )
    return pd.DataFrame(rows)


def _priors():
    base = {
        "prior_completion_rate": 0.64,
        "prior_yards_per_completion_mean": 11.2,
        "prior_yards_per_completion_sd": 6.0,
        "prior_qb_rush_ypc_mean": 5.0,
        "prior_qb_rush_ypc_sd": 4.0,
        "prior_rush_ypc_mean": 4.3,
        "prior_rush_ypc_sd": 3.8,
        "prior_catch_rate": 0.68,
        "prior_receiving_ypr_mean": 10.5,
        "prior_receiving_ypr_sd": 6.0,
        "prior_red_zone_target_rate": 0.14,
        "prior_end_zone_target_rate": 0.07,
        "prior_goal_line_carry_rate": 0.08,
    }
    assert set(base) == EFFICIENCY_PRIOR_FIELDS
    return {position: dict(base) for position in ("QB", "RB", "WR", "TE")}


def test_lagged_history_excludes_target_week_and_separates_qb_scrambles():
    history = build_lagged_props_history(_pbp(), _identity(), season=2026, week=3)

    assert history.audit["target_week_rows_used"] == 0
    assert history.audit["historical_max_period_used"] == {"season": 2026, "week": 2}
    ari = history.team_history[history.team_history["team"].eq("ARI")]
    assert len(ari) == 2
    assert ari["pass_attempts"].tolist() == [3.0, 3.0]
    assert ari["qb_scrambles"].tolist() == [1.0, 1.0]
    assert ari["designed_rush_attempts"].tolist() == [1.0, 1.0]
    assert ari["dropbacks"].tolist() == [4.0, 4.0]
    assert ari["offensive_plays"].tolist() == [5.0, 5.0]

    qb = history.player_history[history.player_history["player_id"].eq("A-QB")]
    assert qb["qb_scrambles"].sum() == 2.0
    assert qb["designed_carries"].sum() == 0.0

    eff = history.efficiency_history.set_index("player_id")
    assert eff.loc["A-QB", "hist_passing_yards"] == 60.0
    assert eff.loc["A-QB", "hist_qb_rush_attempts"] == 2.0
    assert eff.loc["A-WR", "hist_receiving_yards"] == 36.0
    assert eff.loc["A-WR", "hist_receiving_yards"] != 135.0


def test_history_refuses_missing_scramble_evidence():
    bad = _pbp().drop(columns=["qb_scramble"])
    with pytest.raises(PropsUpstreamError, match="qb_scramble"):
        build_lagged_props_history(bad, _identity(), season=2026, week=3)


def test_efficiency_baselines_require_explicit_position_priors():
    history = build_lagged_props_history(_pbp(), _identity(), season=2026, week=3)
    with pytest.raises(PropsUpstreamError, match="missing explicit efficiency priors"):
        build_efficiency_baselines(
            projection_players=[{"player_id": "A-QB", "position": "QB"}],
            efficiency_history=history.efficiency_history,
            position_priors={},
        )


def test_game_upstream_package_runs_real_lane_interfaces_without_hidden_defaults():
    history = build_lagged_props_history(_pbp(), _identity(), season=2026, week=3)
    scoring = {
        team: {
            "expected_drives": 10.5,
            "expected_red_zone_trips": 3.2,
            "prior_red_zone_td_rate": 0.58,
            "prior_pass_td_fraction": 0.62,
            "expected_non_red_zone_pass_tds": 0.2,
            "expected_non_red_zone_rush_tds": 0.08,
        }
        for team in ("ARI", "LAR")
    }
    residual = {
        team: {
            "catch_rate": 0.62,
            "receiving_yards_per_reception": 9.5,
            "rushing_yards_per_carry": 4.0,
        }
        for team in ("ARI", "LAR")
    }

    package = build_game_upstream_package(
        player_state=_player_state(),
        history=history,
        game_id=GAME_ID,
        season=2026,
        week=3,
        forecast_timestamp=FORECAST,
        route_prior_means={"RB": 0.55, "WR": 0.90, "TE": 0.75},
        availability_priors={},
        position_efficiency_priors=_priors(),
        scoring_context_by_team=scoring,
        residual_efficiency_by_team=residual,
        source_status="qualified",
        prior_model_trained_through_season=2025,
        primary_qb_by_team={
            "ARI": {"player_id": "A-QB", "provenance": "pregame starter fixture"},
            "LAR": {"player_id": "L-QB", "provenance": "pregame starter fixture"},
        },
    )

    assert package.game_id == GAME_ID
    assert len(package.opportunity_projections) == 2
    assert len(package.team_td_parameters) == 2
    assert len(package.efficiency_player_parameters) == 8
    assert set(package.residual_efficiency_by_team) == {"ARI", "LAR"}
    assert package.audit["efficiency_td"]["td_reconciliation_failures"] == 0
    assert package.audit["history"]["target_week_rows_used"] == 0


def test_2026_trained_priors_fail_closed_before_lane_build():
    history = build_lagged_props_history(_pbp(), _identity(), season=2026, week=3)
    with pytest.raises(PropsUpstreamError, match="2026 outcomes"):
        build_game_upstream_package(
            player_state=_player_state(),
            history=history,
            game_id=GAME_ID,
            season=2026,
            week=3,
            forecast_timestamp=FORECAST,
            route_prior_means={"RB": 0.55, "WR": 0.90, "TE": 0.75},
            availability_priors={},
            position_efficiency_priors=_priors(),
            scoring_context_by_team={},
            residual_efficiency_by_team={},
            source_status="qualified",
            prior_model_trained_through_season=2026,
            primary_qb_by_team={},
        )


def test_missing_scoring_area_columns_degrade_to_zero_without_crash():
    pbp = _pbp().drop(columns=["yardline_100", "air_yards"])
    history = build_lagged_props_history(pbp, _identity(), season=2026, week=3)
    assert history.player_history["red_zone_targets"].sum() == 0.0
    assert history.player_history["end_zone_targets"].sum() == 0.0
    assert history.player_history["goal_line_carries"].sum() == 0.0

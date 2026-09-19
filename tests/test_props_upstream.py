from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from nfl_forecast.props_upstream import (
    EFFICIENCY_PRIOR_FIELDS,
    PropsUpstreamError,
    build_efficiency_baselines,
    build_empirical_scoring_context,
    build_game_upstream_package,
    build_lagged_props_history,
    fit_pre2026_efficiency_priors,
    fit_pre2026_injury_availability_priors,
    normalize_nflverse_scramble_semantics,
    residual_efficiency_by_team_from_empirical_priors,
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
    drive=1,
    pass_touchdown=0,
    rush_touchdown=0,
    season_type="REG",
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
        "drive": drive,
        "pass_touchdown": pass_touchdown,
        "rush_touchdown": rush_touchdown,
        "season_type": season_type,
    }


def test_nflverse_scramble_normalization_uses_rusher_then_passer_fallback():
    frame = pd.DataFrame(
        [
            _play(
                game_id="2026_01_ARI_LAR",
                season=2026,
                week=1,
                team="ARI",
                passer="A-QB",
                rusher="",
                rush_attempt=0,
                qb_scramble=1,
                rushing_yards=0,
            ),
            _play(
                game_id="2026_01_ARI_LAR",
                season=2026,
                week=1,
                team="ARI",
                passer="",
                rusher="A-QB",
                rush_attempt=1,
                qb_scramble=1,
                rushing_yards=7,
            ),
            _play(
                game_id="2026_01_ARI_LAR",
                season=2026,
                week=1,
                team="ARI",
                passer="L-QB",
                rusher="",
                rush_attempt=1,
                qb_scramble=1,
                rushing_yards=5,
            ),
            _play(
                game_id="2026_01_ARI_LAR",
                season=2026,
                week=1,
                team="ARI",
                rusher="A-RB",
                rush_attempt=0,
                qb_scramble=0,
                rushing_yards=0,
            ),
        ]
    )

    normalized, audit = normalize_nflverse_scramble_semantics(frame)

    assert normalized.loc[0, "rush_attempt"] == 0
    assert normalized.loc[0, "qb_scramble"] == 0
    assert normalized.loc[1, "rush_attempt"] == 1
    assert normalized.loc[1, "qb_scramble"] == 1
    assert normalized.loc[1, "rusher_player_id"] == "A-QB"
    assert normalized.loc[2, "rusher_player_id"] == "L-QB"
    assert normalized.loc[3, "rush_attempt"] == 0
    assert normalized.loc[3, "rusher_player_id"] == "A-RB"
    assert audit["raw_scramble_rows"] == 3
    assert audit["countable_scramble_rows"] == 2
    assert audit["non_statistical_scramble_labels_suppressed"] == 1
    assert audit["rush_attempt_promotions"] == 0
    assert audit["countable_scrambles_with_existing_rusher_id"] == 1
    assert audit["rusher_identity_repairs_from_passer"] == 1
    assert audit["non_scramble_rows_modified"] == 0
    assert audit["outcome_or_market_fields_used_for_repair"] is False


def test_nflverse_scramble_normalization_refuses_only_when_all_identity_missing():
    frame = pd.DataFrame(
        [
            _play(
                game_id="2026_01_ARI_LAR",
                season=2026,
                week=1,
                team="ARI",
                passer="",
                rusher="",
                rush_attempt=1,
                qb_scramble=1,
                rushing_yards=4,
            )
        ]
    )
    with pytest.raises(PropsUpstreamError, match="missing stable rusher/QB identity"):
        normalize_nflverse_scramble_semantics(frame)


def test_core_history_still_refuses_unadapted_scramble_mismatch():
    frame = _pbp()
    scramble_index = frame.index[frame["qb_scramble"].eq(1)][0]
    frame.loc[scramble_index, "rush_attempt"] = 0
    with pytest.raises(PropsUpstreamError, match="qb_scramble rows"):
        build_lagged_props_history(frame, _identity(), season=2026, week=3)



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



def _training_pbp():
    rows = []
    for week in (1, 2):
        for team, qb, rb, wr, te, opponent in (
            ("ARI", "A-QB", "A-RB", "A-WR", "A-TE", "LAR"),
            ("LAR", "L-QB", "L-RB", "L-WR", "L-TE", "ARI"),
        ):
            gid = f"2025_{week:02d}_{team}_{opponent}"
            rows.extend(
                [
                    _play(
                        game_id=gid, season=2025, week=week, team=team,
                        passer=qb, receiver=wr, pass_attempt=1, complete_pass=1,
                        passing_yards=31, receiving_yards=31, yardline_100=31,
                        air_yards=18, drive=1, pass_touchdown=1,
                    ),
                    _play(
                        game_id=gid, season=2025, week=week, team=team,
                        passer=qb, receiver=te, pass_attempt=1, complete_pass=1,
                        passing_yards=11, receiving_yards=11, yardline_100=15,
                        air_yards=8, drive=2,
                    ),
                    _play(
                        game_id=gid, season=2025, week=week, team=team,
                        rusher=rb, rush_attempt=1, rushing_yards=4, yardline_100=4,
                        drive=2, rush_touchdown=1,
                    ),
                    _play(
                        game_id=gid, season=2025, week=week, team=team,
                        passer=qb, receiver=rb, pass_attempt=1, complete_pass=0,
                        yardline_100=45, air_yards=4, drive=3,
                    ),
                    _play(
                        game_id=gid, season=2025, week=week, team=team,
                        rusher=qb, rush_attempt=1, qb_scramble=1, rushing_yards=5,
                        yardline_100=40, drive=4,
                    ),
                ]
            )
    return pd.DataFrame(rows)


def _combined_pbp():
    return pd.concat([_training_pbp(), _pbp()], ignore_index=True)

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



def test_replacement_qb_override_propagates_into_opportunity_package():
    history = build_lagged_props_history(_pbp(), _identity(), season=2026, week=3)
    state = _player_state().copy()
    backup = state[
        state["player_id"].eq("A-QB")
    ].iloc[0].to_dict()
    backup["player_id"] = "A-QB2"
    backup["player_name"] = "ARI Backup QB"
    backup["expected_role"] = "QB_RESERVE"
    state = pd.concat([state, pd.DataFrame([backup])], ignore_index=True)

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
        player_state=state,
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
            "ARI": {
                "player_id": "A-QB2",
                "provenance": "qualified shared LevLine starter reporting",
            },
            "LAR": {"player_id": "L-QB", "provenance": "pregame starter fixture"},
        },
    )

    ari = next(
        projection
        for projection in package.opportunity_projections
        if projection["metadata"]["team"] == "ARI"
    )
    assert ari["marginals"]["primary_qb_player_id"] == "A-QB2"
    players = {row["player_id"]: row for row in ari["players"]}
    assert players["A-QB2"]["is_primary_qb"] is True
    assert players["A-QB"]["is_primary_qb"] is False
    assert ari["marginals"]["qb_pass_attempts"]["mean"] > 0

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



def test_pre2026_empirical_priors_ignore_all_2026_outcomes():
    base = _combined_pbp()
    fitted = fit_pre2026_efficiency_priors(base, _identity())

    poisoned = base.copy()
    mask_2026 = poisoned["season"].eq(2026)
    poisoned.loc[mask_2026, "passing_yards"] = 9999
    poisoned.loc[mask_2026, "rushing_yards"] = 9999
    poisoned.loc[mask_2026, "receiving_yards"] = 9999
    poisoned.loc[mask_2026, "complete_pass"] = 1
    poisoned_fit = fit_pre2026_efficiency_priors(poisoned, _identity())

    assert fitted["trained_through_season"] == 2025
    assert fitted["efficiency_position_priors"] == poisoned_fit["efficiency_position_priors"]
    assert fitted["residual_efficiency"] == poisoned_fit["residual_efficiency"]
    assert fitted["audit"]["completed_2026_outcomes_used_for_prior_fit"] == 0
    for position in ("QB", "RB", "WR", "TE"):
        assert set(fitted["efficiency_position_priors"][position]) == EFFICIENCY_PRIOR_FIELDS


def test_empirical_scoring_uses_pre2026_conversion_priors_but_prior_week_live_state():
    base = _combined_pbp()
    context = build_empirical_scoring_context(
        base,
        teams=["ARI", "LAR"],
        season=2026,
        week=3,
    )
    ari = context["scoring_context_by_team"]["ARI"]
    assert ari["expected_drives"] > 0
    assert 0 < ari["prior_red_zone_td_rate"] < 1
    assert 0 < ari["prior_pass_td_fraction"] < 1
    assert context["audit"]["completed_2026_outcomes_used_for_prior_fit"] == 0
    assert context["audit"]["prior_2026_games_allowed_for_chronological_team_state"] is True

    poisoned = base.copy()
    mask_2026 = poisoned["season"].eq(2026)
    poisoned.loc[mask_2026, "pass_touchdown"] = 1
    poisoned.loc[mask_2026, "rush_touchdown"] = 1
    poisoned_context = build_empirical_scoring_context(
        poisoned,
        teams=["ARI", "LAR"],
        season=2026,
        week=3,
    )
    poisoned_ari = poisoned_context["scoring_context_by_team"]["ARI"]
    assert poisoned_ari["prior_red_zone_td_rate"] == ari["prior_red_zone_td_rate"]
    assert poisoned_ari["prior_pass_td_fraction"] == ari["prior_pass_td_fraction"]
    # Chronological state is allowed to change from completed prior-week 2026 games.
    assert (
        poisoned_ari["expected_non_red_zone_pass_tds"]
        != ari["expected_non_red_zone_pass_tds"]
    )


def test_empirical_scoring_excludes_target_week_poison_rows():
    base = _combined_pbp()
    context = build_empirical_scoring_context(
        base,
        teams=["ARI"],
        season=2026,
        week=3,
    )
    with_poison = base.copy()
    poison = _play(
        game_id=GAME_ID,
        season=2026,
        week=3,
        team="ARI",
        passer="A-QB",
        receiver="A-WR",
        pass_attempt=1,
        complete_pass=1,
        passing_yards=500,
        receiving_yards=500,
        yardline_100=50,
        air_yards=50,
        drive=99,
        pass_touchdown=1,
    )
    with_poison = pd.concat([with_poison, pd.DataFrame([poison])], ignore_index=True)
    poisoned = build_empirical_scoring_context(
        with_poison,
        teams=["ARI"],
        season=2026,
        week=3,
    )
    assert poisoned["scoring_context_by_team"] == context["scoring_context_by_team"]


def test_residual_efficiency_is_derived_from_pre2026_empirical_priors():
    fitted = fit_pre2026_efficiency_priors(_combined_pbp(), _identity())
    residual = residual_efficiency_by_team_from_empirical_priors(
        ["ARI", "LAR"],
        fitted,
    )
    assert set(residual) == {"ARI", "LAR"}
    assert residual["ARI"] == residual["LAR"]
    assert 0 < residual["ARI"]["catch_rate"] < 1



def test_historical_injury_availability_priors_use_only_pre2026_snap_outcomes():
    injuries = pd.DataFrame(
        [
            {
                "season": 2024,
                "season_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "A-WR",
                "position": "WR",
                "report_status": "Questionable",
                "date_modified": "2024-09-05T18:00:00Z",
            },
            {
                "season": 2024,
                "season_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "A-WR",
                "position": "WR",
                "report_status": "Questionable",
                "date_modified": "2024-09-12T18:00:00Z",
            },
            {
                "season": 2024,
                "season_type": "REG",
                "week": 3,
                "team": "LAR",
                "gsis_id": "L-RB",
                "position": "RB",
                "report_status": "Doubtful",
                "date_modified": "2024-09-19T18:00:00Z",
            },
            {
                "season": 2026,
                "season_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "A-WR",
                "position": "WR",
                "report_status": "Questionable",
                "date_modified": "2026-09-05T18:00:00Z",
            },
        ]
    )
    snaps = pd.DataFrame(
        [
            {
                "season": 2024, "week": 1, "team": "ARI", "player_id": "A-WR",
                "offense_snaps": 55, "game_type": "REG",
            },
            {
                "season": 2024, "week": 2, "team": "ARI", "player_id": "OTHER",
                "offense_snaps": 60, "game_type": "REG",
            },
            {
                "season": 2024, "week": 3, "team": "LAR", "player_id": "OTHER",
                "offense_snaps": 60, "game_type": "REG",
            },
            {
                "season": 2026, "week": 1, "team": "ARI", "player_id": "A-WR",
                "offense_snaps": 99, "game_type": "REG",
            },
        ]
    )

    fitted = fit_pre2026_injury_availability_priors(
        injuries,
        snaps,
        trained_through_season=2024,
    )
    q = fitted["availability_beta_priors"]["QUESTIONABLE"]
    d = fitted["availability_beta_priors"]["DOUBTFUL"]
    assert q == {"alpha": 2.0, "beta": 2.0}
    assert d == {"alpha": 1.0, "beta": 2.0}
    assert fitted["audit"]["states"]["QUESTIONABLE"]["observations"] == 2
    assert fitted["audit"]["states"]["DOUBTFUL"]["observations"] == 1
    assert fitted["audit"]["completed_2026_outcomes_used_for_prior_fit"] == 0


def test_injury_availability_fit_drops_team_weeks_without_snap_source_coverage():
    injuries = pd.DataFrame(
        [
            {
                "season": 2024,
                "week": 1,
                "team": "ARI",
                "gsis_id": "A-WR",
                "position": "WR",
                "report_status": "Questionable",
            },
            {
                "season": 2024,
                "week": 2,
                "team": "LAR",
                "gsis_id": "L-WR",
                "position": "WR",
                "report_status": "Questionable",
            },
        ]
    )
    snaps = pd.DataFrame(
        [
            {
                "season": 2024,
                "week": 1,
                "team": "ARI",
                "player_id": "A-WR",
                "offense_snaps": 10,
            }
        ]
    )
    fitted = fit_pre2026_injury_availability_priors(injuries, snaps)
    assert fitted["audit"]["uncovered_team_week_rows_dropped"] == 1
    assert fitted["availability_beta_priors"]["QUESTIONABLE"] == {
        "alpha": 2.0,
        "beta": 1.0,
    }


def test_injury_availability_fit_rejects_2026_training_horizon():
    with pytest.raises(PropsUpstreamError, match="2026 outcomes"):
        fit_pre2026_injury_availability_priors(
            pd.DataFrame(),
            pd.DataFrame(),
            trained_through_season=2026,
        )



def test_non_red_zone_tds_do_not_contaminate_red_zone_pass_fraction_prior():
    base = _combined_pbp()
    baseline = build_empirical_scoring_context(
        base,
        teams=["ARI"],
        season=2026,
        week=3,
    )
    extra = []
    for idx in range(20):
        extra.append(
            _play(
                game_id=f"2025_10_ARI_LAR_{idx}",
                season=2025,
                week=10,
                team="ARI",
                passer="A-QB",
                receiver="A-WR",
                pass_attempt=1,
                complete_pass=1,
                passing_yards=60,
                receiving_yards=60,
                yardline_100=60,
                air_yards=60,
                drive=idx + 1,
                pass_touchdown=1,
            )
        )
    poisoned = pd.concat([base, pd.DataFrame(extra)], ignore_index=True)
    changed = build_empirical_scoring_context(
        poisoned,
        teams=["ARI"],
        season=2026,
        week=3,
    )
    assert (
        changed["scoring_context_by_team"]["ARI"]["prior_pass_td_fraction"]
        == baseline["scoring_context_by_team"]["ARI"]["prior_pass_td_fraction"]
    )



ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_SCRIPT = ROOT / "scripts" / "build_props_upstream_snapshot.py"


def _upstream_cli_module():
    spec = importlib.util.spec_from_file_location(
        "build_props_upstream_snapshot_tested",
        UPSTREAM_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cli_player_state():
    rows = []
    for game_id, home, away in (
        ("g1", "ARI", "LAR"),
        ("g2", "BUF", "MIA"),
    ):
        for team, opponent, prefix in (
            (home, away, home),
            (away, home, away),
        ):
            rows.append(
                {
                    "game_id": game_id,
                    "player_id": f"{prefix}-QB",
                    "player_name": f"{team} QB",
                    "position": "QB",
                    "team": team,
                    "opponent": opponent,
                    "kickoff_timestamp": KICKOFF,
                }
            )
    return pd.DataFrame(rows)


def _cli_package(game_id):
    return SimpleNamespace(
        game_id=game_id,
        opportunity_projections=(
            {"metadata": {"game_id": game_id, "team": "T1"}},
            {"metadata": {"game_id": game_id, "team": "T2"}},
        ),
        efficiency_player_parameters=({"game_id": game_id, "player_id": "p"},),
        team_td_parameters=({"game_id": game_id, "team": "T1"}, {"game_id": game_id, "team": "T2"}),
        residual_efficiency_by_team={"T1": {}, "T2": {}},
        audit={"ok": True},
    )


def _patch_upstream_cli(monkeypatch, module, *, fail_game=None):
    state = _cli_player_state()
    schedules = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "home_team": "ARI",
                "away_team": "LA",
                "kickoff": KICKOFF,
            },
            {
                "game_id": "g2",
                "home_team": "BUF",
                "away_team": "MIA",
                "kickoff": KICKOFF,
            },
        ]
    )
    monkeypatch.setattr(
        module,
        "load_offensive_props_sources",
        lambda **kwargs: SimpleNamespace(
            schedules=schedules,
            roster=pd.DataFrame(),
            pbp=pd.DataFrame(
                columns=[
                    "qb_scramble",
                    "rush_attempt",
                    "rushing_yards",
                    "passer_player_id",
                    "rusher_player_id",
                ]
            ),
            snap_counts=None,
            depth_charts=None,
            routes=None,
            source_status={"test": "qualified"},
        ),
    )
    monkeypatch.setattr(
        module.nfl,
        "load_players",
        lambda: pd.DataFrame([{"gsis_id": "p", "position": "QB"}]),
    )
    monkeypatch.setattr(
        module.nfl,
        "load_injuries",
        lambda seasons: (_ for _ in ()).throw(RuntimeError("offline fixture")),
    )
    monkeypatch.setattr(
        module,
        "build_offensive_player_state_contract",
        lambda **kwargs: SimpleNamespace(
            player_state=state,
            audit={"state": "qualified"},
        ),
    )
    monkeypatch.setattr(
        module,
        "build_lagged_props_history",
        lambda *args, **kwargs: SimpleNamespace(audit={"history": "qualified"}),
    )
    monkeypatch.setattr(
        module,
        "fit_pre2026_efficiency_priors",
        lambda *args, **kwargs: {
            "trained_through_season": 2025,
            "efficiency_position_priors": {"QB": {}},
            "residual_efficiency": {
                "catch_rate": 0.6,
                "receiving_yards_per_reception": 10.0,
                "rushing_yards_per_carry": 4.0,
            },
            "audit": {"fit": "qualified"},
        },
    )
    monkeypatch.setattr(
        module,
        "resolve_primary_qbs_from_depth_charts",
        lambda *args, **kwargs: ({}, {"status": "missing"}),
    )
    monkeypatch.setattr(
        module,
        "build_empirical_scoring_context",
        lambda pbp, *, teams, **kwargs: {
            "scoring_context_by_team": {
                team: {
                    "expected_drives": 10.0,
                    "expected_red_zone_trips": 3.0,
                    "prior_red_zone_td_rate": 0.55,
                    "prior_pass_td_fraction": 0.6,
                    "expected_non_red_zone_pass_tds": 0.2,
                    "expected_non_red_zone_rush_tds": 0.1,
                }
                for team in teams
            },
            "audit": {"scoring": "qualified"},
        },
    )
    monkeypatch.setattr(
        module,
        "residual_efficiency_by_team_from_empirical_priors",
        lambda teams, fitted: {
            team: {
                "catch_rate": 0.6,
                "receiving_yards_per_reception": 10.0,
                "rushing_yards_per_carry": 4.0,
            }
            for team in teams
        },
    )

    calls = []

    def build_package(**kwargs):
        game_id = kwargs["game_id"]
        calls.append(game_id)
        if game_id == fail_game:
            raise PropsUpstreamError("fixture game failure")
        return _cli_package(game_id)

    monkeypatch.setattr(module, "build_game_upstream_package", build_package)
    monkeypatch.setattr(
        module,
        "_schedule_game",
        lambda schedules, game_id: (
            ("ARI", "LAR", KICKOFF)
            if game_id == "g1"
            else ("BUF", "MIA", KICKOFF)
        ),
    )
    return calls


def test_all_games_cli_builds_one_atomic_upstream_slate(monkeypatch, tmp_path):
    module = _upstream_cli_module()
    calls = _patch_upstream_cli(monkeypatch, module)
    priors_path = tmp_path / "priors.json"
    priors_path.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.5, "WR": 0.9, "TE": 0.7},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 1.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "upstream"
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            str(UPSTREAM_SCRIPT),
            "--season",
            "2026",
            "--week",
            "3",
            "--all-games",
            "--priors",
            str(priors_path),
            "--output-dir",
            str(output),
            "--skip-injury-fetch",
        ],
    )

    assert module.main() == 0
    assert calls == ["g1", "g2"]
    index = json.loads((output / "upstream_slate.json").read_text(encoding="utf-8"))
    assert index["game_count"] == 2
    assert [row["game_id"] for row in index["games"]] == ["g1", "g2"]
    assert (output / "player_state.json").exists()
    assert (output / "games" / "g1" / "g1.game_spec.json").exists()
    assert (output / "games" / "g2" / "g2.game_spec.json").exists()


def test_all_games_cli_failure_writes_no_partial_slate(monkeypatch, tmp_path):
    module = _upstream_cli_module()
    _patch_upstream_cli(monkeypatch, module, fail_game="g2")
    priors_path = tmp_path / "priors.json"
    priors_path.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.5, "WR": 0.9, "TE": 0.7},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 1.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "upstream"
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            str(UPSTREAM_SCRIPT),
            "--season",
            "2026",
            "--week",
            "3",
            "--all-games",
            "--priors",
            str(priors_path),
            "--output-dir",
            str(output),
            "--skip-injury-fetch",
        ],
    )

    with pytest.raises(PropsUpstreamError, match="fixture game failure"):
        module.main()
    assert not output.exists()



def test_scheduled_pregame_game_ids_exclude_already_started_games():
    module = _upstream_cli_module()
    schedules = pd.DataFrame(
        [
            {
                "season": 2026,
                "week": 3,
                "game_id": "thu",
                "kickoff": "2026-09-18T00:00:00Z",
            },
            {
                "season": 2026,
                "week": 3,
                "game_id": "sun",
                "kickoff": "2026-09-20T20:00:00Z",
            },
        ]
    )
    pregame, started = module._scheduled_pregame_game_ids(
        schedules,
        season=2026,
        week=3,
        forecast_timestamp=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
    )
    assert pregame == ["sun"]
    assert started == ["thu"]


def test_all_games_cli_fails_if_upcoming_schedule_game_has_no_player_state(
    monkeypatch,
    tmp_path,
):
    module = _upstream_cli_module()
    _patch_upstream_cli(monkeypatch, module)
    original_loader = module.load_offensive_props_sources

    def loader_with_missing_state_game(**kwargs):
        sources = original_loader(**kwargs)
        schedules = pd.concat(
            [
                sources.schedules,
                pd.DataFrame(
                    [
                        {
                            "game_id": "g3",
                            "home_team": "SEA",
                            "away_team": "SF",
                            "kickoff": KICKOFF,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        return SimpleNamespace(**{**sources.__dict__, "schedules": schedules})

    monkeypatch.setattr(module, "load_offensive_props_sources", loader_with_missing_state_game)
    priors_path = tmp_path / "priors.json"
    priors_path.write_text(
        json.dumps(
            {
                "route_prior_means": {"RB": 0.5, "WR": 0.9, "TE": 0.7},
                "availability_beta_priors": {
                    "UNKNOWN": {"alpha": 1.0, "beta": 1.0}
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "upstream"
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            str(UPSTREAM_SCRIPT),
            "--season",
            "2026",
            "--week",
            "3",
            "--all-games",
            "--priors",
            str(priors_path),
            "--output-dir",
            str(output),
            "--skip-injury-fetch",
        ],
    )

    with pytest.raises(PropsUpstreamError, match="missing canonical player state"):
        module.main()
    assert not output.exists()

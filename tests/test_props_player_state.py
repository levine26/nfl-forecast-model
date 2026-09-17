import pandas as pd
import pytest

from nfl_forecast.props_player_state import (
    SCHEMA_VERSION,
    build_offensive_player_state_contract,
    flatten_current_injury_report,
    validate_offensive_player_state,
)


def _schedule():
    return pd.DataFrame(
        [
            {
                "season": 2026,
                "week": 3,
                "game_id": "2026_03_ARI_LA",
                "home_team": "LA",
                "away_team": "ARI",
                "kickoff": "2026-09-20T20:00:00Z",
            }
        ]
    )


def _roster():
    return pd.DataFrame(
        [
            {"gsis_id": "00-QB", "full_name": "Quarter Back", "position": "QB", "team": "ARI"},
            {"gsis_id": "00-RB", "full_name": "Runner One", "position": "RB", "team": "ARI"},
            {"gsis_id": "00-WR", "full_name": "Wide One", "position": "WR", "team": "ARI"},
            {"gsis_id": "00-TE", "full_name": "Tight One", "position": "TE", "team": "ARI"},
            {"gsis_id": "00-LAWR", "full_name": "Rams Wide", "position": "WR", "team": "LA"},
            {"gsis_id": "00-CB", "full_name": "Defender", "position": "CB", "team": "LA"},
        ]
    )


def _pbp():
    rows = []
    for week in (1, 2):
        game_id = f"2026_0{week}_ARI_X"
        for i in range(20):
            rows.append(
                {
                    "season": 2026,
                    "week": week,
                    "game_id": game_id,
                    "posteam": "ARI",
                    "passer_player_id": "00-QB",
                    "passer_player_name": "Quarter Back",
                    "receiver_player_id": "00-WR" if i < 12 else "00-TE",
                    "receiver_player_name": "Wide One" if i < 12 else "Tight One",
                    "rusher_player_id": None,
                    "rusher_player_name": None,
                    "pass_attempt": 1,
                    "sack": 0,
                    "rush_attempt": 0,
                    "complete_pass": 1 if i < 14 else 0,
                    "yardline_100": 50 if i < 16 else 15,
                    "air_yards": 8,
                }
            )
        for i in range(24):
            rows.append(
                {
                    "season": 2026,
                    "week": week,
                    "game_id": game_id,
                    "posteam": "ARI",
                    "passer_player_id": None,
                    "passer_player_name": None,
                    "receiver_player_id": None,
                    "receiver_player_name": None,
                    "rusher_player_id": "00-RB" if i < 18 else "00-QB",
                    "rusher_player_name": "Runner One" if i < 18 else "Quarter Back",
                    "pass_attempt": 0,
                    "sack": 0,
                    "rush_attempt": 1,
                    "complete_pass": 0,
                    "yardline_100": 4 if i >= 20 else 45,
                    "air_yards": None,
                }
            )
    for _ in range(50):
        rows.append(
            {
                "season": 2026,
                "week": 3,
                "game_id": "2026_03_ARI_LA",
                "posteam": "ARI",
                "passer_player_id": "00-QB",
                "passer_player_name": "Quarter Back",
                "receiver_player_id": "00-TE",
                "receiver_player_name": "Tight One",
                "rusher_player_id": None,
                "rusher_player_name": None,
                "pass_attempt": 1,
                "sack": 0,
                "rush_attempt": 0,
                "complete_pass": 1,
                "yardline_100": 10,
                "air_yards": 10,
            }
        )
    return pd.DataFrame(rows)


def test_build_contract_is_strictly_lagged_and_role_aware():
    availability = pd.DataFrame(
        [
            {
                "team": "ARI",
                "name": "Runner One",
                "game_status": "Questionable",
                "practice_status": "Limited Participation",
                "captured_at": "2026-09-17T20:00:00Z",
                "source_name": "NFL.com official injury report",
            }
        ]
    )
    snaps = pd.DataFrame(
        [
            {
                "season": 2026,
                "week": week,
                "game_id": f"2026_0{week}_ARI_X",
                "player_id": player,
                "offense_snaps": snaps,
                "offense_pct": pct,
            }
            for week in (1, 2)
            for player, snaps, pct in (
                ("00-QB", 64, 1.0),
                ("00-RB", 48, 0.75),
                ("00-WR", 55, 0.86),
                ("00-TE", 50, 0.78),
            )
        ]
    )
    routes = pd.DataFrame(
        [
            {
                "season": 2026,
                "week": week,
                "game_id": f"2026_0{week}_ARI_X",
                "player_id": player,
                "routes": count,
                "route_participation": pct,
            }
            for week in (1, 2)
            for player, count, pct in (
                ("00-RB", 12, 0.40),
                ("00-WR", 28, 0.93),
                ("00-TE", 25, 0.83),
            )
        ]
    )
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=_roster(),
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-17T21:00:00Z",
        snap_counts=snaps,
        routes=routes,
        availability=availability,
    )
    state = built.player_state
    assert set(state["position"]) == {"QB", "RB", "WR", "TE"}
    assert set(state["schema_version"]) == {SCHEMA_VERSION}

    qb = state[state["player_id"].eq("00-QB")].iloc[0]
    rb = state[state["player_id"].eq("00-RB")].iloc[0]
    wr = state[state["player_id"].eq("00-WR")].iloc[0]
    te = state[state["player_id"].eq("00-TE")].iloc[0]

    assert qb["prior_pass_attempts_pg_4"] == pytest.approx(20.0)
    assert qb["prior_qb_rushes_per_dropback_4"] == pytest.approx(6 / 20)
    assert rb["prior_carries_pg_4"] == pytest.approx(18.0)
    assert rb["expected_role"] == "RB_LEAD"
    assert rb["expected_active_state"] == "QUESTIONABLE"
    assert wr["prior_targets_pg_4"] == pytest.approx(12.0)
    assert wr["expected_role"] == "WR_PRIMARY"
    assert te["prior_targets_pg_4"] == pytest.approx(8.0)
    assert built.audit["historical_max_period_used"] == {"season": 2026, "week": 2}


def test_future_availability_is_discarded():
    availability = pd.DataFrame(
        [
            {
                "player_id": "00-RB",
                "team": "ARI",
                "status": "Out",
                "captured_at": "2026-09-18T00:00:00Z",
            }
        ]
    )
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=_roster(),
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-17T21:00:00Z",
        availability=availability,
    )
    rb = built.player_state[built.player_state["player_id"].eq("00-RB")].iloc[0]
    assert rb["expected_active_state"] == "UNKNOWN"
    assert rb["availability_source_status"] == "MISSING"
    assert built.audit["availability"]["rows_future_discarded"] == 1


def test_ambiguous_name_identity_fails_closed():
    roster = _roster()
    duplicate = pd.DataFrame(
        [{"gsis_id": "00-RB2", "full_name": "Runner One", "position": "RB", "team": "ARI"}]
    )
    roster = pd.concat([roster, duplicate], ignore_index=True)
    availability = pd.DataFrame(
        [
            {
                "team": "ARI",
                "name": "Runner One",
                "status": "Out",
                "captured_at": "2026-09-17T20:00:00Z",
            }
        ]
    )
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=roster,
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-17T21:00:00Z",
        availability=availability,
    )
    runners = built.player_state[built.player_state["player_name"].eq("Runner One")]
    assert set(runners["expected_active_state"]) == {"UNKNOWN"}
    assert built.audit["availability"]["rows_ambiguous_identity"] == 1


def test_missing_routes_and_snaps_are_explicit_not_fabricated():
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=_roster(),
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-17T21:00:00Z",
    )
    ari = built.player_state[built.player_state["team"].eq("ARI")]
    assert ari["missing_snap_data"].all()
    assert ari["missing_route_data"].all()
    assert set(ari["data_quality_state"]) == {"CORE_HISTORY"}


def test_known_started_game_is_dropped():
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=_roster(),
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-21T00:00:00Z",
    )
    assert built.player_state.empty
    assert built.audit["games_started_and_dropped"] == ["2026_03_ARI_LA"]


def test_validation_rejects_duplicate_identity():
    built = build_offensive_player_state_contract(
        schedules=_schedule(),
        roster=_roster(),
        pbp=_pbp(),
        season=2026,
        week=3,
        forecast_timestamp="2026-09-17T21:00:00Z",
    )
    duplicate = pd.concat([built.player_state, built.player_state.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_offensive_player_state(duplicate)


def test_naive_forecast_timestamp_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        build_offensive_player_state_contract(
            schedules=_schedule(),
            roster=_roster(),
            pbp=_pbp(),
            season=2026,
            week=3,
            forecast_timestamp="2026-09-17 21:00:00",
        )


def test_existing_nfl_injury_adapter_can_be_flattened_with_capture_time():
    injuries = {
        "ARI": [
            {
                "name": "Runner One",
                "position": "RB",
                "status": "Questionable",
                "game_status": "Questionable",
                "practice_status": "Limited Participation",
                "source_name": "NFL.com official injury report",
                "source_url": "https://example.test/injuries",
            }
        ]
    }
    frame = flatten_current_injury_report(
        injuries,
        {"as_of": "2026-09-17T20:00:00Z", "provider": "NFL.com"},
    )
    assert frame.loc[0, "team"] == "ARI"
    assert frame.loc[0, "captured_at"] == "2026-09-17T20:00:00Z"

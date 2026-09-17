from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from nfl_forecast.offensive_player_state import (
    AvailabilityEvidence,
    AvailabilityEvidenceKind,
    AvailabilityHistorySupport,
    AvailabilityStatus,
    ExpectedRole,
    GameContext,
    IdentityResolution,
    PlayerIdentity,
    PriorUsageGame,
    SourceStatus,
    build_offensive_player_state,
    states_to_frame,
    validate_offensive_player_state_frame,
)

UTC = timezone.utc
KICKOFF = datetime(2026, 9, 20, 20, 20, tzinfo=UTC)
FORECAST = KICKOFF - timedelta(hours=3)
HORIZON = FORECAST - timedelta(minutes=5)


def ident(position="RB", resolution=IdentityResolution.UNIQUE):
    return PlayerIdentity(
        player_id="00-0039999",
        player_name="Test Player",
        position=position,
        team="ARI",
        resolution=resolution,
        identity_source="nflverse",
    )


def game():
    return GameContext("2026_03_ARI_SF", "ARI", "SF", KICKOFF)


def usage(**kwargs):
    base = dict(
        game_id="2026_02_ARI_LAR",
        kickoff_at=KICKOFF - timedelta(days=7),
        available_at=KICKOFF - timedelta(days=7) + timedelta(hours=4),
        source="nflverse_pbp",
        snaps=40,
        routes=20,
        carries=15,
        targets=4,
        red_zone_carries=3,
        goal_line_carries=1,
    )
    base.update(kwargs)
    return PriorUsageGame(**base)


def availability(**kwargs):
    base = dict(
        status=AvailabilityStatus.ACTIVE,
        observed_at=HORIZON - timedelta(minutes=1),
        source="official_injury_report",
        evidence_kind=AvailabilityEvidenceKind.OFFICIAL_INJURY_REPORT,
        history_support=AvailabilityHistorySupport.QUALIFIED_POINT_IN_TIME,
        active_probability=0.99,
    )
    base.update(kwargs)
    return AvailabilityEvidence(**base)


def build(**kwargs):
    base = dict(
        identity=ident(),
        game=game(),
        forecast_at=FORECAST,
        data_horizon_at=HORIZON,
        expected_role=ExpectedRole.RB_LEAD,
        role_source="depth_chart_snapshot",
        availability=availability(),
        prior_usage=[usage()],
    )
    base.update(kwargs)
    return build_offensive_player_state(**base)


def test_valid_state_and_sparse_missingness():
    state = build()
    assert state.player_id == "00-0039999"
    assert state.prior_usage_summary.metrics["carries"] == 15
    assert state.prior_usage_summary.metrics["routes"] == 20
    assert state.prior_usage_summary.metrics["targets"] == 4
    assert state.prior_usage_summary.metrics["dropbacks"] is None
    assert "prior_dropbacks" not in state.missing_fields
    assert state.source_status == SourceStatus.OBSERVED
    assert not state.critical_missing


@pytest.mark.parametrize("position", ["QB", "RB", "WR", "TE"])
def test_supported_positions(position):
    state = build(identity=ident(position), expected_role=ExpectedRole.UNKNOWN)
    assert state.position == position


def test_unsupported_position_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        ident("FB")


@pytest.mark.parametrize(
    "resolution", [IdentityResolution.AMBIGUOUS, IdentityResolution.UNRESOLVED]
)
def test_identity_ambiguity_fails_closed(resolution):
    with pytest.raises(ValueError, match="uniquely"):
        ident("RB", resolution)


def test_naive_forecast_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        build(forecast_at=FORECAST.replace(tzinfo=None))


def test_forecast_must_precede_kickoff():
    with pytest.raises(ValueError, match="strictly before"):
        build(forecast_at=KICKOFF)


def test_horizon_cannot_exceed_forecast():
    with pytest.raises(ValueError, match="later than forecast"):
        build(data_horizon_at=FORECAST + timedelta(seconds=1))


def test_availability_after_horizon_rejected():
    late = availability(observed_at=HORIZON + timedelta(seconds=1))
    with pytest.raises(ValueError, match="not known"):
        build(availability=late)


def test_final_participation_cannot_reconstruct_availability():
    with pytest.raises(ValueError, match="Final participation"):
        availability(evidence_kind=AvailabilityEvidenceKind.FINAL_PARTICIPATION)


def test_current_game_usage_rejected():
    current = usage(game_id=game().game_id)
    with pytest.raises(ValueError, match="Current-game usage"):
        build(prior_usage=[current])


def test_future_game_usage_rejected():
    future = usage(
        game_id="future",
        kickoff_at=KICKOFF + timedelta(days=1),
        available_at=KICKOFF + timedelta(days=1, hours=3),
    )
    with pytest.raises(ValueError, match="did not occur before"):
        build(prior_usage=[future])


def test_usage_not_available_by_horizon_rejected():
    late = usage(available_at=HORIZON + timedelta(minutes=1))
    with pytest.raises(ValueError, match="not available"):
        build(prior_usage=[late])


def test_duplicate_prior_game_rejected():
    row = usage()
    with pytest.raises(ValueError, match="Duplicate prior"):
        build(prior_usage=[row, row])


def test_prospective_only_availability_is_blanked_in_historical_replay():
    prospective = availability(
        history_support=AvailabilityHistorySupport.PROSPECTIVE_ONLY,
        evidence_kind=AvailabilityEvidenceKind.PROJECTION,
    )
    state = build(availability=prospective, historical_replay=True)
    assert state.availability_status == AvailabilityStatus.UNKNOWN
    assert state.availability_probability is None
    assert state.availability_source is None
    assert state.source_status == SourceStatus.PROSPECTIVE_ONLY
    assert "availability_prospective_only_not_replayed" in state.quality_flags


def test_missing_availability_is_explicit():
    state = build(availability=None)
    assert state.availability_status == AvailabilityStatus.UNKNOWN
    assert "availability" in state.missing_fields
    assert state.critical_missing
    assert state.source_status == SourceStatus.PARTIAL


def test_missing_usage_is_none_not_zero():
    state = build(prior_usage=[])
    assert state.prior_usage_summary.metrics["carries"] is None
    assert state.prior_usage_summary.metrics["routes"] is None
    assert state.prior_usage_summary.metrics["targets"] is None
    assert "prior_usage" in state.missing_fields
    assert state.critical_missing


def test_qb_state_requires_dropback_and_rush_inputs_explicitly():
    qb_usage = usage(carries=None, routes=None, targets=None, dropbacks=34, qb_rush_attempts=5)
    state = build(
        identity=ident("QB"),
        expected_role=ExpectedRole.QB_STARTER,
        prior_usage=[qb_usage],
    )
    assert state.prior_usage_summary.metrics["dropbacks"] == 34
    assert state.prior_usage_summary.metrics["qb_rush_attempts"] == 5
    assert "prior_dropbacks" not in state.missing_fields
    assert "prior_qb_rush_attempts" not in state.missing_fields


def test_probability_bounds():
    with pytest.raises(ValueError, match="between 0 and 1"):
        availability(active_probability=1.1)


def test_frame_schema_and_duplicates():
    state = build()
    frame = states_to_frame([state])
    assert len(frame) == 1
    assert frame.loc[0, "prior_carries_mean"] == 15
    duplicated = pd.concat([frame, frame], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_offensive_player_state_frame(duplicated)


def test_role_unknown_is_explicit():
    state = build(expected_role=ExpectedRole.UNKNOWN, role_source=None)
    assert "expected_role" in state.missing_fields
    assert "expected_role_unknown" in state.quality_flags
    assert state.critical_missing


def test_team_mismatch_rejected():
    other = GameContext("g", "LAR", "SF", KICKOFF)
    with pytest.raises(ValueError, match="does not match"):
        build(game=other)


def test_prior_usage_available_at_cannot_precede_game_kickoff():
    with pytest.raises(ValueError, match="cannot precede"):
        usage(available_at=KICKOFF - timedelta(days=8))

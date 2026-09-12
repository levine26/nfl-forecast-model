from __future__ import annotations

import pytest

from research.market_state_v1 import build_market_state, select_consensus_horizons


def _row(
    horizon: str,
    probability: float,
    *,
    game_id: str = "2026_01_ARI_LAC",
    event_id: str = "event-1",
    timing_error: float = 0.0,
    source_count: int = 3,
    spread: float = -2.5,
    total: float = 45.5,
    probability_range: float = 0.04,
    request: str | None = None,
    row_type: str = "consensus",
) -> dict:
    targets = {
        "T-120m": "2026-09-13T18:25:00+00:00",
        "T-60m": "2026-09-13T19:25:00+00:00",
        "T-45m": "2026-09-13T19:40:00+00:00",
        "T-30m": "2026-09-13T19:55:00+00:00",
    }
    if request is None:
        request = targets[horizon]
    return {
        "row_type": row_type,
        "game_id": game_id,
        "event_id": event_id,
        "provider_commence_time_utc": "2026-09-13T20:25:00+00:00",
        "home_team": "LAC",
        "away_team": "ARI",
        "kickoff_timestamp_utc": "2026-09-13T20:25:00+00:00",
        "horizon": horizon,
        "target_timestamp_utc": targets[horizon],
        "request_timestamp_utc": request,
        "timing_error_minutes": timing_error,
        "sportsbook_key": "sportsbook_consensus",
        "h2h_home_no_vig": probability,
        "home_spread": spread,
        "total_points": total,
        "source_count": source_count,
        "source_names": "a|b|c",
        "max_freshness_minutes": 2.0,
        "probability_range": probability_range,
        "research_only": True,
        "production_authorized": False,
    }


def test_market_state_derives_four_horizon_movement_without_outcomes() -> None:
    rows = [
        _row("T-120m", 0.55, spread=-2.5, total=45.5, probability_range=0.06),
        _row("T-60m", 0.58, spread=-3.0, total=46.0, probability_range=0.05),
        _row("T-45m", 0.59, spread=-3.0, total=46.0, probability_range=0.04),
        _row("T-30m", 0.60, spread=-3.5, total=46.5, probability_range=0.03),
    ]
    states, audit = build_market_state(rows)
    assert len(states) == 1
    state = states[0]

    assert state["complete_horizons"] is True
    assert state["missing_horizons"] == []
    assert state["market_home_prob_t120"] == pytest.approx(0.55)
    assert state["market_home_prob_t45"] == pytest.approx(0.59)
    assert state["market_home_prob_t30"] == pytest.approx(0.60)
    assert state["home_probability_pp_t45_minus_t120"] == pytest.approx(4.0)
    assert state["home_probability_pp_t30_minus_t45"] == pytest.approx(1.0)
    assert state["home_probability_pp_t30_minus_t120"] == pytest.approx(5.0)
    assert state["home_spread_t30_minus_t120"] == pytest.approx(-1.0)
    assert state["total_points_t30_minus_t120"] == pytest.approx(1.0)
    assert state["probability_range_t30_minus_t120"] == pytest.approx(-0.03)
    assert state["home_logit_t30_minus_t120"] > 0
    assert state["strict_no_later_than_cutoff"] is True
    assert state["completed_2026_outcomes_used"] == 0
    assert state["production_authorized"] is False
    assert audit["games_with_all_four_horizons"] == 1
    assert audit["strict_no_later_than_cutoff"] is True
    assert audit["completed_2026_outcomes_used"] == 0


def test_horizon_retry_selects_closest_eligible_pre_cutoff_request() -> None:
    rows = [
        _row("T-120m", 0.51, timing_error=-6.0, request="2026-09-13T18:19:00+00:00"),
        _row("T-120m", 0.54, timing_error=1.0, request="2026-09-13T18:26:00+00:00"),
        _row("T-120m", 0.57, timing_error=-2.0, request="2026-09-13T18:23:00+00:00"),
    ]
    selected = select_consensus_horizons(rows)
    assert selected["2026_01_ARI_LAC"]["T-120m"]["h2h_home_no_vig"] == 0.57


def test_post_cutoff_request_is_ineligible_even_inside_capture_tolerance() -> None:
    rows = [
        _row("T-45m", 0.58, timing_error=-2.0, request="2026-09-13T19:38:00+00:00"),
        _row("T-45m", 0.62, timing_error=1.0, request="2026-09-13T19:41:00+00:00"),
    ]
    selected = select_consensus_horizons(rows)
    assert selected["2026_01_ARI_LAC"]["T-45m"]["h2h_home_no_vig"] == 0.58


def test_request_timestamp_after_target_fails_closed_even_if_timing_field_claims_early() -> None:
    rows = [
        _row("T-45m", 0.62, timing_error=-1.0, request="2026-09-13T19:41:00+00:00"),
    ]
    assert select_consensus_horizons(rows) == {}


def test_nonqualifying_rows_cannot_close_or_influence_state() -> None:
    rows = [
        _row("T-120m", 0.55),
        _row("T-60m", 0.99, source_count=1),
        _row("T-45m", 0.96, timing_error=0.5, request="2026-09-13T19:40:30+00:00"),
        _row("T-30m", 0.98, row_type="book"),
        _row("T-30m", 0.97, timing_error=-9.0, request="2026-09-13T19:46:00+00:00"),
    ]
    states, audit = build_market_state(rows)
    state = states[0]

    assert state["available_horizons"] == ["T-120m"]
    assert state["missing_horizons"] == ["T-60m", "T-45m", "T-30m"]
    assert state["market_home_prob_t60"] is None
    assert state["market_home_prob_t45"] is None
    assert state["market_home_prob_t30"] is None
    assert state["home_probability_t30_minus_t120"] is None
    assert audit["games_with_missing_horizons"] == 1


def test_missing_optional_spread_total_remain_missing_not_imputed() -> None:
    rows = [
        _row("T-120m", 0.55, spread=-2.5, total=45.5),
        _row("T-60m", 0.56, spread=None, total=None),
    ]
    states, _ = build_market_state(rows)
    state = states[0]
    assert state["home_spread_t60"] is None
    assert state["total_points_t60"] is None
    assert state["home_spread_t60_minus_t120"] is None
    assert state["total_points_t60_minus_t120"] is None


def test_cross_horizon_event_identity_mismatch_fails_closed() -> None:
    rows = [
        _row("T-120m", 0.55, event_id="event-current"),
        _row("T-60m", 0.58, event_id="event-rematch"),
    ]
    with pytest.raises(ValueError, match="horizons disagree on event identity"):
        build_market_state(rows)


def test_retry_identity_mismatch_within_horizon_fails_closed() -> None:
    rows = [
        _row("T-120m", 0.55, event_id="event-current", timing_error=-1.0, request="2026-09-13T18:24:00+00:00"),
        _row("T-120m", 0.56, event_id="event-rematch", timing_error=-2.0, request="2026-09-13T18:23:00+00:00"),
    ]
    with pytest.raises(ValueError, match="retries disagree on event identity"):
        select_consensus_horizons(rows)

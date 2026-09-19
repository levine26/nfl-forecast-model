import pytest

from nfl_forecast.props21_market import (
    INSUFFICIENT, SUPPORTED, build_market_state, probability_at,
)


AS_OF = "2026-09-19T20:00:00+00:00"
KICKOFF = "2026-09-20T17:00:00+00:00"


def quote(book, line, over, under, *, alt=False, player_id="p"):
    return {"provider": "propline", "sportsbook_key": book, "sportsbook_title": book,
            "captured_at_utc": "2026-09-19T19:50:00+00:00",
            "sportsbook_last_update_utc": "2026-09-19T19:49:00+00:00",
            "player_id": player_id, "player": "Player", "game_id": "g",
            "prop_type": "receiving_yards", "line": line,
            "over_american": over, "under_american": under,
            "kickoff_utc": KICKOFF, "is_alternative_line": alt}


def test_market_curve_is_monotone_and_never_extrapolates_tails():
    rows = []
    for book in ("a", "b"):
        rows.extend([quote(book, 39.5, -150, 120), quote(book, 49.5, -110, -110, alt=True),
                     quote(book, 59.5, 120, -150, alt=True)])
    state = build_market_state(rows, as_of_utc=AS_OF, kickoff_utc=KICKOFF,
                               fair_line=52.5, sportsbook_line=39.5)
    assert state["status"] == SUPPORTED
    probabilities = [point["monotone_p_over"] for point in state["survival_points"]]
    assert probabilities == sorted(probabilities, reverse=True)
    assert probability_at(state["survival_points"], 52.5) is not None
    assert probability_at(state["survival_points"], 80.5) is None
    assert state["market_mean"] is None
    assert "UNOBSERVED_TAILS" in state["reasons"]


def test_thin_market_uses_explicit_fallback():
    state = build_market_state([quote("a", 49.5, -110, -110)],
                               as_of_utc=AS_OF, kickoff_utc=KICKOFF)
    assert state["status"] == INSUFFICIENT
    assert state["fallback"]["consensus_line"] == 49.5
    assert "THIN_MARKET" in state["reasons"]


def test_stale_post_cutoff_and_identity_collisions_fail_closed():
    stale = quote("a", 49.5, -110, -110)
    stale["sportsbook_last_update_utc"] = "2026-09-19T10:00:00+00:00"
    state = build_market_state([stale], as_of_utc=AS_OF, kickoff_utc=KICKOFF,
                               max_quote_age_minutes=60)
    assert state["book_count"] == 0
    assert state["rejected_counts"]["STALE_QUOTE"] == 1
    with pytest.raises(ValueError, match="cannot mix"):
        build_market_state([quote("a", 49.5, -110, -110),
                            quote("b", 49.5, -110, -110, player_id="other")],
                           as_of_utc=AS_OF, kickoff_utc=KICKOFF)


def test_integer_line_is_conditional_when_push_mass_is_unknown():
    state = build_market_state([quote("a", 50.0, -110, -110)],
                               as_of_utc=AS_OF, kickoff_utc=KICKOFF,
                               sportsbook_line=50.0)
    assert state["survival_points"] == []
    assert state["conditional_push_observations"][0]["push_probability"] is None
    assert "PUSH_PROBABILITY_UNIDENTIFIED" in state["reasons"]

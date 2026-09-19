from __future__ import annotations

from copy import deepcopy

import pytest

from nfl_forecast.props_live_role_intel import (
    PropsLiveRoleIntelError,
    build_live_role_intelligence,
    contextual_availability_rows,
    validate_market_backed_primary_qb_forecasts,
)


GAME_SEA = "2026_02_SEA_ARI"
GAME_ATL = "2026_02_CAR_ATL"
CAPTURE = "2026-09-18T22:30:28Z"


def _qb(
    game_id: str,
    player_id: str,
    player_name: str,
    team: str,
    opponent: str,
    *,
    active_state: str = "UNKNOWN",
):
    return {
        "game_id": game_id,
        "player_id": player_id,
        "player_name": player_name,
        "position": "QB",
        "team": team,
        "opponent": opponent,
        "expected_active_state": active_state,
    }


def _state():
    return [
        _qb(GAME_SEA, "LOCK", "Drew Lock", "SEA", "ARI"),
        _qb(GAME_SEA, "DARNOLD", "Sam Darnold", "SEA", "ARI"),
        _qb(GAME_ATL, "RUSH", "Cooper Rush", "ATL", "CAR"),
        _qb(GAME_ATL, "PENIX", "Michael Penix Jr.", "ATL", "CAR"),
    ]


def _passing_market(game_id: str, player_id: str, *, books: int = 3, line: float = 204.5):
    return {
        "game_id": game_id,
        "player_id": player_id,
        "prop_type": "passing_yards",
        "sportsbook_count": books,
        "consensus_line": line,
    }


def _media(game_id: str, text: str, generated: str = "2026-09-18T20:00:00Z"):
    return {
        "generated_utc": generated,
        "games": {
            game_id: {
                "generated_utc": generated,
                "headline": "Current quarterback update",
                "paragraph1": text,
                "sources": [
                    {
                        "name": "Team source",
                        "url": "https://example.com/report",
                    }
                ],
            }
        },
    }


def test_drew_lock_explicit_news_and_multi_book_market_resolves_primary_qb():
    payload = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_SEA, "LOCK", books=4)],
        market_captured_at_utc=CAPTURE,
        media_reads=_media(
            GAME_SEA,
            "Drew Lock is expected to start after Sam Darnold's hip injury.",
        ),
    )

    selected = payload["primary_qb_by_game"][GAME_SEA]["SEA"]
    assert selected["player_id"] == "LOCK"
    assert selected["resolution"] == "news_and_market_agree"
    assert payload["market_line_magnitude_used_for_projection"] is False
    assert payload["market_price_used_for_projection"] is False


def test_cooper_rush_unique_multi_book_passing_market_can_resolve_when_news_is_silent():
    payload = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_ATL, "RUSH", books=5, line=184.5)],
        market_captured_at_utc=CAPTURE,
    )
    selected = payload["primary_qb_by_game"][GAME_ATL]["ATL"]
    assert selected["player_id"] == "RUSH"
    assert selected["resolution"] == "market_presence_unique"


def test_single_book_market_is_too_thin_to_override_depth_chart_state():
    payload = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_SEA, "LOCK", books=1)],
        market_captured_at_utc=CAPTURE,
    )
    assert GAME_SEA not in payload["primary_qb_by_game"]
    assert any(
        row["status"] == "passing_market_too_thin_for_role_inference"
        for row in payload["audit"]["market_audit"]
    )


def test_market_line_magnitude_does_not_change_role_resolution():
    low = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_ATL, "RUSH", books=3, line=100.5)],
        market_captured_at_utc=CAPTURE,
    )
    high = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_ATL, "RUSH", books=3, line=399.5)],
        market_captured_at_utc=CAPTURE,
    )
    assert low["primary_qb_by_game"] == high["primary_qb_by_game"]
    assert low["market_line_magnitude_used_for_projection"] is False
    assert high["market_line_magnitude_used_for_projection"] is False


def test_future_or_stale_media_cannot_override():
    future = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[],
        market_captured_at_utc=CAPTURE,
        media_reads=_media(
            GAME_SEA,
            "Drew Lock will start at quarterback.",
            generated="2026-09-19T01:00:00Z",
        ),
    )
    assert GAME_SEA not in future["primary_qb_by_game"]

    stale = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[],
        market_captured_at_utc=CAPTURE,
        media_reads=_media(
            GAME_SEA,
            "Drew Lock will start at quarterback.",
            generated="2026-09-14T01:00:00Z",
        ),
    )
    assert GAME_SEA not in stale["primary_qb_by_game"]


def test_fresh_media_market_disagreement_fails_closed():
    payload = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_SEA, "DARNOLD", books=4)],
        market_captured_at_utc=CAPTURE,
        media_reads=_media(
            GAME_SEA,
            "Drew Lock is expected to start at quarterback.",
            generated="2026-09-18T21:30:00Z",
        ),
    )
    assert GAME_SEA not in payload["primary_qb_by_game"]
    assert payload["blocking_conflicts"][0]["reason"] == "fresh_media_market_qb_conflict"


def test_multiple_multi_book_qb_markets_fail_closed():
    payload = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[
            _passing_market(GAME_SEA, "LOCK", books=3),
            _passing_market(GAME_SEA, "DARNOLD", books=3, line=240.5),
        ],
        market_captured_at_utc=CAPTURE,
    )
    assert GAME_SEA not in payload["primary_qb_by_game"]
    assert payload["blocking_conflicts"][0]["reason"] == "multiple_multi_book_passing_market_qbs"


def test_explicit_out_state_vetoes_market_selected_qb():
    state = _state()
    for row in state:
        if row["player_id"] == "LOCK":
            row["expected_active_state"] = "OUT"
    payload = build_live_role_intelligence(
        player_state_rows=state,
        market_artifacts=[_passing_market(GAME_SEA, "LOCK", books=4)],
        market_captured_at_utc=CAPTURE,
    )
    assert GAME_SEA not in payload["primary_qb_by_game"]
    assert payload["blocking_conflicts"][0]["reason"] == "selected_qb_explicitly_out"


def test_shared_contextual_availability_converts_only_qualified_timestamped_status():
    context = {
        GAME_ATL: [
            {
                "category": "personnel",
                "title": "ATL: Michael Penix Jr. — Out",
                "summary": "The official NFL injury report lists Michael Penix Jr. as Out.",
                "as_of": "2026-09-18T21:00:00Z",
                "source_name": "NFL.com official injury report + nflverse usage",
                "source_url": "https://www.nfl.com/injuries/league/2026/reg2",
                "metadata": {
                    "family": "availability",
                    "team": "ATL",
                    "position": "QB",
                },
            },
            {
                "category": "personnel",
                "title": "ATL: Example WR — Questionable",
                "summary": "Unqualified blog report.",
                "as_of": "2026-09-18T21:00:00Z",
                "source_name": "Random Blog",
                "source_url": "https://example.com/blog",
                "metadata": {
                    "family": "availability",
                    "team": "ATL",
                    "position": "WR",
                },
            },
        ]
    }
    rows = contextual_availability_rows(context, as_of_utc=CAPTURE)
    assert len(rows) == 1
    assert rows[0]["name"] == "Michael Penix Jr."
    assert rows[0]["game_status"] == "Out"
    assert rows[0]["shared_context_evidence"] is True


def test_market_backed_primary_qb_zero_projection_fails_publication_guard():
    intel = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_SEA, "LOCK", books=4)],
        market_captured_at_utc=CAPTURE,
    )
    forecast = {
        "forecasts": [
            {
                "game_id": GAME_SEA,
                "player_id": "LOCK",
                "prop_type": "passing_yards",
                "model": {"mean": 0.0, "fair_line": 0.0},
            }
        ]
    }
    with pytest.raises(PropsLiveRoleIntelError, match="non-positive passing projection"):
        validate_market_backed_primary_qb_forecasts(intel, forecast)


def test_market_backed_primary_qb_positive_projection_passes_without_market_comparison():
    intel = build_live_role_intelligence(
        player_state_rows=_state(),
        market_artifacts=[_passing_market(GAME_ATL, "RUSH", books=4, line=184.5)],
        market_captured_at_utc=CAPTURE,
    )
    forecast = {
        "forecasts": [
            {
                "game_id": GAME_ATL,
                "player_id": "RUSH",
                "prop_type": "passing_yards",
                "model": {"mean": 191.2, "fair_line": 190.5},
            }
        ]
    }
    audit = validate_market_backed_primary_qb_forecasts(intel, forecast)
    assert audit["status"] == "passed"
    assert audit["market_backed_primary_qbs_checked"] == 1
    assert audit["market_line_magnitude_compared"] is False
    assert audit["market_price_compared"] is False

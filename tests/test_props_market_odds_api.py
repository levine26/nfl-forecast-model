from __future__ import annotations

from datetime import datetime, timezone

from nfl_forecast.props_market_odds_api import ingest_odds_api_event


UTC = timezone.utc
CAPTURE = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)


def _resolver(name: str) -> str | None:
    return {
        "Example Receiver": "00-0031234",
        "Example Runner": "00-0035678",
    }.get(name)


def _context(player_id: str) -> dict:
    return {
        "team": "A",
        "opponent": "B",
        "position": "WR" if player_id == "00-0031234" else "RB",
        "related_market_group_id": "2026_03_A_B:A",
    }


def _event() -> dict:
    return {
        "id": "evt-1",
        "commence_time": "2026-09-20T17:00:00Z",
        "bookmakers": [
            {
                "key": "book-a",
                "title": "Book A",
                "last_update": "2026-09-20T14:59:00Z",
                "markets": [
                    {
                        "key": "player_reception_yds",
                        "outcomes": [
                            {
                                "name": "Over",
                                "description": "Example Receiver",
                                "price": -115,
                                "point": 75.5,
                            },
                            {
                                "name": "Under",
                                "description": "Example Receiver",
                                "price": -105,
                                "point": 75.5,
                            },
                        ],
                    },
                    {
                        "key": "player_anytime_td",
                        "outcomes": [
                            {"name": "Example Runner", "price": 145},
                            {"name": "Unknown Player", "price": 200},
                        ],
                    },
                    {
                        "key": "some_new_provider_market",
                        "outcomes": [],
                    },
                ],
            }
        ],
    }


def test_adapter_normalizes_two_way_prop_and_preserves_provider_identity() -> None:
    result = ingest_odds_api_event(
        _event(),
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
        player_context_resolver=_context,
    )
    receiving = [q for q in result.quotes if q.prop_type == "receiving_yards"]
    assert len(receiving) == 1
    quote = receiving[0]
    assert quote.player_id == "00-0031234"
    assert quote.line == 75.5
    assert quote.over_american == -115
    assert quote.under_american == -105
    assert quote.team == "A"
    assert quote.position == "WR"
    assert quote.provider_event_id == "evt-1"
    assert quote.provider_market_key == "player_reception_yds"
    assert quote.is_alternative_line is False
    assert quote.to_record()["over_no_vig"] is not None


def test_adapter_preserves_one_sided_anytime_td_and_rejects_unresolved_identity() -> None:
    result = ingest_odds_api_event(
        _event(),
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
        player_context_resolver=_context,
    )
    anytime = [q for q in result.quotes if q.prop_type == "anytime_td"]
    assert len(anytime) == 1
    assert anytime[0].player == "Example Runner"
    assert anytime[0].yes_american == 145
    assert anytime[0].no_american is None
    assert anytime[0].to_record()["yes_no_vig"] is None
    assert any(
        row.get("reason") == "unresolved_player_id"
        and row.get("player") == "Unknown Player"
        for row in result.rejected
    )


def test_adapter_reports_unsupported_provider_markets_without_expanding_scope() -> None:
    result = ingest_odds_api_event(
        _event(),
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
    )
    assert result.ignored_market_keys == ("some_new_provider_market",)


def test_explicit_alternate_market_key_maps_to_same_prop_and_is_flagged() -> None:
    event = _event()
    event["bookmakers"][0]["markets"] = [
        {
            "key": "player_reception_yds_alternate",
            "outcomes": [
                {
                    "name": "Over",
                    "description": "Example Receiver",
                    "price": 120,
                    "point": 80.5,
                },
                {
                    "name": "Under",
                    "description": "Example Receiver",
                    "price": -140,
                    "point": 80.5,
                },
            ],
        }
    ]
    result = ingest_odds_api_event(
        event,
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
    )
    assert len(result.quotes) == 1
    assert result.quotes[0].prop_type == "receiving_yards"
    assert result.quotes[0].is_alternative_line is True


def test_multiple_thresholds_in_standard_market_are_not_guessed_as_primary() -> None:
    event = _event()
    event["bookmakers"][0]["markets"] = [
        {
            "key": "player_reception_yds",
            "outcomes": [
                {"name": "Over", "description": "Example Receiver", "price": -150, "point": 70.5},
                {"name": "Under", "description": "Example Receiver", "price": 130, "point": 70.5},
                {"name": "Over", "description": "Example Receiver", "price": 120, "point": 80.5},
                {"name": "Under", "description": "Example Receiver", "price": -140, "point": 80.5},
            ],
        }
    ]
    result = ingest_odds_api_event(
        event,
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
    )
    assert len(result.quotes) == 2
    assert all(q.is_alternative_line for q in result.quotes)


def test_yes_no_binary_shape_can_be_devigged_when_provider_supplies_both_sides() -> None:
    event = _event()
    event["bookmakers"][0]["markets"] = [
        {
            "key": "player_anytime_td",
            "outcomes": [
                {"name": "Yes", "description": "Example Runner", "price": -135},
                {"name": "No", "description": "Example Runner", "price": 115},
            ],
        }
    ]
    result = ingest_odds_api_event(
        event,
        captured_at_utc=CAPTURE,
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
    )
    assert len(result.quotes) == 1
    record = result.quotes[0].to_record()
    assert record["yes_no_vig"] is not None
    assert record["yes_no_vig"] + record["no_no_vig"] == 1.0


def test_capture_after_kickoff_fails_closed_as_invalid_quote() -> None:
    result = ingest_odds_api_event(
        _event(),
        captured_at_utc=datetime(2026, 9, 20, 17, 1, tzinfo=UTC),
        game_id="2026_03_A_B",
        player_id_resolver=_resolver,
    )
    assert result.quotes == ()
    assert any(row.get("reason") == "invalid_quote" for row in result.rejected)

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nfl_forecast import props_market_live as live


UTC = timezone.utc
CAPTURE = datetime(2026, 9, 20, 16, 0, tzinfo=UTC)
KICKOFF = "2026-09-20T20:05:00+00:00"


def _player_state():
    rows = []
    players = [
        ("QB1", "Kyler Murray", "QB", "ARI", "LAR"),
        ("RB1", "Example Runner", "RB", "ARI", "LAR"),
        ("WR1", "Example Receiver", "WR", "ARI", "LAR"),
        ("QB2", "Matthew Stafford", "QB", "LAR", "ARI"),
    ]
    for player_id, name, position, team, opponent in players:
        rows.append(
            {
                "game_id": "2026_03_LAR_ARI",
                "player_id": player_id,
                "player_name": name,
                "position": position,
                "team": team,
                "opponent": opponent,
                "kickoff_timestamp": KICKOFF,
            }
        )
    return rows


def _event():
    return {
        "id": "evt-ari-lar",
        "home_team": "Arizona Cardinals",
        "away_team": "Los Angeles Rams",
        "commence_time": KICKOFF,
        "bookmakers": [
            {
                "key": "book-a",
                "title": "Book A",
                "last_update": "2026-09-20T15:58:00Z",
                "markets": [
                    {
                        "key": "player_pass_yds",
                        "outcomes": [
                            {
                                "name": "Over",
                                "description": "Kyler Murray",
                                "price": -110,
                                "point": 244.5,
                            },
                            {
                                "name": "Under",
                                "description": "Kyler Murray",
                                "price": -110,
                                "point": 244.5,
                            },
                        ],
                    },
                    {
                        "key": "player_reception_yds",
                        "outcomes": [
                            {
                                "name": "Over",
                                "description": "Example Receiver",
                                "price": -115,
                                "point": 67.5,
                            },
                            {
                                "name": "Under",
                                "description": "Example Receiver",
                                "price": -105,
                                "point": 67.5,
                            },
                            {
                                "name": "Over",
                                "description": "Unknown Receiver",
                                "price": -110,
                                "point": 40.5,
                            },
                            {
                                "name": "Under",
                                "description": "Unknown Receiver",
                                "price": -110,
                                "point": 40.5,
                            },
                        ],
                    },
                    {
                        "key": "player_anytime_td",
                        "outcomes": [
                            {"name": "Yes", "description": "Example Runner", "price": 120},
                            {"name": "No", "description": "Example Runner", "price": -140},
                        ],
                    },
                ],
            },
            {
                "key": "book-b",
                "title": "Book B",
                "last_update": "2026-09-20T15:59:00Z",
                "markets": [
                    {
                        "key": "player_pass_yds",
                        "outcomes": [
                            {
                                "name": "Over",
                                "description": "Kyler Murray",
                                "price": -105,
                                "point": 244.5,
                            },
                            {
                                "name": "Under",
                                "description": "Kyler Murray",
                                "price": -115,
                                "point": 244.5,
                            },
                        ],
                    }
                ],
            },
        ],
    }


def test_live_snapshot_matches_provider_event_to_canonical_game_and_stable_ids():
    snapshot = live.build_market_snapshot(
        player_state_rows=_player_state(),
        provider_events=[_event()],
        captured_at_utc=CAPTURE,
    )

    assert snapshot["contract_version"] == live.SNAPSHOT_CONTRACT_VERSION
    assert snapshot["audit"]["matched_event_count"] == 1
    assert snapshot["audit"]["quote_count"] == 4
    assert snapshot["audit"]["artifact_count"] == 3

    by_key = {
        (row["player_id"], row["prop_type"]): row
        for row in snapshot["market_artifacts"]
    }
    passing = by_key[("QB1", "passing_yards")]
    assert passing["game_id"] == "2026_03_LAR_ARI"
    assert passing["consensus_line"] == 244.5
    assert passing["sportsbook_count"] == 2
    assert passing["consensus_no_vig_p_over"] is not None

    anytime = by_key[("RB1", "anytime_td")]
    assert anytime["consensus_no_vig_probability"] is not None
    assert any(
        row.get("reason") == "unresolved_player_id"
        and row.get("player") == "Unknown Receiver"
        for row in snapshot["audit"]["rejected"]
    )


def test_provider_team_aliases_cover_propline_nfl_labels_without_guessing_player_identity():
    provider_labels = {
        "ARI Cardinals": "ARI",
        "ATL Falcons": "ATL",
        "BAL Ravens": "BAL",
        "BUF Bills": "BUF",
        "CAR Panthers": "CAR",
        "CHI Bears": "CHI",
        "CIN Bengals": "CIN",
        "CLE Browns": "CLE",
        "DAL Cowboys": "DAL",
        "DEN Broncos": "DEN",
        "DET Lions": "DET",
        "GB Packers": "GB",
        "HOU Texans": "HOU",
        "IND Colts": "IND",
        "JAX Jaguars": "JAX",
        "KC Chiefs": "KC",
        "LV Raiders": "LV",
        "LA Chargers": "LAC",
        "LA Rams": "LAR",
        "MIA Dolphins": "MIA",
        "MIN Vikings": "MIN",
        "NE Patriots": "NE",
        "NO Saints": "NO",
        "NY Giants": "NYG",
        "NY Jets": "NYJ",
        "PHI Eagles": "PHI",
        "PIT Steelers": "PIT",
        "SF 49ers": "SF",
        "SEA Seahawks": "SEA",
        "TB Buccaneers": "TB",
        "TEN Titans": "TEN",
        "WAS Commanders": "WAS",
    }
    for label, expected in provider_labels.items():
        assert live.provider_team_code(label) == expected

    assert live.provider_team_code("Los Angeles Rams") == "LAR"
    assert live.provider_team_code("Los Angeles Chargers") == "LAC"


def test_kickoff_mismatch_fails_event_closed():
    event = _event()
    event["commence_time"] = "2026-09-20T22:05:00Z"
    snapshot = live.build_market_snapshot(
        player_state_rows=_player_state(),
        provider_events=[event],
        captured_at_utc=CAPTURE,
    )
    assert snapshot["market_artifacts"] == []
    assert snapshot["audit"]["matched_event_count"] == 0
    assert snapshot["audit"]["unmatched_events"][0]["reason"] == "provider_event_kickoff_mismatch"


def test_capture_at_or_after_kickoff_rejects_event():
    snapshot = live.build_market_snapshot(
        player_state_rows=_player_state(),
        provider_events=[_event()],
        captured_at_utc="2026-09-20T20:05:00Z",
    )
    assert snapshot["market_artifacts"] == []
    assert snapshot["audit"]["rejected"][0]["reason"] == "capture_not_pregame"


def test_duplicate_normalized_player_names_are_unresolved_not_guessed():
    state = _player_state()
    state.append(
        {
            "game_id": "2026_03_LAR_ARI",
            "player_id": "WRX",
            "player_name": "Example Receiver",
            "position": "WR",
            "team": "LAR",
            "opponent": "ARI",
            "kickoff_timestamp": KICKOFF,
        }
    )
    snapshot = live.build_market_snapshot(
        player_state_rows=state,
        provider_events=[_event()],
        captured_at_utc=CAPTURE,
    )
    assert not any(
        row["player_id"] == "WR1" and row["prop_type"] == "receiving_yards"
        for row in snapshot["market_artifacts"]
    )
    assert any(
        row.get("reason") == "unresolved_player_id"
        and row.get("player") == "Example Receiver"
        for row in snapshot["audit"]["rejected"]
    )


def test_live_fetch_discovers_only_canonical_slate_events(monkeypatch):
    calls = []

    def fake_get(path, *, api_key, params=None, timeout_seconds=20.0):
        calls.append((path, dict(params or {}), api_key))
        if path.endswith("/events"):
            return [
                {
                    "id": "evt-ari-lar",
                    "home_team": "Arizona Cardinals",
                    "away_team": "Los Angeles Rams",
                    "commence_time": KICKOFF,
                },
                {
                    "id": "evt-other",
                    "home_team": "Buffalo Bills",
                    "away_team": "Miami Dolphins",
                    "commence_time": KICKOFF,
                },
            ]
        assert path.endswith("/events/evt-ari-lar/odds")
        event = _event()
        event["bookmakers"] = []
        return event

    monkeypatch.setattr(live, "_provider_get_json", fake_get)
    events, raw = live.fetch_live_nfl_prop_events(
        player_state_rows=_player_state(),
        api_key="secret-value",
        regions="us",
    )

    assert len(events) == 1
    assert raw["discovery_event_count"] == 2
    assert len(calls) == 2
    assert calls[0][2] == "secret-value"
    assert "player_pass_yds" in calls[1][1]["markets"]
    assert "secret-value" not in str(raw)


def test_missing_api_key_fails_before_network():
    with pytest.raises(live.PropsMarketLiveError, match="authorized"):
        live._provider_get_json("/sports/test/events", api_key="")


def test_propline_fetch_uses_compatible_nfl_prop_shape(monkeypatch):
    calls = []

    def fake_get(path, *, api_key, params=None, timeout_seconds=20.0):
        calls.append((path, dict(params or {}), api_key))
        if path.endswith("/events"):
            return [
                {
                    "id": "pl-evt-ari-lar",
                    "home_team": "Arizona Cardinals",
                    "away_team": "Los Angeles Rams",
                    "commence_time": KICKOFF,
                }
            ]
        assert path.endswith("/events/pl-evt-ari-lar/odds")
        event = _event()
        event["id"] = "pl-evt-ari-lar"
        event["bookmakers"][0]["key"] = "draftkings"
        event["bookmakers"][0]["title"] = "DraftKings"
        event["bookmakers"][1]["key"] = "prizepicks"
        event["bookmakers"][1]["title"] = "PrizePicks"
        return event

    monkeypatch.setattr(live, "_propline_get_json", fake_get)
    events, raw = live.fetch_live_nfl_prop_events(
        player_state_rows=_player_state(),
        api_key="propline-secret",
        provider="propline",
    )

    assert len(events) == 1
    assert raw["provider"] == "propline"
    assert raw["discovery_event_count"] == 1
    assert calls[0][1] == {}
    assert "player_pass_yds" in calls[1][1]["markets"]
    assert calls[1][1]["bookmakers"] == ",".join(
        sorted(live.PROPLINE_SPORTSBOOK_KEYS)
    )
    assert "regions" not in calls[1][1]
    assert [book["key"] for book in events[0]["bookmakers"]] == ["draftkings"]
    assert "propline-secret" not in str(raw)


def test_propline_bookmaker_filter_excludes_dfs_and_exchange_sources():
    assert live._propline_sportsbook_filter(
        "draftkings,prizepicks,kalshi,polymarket_us,underdog"
    ) == "draftkings"

    with pytest.raises(live.PropsMarketLiveError, match="no approved sportsbook"):
        live._propline_sportsbook_filter("prizepicks,kalshi,underdog")



def _sportsgameodds_event():
    return {
        "eventID": "sgo-evt-ari-lar",
        "leagueID": "NFL",
        "teams": {
            "home": {"names": {"long": "Arizona Cardinals"}},
            "away": {"names": {"long": "Los Angeles Rams"}},
        },
        "status": {"startsAt": KICKOFF},
        "players": {
            "KYLER": {"name": "Kyler Murray"},
            "RUNNER": {"name": "Example Runner"},
        },
        "odds": {
            "passing_yards-KYLER-game-ou-over": {
                "statID": "passing_yards",
                "statEntityID": "KYLER",
                "playerID": "KYLER",
                "periodID": "game",
                "betTypeID": "ou",
                "sideID": "over",
                "byBookmaker": {
                    "draftkings": {
                        "available": True,
                        "odds": "-110",
                        "overUnder": "244.5",
                        "lastUpdatedAt": "2026-09-20T15:58:00Z",
                    },
                    "prizepicks": {
                        "available": True,
                        "odds": "+100",
                        "overUnder": "244.5",
                    },
                },
            },
            "passing_yards-KYLER-game-ou-under": {
                "statID": "passing_yards",
                "statEntityID": "KYLER",
                "playerID": "KYLER",
                "periodID": "game",
                "betTypeID": "ou",
                "sideID": "under",
                "byBookmaker": {
                    "draftkings": {
                        "available": True,
                        "odds": "-110",
                        "overUnder": "244.5",
                        "lastUpdatedAt": "2026-09-20T15:58:30Z",
                    },
                    "prizepicks": {
                        "available": True,
                        "odds": "+100",
                        "overUnder": "244.5",
                    },
                },
            },
            "touchdowns-RUNNER-game-yn-yes": {
                "statID": "touchdowns",
                "statEntityID": "RUNNER",
                "playerID": "RUNNER",
                "periodID": "game",
                "betTypeID": "yn",
                "sideID": "yes",
                "byBookmaker": {
                    "fanduel": {
                        "available": True,
                        "odds": "+120",
                        "lastUpdatedAt": "2026-09-20T15:59:00Z",
                    }
                },
            },
            "touchdowns-RUNNER-game-yn-no": {
                "statID": "touchdowns",
                "statEntityID": "RUNNER",
                "playerID": "RUNNER",
                "periodID": "game",
                "betTypeID": "yn",
                "sideID": "no",
                "byBookmaker": {
                    "fanduel": {
                        "available": True,
                        "odds": "-140",
                        "lastUpdatedAt": "2026-09-20T15:59:00Z",
                    }
                },
            },
        },
    }


def test_sportsgameodds_normalizes_supported_props_and_excludes_pickem_sources():
    normalized = live._sportsgameodds_event_to_odds_api(_sportsgameodds_event())

    assert normalized["id"] == "sgo-evt-ari-lar"
    by_book = {row["key"]: row for row in normalized["bookmakers"]}
    assert set(by_book) == {"draftkings", "fanduel"}

    dk_market = by_book["draftkings"]["markets"][0]
    assert dk_market["key"] == "player_pass_yds"
    assert {row["name"] for row in dk_market["outcomes"]} == {"Over", "Under"}
    assert {row["point"] for row in dk_market["outcomes"]} == {244.5}

    fd_market = by_book["fanduel"]["markets"][0]
    assert fd_market["key"] == "player_anytime_td"
    assert {row["name"] for row in fd_market["outcomes"]} == {"Yes", "No"}

    snapshot = live.build_market_snapshot(
        player_state_rows=_player_state(),
        provider_events=[normalized],
        captured_at_utc=CAPTURE,
        provider="sportsgameodds",
    )
    by_key = {
        (row["player_id"], row["prop_type"]): row
        for row in snapshot["market_artifacts"]
    }
    assert by_key[("QB1", "passing_yards")]["sportsbook_count"] == 1
    assert by_key[("RB1", "anytime_td")]["consensus_no_vig_probability"] is not None


def test_sportsgameodds_fetch_is_bounded_to_canonical_slate(monkeypatch):
    calls = []

    def fake_get(path, *, api_key, params=None, timeout_seconds=20.0):
        calls.append((path, dict(params or {}), api_key))
        return {"data": [_sportsgameodds_event()], "nextCursor": None}

    monkeypatch.setattr(live, "_sportsgameodds_get_json", fake_get)
    events, raw = live.fetch_sportsgameodds_nfl_prop_events(
        player_state_rows=_player_state(),
        api_key="sgo-secret",
    )

    assert len(events) == 1
    assert raw["provider"] == "sportsgameodds"
    assert calls[0][0] == "/events"
    assert calls[0][1]["leagueID"] == "NFL"
    assert calls[0][1]["includeAltLines"] == "false"
    assert calls[0][1]["includeOpposingOdds"] == "true"
    assert calls[0][1]["startsAfter"]
    assert calls[0][1]["startsBefore"]
    assert "sgo-secret" not in str(raw)


def test_live_provider_fallback_selects_sportsgameodds_after_prior_failures(monkeypatch):
    monkeypatch.setattr(
        live,
        "_provider_get_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            live.PropsMarketLiveError("primary unavailable")
        ),
    )
    monkeypatch.setattr(
        live,
        "_propline_get_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            live.PropsMarketLiveError("propline unavailable")
        ),
    )
    monkeypatch.setattr(
        live,
        "_sportsgameodds_get_json",
        lambda *args, **kwargs: {
            "data": [_sportsgameodds_event()],
            "nextCursor": None,
        },
    )

    events, raw = live.fetch_live_nfl_prop_events_with_fallback(
        player_state_rows=_player_state(),
        the_odds_api_key="primary",
        propline_api_key="propline",
        sportsgameodds_api_key="sgo",
    )

    assert events
    assert raw["provider"] == "sportsgameodds"
    assert raw["provider_attempts"] == [
        {
            "provider": "the_odds_api",
            "status": "failed",
            "detail": "primary unavailable",
        },
        {
            "provider": "propline",
            "status": "failed",
            "detail": "propline unavailable",
        },
        {"provider": "sportsgameodds", "status": "selected"},
    ]


def test_live_provider_fallback_selects_propline_after_primary_failure(monkeypatch):
    def primary_fail(*args, **kwargs):
        raise live.PropsMarketLiveError(
            "The Odds API request failed for /sports/americanfootball_nfl/events with HTTP 401"
        )

    fallback_event = _event()
    fallback_event["id"] = "pl-evt-ari-lar"

    def fallback_get(path, *, api_key, params=None, timeout_seconds=20.0):
        if path.endswith("/events"):
            return [
                {
                    "id": "pl-evt-ari-lar",
                    "home_team": "Arizona Cardinals",
                    "away_team": "Los Angeles Rams",
                    "commence_time": KICKOFF,
                }
            ]
        return fallback_event

    monkeypatch.setattr(live, "_provider_get_json", primary_fail)
    monkeypatch.setattr(live, "_propline_get_json", fallback_get)

    events, raw = live.fetch_live_nfl_prop_events_with_fallback(
        player_state_rows=_player_state(),
        the_odds_api_key="bad-primary",
        propline_api_key="good-fallback",
    )

    assert len(events) == 1
    assert raw["provider"] == "propline"
    assert raw["provider_attempts"] == [
        {
            "provider": "the_odds_api",
            "status": "failed",
            "detail": (
                "The Odds API request failed for /sports/americanfootball_nfl/events "
                "with HTTP 401"
            ),
        },
        {"provider": "propline", "status": "selected"},
    ]


def test_live_provider_fallback_uses_public_propline_demo_when_secrets_missing(monkeypatch):
    calls = []
    fallback_event = _event()
    fallback_event["id"] = "pl-demo-evt-ari-lar"

    def demo_get(path, *, api_key, params=None, timeout_seconds=20.0):
        calls.append((path, api_key))
        assert api_key == live.PROPLINE_PUBLIC_DEMO_KEY
        if path.endswith("/events"):
            return [
                {
                    "id": "pl-demo-evt-ari-lar",
                    "home_team": "Arizona Cardinals",
                    "away_team": "Los Angeles Rams",
                    "commence_time": KICKOFF,
                }
            ]
        return fallback_event

    monkeypatch.setattr(live, "_propline_get_json", demo_get)

    events, raw = live.fetch_live_nfl_prop_events_with_fallback(
        player_state_rows=_player_state(),
    )

    assert len(events) == 1
    assert raw["provider"] == "propline"
    assert raw["credential_mode"] == "shared_public_demo"
    assert raw["provider_attempts"] == [
        {"provider": "the_odds_api", "status": "not_configured"},
        {"provider": "propline", "status": "not_configured"},
        {"provider": "sportsgameodds", "status": "not_configured"},
        {"provider": "propline_demo", "status": "selected"},
    ]
    assert len(calls) == 2


def test_live_provider_fallback_fails_closed_when_all_configured_sources_fail(monkeypatch):
    monkeypatch.setattr(
        live,
        "_provider_get_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            live.PropsMarketLiveError("primary unavailable")
        ),
    )
    monkeypatch.setattr(
        live,
        "_propline_get_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            live.PropsMarketLiveError("fallback unavailable")
        ),
    )
    monkeypatch.setattr(
        live,
        "_sportsgameodds_get_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            live.PropsMarketLiveError("tertiary unavailable")
        ),
    )

    with pytest.raises(live.PropsMarketLiveError, match="all configured"):
        live.fetch_live_nfl_prop_events_with_fallback(
            player_state_rows=_player_state(),
            the_odds_api_key="primary",
            propline_api_key="fallback",
            sportsgameodds_api_key="tertiary",
        )



def test_nflverse_la_player_state_matches_rams_provider_event():
    state = []
    for row in _player_state():
        updated = dict(row)
        if updated["team"] == "LAR":
            updated["team"] = "LA"
        if updated["opponent"] == "LAR":
            updated["opponent"] = "LA"
        updated["game_id"] = "2026_03_ARI_LA"
        state.append(updated)

    event = _event()
    snapshot = live.build_market_snapshot(
        player_state_rows=state,
        provider_events=[event],
        captured_at_utc=CAPTURE,
    )
    assert snapshot["audit"]["matched_event_count"] == 1
    assert snapshot["audit"]["unmatched_event_count"] == 0
    assert snapshot["market_artifacts"]
    assert all(
        row["game_id"] == "2026_03_ARI_LA"
        for row in snapshot["market_artifacts"]
    )


def test_live_fetch_audits_unmatched_provider_event_identity(monkeypatch):
    def fake_get(path, *, api_key, params=None, timeout_seconds=20.0):
        if path.endswith("/events"):
            return [
                {
                    "id": "evt-unmatched",
                    "home_team": "Mystery Home",
                    "away_team": "Mystery Away",
                    "commence_time": KICKOFF,
                }
            ]
        raise AssertionError("unmatched event must not fetch event odds")

    monkeypatch.setattr(live, "_provider_get_json", fake_get)
    events, raw = live.fetch_live_nfl_prop_events(
        player_state_rows=_player_state(),
        api_key="test-key",
    )

    assert events == []
    assert raw["discovery_unmatched"] == [
        {
            "provider_event_id": "evt-unmatched",
            "home_team": "Mystery Home",
            "away_team": "Mystery Away",
            "commence_time": KICKOFF,
            "reason": "unresolved_provider_team",
        }
    ]

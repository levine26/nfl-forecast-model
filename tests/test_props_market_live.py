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


def test_provider_team_aliases_cover_los_angeles_teams_without_guessing_player_identity():
    assert live.provider_team_code("Los Angeles Rams") == "LAR"
    assert live.provider_team_code("LA Rams") == "LAR"
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

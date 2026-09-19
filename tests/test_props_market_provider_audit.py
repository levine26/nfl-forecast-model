from __future__ import annotations

from nfl_forecast import props_market_live as live

KICKOFF = "2026-09-20T20:05:00+00:00"


def _player_state():
    return [
        {
            "game_id": "2026_03_LAR_ARI",
            "player_id": "QB1",
            "player_name": "Kyler Murray",
            "position": "QB",
            "team": "ARI",
            "opponent": "LAR",
            "kickoff_timestamp": KICKOFF,
        },
        {
            "game_id": "2026_03_LAR_ARI",
            "player_id": "QB2",
            "player_name": "Matthew Stafford",
            "position": "QB",
            "team": "LAR",
            "opponent": "ARI",
            "kickoff_timestamp": KICKOFF,
        },
    ]


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

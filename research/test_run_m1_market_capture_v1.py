from __future__ import annotations

from datetime import datetime, timedelta, timezone

from research.run_m1_market_capture_v1 import normalize_team_token, resolve_event

KICKOFF = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)


def _event(event_id: str, away: str, home: str, kickoff: datetime) -> dict:
    return {
        "id": event_id,
        "away_team": away,
        "home_team": home,
        "commence_time": kickoff.isoformat().replace("+00:00", "Z"),
        "bookmakers": [],
    }


def test_team_normalizer_accepts_provider_names_and_schedule_abbreviations() -> None:
    assert normalize_team_token("Atlanta Falcons") == "ATL"
    assert normalize_team_token("ATL") == "ATL"
    assert normalize_team_token("Los Angeles Rams") == "LA"
    assert normalize_team_token("LAR") == "LA"


def test_event_resolution_handles_full_name_provider_against_abbreviation_slate() -> None:
    events = [_event("evt", "Atlanta Falcons", "Green Bay Packers", KICKOFF)]
    matched = resolve_event(events, away_team="ATL", home_team="GB", kickoff_timestamp_utc=KICKOFF)
    assert matched is not None
    assert matched["id"] == "evt"


def test_event_resolution_accepts_small_kickoff_revision_but_rejects_large_revision() -> None:
    accepted = [_event("evt", "ATL", "GB", KICKOFF + timedelta(minutes=20))]
    assert resolve_event(accepted, away_team="ATL", home_team="GB", kickoff_timestamp_utc=KICKOFF) is not None

    rejected = [_event("evt", "ATL", "GB", KICKOFF + timedelta(minutes=31))]
    assert resolve_event(rejected, away_team="ATL", home_team="GB", kickoff_timestamp_utc=KICKOFF) is None


def test_event_resolution_fails_closed_on_ambiguity() -> None:
    events = [
        _event("evt-a", "ATL", "GB", KICKOFF),
        _event("evt-b", "Atlanta Falcons", "Green Bay Packers", KICKOFF + timedelta(minutes=5)),
    ]
    assert resolve_event(events, away_team="ATL", home_team="GB", kickoff_timestamp_utc=KICKOFF) is None

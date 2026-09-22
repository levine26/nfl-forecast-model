from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from research.market_capture_contract_v2 import (
    LEDGER_IDENTITY_COLUMNS,
    MIN_CONSENSUS_BOOKS,
    QUALIFYING_CLOSE_ROW_TYPE,
    attempt_identity,
)
from research.market_capture_v2 import (
    american_implied,
    consensus_row,
    due_horizons,
    normalize_bookmaker,
    two_way_metrics,
)
from research.run_market_capture_v2 import (
    MAX_EVENT_KICKOFF_DELTA_MINUTES,
    PROPLINE_API_URL,
    THE_ODDS_API_URL,
    _captured_pairs,
    _match_event,
    _provider_configs,
    _request_market_events,
)


def _event(event_id: str = "evt-1", commence_time: str = "2026-09-13T17:00:00Z"):
    return {
        "id": event_id,
        "home_team": "Chicago Bears",
        "away_team": "Carolina Panthers",
        "commence_time": commence_time,
    }


def _book(key: str, home_ml: object, away_ml: object, spread: object, total: object):
    return {
        "key": key,
        "title": key.upper(),
        "last_update": "2026-09-13T14:58:00Z",
        "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Chicago Bears", "price": home_ml},
                {"name": "Carolina Panthers", "price": away_ml},
            ]},
            {"key": "spreads", "outcomes": [
                {"name": "Chicago Bears", "price": -110, "point": spread},
                {"name": "Carolina Panthers", "price": -110, "point": -float(spread) if isinstance(spread, (int, float)) else spread},
            ]},
            {"key": "totals", "outcomes": [
                {"name": "Over", "price": -108, "point": total},
                {"name": "Under", "price": -112, "point": total},
            ]},
        ],
    }


def _normalized(key: str = "book-a", *, event: dict | None = None, request_time: datetime | None = None):
    now = request_time or datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    return normalize_bookmaker(
        event=event or _event(), bookmaker=_book(key, -150, 130, -3.0, 44.5),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc),
        request_timestamp_utc=now, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )


def test_american_and_devig_metrics_preserve_overround() -> None:
    assert round(american_implied(-110), 6) == round(110 / 210, 6)
    metrics = two_way_metrics(-110, -110)
    assert metrics["overround"] > 0
    assert abs(metrics["first_no_vig"] - 0.5) < 1e-12
    assert abs(metrics["first_no_vig"] + metrics["second_no_vig"] - 1) < 1e-12


def test_american_odds_reject_zero_nan_and_infinity() -> None:
    for value in (0, float("nan"), float("inf"), float("-inf")):
        try:
            american_implied(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected malformed odds to fail: {value!r}")


def test_due_horizons_only_fire_near_preregistered_targets() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    due = due_horizons(kickoff, datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc))
    assert [row["horizon"] for row in due] == ["T-120m"]
    assert due_horizons(kickoff, datetime(2026, 9, 13, 15, 30, tzinfo=timezone.utc)) == []


def test_event_identity_requires_matchup_and_kickoff_proximity() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    current = _event("current", "2026-09-13T17:00:00Z")
    rematch = _event("future-rematch", "2026-11-15T18:00:00Z")
    resolved = _match_event(
        [rematch, current],
        away_team="CAR",
        home_team="CHI",
        kickoff_timestamp_utc=kickoff,
    )
    assert resolved is not None
    assert resolved["id"] == "current"
    assert MAX_EVENT_KICKOFF_DELTA_MINUTES == 30.0

    too_far = _event("shifted", "2026-09-13T17:31:00Z")
    assert _match_event(
        [too_far],
        away_team="CAR",
        home_team="CHI",
        kickoff_timestamp_utc=kickoff,
    ) is None

    duplicate = _event("duplicate", "2026-09-13T17:00:00Z")
    assert _match_event(
        [current, duplicate],
        away_team="CAR",
        home_team="CHI",
        kickoff_timestamp_utc=kickoff,
    ) is None


def test_book_snapshot_keeps_moneyline_spread_total_freshness_and_event_time() -> None:
    row = _normalized()
    assert row is not None
    assert row["home_moneyline"] == -150
    assert row["home_spread"] == -3.0
    assert row["total_points"] == 44.5
    assert row["h2h_overround"] > 0
    assert row["freshness_minutes"] == 2.0
    assert row["provider_commence_time_utc"] == "2026-09-13T17:00:00+00:00"
    assert row["provider_kickoff_delta_minutes"] == 0.0
    assert row["research_only"] is True
    assert row["production_authorized"] is False


def test_malformed_h2h_book_is_skipped_and_optional_markets_degrade_to_missing() -> None:
    now = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    bad_h2h = normalize_bookmaker(
        event=_event(), bookmaker=_book("bad", "not-a-price", 130, -3.0, 44.5),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=now,
        request_timestamp_utc=now, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )
    assert bad_h2h is None

    optional_bad = normalize_bookmaker(
        event=_event(), bookmaker=_book("partial", -150, 130, "bad-spread", "bad-total"),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=now,
        request_timestamp_utc=now, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )
    assert optional_bad is not None
    assert optional_bad["home_spread"] is None
    assert optional_bad["total_points"] is None


def test_consensus_retains_source_count_market_dispersion_and_event_identity() -> None:
    now = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    rows = [normalize_bookmaker(
        event=_event(), bookmaker=_book(key, home, away, spread, total),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=now,
        request_timestamp_utc=now, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    ) for key, home, away, spread, total in [
        ("book-a", -150, 130, -3.0, 44.5),
        ("book-b", -145, 125, -2.5, 45.0),
        ("book-c", -155, 135, -3.0, 44.0),
    ]]
    consensus = consensus_row([row for row in rows if row])
    assert consensus is not None
    assert consensus["source_count"] == 3
    assert consensus["sportsbook_key"] == "sportsbook_consensus"
    assert consensus["event_id"] == "evt-1"
    assert consensus["provider_commence_time_utc"] == "2026-09-13T17:00:00+00:00"
    assert consensus["provider_kickoff_delta_minutes"] == 0.0
    assert consensus["probability_range"] > 0
    assert consensus["home_spread"] == -3.0
    assert consensus["total_points"] == 44.5
    assert QUALIFYING_CLOSE_ROW_TYPE == "consensus"
    assert MIN_CONSENSUS_BOOKS == 5


def test_consensus_rejects_duplicate_books_or_mixed_event_identity() -> None:
    first = _normalized("book-a")
    second = _normalized("book-b")
    assert first is not None and second is not None
    duplicate = dict(first)
    duplicate["h2h_home_no_vig"] = 0.6
    assert consensus_row([first, duplicate]) is None

    mixed_event = dict(second)
    mixed_event["event_id"] = "different-event"
    assert consensus_row([first, mixed_event]) is None

    mixed_request = dict(second)
    mixed_request["request_timestamp_utc"] = "2026-09-13T15:01:00+00:00"
    assert consensus_row([first, mixed_request]) is None


def test_retry_attempts_have_distinct_append_only_identity() -> None:
    first_time = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(minutes=5)
    first = _normalized("book-a", request_time=first_time)
    second = _normalized("book-a", request_time=second_time)
    assert first is not None and second is not None
    assert "request_timestamp_utc" in LEDGER_IDENTITY_COLUMNS
    assert attempt_identity(first) != attempt_identity(second)


def test_only_qualified_multibook_consensus_closes_a_horizon(tmp_path) -> None:
    ledger = tmp_path / "ledger.csv"
    pd.DataFrame([
        {
            "game_id": "game-a",
            "horizon": "T-120m",
            "row_type": "book",
            "sportsbook_key": "book-a",
            "source_count": None,
            "timing_error_minutes": 0.0,
        },
        {
            "game_id": "game-a",
            "horizon": "T-120m",
            "row_type": "consensus",
            "sportsbook_key": "sportsbook_consensus",
            "source_count": 1,
            "timing_error_minutes": 0.0,
        },
        {
            "game_id": "game-b",
            "horizon": "T-60m",
            "row_type": "consensus",
            "sportsbook_key": "sportsbook_consensus",
            "source_count": MIN_CONSENSUS_BOOKS,
            "timing_error_minutes": 0.0,
        },
    ]).to_csv(ledger, index=False)

    assert _captured_pairs(ledger) == {("game-b", "T-60m")}

    legacy = tmp_path / "legacy.csv"
    pd.DataFrame([
        {
            "game_id": "game-c",
            "horizon": "T-30m",
            "row_type": "consensus",
        }
    ]).to_csv(legacy, index=False)
    assert _captured_pairs(legacy) == set()



class _FakeResponse:
    def __init__(self, *, payload=None, status_code=200, headers=None):
        self._payload = [] if payload is None else payload
        self.status_code = status_code
        self.headers = headers or {}
        self.url = "https://provider.invalid/?apiKey=should-never-be-surfaced"

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = RuntimeError(f"http status {self.status_code}")
            exc.response = self
            raise exc

    def json(self):
        return self._payload


def test_provider_config_prefers_propline_and_uses_header_auth(monkeypatch) -> None:
    monkeypatch.setenv("PROPLINE_API_KEY", "prop-secret")
    monkeypatch.setenv("THE_ODDS_API_KEY", "odds-secret")
    providers = _provider_configs()
    assert [row["name"] for row in providers] == ["propline", "the_odds_api"]
    assert providers[0]["url"] == PROPLINE_API_URL
    assert providers[0]["headers"] == {"X-API-Key": "prop-secret"}
    assert "apiKey" not in providers[0]["params"]
    assert providers[1]["url"] == THE_ODDS_API_URL
    assert providers[1]["params"]["apiKey"] == "odds-secret"


def test_provider_failover_does_not_surface_credentials(monkeypatch) -> None:
    monkeypatch.setenv("PROPLINE_API_KEY", "prop-secret")
    monkeypatch.setenv("THE_ODDS_API_KEY", "odds-secret")
    calls = []

    def fake_get(url, *, params=None, headers=None, timeout=None):
        calls.append((url, params, headers))
        if url == PROPLINE_API_URL:
            return _FakeResponse(status_code=503)
        return _FakeResponse(payload=[{"id": "evt"}], status_code=200)

    monkeypatch.setattr("research.run_market_capture_v2.requests.get", fake_get)
    provider, response, events, failures, cost = _request_market_events(_provider_configs())
    assert provider == "the_odds_api"
    assert response.status_code == 200
    assert events == [{"id": "evt"}]
    assert failures == [{"provider": "propline", "error_type": "RuntimeError", "http_status": 503}]
    assert cost == 3
    rendered = repr(failures)
    assert "prop-secret" not in rendered
    assert "odds-secret" not in rendered


def test_all_provider_failures_expose_only_safe_metadata(monkeypatch) -> None:
    monkeypatch.setenv("PROPLINE_API_KEY", "prop-secret")
    monkeypatch.setenv("THE_ODDS_API_KEY", "odds-secret")

    def fake_get(url, *, params=None, headers=None, timeout=None):
        return _FakeResponse(status_code=401)

    monkeypatch.setattr("research.run_market_capture_v2.requests.get", fake_get)
    try:
        _request_market_events(_provider_configs())
    except RuntimeError as exc:
        text = str(exc)
        assert "propline:RuntimeError:401" in text
        assert "the_odds_api:RuntimeError:401" in text
        assert "prop-secret" not in text
        assert "odds-secret" not in text
        assert "apiKey=" not in text
    else:
        raise AssertionError("expected all-provider failure")


def test_due_horizons_never_accept_post_cutoff_capture() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    target = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    early = due_horizons(kickoff, target - timedelta(minutes=5))
    exact = due_horizons(kickoff, target)
    late = due_horizons(kickoff, target + timedelta(minutes=1))
    assert [row["horizon"] for row in early] == ["T-120m"]
    assert [row["horizon"] for row in exact] == ["T-120m"]
    assert late == []


def test_late_consensus_never_closes_horizon(tmp_path) -> None:
    ledger = tmp_path / "ledger.csv"
    pd.DataFrame([
        {
            "game_id": "game-late",
            "horizon": "T-60m",
            "row_type": "consensus",
            "sportsbook_key": "sportsbook_consensus",
            "source_count": MIN_CONSENSUS_BOOKS,
            "timing_error_minutes": 1.0,
        },
        {
            "game_id": "game-early",
            "horizon": "T-60m",
            "row_type": "consensus",
            "sportsbook_key": "sportsbook_consensus",
            "source_count": MIN_CONSENSUS_BOOKS,
            "timing_error_minutes": -1.0,
        },
    ]).to_csv(ledger, index=False)
    assert _captured_pairs(ledger) == {("game-early", "T-60m")}

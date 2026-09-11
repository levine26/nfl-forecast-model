from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def _event():
    return {
        "id": "evt-1",
        "home_team": "Chicago Bears",
        "away_team": "Carolina Panthers",
    }


def _book(key: str, home_ml: int, away_ml: int, spread: float, total: float):
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
                {"name": "Carolina Panthers", "price": -110, "point": -spread},
            ]},
            {"key": "totals", "outcomes": [
                {"name": "Over", "price": -108, "point": total},
                {"name": "Under", "price": -112, "point": total},
            ]},
        ],
    }


def test_american_and_devig_metrics_preserve_overround() -> None:
    assert round(american_implied(-110), 6) == round(110 / 210, 6)
    metrics = two_way_metrics(-110, -110)
    assert metrics["overround"] > 0
    assert abs(metrics["first_no_vig"] - 0.5) < 1e-12
    assert abs(metrics["first_no_vig"] + metrics["second_no_vig"] - 1) < 1e-12


def test_due_horizons_only_fire_near_preregistered_targets() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    due = due_horizons(kickoff, datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc))
    assert [row["horizon"] for row in due] == ["T-120m"]
    assert due_horizons(kickoff, datetime(2026, 9, 13, 15, 30, tzinfo=timezone.utc)) == []


def test_book_snapshot_keeps_moneyline_spread_total_and_freshness() -> None:
    now = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    row = normalize_bookmaker(
        event=_event(), bookmaker=_book("book-a", -150, 130, -3.0, 44.5),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=now,
        request_timestamp_utc=now, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )
    assert row is not None
    assert row["home_moneyline"] == -150
    assert row["home_spread"] == -3.0
    assert row["total_points"] == 44.5
    assert row["h2h_overround"] > 0
    assert row["freshness_minutes"] == 2.0
    assert row["research_only"] is True
    assert row["production_authorized"] is False


def test_consensus_retains_source_count_and_market_dispersion() -> None:
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
    assert consensus["probability_range"] > 0
    assert consensus["home_spread"] == -3.0
    assert consensus["total_points"] == 44.5
    assert QUALIFYING_CLOSE_ROW_TYPE == "consensus"
    assert MIN_CONSENSUS_BOOKS == 2


def test_retry_attempts_have_distinct_append_only_identity() -> None:
    first_time = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    second_time = first_time + timedelta(minutes=5)
    first = normalize_bookmaker(
        event=_event(), bookmaker=_book("book-a", -150, 130, -3.0, 44.5),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=first_time,
        request_timestamp_utc=first_time, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )
    second = normalize_bookmaker(
        event=_event(), bookmaker=_book("book-a", -160, 140, -3.5, 45.0),
        game_id="2026_01_CAR_CHI", home_team="CHI", away_team="CAR",
        horizon="T-120m", target_timestamp_utc=first_time,
        request_timestamp_utc=second_time, kickoff_timestamp_utc=datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc),
    )
    assert first is not None and second is not None
    assert "request_timestamp_utc" in LEDGER_IDENTITY_COLUMNS
    assert attempt_identity(first) != attempt_identity(second)

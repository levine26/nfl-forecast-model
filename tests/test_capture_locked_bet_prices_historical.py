from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import scripts.capture_locked_bet_prices as capture_mod


def test_historical_backfill_uses_archived_snapshot_only_when_probability_matches(monkeypatch):
    home_ml, away_ml = -150, 130
    probability = capture_mod.vig_free_home_probability(home_ml, away_ml)
    history = pd.DataFrame([{
        "game_id": "2026_01_A_B",
        "season": 2026,
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-09-13T15:00:00+00:00",
        "market_home_prob": probability,
    }])
    archived = pd.DataFrame([{
        "game_id": "2026_01_A_B",
        "season": 2026,
        "home_moneyline": home_ml,
        "away_moneyline": away_ml,
    }])

    monkeypatch.setattr(
        capture_mod,
        "_historical_market_snapshot",
        lambda lock_utc: (archived, "abc123"),
    )

    ledger, changed = capture_mod._historical_backfill(
        history,
        capture_mod._empty_ledger(),
        season=2026,
    )

    assert changed == 1
    assert ledger.loc[0, "locked_home_moneyline"] == home_ml
    assert ledger.loc[0, "locked_away_moneyline"] == away_ml
    assert ledger.loc[0, "bet_price_source"].startswith("nflverse_git:abc123_")


def test_historical_backfill_fails_closed_on_nonmatching_archived_snapshot(monkeypatch):
    probability = capture_mod.vig_free_home_probability(-150, 130)
    history = pd.DataFrame([{
        "game_id": "2026_01_A_B",
        "season": 2026,
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-09-13T15:00:00+00:00",
        "market_home_prob": probability,
    }])
    different = pd.DataFrame([{
        "game_id": "2026_01_A_B",
        "season": 2026,
        "home_moneyline": -200,
        "away_moneyline": 170,
    }])

    monkeypatch.setattr(
        capture_mod,
        "_historical_market_snapshot",
        lambda lock_utc: (different, "def456"),
    )

    ledger, changed = capture_mod._historical_backfill(
        history,
        capture_mod._empty_ledger(),
        season=2026,
    )

    assert changed == 0
    assert ledger.empty


def test_lock_timestamp_normalization_is_utc():
    parsed = capture_mod._lock_timestamp("2026-09-13T08:00:00-07:00")
    assert parsed == datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import scripts.capture_locked_bet_prices as bet_prices
from scripts.capture_locked_bet_prices import (
    enrich_price_ledger,
    vig_free_home_probability,
)


def _receipt(game_id: str, market_home_prob: float) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-09-14T15:00:00+00:00",
        "market_home_prob": market_home_prob,
    }


def test_appends_moneyline_only_when_pair_reproduces_locked_market_probability():
    home_ml, away_ml = -170, 142
    locked_probability = vig_free_home_probability(home_ml, away_ml)
    history = pd.DataFrame([_receipt("2026_01_ARI_LAC", locked_probability)])
    market = pd.DataFrame([
        {
            "game_id": "2026_01_ARI_LAC",
            "season": 2026,
            "home_moneyline": home_ml,
            "away_moneyline": away_ml,
        }
    ])

    ledger, changed = enrich_price_ledger(
        history,
        market,
        verified_utc=datetime(2026, 9, 14, 15, 1, tzinfo=timezone.utc),
    )

    assert changed == 1
    assert ledger.loc[0, "locked_home_moneyline"] == home_ml
    assert ledger.loc[0, "locked_away_moneyline"] == away_ml
    assert ledger.loc[0, "bet_price_source"] == "nflverse_moneyline_verified_against_locked_market_probability"


def test_rejects_later_market_pair_when_it_does_not_match_immutable_receipt():
    locked_probability = vig_free_home_probability(-170, 142)
    history = pd.DataFrame([_receipt("2026_01_ARI_LAC", locked_probability)])
    later_market = pd.DataFrame([
        {
            "game_id": "2026_01_ARI_LAC",
            "season": 2026,
            "home_moneyline": -190,
            "away_moneyline": 160,
        }
    ])

    ledger, changed = enrich_price_ledger(history, later_market)

    assert changed == 0
    assert ledger.empty


def test_append_only_ledger_never_overwrites_existing_price_receipt():
    locked_probability = vig_free_home_probability(-170, 142)
    history = pd.DataFrame([_receipt("2026_01_ARI_LAC", locked_probability)])
    existing = pd.DataFrame([
        {
            "game_id": "2026_01_ARI_LAC",
            "season": 2026,
            "lock_timestamp_utc": "2026-09-14T15:00:00+00:00",
            "locked_home_moneyline": -165,
            "locked_away_moneyline": 140,
            "bet_price_source": "existing_receipt",
            "bet_price_verified_utc": "2026-09-14T15:00:30+00:00",
        }
    ])
    market = pd.DataFrame([
        {
            "game_id": "2026_01_ARI_LAC",
            "season": 2026,
            "home_moneyline": -170,
            "away_moneyline": 142,
        }
    ])

    ledger, changed = enrich_price_ledger(history, market, existing)

    assert changed == 0
    assert ledger.loc[0, "locked_home_moneyline"] == -165
    assert ledger.loc[0, "locked_away_moneyline"] == 140
    assert ledger.loc[0, "bet_price_source"] == "existing_receipt"


def test_does_not_import_later_spread_juice_without_lock_time_proof():
    home_ml, away_ml = -170, 142
    locked_probability = vig_free_home_probability(home_ml, away_ml)
    history = pd.DataFrame([_receipt("2026_01_ARI_LAC", locked_probability)])
    market = pd.DataFrame([
        {
            "game_id": "2026_01_ARI_LAC",
            "season": 2026,
            "home_moneyline": home_ml,
            "away_moneyline": away_ml,
            "home_spread_price": -118,
            "away_spread_price": -102,
        }
    ])

    ledger, changed = enrich_price_ledger(history, market)

    assert changed == 1
    assert "locked_home_spread_price" not in ledger.columns
    assert "locked_away_spread_price" not in ledger.columns


def test_historical_backfill_walks_backward_until_exact_snapshot_matches(monkeypatch):
    locked_probability = vig_free_home_probability(142, -170)
    history = pd.DataFrame([
        {
            **_receipt("2026_01_CHI_CAR", locked_probability),
            "lock_timestamp_utc": "2026-09-13T15:37:41.752256+00:00",
        }
    ])
    newer_market = pd.DataFrame([
        {
            "game_id": "2026_01_CHI_CAR",
            "season": 2026,
            "home_moneyline": 140,
            "away_moneyline": -166,
        }
    ])
    matching_market = pd.DataFrame([
        {
            "game_id": "2026_01_CHI_CAR",
            "season": 2026,
            "home_moneyline": 142,
            "away_moneyline": -170,
        }
    ])

    monkeypatch.setattr(
        bet_prices,
        "_nflverse_snapshot_shas_at_or_before",
        lambda _lock_utc: ["newer-sha", "matching-sha"],
    )
    monkeypatch.setattr(
        bet_prices,
        "_historical_market_snapshot_by_sha",
        lambda sha: newer_market if sha == "newer-sha" else matching_market,
    )

    ledger, changed = bet_prices._historical_backfill(
        history,
        bet_prices._empty_ledger(),
        season=2026,
    )

    assert changed == 1
    assert ledger.loc[0, "locked_home_moneyline"] == 142
    assert ledger.loc[0, "locked_away_moneyline"] == -170
    assert ledger.loc[0, "bet_price_source"] == (
        "nflverse_git:matching-sha_verified_against_locked_market_probability"
    )

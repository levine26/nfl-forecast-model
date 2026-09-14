from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from scripts.capture_locked_bet_prices import (
    enrich_locked_bet_prices,
    vig_free_home_probability,
)


def _receipt(game_id: str, market_home_prob: float) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "lock_status": "LOCKED",
        "market_home_prob": market_home_prob,
    }


def test_backfills_moneyline_only_when_pair_reproduces_locked_market_probability():
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

    enriched, changed = enrich_locked_bet_prices(
        history,
        market,
        verified_utc=datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc),
    )

    assert changed == 1
    assert enriched.loc[0, "locked_home_moneyline"] == home_ml
    assert enriched.loc[0, "locked_away_moneyline"] == away_ml
    assert enriched.loc[0, "bet_price_source"] == "nflverse_moneyline_verified_against_locked_market_probability"


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

    enriched, changed = enrich_locked_bet_prices(history, later_market)

    assert changed == 0
    assert pd.isna(enriched.loc[0, "locked_home_moneyline"])
    assert pd.isna(enriched.loc[0, "locked_away_moneyline"])


def test_never_overwrites_an_existing_locked_moneyline_pair():
    locked_probability = vig_free_home_probability(-170, 142)
    history = pd.DataFrame([
        {
            **_receipt("2026_01_ARI_LAC", locked_probability),
            "locked_home_moneyline": -165,
            "locked_away_moneyline": 140,
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

    enriched, changed = enrich_locked_bet_prices(history, market)

    assert changed == 0
    assert enriched.loc[0, "locked_home_moneyline"] == -165
    assert enriched.loc[0, "locked_away_moneyline"] == 140


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

    enriched, changed = enrich_locked_bet_prices(history, market)

    assert changed == 1
    assert pd.isna(enriched.loc[0, "locked_home_spread_price"])
    assert pd.isna(enriched.loc[0, "locked_away_spread_price"])

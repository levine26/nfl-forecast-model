from __future__ import annotations

import pandas as pd

from nfl_forecast.market_t120 import select_t120_market_snapshots


def _row(ts: str, prob: float | None, game_id: str = "2026_01_A_B") -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-13",
        "gametime": "13:00",
        "away_team": "A",
        "home_team": "B",
        "snapshot_type": "MARKET",
        "prediction_timestamp_utc": ts,
        "prediction_id": f"{game_id}__MARKET__{ts}",
        "market_home_prob": prob,
        "pure_home_prob": 0.60,
        "final_home_prob": None if prob is None else 0.75 * 0.60 + 0.25 * prob,
        "spread_line": 2.5,
        "total_line": 44.5,
    }


def test_t120_selector_uses_latest_snapshot_at_or_before_cutoff():
    # 1 PM ET kickoff = 17:00 UTC; T-120 cutoff = 15:00 UTC.
    runs = pd.DataFrame([
        _row("2026-09-13T13:35:00+00:00", 0.51),
        _row("2026-09-13T14:35:00+00:00", 0.53),
        _row("2026-09-13T15:05:00+00:00", 0.59),  # forbidden lookahead
    ])
    result = select_t120_market_snapshots(runs)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["market_home_prob"] == 0.53
    assert row["snapshot_timestamp_utc"].startswith("2026-09-13T14:35:00")
    assert row["minutes_to_kickoff_at_snapshot"] == 145.0
    assert row["staleness_minutes_vs_t120"] == 25.0
    assert bool(row["no_lookahead"]) is True


def test_t120_selector_omits_game_when_only_post_cutoff_market_exists():
    runs = pd.DataFrame([_row("2026-09-13T15:01:00+00:00", 0.57)])
    result = select_t120_market_snapshots(runs)
    assert result.empty


def test_t120_selector_uses_prior_valid_market_when_latest_pre_cutoff_row_is_null():
    runs = pd.DataFrame([
        _row("2026-09-13T14:20:00+00:00", 0.52),
        _row("2026-09-13T14:55:00+00:00", None),
    ])
    result = select_t120_market_snapshots(runs)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["market_home_prob"] == 0.52
    assert row["snapshot_timestamp_utc"].startswith("2026-09-13T14:20:00")
    assert row["staleness_minutes_vs_t120"] == 40.0


def test_t120_selector_ignores_non_market_rows_and_can_attach_results():
    market = _row("2026-09-13T14:55:00+00:00", 0.54)
    early = dict(market)
    early["snapshot_type"] = "EARLY"
    early["prediction_timestamp_utc"] = "2026-09-13T14:59:00+00:00"
    early["market_home_prob"] = 0.99
    official = pd.DataFrame([{
        "game_id": market["game_id"],
        "actual_home_score": 24,
        "actual_away_score": 20,
    }])
    result = select_t120_market_snapshots(pd.DataFrame([market, early]), official)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["market_home_prob"] == 0.54
    assert bool(row["graded"]) is True
    assert bool(row["actual_home_win"]) is True


def test_t120_selector_excludes_ties_from_binary_grading():
    market = _row("2026-09-13T14:55:00+00:00", 0.54)
    official = pd.DataFrame([{
        "game_id": market["game_id"],
        "actual_home_score": 20,
        "actual_away_score": 20,
    }])
    result = select_t120_market_snapshots(pd.DataFrame([market]), official)
    assert len(result) == 1
    row = result.iloc[0]
    assert bool(row["graded"]) is False
    assert pd.isna(row["actual_home_win"])

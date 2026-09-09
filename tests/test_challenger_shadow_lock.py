from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_v06 import logit_blend_probabilities
from scripts.lock_challenger_shadow import HISTORY_COLUMNS, lock_shadow


def _production(
    *,
    game_id="2026_01_AWAY_HOME",
    snapshot="FINAL",
    market=0.60,
    gameday="2026-09-10",
    gametime="20:00",
):
    return pd.DataFrame([{
        "game_id": game_id,
        "season": 2026,
        "week": 1,
        "gameday": gameday,
        "gametime": gametime,
        "away_team": "AWAY",
        "home_team": "HOME",
        "market_home_prob": market,
        "snapshot_type": snapshot,
        "model_version": "0.4.0-accountability",
        "prediction_timestamp_utc": "2026-09-10T22:25:00+00:00",
    }])


def _challenger(
    *,
    game_id="2026_01_AWAY_HOME",
    pure=0.55,
    stale_market=0.52,
    stale_final=0.53,
    weight=0.25,
    method="logit",
):
    return pd.DataFrame([{
        "game_id": game_id,
        "challenger_pure_home_prob": pure,
        "market_home_prob": stale_market,
        "challenger_final_home_prob": stale_final,
        "challenger_pick": "HOME",
        "effective_pure_weight": weight,
        "effective_market_weight": 1.0 - weight,
        "research_candidate": "Logit hybrid adaptive Brier",
        "research_method": method,
    }])


def _now(minutes_before_kickoff: int):
    # 2026-09-10 20:00 ET is 2026-09-11 00:00 UTC during EDT.
    return datetime(2026, 9, 11, 0, 0, tzinfo=timezone.utc) - pd.Timedelta(
        minutes=minutes_before_kickoff
    )


def test_locks_due_final_game_and_recomputes_from_t120_market():
    production = _production(market=0.66)
    challenger = _challenger(pure=0.54, stale_market=0.51, stale_final=0.52, weight=0.25)
    history, added = lock_shadow(
        production,
        challenger,
        now_utc=_now(90),
    )
    assert added == 1
    assert len(history) == 1
    row = history.iloc[0]
    expected = logit_blend_probabilities([0.54], [0.66], 0.25)[0]
    assert np.isclose(row.challenger_final_home_prob, expected)
    assert np.isclose(row.market_home_prob_t120, 0.66)
    assert not np.isclose(row.challenger_final_home_prob, 0.52)
    assert row.production_snapshot_type == "FINAL"
    assert row.lock_status == "LOCKED"
    assert 0 < float(row.minutes_to_kickoff_at_shadow_lock) <= 120


def test_does_not_lock_early_snapshot_or_outside_window_or_after_kickoff():
    challenger = _challenger()
    early, added_early = lock_shadow(
        _production(snapshot="EARLY"), challenger, now_utc=_now(90)
    )
    outside, added_outside = lock_shadow(
        _production(snapshot="FINAL"), challenger, now_utc=_now(121)
    )
    after, added_after = lock_shadow(
        _production(snapshot="FINAL"), challenger, now_utc=_now(-1)
    )
    assert added_early == added_outside == added_after == 0
    assert early.empty and outside.empty and after.empty


def test_existing_lock_is_immutable_when_market_moves():
    production = _production(market=0.61)
    challenger = _challenger(pure=0.56, weight=0.25)
    first, added = lock_shadow(production, challenger, now_utc=_now(100))
    assert added == 1
    first_prob = float(first.iloc[0].challenger_final_home_prob)
    first_market = float(first.iloc[0].market_home_prob_t120)

    moved = _production(market=0.85)
    second, added_again = lock_shadow(
        moved, challenger, existing_history=first, now_utc=_now(60)
    )
    assert added_again == 0
    assert len(second) == 1
    assert np.isclose(float(second.iloc[0].challenger_final_home_prob), first_prob)
    assert np.isclose(float(second.iloc[0].market_home_prob_t120), first_market)


def test_missing_market_falls_back_to_pure_like_production():
    production = _production(market=np.nan)
    challenger = _challenger(pure=0.57, weight=0.25)
    history, added = lock_shadow(production, challenger, now_utc=_now(80))
    assert added == 1
    assert np.isclose(float(history.iloc[0].challenger_final_home_prob), 0.57)


def test_rejects_hybrid_below_pure_floor_and_unknown_method():
    with pytest.raises(RuntimeError, match="PURE floor"):
        lock_shadow(
            _production(), _challenger(weight=0.20), now_utc=_now(90)
        )
    with pytest.raises(RuntimeError, match="Unsupported challenger shadow method"):
        lock_shadow(
            _production(), _challenger(method="confidence", weight=0.25), now_utc=_now(90)
        )


def test_grades_existing_lock_without_changing_forecast():
    production = _production(market=0.65)
    challenger = _challenger(pure=0.55, weight=0.25)
    history, _ = lock_shadow(production, challenger, now_utc=_now(90))
    locked_prob = float(history.iloc[0].challenger_final_home_prob)
    production_history = pd.DataFrame([{
        "game_id": "2026_01_AWAY_HOME",
        "actual_home_score": 24,
        "actual_away_score": 17,
    }])
    graded, added = lock_shadow(
        production,
        challenger,
        existing_history=history,
        production_history=production_history,
        now_utc=_now(60),
    )
    assert added == 0
    assert np.isclose(float(graded.iloc[0].challenger_final_home_prob), locked_prob)
    assert float(graded.iloc[0].actual_home_score) == 24
    assert float(graded.iloc[0].actual_away_score) == 17
    assert bool(graded.iloc[0].winner_correct) is True
    assert list(graded.columns) == HISTORY_COLUMNS

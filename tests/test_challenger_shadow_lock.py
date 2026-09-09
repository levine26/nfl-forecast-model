from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_shadow import (
    HISTORY_COLUMNS,
    LEGACY_VERSION,
    lock_shadow,
    normalize_history,
    shadow_identity,
)
from nfl_forecast.challenger_v06 import logit_blend_probabilities


LOCK_TIME = "2026-09-10T22:00:00+00:00"
KICKOFF = "2026-09-10T23:30:00+00:00"


def _production_lock(
    *,
    game_id="2026_01_AWAY_HOME",
    snapshot="FINAL",
    market=0.60,
    status="LOCKED",
    minutes=90.0,
    home_score=np.nan,
    away_score=np.nan,
):
    return pd.DataFrame([{
        "game_id": game_id,
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-10",
        "gametime": "19:30",
        "away_team": "AWAY",
        "home_team": "HOME",
        "market_home_prob": market,
        "snapshot_type": snapshot,
        "model_version": "0.4.0-accountability",
        "prediction_timestamp_utc": "2026-09-10T21:58:00+00:00",
        "lock_status": status,
        "lock_timestamp_utc": LOCK_TIME,
        "kickoff_utc": KICKOFF,
        "minutes_to_kickoff_at_lock": minutes,
        "actual_home_score": home_score,
        "actual_away_score": away_score,
    }])


def _challenger(
    *,
    game_id="2026_01_AWAY_HOME",
    pure=0.55,
    stale_market=0.52,
    stale_final=0.53,
    weight=0.25,
    method="logit",
    generated="2026-09-10T18:00:00+00:00",
    candidate="Logit hybrid adaptive Brier",
    version=None,
    feature_set=None,
    selected=True,
):
    row = {
        "game_id": game_id,
        "challenger_pure_home_prob": pure,
        "market_home_prob": stale_market,
        "challenger_final_home_prob": stale_final,
        "challenger_pick": "HOME",
        "effective_pure_weight": weight,
        "effective_market_weight": 1.0 - weight,
        "research_candidate": candidate,
        "research_method": method,
        "shadow_generated_utc": generated,
        "shadow_source_sha": "abc123",
    }
    if version is not None:
        row["challenger_version"] = version
    if feature_set is not None:
        row["research_feature_set"] = feature_set
    if selected is not None:
        row["selected_shadow_candidate"] = selected
    return pd.DataFrame([row])


def test_locks_from_authoritative_production_row_and_recomputes_t120_market():
    production = _production_lock(market=0.66)
    challenger = _challenger(pure=0.54, stale_market=0.51, stale_final=0.52, weight=0.25)
    history, added, skipped = lock_shadow(
        production,
        challenger,
        now_utc=datetime(2026, 9, 10, 22, 1, tzinfo=timezone.utc),
    )
    assert added == 1
    assert skipped == 0
    assert len(history) == 1
    row = history.iloc[0]
    expected = logit_blend_probabilities([0.54], [0.66], 0.25)[0]
    assert np.isclose(row.challenger_final_home_prob, expected)
    assert np.isclose(row.market_home_prob_t120, 0.66)
    assert not np.isclose(row.challenger_final_home_prob, 0.52)
    assert row.production_snapshot_type == "FINAL"
    assert row.production_lock_timestamp_utc == LOCK_TIME
    assert row.shadow_generated_utc == "2026-09-10T18:00:00+00:00"
    assert row.lock_status == "LOCKED"


def test_requires_final_locked_production_row():
    challenger = _challenger()
    not_final, added_final, _ = lock_shadow(
        _production_lock(snapshot="EARLY"), challenger
    )
    not_locked, added_locked, _ = lock_shadow(
        _production_lock(status="PENDING"), challenger
    )
    assert added_final == added_locked == 0
    assert not_final.empty and not_locked.empty


def test_rejects_invalid_production_lock_window():
    with pytest.raises(RuntimeError, match="outside authoritative T-120"):
        lock_shadow(_production_lock(minutes=121.0), _challenger())


def test_existing_shadow_lock_is_immutable_when_market_moves():
    challenger = _challenger(pure=0.56, weight=0.25)
    first, added, _ = lock_shadow(_production_lock(market=0.61), challenger)
    assert added == 1
    first_prob = float(first.iloc[0].challenger_final_home_prob)
    first_market = float(first.iloc[0].market_home_prob_t120)

    moved = _production_lock(market=0.85)
    second, added_again, _ = lock_shadow(
        moved,
        challenger,
        existing_history=first,
        now_utc=datetime(2026, 9, 10, 22, 30, tzinfo=timezone.utc),
    )
    assert added_again == 0
    assert len(second) == 1
    assert np.isclose(float(second.iloc[0].challenger_final_home_prob), first_prob)
    assert np.isclose(float(second.iloc[0].market_home_prob_t120), first_market)


def test_missing_market_falls_back_to_pure_like_production():
    history, added, _ = lock_shadow(
        _production_lock(market=np.nan), _challenger(pure=0.57, weight=0.25)
    )
    assert added == 1
    assert np.isclose(float(history.iloc[0].challenger_final_home_prob), 0.57)


def test_rejects_hybrid_below_pure_floor_and_unknown_method():
    with pytest.raises(RuntimeError, match="PURE floor"):
        lock_shadow(_production_lock(), _challenger(weight=0.20))
    with pytest.raises(RuntimeError, match="Unsupported challenger shadow method"):
        lock_shadow(_production_lock(), _challenger(method="confidence", weight=0.25))


def test_never_retroactively_backfills_model_generated_after_production_lock():
    history, added, skipped = lock_shadow(
        _production_lock(),
        _challenger(generated="2026-09-10T22:05:00+00:00"),
    )
    assert history.empty
    assert added == 0
    assert skipped == 1


def test_grades_existing_lock_without_changing_forecast():
    challenger = _challenger(pure=0.55, weight=0.25)
    history, _, _ = lock_shadow(_production_lock(market=0.65), challenger)
    locked_prob = float(history.iloc[0].challenger_final_home_prob)
    completed = _production_lock(market=0.65, home_score=24, away_score=17)
    graded, added, _ = lock_shadow(
        completed,
        challenger,
        existing_history=history,
        now_utc=datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc),
    )
    assert added == 0
    assert np.isclose(float(graded.iloc[0].challenger_final_home_prob), locked_prob)
    assert float(graded.iloc[0].actual_home_score) == 24
    assert float(graded.iloc[0].actual_away_score) == 17
    assert bool(graded.iloc[0].winner_correct) is True
    assert list(graded.columns) == HISTORY_COLUMNS


def test_two_candidates_for_same_game_both_lock_at_same_t120_market():
    candidates = pd.concat([
        _challenger(
            pure=0.54,
            weight=0.25,
            method="logit",
            candidate="v07 logit",
            version="0.7-opponent-adjusted",
            feature_set="opponent_adjusted",
            selected=False,
        ),
        _challenger(
            pure=0.48,
            weight=0.25,
            method="linear",
            candidate="v08 hybrid",
            version="0.8-qb-starter",
            feature_set="opponent_adjusted_qb",
            selected=True,
        ),
    ], ignore_index=True)
    history, added, skipped = lock_shadow(_production_lock(market=0.63), candidates)

    assert added == 2
    assert skipped == 0
    assert len(history) == 2
    assert history.game_id.nunique() == 1
    assert history.shadow_key.nunique() == 2
    assert set(history.challenger_version) == {
        "0.7-opponent-adjusted", "0.8-qb-starter"
    }
    assert history.market_home_prob_t120.astype(float).eq(0.63).all()
    assert history.selected_shadow_candidate.astype(bool).sum() == 1


def test_precommit_skip_is_candidate_specific():
    early = _challenger(
        candidate="early",
        version="0.7",
        generated="2026-09-10T18:00:00+00:00",
    )
    late = _challenger(
        candidate="late",
        version="0.8",
        generated="2026-09-10T22:05:00+00:00",
    )
    history, added, skipped = lock_shadow(
        _production_lock(), pd.concat([early, late], ignore_index=True)
    )
    assert added == 1
    assert skipped == 1
    assert history.research_candidate.tolist() == ["early"]


def test_market_move_cannot_mutate_either_candidate_lock():
    candidates = pd.concat([
        _challenger(candidate="a", version="0.7", pure=0.55, method="logit"),
        _challenger(candidate="b", version="0.8", pure=0.45, method="linear"),
    ], ignore_index=True)
    first, added, _ = lock_shadow(_production_lock(market=0.61), candidates)
    assert added == 2
    snapshot = first.set_index("shadow_key")[[
        "market_home_prob_t120", "challenger_final_home_prob", "challenger_pick"
    ]].copy()

    second, added_again, _ = lock_shadow(
        _production_lock(market=0.88), candidates, existing_history=first
    )
    assert added_again == 0
    current = second.set_index("shadow_key")[[
        "market_home_prob_t120", "challenger_final_home_prob", "challenger_pick"
    ]]
    pd.testing.assert_frame_equal(snapshot.sort_index(), current.sort_index())


def test_grades_multiple_candidates_independently_for_same_game():
    candidates = pd.concat([
        _challenger(
            candidate="home-pick", version="0.7", pure=0.90,
            weight=0.25, method="linear"
        ),
        _challenger(
            candidate="away-pick", version="0.8", pure=0.10,
            weight=0.25, method="linear"
        ),
    ], ignore_index=True)
    history, added, _ = lock_shadow(_production_lock(market=0.60), candidates)
    assert added == 2
    picks = dict(zip(history.research_candidate, history.challenger_pick))
    assert picks == {"home-pick": "HOME", "away-pick": "AWAY"}

    graded, _, _ = lock_shadow(
        _production_lock(market=0.60, home_score=27, away_score=20),
        candidates,
        existing_history=history,
    )
    results = dict(zip(graded.research_candidate, graded.winner_correct))
    assert bool(results["home-pick"]) is True
    assert bool(results["away-pick"]) is False


def test_legacy_single_candidate_history_normalizes_without_losing_identity():
    old = pd.DataFrame([{
        "game_id": "legacy_game",
        "research_candidate": "Old challenger",
        "challenger_pick": "HOME",
    }])
    normalized = normalize_history(old)
    assert len(normalized) == 1
    row = normalized.iloc[0]
    assert row.challenger_version == LEGACY_VERSION
    assert bool(row.selected_shadow_candidate) is True
    assert row.shadow_key == shadow_identity(
        "legacy_game", LEGACY_VERSION, "Old challenger"
    )
    assert list(normalized.columns) == HISTORY_COLUMNS

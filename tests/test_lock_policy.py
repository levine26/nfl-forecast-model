from __future__ import annotations

import pytest

from nfl_forecast.lock_policy import (
    CURRENT_TARGET_MINUTES, EFFECTIVE_SEASON, EFFECTIVE_WEEK,
    LEGACY_TARGET_MINUTES, official_lock_target_minutes,
)


def test_boundary_and_prior_lock_targets_are_stable():
    assert (EFFECTIVE_SEASON, EFFECTIVE_WEEK) == (2026, 6)
    assert (LEGACY_TARGET_MINUTES, CURRENT_TARGET_MINUTES) == (120.0, 60.0)
    for week in range(1, 6):
        assert official_lock_target_minutes({"season": 2026, "week": week}) == 120
    assert official_lock_target_minutes({"season": 2026, "week": 6}) == 60
    assert official_lock_target_minutes({"season": 2026, "week": 18}) == 60
    assert official_lock_target_minutes({"season": 2027, "week": 1}) == 60
    assert official_lock_target_minutes({"season": 2025, "week": 18}) == 120


def test_csv_and_canonical_id_fallbacks_agree_without_timestamp_guesswork():
    assert official_lock_target_minutes({"game_id": "2026_05_PHI_JAX"}) == 120
    assert official_lock_target_minutes({"game_id": "2026_06_CHI_GB"}) == 60
    assert official_lock_target_minutes({"game_id": "2026_07_CHI_GB", "season": "2026", "week": "07"}) == 60
    assert official_lock_target_minutes({}) == 120


def test_invalid_season_week_fail_closed():
    with pytest.raises(ValueError, match="invalid official lock season"):
        official_lock_target_minutes({"season": "not-a-year", "week": "6"})
    with pytest.raises(ValueError, match="invalid official lock week"):
        official_lock_target_minutes({"season": "2026", "week": "0"})

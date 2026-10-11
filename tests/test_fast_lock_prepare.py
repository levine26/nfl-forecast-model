from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scripts.fast_lock_prepare import LockPreparationError, stale_due_games


NOW = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)


def row(**updates):
    result = {
        "game_id": "2026_05_CHI_GB",
        "gameday": "2026-10-11",
        "gametime": "13:00",  # 17:00 UTC, T-120 at 15:00 UTC
        "prediction_timestamp_utc": "2026-10-11T07:47:30+00:00",
    }
    result.update(updates)
    return result


def test_stale_published_canonical_snapshot_requires_refresh_not_stale_lock():
    assert stale_due_games([row()], [], now_utc=NOW) == ["2026_05_CHI_GB"]


def test_fresh_due_snapshot_keeps_lightweight_lock_path():
    current = row(prediction_timestamp_utc=(NOW - timedelta(minutes=89)).isoformat())
    assert stale_due_games([current], [], now_utc=NOW) == []


def test_at_exact_freshness_boundary_still_safe():
    current = row(prediction_timestamp_utc=(NOW - timedelta(minutes=90)).isoformat())
    assert stale_due_games([current], [], now_utc=NOW) == []


def test_historical_locked_receipt_never_gets_reworked():
    old = {"game_id": "2026_05_CHI_GB", "lock_status": "LOCKED"}
    assert stale_due_games([row()], [old], now_utc=NOW) == []


def test_kickoff_already_passed_is_not_backfilled():
    assert stale_due_games([row()], [], now_utc=NOW + timedelta(hours=3)) == []


def test_future_and_naive_timestamps_fail_closed():
    with pytest.raises(LockPreparationError, match="future"):
        stale_due_games([row(prediction_timestamp_utc=(NOW + timedelta(minutes=5)).isoformat())], [], now_utc=NOW)
    with pytest.raises(LockPreparationError, match="Naive"):
        stale_due_games([row(prediction_timestamp_utc="2026-10-11T14:00:00")], [], now_utc=NOW)


def test_malformed_and_duplicate_input_fail_closed():
    with pytest.raises(LockPreparationError, match="duplicate"):
        stale_due_games([row(), row()], [], now_utc=NOW)
    with pytest.raises(LockPreparationError, match="invalid kickoff"):
        stale_due_games([row(gametime="invalid")], [], now_utc=NOW)
    with pytest.raises(LockPreparationError, match="Empty"):
        stale_due_games([], [], now_utc=NOW)


def test_independent_of_prior_missed_game():
    past = row(game_id="2026_05_PHI_JAX", gametime="09:30")
    assert stale_due_games([past, row()], [], now_utc=NOW) == ["2026_05_CHI_GB"]


def test_accepts_offset_aware_clock_and_dst_kickoffs():
    from datetime import timezone as tz
    fallback = row(gameday="2026-11-01", gametime="13:00",
                   prediction_timestamp_utc="2026-11-01T10:00:00+00:00")
    at_target = datetime(2026, 11, 1, 16, 0, tzinfo=tz.utc)
    assert stale_due_games([fallback], [], now_utc=at_target) == ["2026_05_CHI_GB"]


def test_fast_lock_worker_preserves_freshness_gate_and_atomically_publishes_refresh():
    from pathlib import Path
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "fast_official_lock.yml").read_text()
    assert "python -m scripts.fast_lock_prepare --output-dir outputs" in workflow
    assert "python scripts/refresh_market.py --season 2026 --output-dir outputs" in workflow
    assert workflow.index("scripts.fast_lock_prepare") < workflow.index("scripts/refresh_market.py")
    assert workflow.index("scripts/refresh_market.py") < workflow.index("scripts/fast_official_lock.py --output-dir")
    assert "python -m scripts.sync_market_reads --output-dir outputs --check" in workflow
    assert "git add outputs/" in workflow  # Include canonical forecast, Read and lock in recovery transaction.
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow
    assert "git reset --hard origin/main" in workflow

def test_prospective_week6_stale_preflight_only_checks_at_t60():
    target = datetime(2026, 10, 18, 16, 0, tzinfo=timezone.utc)
    future = row(game_id="2026_06_CHI_GB", gameday="2026-10-18",
                 gametime="13:00", prediction_timestamp_utc="2026-10-18T12:00:00+00:00")
    assert stale_due_games([future], [], now_utc=target-timedelta(seconds=1)) == []
    assert stale_due_games([future], [], now_utc=target) == ["2026_06_CHI_GB"]

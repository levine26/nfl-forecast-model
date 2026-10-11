from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scripts.audit_current_lock_deadlines import audit_current_deadlines

KICKOFF = datetime(2026, 10, 11, 13, 30, tzinfo=timezone.utc)
TARGET = KICKOFF - timedelta(minutes=120)
GRACE_END = TARGET + timedelta(minutes=10)


def slate():
    return [
        {"game_id": "2026_05_PHI_JAX", "gameday": "2026-10-11", "gametime": "09:30"},
        {"game_id": "2026_05_DEN_LAC", "gameday": "2026-10-11", "gametime": "09:30"},
    ]


def lock(gid, actual=TARGET):
    return {"game_id": gid, "lock_status": "LOCKED", "lock_timestamp_utc": actual.isoformat()}


def test_does_not_fail_before_official_target_plus_grace():
    x = audit_current_deadlines(slate(), [], now_utc=GRACE_END-timedelta(seconds=1))
    assert not x["issues"]
    assert x["counts"]["deadline_not_elapsed"] == 2


def test_all_missing_locks_are_reported_together_after_grace():
    x = audit_current_deadlines(slate(), [], now_utc=GRACE_END+timedelta(seconds=1))
    assert set(x["issues"]) == {"2026_05_PHI_JAX", "2026_05_DEN_LAC"}
    assert x["games_audited"] == 2
    assert x["status"] == "overdue_missing_locks"


def test_one_lock_does_not_mask_another_missing_lock():
    x = audit_current_deadlines(slate(), [lock("2026_05_PHI_JAX")],
                                now_utc=GRACE_END+timedelta(minutes=4))
    assert x["games"]["2026_05_PHI_JAX"]["state"] == "on_time_lock"
    assert set(x["issues"]) == {"2026_05_DEN_LAC"}


def test_historical_late_lock_remains_truthful_without_modifying_row():
    before = lock("2026_05_PHI_JAX", KICKOFF-timedelta(minutes=19))
    original = dict(before)
    x = audit_current_deadlines(slate(), [before, lock("2026_05_DEN_LAC")],
                                now_utc=KICKOFF+timedelta(hours=1))
    assert before == original
    assert x["games"]["2026_05_PHI_JAX"]["state"] == "historically_late_lock"
    assert x["games"]["2026_05_PHI_JAX"]["minutes_late_vs_t120"] == 101
    assert x["issues"] == {}
    assert x["historical_lock_records_modified"] is False


def test_missing_lock_after_kickoff_is_visible_during_bounded_window():
    x = audit_current_deadlines(slate(), [], now_utc=KICKOFF+timedelta(hours=1))
    assert x["counts"]["overdue_missing_official_lock"] == 2
    beyond = audit_current_deadlines(slate(), [], now_utc=KICKOFF+timedelta(hours=4))
    assert beyond["status"] == "no_current_missing_lock_overdue"
    assert beyond["counts"]["missing_lock_outside_active_watch_window"] == 2


def test_recorded_missed_lock_recovery_not_confused_with_on_time_lock():
    hist=[{"game_id": "2026_05_PHI_JAX", "lock_status": "RECOVERED_MISSED_LOCK"},
          lock("2026_05_DEN_LAC")]
    report = audit_current_deadlines(slate(), hist, now_utc=GRACE_END+timedelta(minutes=4))
    assert report["games"]["2026_05_PHI_JAX"]["state"] == "recorded_missed_lock_recovery"
    assert report["issues"] == {}


def test_canonical_and_historical_duplicates_refused():
    with pytest.raises(ValueError, match="duplicate"):
        audit_current_deadlines(slate()+[slate()[0]], [], now_utc=TARGET)
    with pytest.raises(ValueError, match="duplicate"):
        audit_current_deadlines(slate(), [lock("2026_05_PHI_JAX")] * 2, now_utc=TARGET)


def test_invalid_datetime_refused():
    with pytest.raises(ValueError):
        audit_current_deadlines(
            [{"game_id": "2026_05_PHI_JAX", "gameday": "bad", "gametime": "bad"}],
            [], now_utc=TARGET)

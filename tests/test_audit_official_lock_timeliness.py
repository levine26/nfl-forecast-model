from datetime import datetime, timedelta, timezone

import pytest

from scripts.audit_official_lock_timeliness import audit_history

KICKOFF = datetime(2026, 10, 9, 0, 15, tzinfo=timezone.utc)


def record(gid: str, minutes_before: float) -> dict:
    return {
        "game_id": gid,
        "season": 2026,
        "week": 5,
        "lock_status": "LOCKED",
        "kickoff_utc": KICKOFF.isoformat(),
        "lock_timestamp_utc": (KICKOFF-timedelta(minutes=minutes_before)).isoformat(),
    }


def test_real_buccaneers_cowboys_late_classification_not_rewritten():
    row = record("2026_05_TB_DAL", 19.34158358)
    before = row.copy()
    r = audit_history([row], season=2026, week=5)
    assert r["counts"]["late"] == 1
    assert r["games"][0]["minutes_late_vs_t120"] > 100
    assert row == before


def test_t120_deadline_accepts_short_queue_delay_but_not_early_lock():
    r = audit_history([
        record("exact", 120.0),
        record("five_minutes_late", 115.0),
        record("too_early", 140.0),
        record("too_late", 100.0),
        record("post_kickoff", -1.0),
    ], season=2026, week=5)
    assert r["counts"] == {
        "on_time": 2, "late": 1, "at_or_after_kickoff": 1, "premature": 1
    }
    assert not r["all_locks_on_time"]


def test_duplicate_and_invalid_lock_times_fail_closed():
    with pytest.raises(ValueError, match="duplicate"):
        audit_history([record("same", 120), record("same", 115)], season=2026)
    bad = record("missing", 120)
    bad["kickoff_utc"] = "not-a-date"
    with pytest.raises(ValueError, match="malformed"):
        audit_history([bad], season=2026)


def test_scope_excludes_other_weeks_and_nonofficial_rows():
    historic = record("week4", 120)
    historic["week"] = 4
    pending = record("notlocked", 120)
    pending["lock_status"] = "EARLY"
    r = audit_history([historic, pending, record("week5", 119)], season=2026, week=5)
    assert r["locked_count"] == 1
    assert r["all_locks_on_time"]

def test_week6_t60_receipts_get_new_target_without_regrading_week5():
    kickoff = datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc)
    def week6(gid, minutes):
        return {"game_id": gid, "season": "2026", "week": "6",
                "lock_status": "LOCKED", "kickoff_utc": kickoff.isoformat(),
                "lock_timestamp_utc": (kickoff-timedelta(minutes=minutes)).isoformat()}
    week5 = record("2026_05_TB_DAL", 19.34158358)
    result = audit_history([week5, week6("2026_06_CHI_GB", 60),
                            week6("2026_06_CIN_MIA", 48)])
    assert result["official_lock_target_minutes"] is None
    assert result["observed_target_minutes"] == [60.0, 120.0]
    by_id = {x["game_id"]: x for x in result["games"]}
    assert by_id["2026_05_TB_DAL"]["official_target_minutes"] == 120
    assert by_id["2026_05_TB_DAL"]["classification"] == "late"
    assert by_id["2026_06_CHI_GB"]["official_target_minutes"] == 60
    assert by_id["2026_06_CHI_GB"]["classification"] == "on_time"
    assert by_id["2026_06_CIN_MIA"]["classification"] == "late"
    assert by_id["2026_06_CIN_MIA"]["minutes_late_vs_target"] == 12

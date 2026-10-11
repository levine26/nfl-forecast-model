from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nfl_forecast.official_lock_policy import (
    official_lock_policy_name,
    official_lock_target_minutes,
)
from scripts.audit_current_lock_deadlines import audit_current_deadlines
from scripts.audit_official_lock_timeliness import audit_history
from scripts.fast_official_lock import plan_fast_locks
from scripts.fast_lock_prepare import stale_due_games
from nfl_forecast.publish import CURRENT_COLUMNS


def status():
    return {"games": 1,
            "final_probability_strategy": "F-ST-01-FROZEN-2026",
            "fst_artifact_id": "F-ST-01-FROZEN-2026"}


def snapshot(now):
    row = {key: "" for key in CURRENT_COLUMNS}
    row.update({
        "game_id": "2026_05_PHI_JAX", "season": "2026", "week": "5",
        "gameday": "2026-10-11", "gametime": "09:30",
        "away_team": "PHI", "home_team": "JAX", "pick": "JAX",
        "final_home_prob": "0.70", "expected_margin": "6.0",
        "spread_line": "3.5", "market_home_prob": "0.65",
        "model_version": "0.9.0-fst",
        "prediction_timestamp_utc": (now-timedelta(minutes=15)).isoformat(),
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
    })
    return row


KICKOFF = datetime(2026, 10, 15, 20, 15, tzinfo=timezone.utc)


def week6_prediction(now: datetime) -> dict:
    row = snapshot(now)
    row.update(game_id="2026_06_X_Y", season="2026", week="6",
               gameday="2026-10-15", gametime="16:15",
               prediction_timestamp_utc=(now-timedelta(minutes=15)).isoformat())
    return row


def test_policy_switch_is_prospective_with_strict_date_guard():
    assert official_lock_target_minutes("2026-10-11") == 120
    assert official_lock_target_minutes("2026-10-12") == 120
    assert official_lock_target_minutes("2026-10-15") == 60
    assert official_lock_target_minutes("2026-11-01") == 60
    assert official_lock_policy_name("2026-10-11") == "T-120-LEGACY"
    assert official_lock_policy_name("2026-10-15") == "T-60-WEEK6-2026"


def test_fast_worker_rejects_week6_t120_and_t61_but_locks_at_t60():
    early = KICKOFF - timedelta(minutes=120)
    near = KICKOFF - timedelta(minutes=61)
    target = KICKOFF - timedelta(minutes=60)
    assert plan_fast_locks([week6_prediction(early)], [], status(), now_utc=early) == []
    assert plan_fast_locks([week6_prediction(near)], [], status(), now_utc=near) == []
    result = plan_fast_locks([week6_prediction(target)], [], status(), now_utc=target)
    assert len(result) == 1
    assert result[0]["game_id"] == "2026_06_X_Y"
    assert float(result[0]["minutes_to_kickoff_at_lock"]) == 60.0
    assert result[0]["lock_timestamp_utc"] == target.isoformat()


def test_week6_preflight_does_not_refresh_before_t60():
    stale = week6_prediction(KICKOFF - timedelta(minutes=120))
    stale["prediction_timestamp_utc"] = (KICKOFF - timedelta(hours=6)).isoformat()
    assert stale_due_games([stale], [], now_utc=KICKOFF-timedelta(minutes=61)) == []
    assert stale_due_games([stale], [], now_utc=KICKOFF-timedelta(minutes=60)) == ["2026_06_X_Y"]


def test_current_deadline_audit_uses_week6_target_with_ten_minute_grace():
    row = week6_prediction(KICKOFF-timedelta(minutes=60))
    row["gametime"] = "16:15"
    at_61 = audit_current_deadlines([row], [],
                                    now_utc=KICKOFF-timedelta(minutes=61))
    assert not at_61["issues"]
    assert at_61["games"]["2026_06_X_Y"]["target_minutes_before_kickoff"] == 60.0
    after_grace = audit_current_deadlines([row], [],
                     now_utc=KICKOFF-timedelta(minutes=49))
    assert "2026_06_X_Y" in after_grace["issues"]
    assert "T-60" in after_grace["issues"]["2026_06_X_Y"][0]


def test_historical_t120_and_new_t60_retain_distinct_timing_classifications():
    legacy_kick = datetime(2026, 10, 11, 17, tzinfo=timezone.utc)
    legacy = {"game_id":"2026_05_A_B","season":2026,"week":5,
              "gameday":"2026-10-11", "lock_status":"LOCKED",
              "kickoff_utc":legacy_kick.isoformat(),
              "lock_timestamp_utc":(legacy_kick-timedelta(minutes=100)).isoformat()}
    fresh = {"game_id":"2026_06_X_Y","season":2026,"week":6,
             "gameday":"2026-10-15", "lock_status":"LOCKED",
             "kickoff_utc":KICKOFF.isoformat(),
             "lock_timestamp_utc":(KICKOFF-timedelta(minutes=60)).isoformat()}
    rows = [legacy, fresh]
    before = [x.copy() for x in rows]
    result = audit_history(rows, season=2026)
    assert rows == before
    assert result["official_lock_target_minutes"] is None
    assert result["counts"]["late"] == 1
    assert result["counts"]["on_time"] == 1
    by_id = {game["game_id"]:game for game in result["games"]}
    assert by_id["2026_05_A_B"]["minutes_late_vs_t120"] == 20.0
    assert by_id["2026_06_X_Y"]["target_minutes_before_kickoff"] == 60.0
    assert by_id["2026_06_X_Y"]["minutes_late_vs_t120"] is None


def test_importability_from_explicit_cli_path():
    assert official_lock_target_minutes("2026-10-15T16:15") == 60

def test_pregame_publication_postcondition_waits_until_t60_for_week6():
    import pandas as pd
    from nfl_forecast.lock_verify import verify_pregame_locks

    current = pd.DataFrame([week6_prediction(KICKOFF-timedelta(minutes=90))])
    # Merely having a live prediction before the new window must not
    # obligate production to manufacture an earlier immutable lock.
    assert verify_pregame_locks(current, pd.DataFrame(),
        KICKOFF-timedelta(minutes=90)) == []

    receipt = dict(week6_prediction(KICKOFF-timedelta(minutes=60)))
    receipt.update(lock_status="LOCKED", locked_ats_status="UNAVAILABLE",
                   lock_timestamp_utc=(KICKOFF-timedelta(minutes=60)).isoformat())
    assert verify_pregame_locks(current, pd.DataFrame([receipt]),
        KICKOFF-timedelta(minutes=59)) == ["2026_06_X_Y"]

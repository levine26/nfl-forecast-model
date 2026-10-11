from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from nfl_forecast.official_lock_policy import official_lock_lead_minutes
from nfl_forecast.publish import CURRENT_COLUMNS, write_outputs
from nfl_forecast.lock_verify import verify_pregame_locks
from scripts.fast_official_lock import plan_fast_locks
from scripts.fast_lock_prepare import stale_due_games
from scripts.audit_official_lock_timeliness import audit_history
from scripts.audit_current_lock_deadlines import audit_current_deadlines
from scripts.pregame_due import due_games


KICKOFF = datetime(2026, 10, 16, 0, 15, tzinfo=timezone.utc)  # Week 6 Thu 8:15 ET
T60 = KICKOFF - timedelta(minutes=60)


def new_row():
    row = {k: "" for k in CURRENT_COLUMNS}
    row.update({
        "game_id": "2026_06_A_B", "season": "2026", "week": "6",
        "gameday": "2026-10-15", "gametime": "20:15",
        "away_team": "A", "home_team": "B", "pick": "B",
        "final_home_prob": "0.65", "expected_margin": "3.5",
        "spread_line": "2.5", "expected_total": "45.0",
        "model_version": "0.9.0-fst", "margin_sigma": "12.5",
        "market_home_prob": "0.60", "pure_home_prob": "0.55",
        "fst_pure_home_prob": "0.58",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "prediction_timestamp_utc": (T60-timedelta(minutes=20)).isoformat(),
    })
    return row


def official_status():
    return {"games": 1, "final_probability_strategy": "F-ST-01-FROZEN-2026",
            "fst_artifact_id": "F-ST-01-FROZEN-2026"}


def test_policy_is_explicit_and_mixed_history_cannot_shift():
    assert official_lock_lead_minutes({"game_id": "2026_05_A_B"}) == 120.0
    assert official_lock_lead_minutes({"game_id": "2026_06_A_B"}) == 60.0
    assert official_lock_lead_minutes({"season": "2027", "week": "1"}) == 60.0
    assert official_lock_lead_minutes({"season": "2025", "week": "22"}) == 120.0
    with pytest.raises(ValueError, match="season/week"):
        official_lock_lead_minutes({"game_id": "bad"})


def test_new_lock_cannot_be_created_at_t120_or_t61():
    p = new_row()
    for delta in (120, 61):
        now = KICKOFF-timedelta(minutes=delta)
        assert plan_fast_locks([p], [], official_status(), now_utc=now) == []
    official = plan_fast_locks([p], [], official_status(), now_utc=T60)
    assert len(official) == 1
    assert official[0]["lock_timestamp_utc"] == T60.isoformat()
    assert official[0]["final_home_prob"] == p["final_home_prob"]
    assert official[0]["lock_status"] == "LOCKED"


def test_stale_refresh_eligibility_matches_new_lock_window():
    p = new_row()
    p["prediction_timestamp_utc"] = (T60-timedelta(minutes=100)).isoformat()
    assert stale_due_games([p], [], now_utc=T60-timedelta(minutes=1)) == []
    assert stale_due_games([p], [], now_utc=T60) == [p["game_id"]]


def test_official_writer_waits_for_t60_and_preserves_first_receipt(tmp_path):
    p = new_row()
    predictions = pd.DataFrame([p])
    games = pd.DataFrame([{"game_id": p["game_id"], "home_team":"B","away_team":"A",
                           "home_score":None,"away_score":None}])
    writer = SimpleNamespace(predictions=predictions, games=games)
    write_outputs(writer, tmp_path, now_utc=T60-timedelta(minutes=1), enforce_read_sync=False)
    before = pd.read_csv(tmp_path/"prediction_history.csv")
    assert before.empty
    write_outputs(writer, tmp_path, now_utc=T60, enforce_read_sync=False)
    actual = pd.read_csv(tmp_path/"prediction_history.csv")
    assert len(actual) == 1
    assert actual.loc[0, "minutes_to_kickoff_at_lock"] == pytest.approx(60)
    expected = float(actual.loc[0, "final_home_prob"])
    upgraded = pd.DataFrame([{**p,"final_home_prob":"0.89"}])
    write_outputs(SimpleNamespace(predictions=upgraded, games=games),
                  tmp_path, now_utc=T60+timedelta(minutes=3), enforce_read_sync=False)
    retained = pd.read_csv(tmp_path/"prediction_history.csv")
    assert len(retained) == 1
    assert float(retained.loc[0, "final_home_prob"]) == expected
    assert verify_pregame_locks(upgraded, retained, T60) == [p["game_id"]]


def test_combined_timeliness_report_preserves_prior_lateness_and_new_target():
    week5_kickoff = datetime(2026,10,11,17,tzinfo=timezone.utc)
    old = {
        "game_id":"2026_05_CHI_GB", "season":"2026", "week":"5", "lock_status":"LOCKED",
        "kickoff_utc":week5_kickoff.isoformat(),
        "lock_timestamp_utc":(week5_kickoff-timedelta(minutes=18)).isoformat()
    }
    new = {
        "game_id":"2026_06_A_B", "season":"2026", "week":"6", "lock_status":"LOCKED",
        "kickoff_utc":KICKOFF.isoformat(), "lock_timestamp_utc":T60.isoformat()
    }
    before = (dict(old),dict(new))
    report = audit_history([old,new],season=2026)
    assert report["counts"]["late"] == 1
    assert report["counts"]["on_time"] == 1
    assert report["official_lock_target_minutes"] is None
    assert report["official_lock_targets_minutes"] == [60.0,120.0]
    assert report["games"][0]["minutes_late_vs_t120"] == 102
    assert report["games"][1]["minutes_late_vs_t120"] is None
    assert report["games"][1]["minutes_late_vs_target"] == 0
    assert report["games"][1]["target_minutes_before_kickoff"] == 60
    assert old == before[0] and new == before[1]


def test_week6_overdue_watch_begins_at_t50_not_t110():
    p = new_row()
    base = {"game_id":p["game_id"],"gameday":p["gameday"],"gametime":p["gametime"],"season":2026,"week":6}
    at_t110 = audit_current_deadlines([base],[],now_utc=KICKOFF-timedelta(minutes=110))
    assert not at_t110["issues"]
    at_t50 = audit_current_deadlines([base],[],now_utc=KICKOFF-timedelta(minutes=50))
    assert p["game_id"] in at_t50["issues"]
    assert at_t50["games"][p["game_id"]]["target_minutes_before_kickoff"] == 60.0
    assert "T-60" in at_t50["issues"][p["game_id"]][0]


def test_fast_gate_is_bounded_to_policy_while_pregame_recompute_starts_early(tmp_path):
    p = new_row()
    feed = tmp_path/"forecast.csv"
    history = tmp_path/"history.csv"
    feed.write_text("game_id,season,week,gameday,gametime\n"
                    "2026_06_A_B,2026,6,2026-10-15,20:15\n")
    history.write_text("game_id,lock_status\n")
    assert due_games(feed,history,T60-timedelta(minutes=4),0,123,3) == []
    assert due_games(feed,history,T60-timedelta(minutes=2),0,123,3)
    assert due_games(feed,history,T60-timedelta(minutes=45),0,165)

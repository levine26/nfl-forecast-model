from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from nfl_forecast.publish import CURRENT_COLUMNS, LOCK_META_COLUMNS
from scripts.fast_official_lock import FastLockError, plan_fast_locks, write_fast_locks

IDENTITY="F-ST-01-FROZEN-2026"
KICKOFF=datetime(2026,10,11,13,30,tzinfo=timezone.utc)
TARGET=KICKOFF-timedelta(minutes=120)


def snapshot(now=TARGET):
    row={name:"" for name in CURRENT_COLUMNS}
    row.update({
        "game_id":"2026_05_PHI_JAX","season":"2026","week":"5",
        "gameday":"2026-10-11","gametime":"09:30",
        "away_team":"PHI","home_team":"JAX","pick":"JAX",
        "final_home_prob":"0.7596917948","fst_pure_home_prob":"0.7322728336",
        "expected_margin":"10.69921521","spread_line":"7.5","expected_total":"48.27628888",
        "margin_sigma":"12.89176927","market_home_prob":"0.7659021045",
        "model_version":"0.9.0-fst","snapshot_type":"MARKET",
        "prediction_timestamp_utc":(now-timedelta(minutes=35)).isoformat(),
        "final_probability_strategy":IDENTITY,"fst_artifact_id":IDENTITY,
    })
    return row


def status():
    return {"games":1,"final_probability_strategy":IDENTITY,
            "fst_artifact_id":IDENTITY,"locked_official_predictions":1,
            "generated_utc":"2026-10-11T10:55:00+00:00"}


def test_fast_path_locks_at_t120_using_unchanged_official_probability():
    before=snapshot()
    locked=plan_fast_locks([before],[],status(),now_utc=TARGET)
    assert len(locked)==1
    row=locked[0]
    assert row["final_home_prob"]==before["final_home_prob"]
    assert row["fst_artifact_id"]==IDENTITY
    assert row["lock_status"]=="LOCKED"
    assert row["lock_timestamp_utc"]==TARGET.isoformat()
    assert float(row["minutes_to_kickoff_at_lock"])==pytest.approx(120.0)
    assert row["locked_ats_status"]=="VALUE"
    assert row["locked_ats_pick_team"]=="JAX"
    assert row["locked_ats_pick_market_spread"]==-7.5
    assert row["snapshot_type"]=="MARKET"  # truthfully retain input provenance


def test_never_locks_early_but_can_record_an_actual_late_attempt():
    assert plan_fast_locks([snapshot()],[],status(),now_utc=TARGET-timedelta(seconds=1))==[]
    late=TARGET+timedelta(minutes=15)
    row=snapshot(late)
    new=plan_fast_locks([row],[],status(),now_utc=late)
    assert len(new)==1
    assert float(new[0]["minutes_to_kickoff_at_lock"])==pytest.approx(105.0)
    assert new[0]["lock_timestamp_utc"]==late.isoformat()


def test_existing_official_lock_or_recovery_is_immutable():
    current=[snapshot()]
    for old_state in ("LOCKED","RECOVERED_MISSED_LOCK"):
        old={"game_id":"2026_05_PHI_JAX","lock_status":old_state}
        assert plan_fast_locks(current,[old],status(),now_utc=TARGET)==[]


def test_stale_future_and_wrong_artifact_fail_closed():
    row=snapshot(TARGET-timedelta(hours=3))
    with pytest.raises(FastLockError,match="stale"):
        plan_fast_locks([row],[],status(),now_utc=TARGET)
    row=snapshot()
    row["prediction_timestamp_utc"]=(TARGET+timedelta(minutes=5)).isoformat()
    with pytest.raises(FastLockError,match="stale/future"):
        plan_fast_locks([row],[],status(),now_utc=TARGET)
    row=snapshot()
    row["final_probability_strategy"]="75-25-LEGACY"
    with pytest.raises(FastLockError,match="strategy"):
        plan_fast_locks([row],[],status(),now_utc=TARGET)
    with pytest.raises(FastLockError,match="Missing or duplicate"):
        plan_fast_locks([snapshot(),snapshot()],[],{**status(),"games":2},now_utc=TARGET)


def test_kickoff_timezone_is_dst_safe():
    row=snapshot()
    row["gameday"]="2026-11-01"
    row["gametime"]="13:00" # 18:00 UTC after the fall-back
    row["prediction_timestamp_utc"]="2026-11-01T15:30:00+00:00"
    due=datetime(2026,11,1,16,0,tzinfo=timezone.utc)
    locked=plan_fast_locks([row],[],status(),now_utc=due)
    assert locked[0]["kickoff_utc"]=="2026-11-01T18:00:00+00:00"


def _write_csv(path,fields,rows):
    with path.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_append_only_history_is_byte_preserving_atomic_and_retry_idempotent(tmp_path):
    _write_csv(tmp_path/"this_week.csv",CURRENT_COLUMNS,[snapshot()])
    historic_fields=CURRENT_COLUMNS+LOCK_META_COLUMNS
    history_old={x:"" for x in historic_fields}
    history_old.update({"game_id":"2026_04_IND_WAS","season":"2026","week":"4",
                        "lock_status":"RECOVERED_MISSED_LOCK"})
    _write_csv(tmp_path/"prediction_history.csv",historic_fields,[history_old])
    before=(tmp_path/"prediction_history.csv").read_bytes()
    (tmp_path/"status.json").write_text(json.dumps(status()),encoding="utf-8")

    ids=write_fast_locks(tmp_path,TARGET)
    assert ids==["2026_05_PHI_JAX"]
    after=(tmp_path/"prediction_history.csv").read_bytes()
    assert after.startswith(before)
    assert after!=before
    receipts=json.loads((tmp_path/"lock_fast_path_receipts"/"2026_05_PHI_JAX.json").read_text())
    assert receipts["no_model_recomputation"] is True
    assert receipts["source_prediction_timestamp_utc"]==snapshot()["prediction_timestamp_utc"]
    fresh_status=json.loads((tmp_path/"status.json").read_text())
    assert fresh_status["generated_utc"]==status()["generated_utc"]
    assert fresh_status["locked_official_predictions"]==2

    assert write_fast_locks(tmp_path,TARGET+timedelta(minutes=1))==[]
    assert (tmp_path/"prediction_history.csv").read_bytes()==after


def test_rejects_schema_drift_without_touching_history(tmp_path):
    (tmp_path/"this_week.csv").write_text("game_id\n123\n",encoding="utf-8")
    (tmp_path/"prediction_history.csv").write_text("game_id\nold\n",encoding="utf-8")
    old=(tmp_path/"prediction_history.csv").read_bytes()
    (tmp_path/"status.json").write_text(json.dumps(status()),encoding="utf-8")
    with pytest.raises(FastLockError,match="schema"):
        write_fast_locks(tmp_path,TARGET)
    assert (tmp_path/"prediction_history.csv").read_bytes()==old

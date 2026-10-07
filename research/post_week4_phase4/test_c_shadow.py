"""Fast, outcome-blind tests for the immutable C shadow PIT gateway and evaluation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import pytest

from research.post_week4_phase4.c_shadow import (
    CANDIDATE_ID, TRAINING_DIGEST, canonical_hash, score_snapshot, write_once,
)
from research.post_week4_phase4.c_shadow_eval import evaluate


def example_model():
    return {
        "candidate_id": CANDIDATE_ID, "training_cutoff":2025,
        "training_games":1615, "training_data_sha256":TRAINING_DIGEST,
        "feature_names":["off_state_diff","def_state_diff","state_uncertainty"],
        "penalty":0.02,"theta":[0.1,0.2,-0.1,0.04],
        "means":[0.0,0.0,0.0],"stds":[1.0,1.0,1.0],
        "builder_source_sha256":"b"*64,
        "historical_state_source_sha256":"c"*64,
        "frozen_at_utc":"2026-10-07T00:00:00+00:00",
        "production_promotion_authorized":False,"outcomes_2026_used":0,
    }


def row(team,season,week,off=0.1,defense=0.02):
    return {
        "team":team, "season":season, "game_id":f"{season}_{week:02d}_{team}_ANY",
        "kickoff_utc": f"{season}-09-{1+week:02d}T00:00:00+00:00",
        "stats_observed_utc": f"{season}-09-{2+week:02d}T00:00:00+00:00",
        "off_epa":off, "def_epa_allowed":defense,
    }


def team_state(team):
    return {
        "team":team,
        "last_eight_previous_season":[row(team,2025,w,off=.03+w*.01) for w in range(1,9)],
        "current_season_completed":[row(team,2026,w,off=.01+w*.015) for w in range(1,5)],
        "previous_season_league_mean":{"off_epa":0.0,"def_epa_allowed":0.0},
        "expected_completed_current_season_games":4,
    }


def example_snapshot():
    return {
        "contract":"c_shadow_pit_v1",
        "game_id":"2026_05_BUF_KC","season":2026,"week":5,
        "home_team":"KC","away_team":"BUF",
        "kickoff_utc":"2026-10-11T20:30:00+00:00",
        "fst_lock_timestamp_utc":"2026-10-11T18:55:00+00:00",
        "snapshot_captured_utc":"2026-10-11T18:50:00+00:00",
        "features_observed_at_utc":"2026-10-11T18:49:00+00:00",
        "feature_source_asof_utc":"2026-10-11T18:45:00+00:00",
        "fst_lock_status":"LOCKED",
        "fst_candidate_id":"F-ST-01-FROZEN-2026",
        "market_home_prob":.57,"fst_home_prob":.56,
        "raw_source_sha256":"d"*64,"schedule_source_sha256":"e"*64,
        "team_state_builder_id":"EARLY-STATE-SHRINKAGE-V1",
        "upstream_completion_audit_passed":True,
        "team_states":{"home":team_state("KC"),"away":team_state("BUF")},
    }


def test_snapshot_scores_deterministically_without_fitting():
    model=example_model()
    record=score_snapshot(example_snapshot(),model)
    assert record["candidate_id"]==CANDIDATE_ID
    assert 0<record["candidate_home_prob"]<1
    assert record["candidate_home_prob"]==score_snapshot(example_snapshot(),model)["candidate_home_prob"]
    assert record["production_changed"] is False
    assert "outcome" not in record
    assert record["input_snapshot_sha256"]==canonical_hash(example_snapshot())
    assert record["frozen_features"]["state_uncertainty"]==0.0


@pytest.mark.parametrize("field,value", [
    ("features_observed_at_utc","2026-10-11T18:56:00+00:00"),
    ("snapshot_captured_utc","2026-10-11T19:10:00+00:00"),
    ("feature_source_asof_utc","2026-10-11T19:10:00+00:00"),
    ("fst_lock_status","PREVIEW"),
    ("fst_candidate_id","F-ST-REWRITTEN"),
    ("raw_source_sha256","invalid"),
    ("upstream_completion_audit_passed",False),
    ("market_home_prob",1.0),
    ("kickoff_utc","2026-10-11T18:45:00+00:00"),
])
def test_unqualified_snapshots_fail_closed(field,value):
    s=example_snapshot();s[field]=value
    with pytest.raises(ValueError):
        score_snapshot(s,example_model())


def test_rejects_bad_historical_team_games_and_missing_count():
    s=example_snapshot()
    s["team_states"]["home"]["expected_completed_current_season_games"]=3
    with pytest.raises(ValueError,match="count"):
        score_snapshot(s,example_model())
    s=example_snapshot()
    s["team_states"]["away"]["current_season_completed"][0]["stats_observed_utc"]="2026-10-12T12:00:00Z"
    with pytest.raises(ValueError,match="post-cutoff"):
        score_snapshot(s,example_model())
    s=example_snapshot()
    s["team_states"]["away"]["last_eight_previous_season"][1]=deepcopy(s["team_states"]["away"]["last_eight_previous_season"][0])
    with pytest.raises(ValueError,match="Duplicate"):
        score_snapshot(s,example_model())


def test_immutable_output_does_not_overwrite(tmp_path: Path):
    dest=tmp_path/"2026_05_BUF_KC.json"
    rec=score_snapshot(example_snapshot(),example_model())
    write_once(dest,rec)
    assert dest.exists()
    with pytest.raises(FileExistsError):
        write_once(dest,rec)


def test_evaluation_separates_advance_grades_and_ties():
    score=score_snapshot(example_snapshot(),example_model())
    empty=evaluate([score],[])
    assert empty["status"]=="AWAITING_ELIGIBLE_LOCKS"
    assert empty["pending_games"]==1
    result={"game_id":score["game_id"],"season":2026,"week":5,"home_score":20,"away_score":20,
            "source_type":"verified_official_game_result","source_sha256":"a"*64,
            "result_observed_utc":"2026-10-12T01:00:00Z"}
    ties=evaluate([score],[result])
    assert ties["ties_excluded"]==1 and ties["graded_non_tie_games"]==0
    result["home_score"]=23
    graded=evaluate([score],[result])
    assert graded["status"]=="ACCUMULATING_EVIDENCE"
    assert graded["graded_non_tie_games"]==1
    assert graded["promotion_authorized"] is False
    assert graded["fst"]["games"]==graded["candidate"]["games"]==1
    result["result_observed_utc"]="2026-10-11T21:00:00Z"
    with pytest.raises(ValueError,match="too early"):
        evaluate([score],[result])


def test_changed_model_cannot_be_used_in_same_grade():
    r=score_snapshot(example_snapshot(),example_model())
    x=deepcopy(r)
    x["game_id"]="2026_06_BUF_KC";x["week"]=6;x["frozen_model_sha256"]="f"*64
    with pytest.raises(ValueError,match="Changed frozen"):
        evaluate([r,x],[])


def test_regression_rejects_tampering_or_unqualified_after_lock():
    model=example_model()
    model["theta"]=[0.0]*5
    with pytest.raises(ValueError):
        score_snapshot(example_snapshot(),model)
    s=example_snapshot()
    s["team_states"]["home"]["current_season_completed"][0]["kickoff_utc"]="2026-10-12T00:00:00Z"
    with pytest.raises(ValueError):
        score_snapshot(s,example_model())

def test_formal_checkpoint_requires_accuracy_edge_and_never_promotes():
    from datetime import datetime,timedelta
    base=score_snapshot(example_snapshot(),example_model())
    predictions=[]
    grades=[]
    for week in range(1,15):
        shift=timedelta(days=(week-1)*7)
        for i in range(15):
            row=deepcopy(base)
            row["season"]=2026
            row["week"]=week
            row["away_team"]=f"AW{i}"
            row["home_team"]=f"HT{i}"
            row["game_id"]=f"2026_{week:02d}_AW{i}_HT{i}"
            for field in ("kickoff_utc","fst_lock_timestamp_utc","snapshot_captured_utc","source_observed_utc"):
                row[field]=(datetime.fromisoformat(base[field])+shift).isoformat()
            predictions.append(row)
            kick=datetime.fromisoformat(row["kickoff_utc"])
            grades.append({
                "game_id":row["game_id"],"season":2026,"week":week,
                "home_score":24 if i%2==0 else 17,
                "away_score":17 if i%2==0 else 24,
                "source_type":"verified_official_game_result",
                "source_sha256":"a"*64,
                "result_observed_utc":(kick+timedelta(hours=4)).isoformat(),
            })
    report=evaluate(predictions,grades)
    assert report["graded_non_tie_games"]==210
    assert report["weeks"]==14
    assert report["status"]=="FORMAL_REVIEW_ELIGIBLE"
    assert report["switches"]==0
    assert report["scientific_preliminary_gate_met"] is False
    assert report["promotion_authorized"] is False
    assert report["week_block_accuracy_delta_ci95"]==[0.0,0.0]

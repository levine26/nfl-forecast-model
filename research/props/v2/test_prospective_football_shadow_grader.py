from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"grade_prospective_football_shadow.py"


def _module():
    spec=importlib.util.spec_from_file_location("shadow_grader_tested",SCRIPT)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(values):
    module=_module()
    support,counts=np.unique(np.asarray(values,dtype=float),return_counts=True)
    material={
        "sample_count":len(values),
        "support":[float(x) for x in support.tolist()],
        "counts":[int(x) for x in counts.tolist()],
    }
    material["sha256"]=module._sha(material)
    return material


def test_empirical_crps_matches_raw_sample_formula():
    module=_module()
    values=np.array([0.0,1.0,1.0,3.0])
    snap=_snapshot(values)
    y=2.0
    raw=float(np.mean(np.abs(values-y))-0.5*np.mean(np.abs(values[:,None]-values[None,:])))
    assert module.empirical_crps(snap,y)==pytest.approx(raw)


def test_distribution_hash_is_enforced():
    module=_module()
    snap=_snapshot([1,2,3])
    snap["counts"][0]=2
    with pytest.raises(module.ShadowGradingError,match="SHA-256"):
        module.validate_distribution(snap)


def test_pushes_are_excluded_only_from_threshold_binary_metrics():
    module=_module()
    receipt={
        "shadow_id":"s1",
        "source_season":2026,
        "source_week":2,
        "game_id":"G1",
        "player_id":"P1",
        "prop_type":"rushing_yards",
        "market":{"line":50.0},
        "v1":{
            "fair_line":50.0,
            "over_probability":0.5,
            "prediction_interval":{"low":30.0,"high":70.0,"coverage":0.8},
            "empirical_distribution":_snapshot([40,50,50,60]),
        },
        "shadow_a":{
            "fair_line":51.0,
            "over_probability":0.55,
            "prediction_interval":{"low":31.0,"high":71.0,"coverage":0.8},
            "empirical_distribution":_snapshot([41,50,50,61]),
        },
        "source_signal_state":"WATCH",
        "source_data_quality":{"state":"HIGH"},
    }
    frame,audit=module.grade_receipts(
        [receipt],
        completed_games={"G1"},
        actuals={("G1","P1","rushing_yards"):50.0},
        participation={("G1","P1"):25},
    )
    assert len(frame)==1
    assert audit["graded"]==1
    assert bool(frame.iloc[0]["push"]) is True
    assert np.isfinite(frame.iloc[0]["v1_crps"])
    assert np.isnan(frame.iloc[0]["v1_brier"])
    assert np.isnan(frame.iloc[0]["v1_direction_hit"])


def test_minimum_discussion_threshold_is_not_automatic_promotion():
    module=_module()
    rows=[]
    for game in range(100):
        for j in range(3):
            rows.append({
                "source_season":2026,
                "source_week":1+(game%8),
                "game_id":f"G{game}",
                "player_id":f"P{game}_{j}",
                "prop_type":"receiving_yards",
                "push":False,
                "v1_crps":10.0,
                "shadow_crps":9.5,
                "shadow_minus_v1_crps":-0.5,
                "v1_abs_error":12.0,
                "shadow_abs_error":11.5,
                "shadow_minus_v1_abs_error":-0.5,
                "v1_brier":0.25,
                "shadow_brier":0.24,
                "shadow_minus_v1_brier":-0.01,
                "v1_log_loss":0.69,
                "shadow_log_loss":0.68,
                "shadow_minus_v1_log_loss":-0.01,
                "v1_interval_score_80":30.0,
                "shadow_interval_score_80":29.0,
                "v1_covered_80":True,
                "shadow_covered_80":True,
                "v1_direction_hit":1.0,
                "shadow_direction_hit":1.0,
                "v1_over_probability":0.55,
                "shadow_over_probability":0.56,
                "over_outcome":1.0,
            })
    frame=pd.DataFrame(rows)
    summary=module.summarize(frame,seed=1)
    assert summary["minimum_discussion_threshold"]["sample_size_conditions_met"] is True
    assert summary["automatic_promotion_authorized"] is False


def test_zero_offense_snaps_are_void_but_positive_snaps_zero_events_grade_zero():
    module=_module()
    base={
        "shadow_id":"s",
        "source_season":2026,
        "source_week":2,
        "game_id":"G1",
        "player_id":"P1",
        "prop_type":"receiving_yards",
        "market":{"line":10.5},
        "v1":{
            "fair_line":12.0,
            "over_probability":0.55,
            "prediction_interval":{"low":0.0,"high":30.0,"coverage":0.8},
            "empirical_distribution":_snapshot([0,5,10,15]),
        },
        "shadow_a":{
            "fair_line":11.0,
            "over_probability":0.52,
            "prediction_interval":{"low":0.0,"high":28.0,"coverage":0.8},
            "empirical_distribution":_snapshot([0,4,9,14]),
        },
    }
    frame,audit=module.grade_receipts(
        [base],
        completed_games={"G1"},
        actuals={},
        participation={("G1","P1"):0},
    )
    assert frame.empty
    assert audit["zero_offense_snaps_void"]==1

    frame,audit=module.grade_receipts(
        [base],
        completed_games={"G1"},
        actuals={},
        participation={("G1","P1"):12},
    )
    assert len(frame)==1
    assert frame.iloc[0]["actual_result"]==0.0
    assert audit["graded"]==1


def test_fixed_80_interval_is_derived_from_empirical_distribution():
    module=_module()
    snapshot=_snapshot([0,10,20,30,40,50,60,70,80,90])
    score,covered,low,high=module.fixed_interval_score(
        snapshot,50.0,level=0.80
    )
    assert low==0.0
    assert high==80.0
    assert covered is True
    assert score==pytest.approx(80.0)


def test_receipt_integrity_hash_is_enforced(tmp_path):
    module=_module()
    row={
        "contract_version":module.RECEIPT_CONTRACT_VERSION,
        "shadow_version":module.SHADOW_VERSION,
        "shadow_id":"shadow-1",
        "source_forecast_sha256":"a"*64,
        "source_manifest_sha256":"b"*64,
        "source_season":2026,
        "source_week":2,
        "source_workflow_run":"12345",
        "source_head_sha":"c"*40,
        "recorded_utc":"2026-09-20T19:00:00+00:00",
        "source_forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "source_market_captured_utc":"2026-09-20T18:05:00+00:00",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "prop_type":"rushing_yards",
        "governance":{
            "production_authorized":False,
            "target_week_outcomes_used":0,
        },
        "v1":{"empirical_distribution":_snapshot([1,2,3])},
        "shadow_a":{"empirical_distribution":_snapshot([1,2,4])},
    }
    row["shadow_sha256"]=module._sha(row)
    path=tmp_path/"ledger.jsonl"
    path.write_text(json.dumps(row)+"\n",encoding="utf-8")
    receipts=module.read_receipts(path)
    assert len(receipts)==1

    corrupted=json.loads(json.dumps(row))
    corrupted["source_week"]=3
    path.write_text(json.dumps(corrupted)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowGradingError,match="receipt SHA-256 mismatch"):
        module.read_receipts(path)


def test_receipt_integrity_rejects_post_kickoff_chronology(tmp_path):
    module=_module()
    row={
        "contract_version":module.RECEIPT_CONTRACT_VERSION,
        "shadow_version":module.SHADOW_VERSION,
        "shadow_id":"shadow-late",
        "source_forecast_sha256":"a"*64,
        "source_manifest_sha256":"b"*64,
        "source_season":2026,
        "source_week":2,
        "source_workflow_run":"12345",
        "source_head_sha":"c"*40,
        "recorded_utc":"2026-09-20T20:01:00+00:00",
        "source_forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "source_market_captured_utc":"2026-09-20T18:05:00+00:00",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "prop_type":"rushing_yards",
        "governance":{
            "production_authorized":False,
            "target_week_outcomes_used":0,
        },
        "v1":{"empirical_distribution":_snapshot([1,2,3])},
        "shadow_a":{"empirical_distribution":_snapshot([1,2,4])},
    }
    row["shadow_sha256"]=module._sha(row)
    path=tmp_path/"ledger.jsonl"
    path.write_text(json.dumps(row)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowGradingError,match="pre-kickoff"):
        module.read_receipts(path)

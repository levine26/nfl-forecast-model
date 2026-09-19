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
    frame=module.grade_receipts(
        [receipt],
        completed_games={"G1"},
        actuals={("G1","P1","rushing_yards"):50.0},
    )
    assert len(frame)==1
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

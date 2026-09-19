from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"grade_prospective_football_shadow_b.py"


def _module():
    spec=importlib.util.spec_from_file_location("shadow_b_grader_tested",SCRIPT)
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


def _b_receipt():
    module=_module()
    row={
        "contract_version":module.SHADOW_B_RECEIPT_CONTRACT,
        "shadow_version":module.SHADOW_B_VERSION,
        "shadow_id":"b-shadow-1",
        "capture_started_utc":"2026-09-20T18:30:00+00:00",
        "capture_completed_utc":"2026-09-20T19:00:00+00:00",
        "recorded_utc":"2026-09-20T19:00:00+00:00",
        "source_workflow_run":"12345",
        "source_head_sha":"c"*40,
        "source_season":2026,
        "source_week":2,
        "source_forecast_id":"forecast-1",
        "source_forecast_sha256":"a"*64,
        "source_manifest_sha256":"b"*64,
        "source_forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "source_market_captured_utc":"2026-09-20T18:05:00+00:00",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "game_id":"G1",
        "player_id":"P1",
        "team":"ARI",
        "prop_type":"rushing_yards",
        "market":{"line":50.5,"no_vig_over_probability":0.51},
        "v1":{
            "fair_line":49.0,
            "over_probability":0.47,
            "empirical_distribution":_snapshot([30,40,50,60,70]),
        },
        "shadow_b":{
            "fair_line":52.0,
            "over_probability":0.54,
            "empirical_distribution":_snapshot([32,42,52,62,72]),
        },
        "defensive_efficiency":{
            "coefficient_contract_version":module.FROZEN_COEFFICIENT_VERSION,
            "fit":{"trained_through_season":2025},
        },
        "dynamic_role_v01":{
            "engine_version":module.DYNAMIC_ROLE_VERSION,
            "mode":"full",
            "adjustment":{"carry_role_multiplier":1.1},
        },
        "governance":{
            "production_authorized":False,
            "published_v1_props_mutated":False,
            "winner_model_mutated":False,
            "target_week_outcomes_used":0,
            "completed_2026_outcomes_used_for_model_selection":0,
            "captured_v1_baseline_reconstructed_before_role_transform":True,
            "dynamic_role_mode":"full",
        },
    }
    row["shadow_sha256"]=module._sha(row)
    return row


def _a_pair_for(b):
    return {
        "source_forecast_id":b["source_forecast_id"],
        "source_workflow_run":b["source_workflow_run"],
        "source_head_sha":b["source_head_sha"],
        "source_forecast_sha256":b["source_forecast_sha256"],
        "source_manifest_sha256":b["source_manifest_sha256"],
        "source_season":b["source_season"],
        "source_week":b["source_week"],
        "game_id":b["game_id"],
        "player_id":b["player_id"],
        "prop_type":b["prop_type"],
        "kickoff_utc":b["kickoff_utc"],
        "market":dict(b["market"]),
        "v1":{
            "empirical_distribution":dict(b["v1"]["empirical_distribution"]),
        },
        "shadow_a":{
            "fair_line":51.0,
            "over_probability":0.52,
            "empirical_distribution":_snapshot([31,41,51,61,71]),
        },
    }


def test_b_grader_is_locked_to_frozen_a_grading_contract():
    module=_module()
    assert module.shadow_a_grader.CONTRACT_VERSION==module.SHADOW_A_GRADING_CONTRACT
    assert module.SHADOW_A_GRADING_CONTRACT=="levline-props-v2-football-shadow-grading-v0.1.0"
    assert module.SHADOW_B_VERSION=="P2-SHADOW-B-DEFENSE-ROLE-v0.1.0"


def test_b_receipt_integrity_locks_role_and_defense_versions(tmp_path):
    module=_module()
    row=_b_receipt()
    path=tmp_path/"b.jsonl"
    path.write_text(json.dumps(row)+"\n",encoding="utf-8")
    receipts=module.read_b_receipts(path)
    assert len(receipts)==1

    bad=json.loads(json.dumps(row))
    bad["dynamic_role_v01"]["engine_version"]="other"
    bad["shadow_sha256"]=module._sha({k:v for k,v in bad.items() if k!="shadow_sha256"})
    path.write_text(json.dumps(bad)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="Dynamic Role engine"):
        module.read_b_receipts(path)

    bad=json.loads(json.dumps(row))
    bad["defensive_efficiency"]["fit"]["trained_through_season"]=2026
    bad["shadow_sha256"]=module._sha({k:v for k,v in bad.items() if k!="shadow_sha256"})
    path.write_text(json.dumps(bad)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="frozen through 2025"):
        module.read_b_receipts(path)


def test_a_b_pair_requires_identical_source_and_v1_distribution():
    module=_module()
    b=_b_receipt()
    a=_a_pair_for(b)
    module.verify_pair(a,b)

    drift=json.loads(json.dumps(a))
    drift["source_workflow_run"]="other"
    with pytest.raises(module.ShadowBGradingError,match="source_workflow_run"):
        module.verify_pair(drift,b)

    drift=json.loads(json.dumps(a))
    drift["v1"]["empirical_distribution"]["sha256"]="f"*64
    with pytest.raises(module.ShadowBGradingError,match="V1 empirical distribution"):
        module.verify_pair(drift,b)


def test_grade_b_uses_shadow_a_only_when_integrity_matched():
    module=_module()
    b=_b_receipt()
    a=_a_pair_for(b)
    frame,audit=module.grade_b_receipts(
        [b],
        matched_a={b["source_forecast_id"]:a},
        completed_games={"G1"},
        outcome_pbp_games={"G1"},
        actuals={("G1","P1","rushing_yards"):55.0},
        participation={("G1","P1"):25},
    )
    assert len(frame)==1
    row=frame.iloc[0]
    assert bool(row["has_shadow_a_pair"]) is True
    assert np.isfinite(row["b_minus_a_crps"])
    assert np.isfinite(row["b_minus_v1_crps"])
    assert audit["graded_with_a_pair"]==1

    frame,audit=module.grade_b_receipts(
        [b],
        matched_a={},
        completed_games={"G1"},
        outcome_pbp_games={"G1"},
        actuals={("G1","P1","rushing_yards"):55.0},
        participation={("G1","P1"):25},
    )
    assert len(frame)==1
    assert bool(frame.iloc[0]["has_shadow_a_pair"]) is False
    assert "b_minus_a_crps" not in frame.columns or pd.isna(frame.iloc[0].get("b_minus_a_crps"))
    assert audit["graded_with_a_pair"]==0


def test_push_policy_matches_shadow_a_contract():
    module=_module()
    b=_b_receipt()
    b["market"]["line"]=50.0
    a=_a_pair_for(b)
    a["market"]["line"]=50.0
    frame,_=module.grade_b_receipts(
        [b],
        matched_a={b["source_forecast_id"]:a},
        completed_games={"G1"},
        outcome_pbp_games={"G1"},
        actuals={("G1","P1","rushing_yards"):50.0},
        participation={("G1","P1"):20},
    )
    row=frame.iloc[0]
    assert bool(row["push"]) is True
    assert np.isfinite(row["b_minus_a_crps"])
    assert np.isnan(row["b_minus_a_brier"])
    assert np.isnan(row["b_minus_a_direction_hit"])


def _summary_rows(n_games=100,rows_per_game=3,paired=True):
    rows=[]
    for game in range(n_games):
        for j in range(rows_per_game):
            rows.append({
                "source_season":2026,
                "source_week":1+(game%8),
                "game_id":f"G{game}",
                "player_id":f"P{game}_{j}",
                "team":"ARI" if game%2==0 else "LAR",
                "prop_type":"receiving_yards",
                "push":False,
                "has_shadow_a_pair":paired,
                "v1_crps":10.2,
                "shadow_a_crps":10.0,
                "shadow_b_crps":9.8,
                "b_minus_a_crps":-0.2,
                "b_minus_v1_crps":-0.4,
                "v1_abs_error":12.2,
                "shadow_a_abs_error":12.0,
                "shadow_b_abs_error":11.7,
                "b_minus_a_abs_error":-0.3,
                "b_minus_v1_abs_error":-0.5,
                "v1_brier":0.26,
                "shadow_a_brier":0.25,
                "shadow_b_brier":0.24,
                "b_minus_a_brier":-0.01,
                "b_minus_v1_brier":-0.02,
                "v1_log_loss":0.70,
                "shadow_a_log_loss":0.69,
                "shadow_b_log_loss":0.68,
                "b_minus_a_log_loss":-0.01,
                "b_minus_v1_log_loss":-0.02,
                "v1_interval_score_80":31.0,
                "shadow_a_interval_score_80":30.0,
                "shadow_b_interval_score_80":29.0,
                "b_minus_a_interval_score_80":-1.0,
                "b_minus_v1_interval_score_80":-2.0,
                "v1_covered_80":False,
                "shadow_a_covered_80":True,
                "shadow_b_covered_80":True,
                "b_minus_a_coverage_80":0.0,
                "b_minus_v1_coverage_80":1.0,
                "v1_direction_hit":0.0,
                "shadow_a_direction_hit":1.0,
                "shadow_b_direction_hit":1.0,
                "b_minus_a_direction_hit":0.0,
                "b_minus_v1_direction_hit":1.0,
                "v1_over_probability":0.45,
                "shadow_a_over_probability":0.52,
                "shadow_b_over_probability":0.55,
                "over_outcome":1.0,
            })
    return pd.DataFrame(rows)


def test_b_vs_a_threshold_uses_only_matched_receipts_and_never_auto_promotes():
    module=_module()
    frame=_summary_rows()
    summary=module.summarize(frame,comparison="b_vs_a",seed=11)
    assert summary["decided_n"]==300
    assert summary["minimum_discussion_threshold"]["sample_size_conditions_met"] is True
    assert summary["minimum_discussion_threshold"]["proper_score_nondegradation_conditions_met"] is True
    assert summary["automatic_promotion_authorized"] is False

    unpaired=_summary_rows(paired=False)
    summary=module.summarize(unpaired,comparison="b_vs_a",seed=11)
    assert summary["n"]==0


def test_b_vs_v1_is_supporting_context_and_reports_clustered_uncertainty():
    module=_module()
    frame=_summary_rows(n_games=12,rows_per_game=1)
    summary=module.summarize(frame,comparison="b_vs_v1",seed=17)
    assert summary["comparison"]=="b_vs_v1"
    for key in (
        "crps_difference_ci95",
        "mae_difference_ci95",
        "brier_difference_ci95",
        "log_loss_difference_ci95",
        "interval_score_difference_ci95",
        "coverage_difference_ci95",
        "direction_accuracy_difference_ci95",
    ):
        assert len(summary[key])==2
        assert all(value is not None for value in summary[key])
    assert "minimum_discussion_threshold" not in summary
    assert summary["automatic_promotion_authorized"] is False


def test_b_receipt_integrity_rejects_source_or_role_schema_drift(tmp_path):
    module=_module()
    row=_b_receipt()
    path=tmp_path/"b.jsonl"

    bad=json.loads(json.dumps(row))
    bad["source_head_sha"]="not-a-sha"
    bad["shadow_sha256"]=module._sha({k:v for k,v in bad.items() if k!="shadow_sha256"})
    path.write_text(json.dumps(bad)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="source head SHA"):
        module.read_b_receipts(path)

    bad=json.loads(json.dumps(row))
    bad["dynamic_role_v01"].pop("mode")
    bad["shadow_sha256"]=module._sha({k:v for k,v in bad.items() if k!="shadow_sha256"})
    path.write_text(json.dumps(bad)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="Dynamic Role mode"):
        module.read_b_receipts(path)

    bad=json.loads(json.dumps(row))
    bad["capture_started_utc"]="2026-09-20T19:10:00+00:00"
    bad["capture_completed_utc"]="2026-09-20T19:00:00+00:00"
    bad["shadow_sha256"]=module._sha({k:v for k,v in bad.items() if k!="shadow_sha256"})
    path.write_text(json.dumps(bad)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="capture timestamps"):
        module.read_b_receipts(path)


def test_b_vs_a_proper_score_nondegradation_is_joint():
    module=_module()
    frame=_summary_rows()
    frame["b_minus_a_brier"]=0.01
    frame["shadow_b_brier"]=frame["shadow_a_brier"]+0.01
    summary=module.summarize(frame,comparison="b_vs_a",seed=23)
    threshold=summary["minimum_discussion_threshold"]
    assert threshold["no_material_crps_degradation_vs_shadow_a"] is True
    assert threshold["no_material_brier_degradation_vs_shadow_a"] is False
    assert threshold["proper_score_nondegradation_conditions_met"] is False


def test_concentration_reports_team_week_player_and_prop():
    module=_module()
    frame=_summary_rows(n_games=12,rows_per_game=1)
    report=module.concentration(frame)
    assert report["largest_week_share"]>0.0
    assert report["largest_team_share"]==pytest.approx(0.5)
    assert report["largest_team"] in {"ARI","LAR"}
    assert report["largest_player_share"]>0.0
    assert report["prop_counts"]["receiving_yards"]==12


def test_b_receipt_integrity_requires_team_identity(tmp_path):
    module=_module()
    row=_b_receipt()
    row["team"]=""
    row["shadow_sha256"]=module._sha({k:v for k,v in row.items() if k!="shadow_sha256"})
    path=tmp_path/"b.jsonl"
    path.write_text(json.dumps(row)+"\n",encoding="utf-8")
    with pytest.raises(module.ShadowBGradingError,match="team identity"):
        module.read_b_receipts(path)

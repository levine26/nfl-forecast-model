from __future__ import annotations

"""Grade immutable Props 2.0 Shadow B receipts against Shadow A and V1."""

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

import grade_prospective_football_shadow as shadow_a_grader  # noqa:E402
from nfl_forecast.data import load_advanced_data, load_core_data  # noqa:E402
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids  # noqa:E402
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics  # noqa:E402

CONTRACT_VERSION="levline-props-v2-football-shadow-b-grading-v0.1.0"
SHADOW_A_GRADING_CONTRACT="levline-props-v2-football-shadow-grading-v0.1.0"
SHADOW_A_RECEIPT_CONTRACT="levline-props-v2-football-shadow-a-v0.1.0"
SHADOW_A_VERSION="P2-SHADOW-A-DEFENSE-v0.1.0"
SHADOW_B_RECEIPT_CONTRACT="levline-props-v2-football-shadow-b-v0.1.0"
SHADOW_B_VERSION="P2-SHADOW-B-DEFENSE-ROLE-v0.1.0"
DYNAMIC_ROLE_VERSION="levline-props-dynamic-role-v0.1.0"
FROZEN_COEFFICIENT_VERSION="levline-props-v2-defensive-efficiency-shadow-v0.1.0"
SUPPORTED_PROPS=("rushing_yards","receiving_yards")
BOOTSTRAP_REPLICATES=5000
BOOTSTRAP_SEED=20260919
MIN_DECIDED_PROPS=300
MIN_UNIQUE_GAMES=100
MIN_WEEKS=8
EPS=1e-12

if shadow_a_grader.CONTRACT_VERSION != SHADOW_A_GRADING_CONTRACT:
    raise RuntimeError("Shadow B grader dependency drift: Shadow A grading contract changed")


class ShadowBGradingError(ValueError):
    pass


def _sha(value: Any)->str:
    return shadow_a_grader._sha(value)


def _aware(value: Any, label: str)->pd.Timestamp:
    try:
        return shadow_a_grader._aware_timestamp(value,label=label)
    except Exception as exc:
        raise ShadowBGradingError(str(exc)) from exc


def _finite(value: Any)->float|None:
    try:
        out=float(value)
    except (TypeError,ValueError):
        return None
    return out if math.isfinite(out) else None


def verify_b_receipt(row: Mapping[str,Any])->None:
    if row.get("contract_version")!=SHADOW_B_RECEIPT_CONTRACT:
        raise ShadowBGradingError("unexpected Shadow B receipt contract")
    if row.get("shadow_version")!=SHADOW_B_VERSION:
        raise ShadowBGradingError("unexpected Shadow B version")

    supplied=str(row.get("shadow_sha256") or "")
    material=dict(row)
    material.pop("shadow_sha256",None)
    if len(supplied)!=64 or supplied!=_sha(material):
        raise ShadowBGradingError("Shadow B receipt SHA-256 mismatch")

    for field in ("source_forecast_sha256","source_manifest_sha256"):
        value=str(row.get(field) or "").lower()
        if len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
            raise ShadowBGradingError(f"invalid Shadow B provenance hash: {field}")

    season=int(row.get("source_season",-1))
    week=int(row.get("source_week",-1))
    if season<2026 or not 1<=week<=18:
        raise ShadowBGradingError("invalid Shadow B season/week")

    kickoff=_aware(row.get("kickoff_utc"),"kickoff_utc")
    forecast_at=_aware(row.get("source_forecast_timestamp_utc"),"source_forecast_timestamp_utc")
    market_at=_aware(row.get("source_market_captured_utc"),"source_market_captured_utc")
    recorded_at=_aware(row.get("recorded_utc"),"recorded_utc")
    if not (forecast_at<kickoff and market_at<kickoff and recorded_at<kickoff):
        raise ShadowBGradingError("Shadow B receipt is not strictly pre-kickoff")
    if forecast_at>recorded_at or market_at>recorded_at:
        raise ShadowBGradingError("Shadow B receipt chronology is inconsistent")

    governance=row.get("governance")
    if not isinstance(governance,Mapping):
        raise ShadowBGradingError("Shadow B receipt missing governance")
    required_false=(
        "production_authorized",
        "published_v1_props_mutated",
        "winner_model_mutated",
    )
    for field in required_false:
        if governance.get(field) is not False:
            raise ShadowBGradingError(f"Shadow B governance violation: {field}")
    if int(governance.get("target_week_outcomes_used",-1))!=0:
        raise ShadowBGradingError("Shadow B used target-week outcomes")
    if int(governance.get("completed_2026_outcomes_used_for_model_selection",-1))!=0:
        raise ShadowBGradingError("Shadow B used completed 2026 outcomes for model selection")
    if governance.get("captured_v1_baseline_reconstructed_before_role_transform") is not True:
        raise ShadowBGradingError("Shadow B did not verify captured V1 opportunity baseline")
    if str(governance.get("dynamic_role_mode") or "")!="full":
        raise ShadowBGradingError("Shadow B Dynamic Role mode is not full")

    defense=row.get("defensive_efficiency")
    if not isinstance(defense,Mapping):
        raise ShadowBGradingError("Shadow B missing defensive-efficiency provenance")
    if str(defense.get("coefficient_contract_version") or "")!=FROZEN_COEFFICIENT_VERSION:
        raise ShadowBGradingError("unexpected Shadow B defensive coefficient contract")
    fit=defense.get("fit")
    if not isinstance(fit,Mapping) or int(fit.get("trained_through_season",-1))!=2025:
        raise ShadowBGradingError("Shadow B defensive coefficients are not frozen through 2025")

    role=row.get("dynamic_role_v01")
    if not isinstance(role,Mapping):
        raise ShadowBGradingError("Shadow B missing Dynamic Role provenance")
    if str(role.get("engine_version") or "")!=DYNAMIC_ROLE_VERSION:
        raise ShadowBGradingError("unexpected Dynamic Role engine version")
    if str(role.get("mode") or "full")!="full":
        raise ShadowBGradingError("unexpected Dynamic Role mode")

    if str(row.get("prop_type") or "") not in SUPPORTED_PROPS:
        raise ShadowBGradingError("unsupported Shadow B prop type")
    shadow_a_grader.validate_distribution(row["v1"]["empirical_distribution"])
    shadow_a_grader.validate_distribution(row["shadow_b"]["empirical_distribution"])


def read_b_receipts(path: Path)->list[dict[str,Any]]:
    if not path.is_file():
        raise ShadowBGradingError(f"Shadow B ledger not found: {path}")
    rows=[]
    seen=set()
    for line_number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),start=1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ShadowBGradingError(f"invalid Shadow B JSONL at line {line_number}") from exc
        if not isinstance(row,dict):
            raise ShadowBGradingError(f"Shadow B line {line_number} is not an object")
        verify_b_receipt(row)
        sid=str(row.get("shadow_id") or "")
        if not sid or sid in seen:
            raise ShadowBGradingError(f"invalid/duplicate Shadow B shadow_id: {sid!r}")
        seen.add(sid)
        rows.append(row)
    return rows


def _num_close(a: Any,b: Any,label: str)->None:
    av=_finite(a); bv=_finite(b)
    if av is None and bv is None:
        return
    if av is None or bv is None or not math.isclose(av,bv,rel_tol=0.0,abs_tol=1e-12):
        raise ShadowBGradingError(f"Shadow A/B pair drift for {label}: {av} != {bv}")


def verify_pair(a: Mapping[str,Any], b: Mapping[str,Any])->None:
    exact_fields=(
        "source_forecast_id",
        "source_workflow_run",
        "source_head_sha",
        "source_forecast_sha256",
        "source_manifest_sha256",
        "source_season",
        "source_week",
        "game_id",
        "player_id",
        "prop_type",
        "kickoff_utc",
    )
    for field in exact_fields:
        if str(a.get(field))!=str(b.get(field)):
            raise ShadowBGradingError(f"Shadow A/B pair drift for {field}")
    _num_close(a.get("market",{}).get("line"),b.get("market",{}).get("line"),"market.line")
    _num_close(
        a.get("market",{}).get("no_vig_over_probability"),
        b.get("market",{}).get("no_vig_over_probability"),
        "market.no_vig_over_probability",
    )
    a_v1=a.get("v1",{}).get("empirical_distribution",{})
    b_v1=b.get("v1",{}).get("empirical_distribution",{})
    if str(a_v1.get("sha256") or "")!=str(b_v1.get("sha256") or ""):
        raise ShadowBGradingError("Shadow A/B pair drift for V1 empirical distribution")


def match_a_receipts(
    a_receipts:list[dict[str,Any]],
    b_receipts:list[dict[str,Any]],
)->tuple[dict[str,dict[str,Any]],dict[str,int]]:
    a_index={}
    for row in a_receipts:
        key=str(row.get("source_forecast_id") or "")
        if not key or key in a_index:
            raise ShadowBGradingError(f"duplicate/invalid Shadow A source forecast ID: {key!r}")
        a_index[key]=row
    matched={}
    missing=0
    for b in b_receipts:
        key=str(b.get("source_forecast_id") or "")
        a=a_index.get(key)
        if a is None:
            missing+=1
            continue
        verify_pair(a,b)
        matched[key]=a
    return matched,{"matched":len(matched),"b_without_a":missing}


def _score_distribution(model: Mapping[str,Any], actual: float, line: float, outcome: float|None):
    crps=shadow_a_grader.empirical_crps(model["empirical_distribution"],actual)
    interval,covered,low,high=shadow_a_grader.fixed_interval_score(
        model["empirical_distribution"],actual,level=.80
    )
    p=float(model["over_probability"])
    if not 0.0<=p<=1.0:
        raise ShadowBGradingError("over probability outside [0,1]")
    if outcome is None:
        brier=log_loss=direction=math.nan
    else:
        brier=(p-outcome)**2
        pc=min(max(p,EPS),1.0-EPS)
        log_loss=-(outcome*math.log(pc)+(1.0-outcome)*math.log(1.0-pc))
        fair=float(model["fair_line"])
        side=1.0 if fair>line else 0.0 if fair<line else math.nan
        direction=float(side==outcome) if math.isfinite(side) else math.nan
    return {
        "crps":crps,
        "abs_error":abs(float(model["fair_line"])-actual),
        "brier":brier,
        "log_loss":log_loss,
        "interval_score_80":interval,
        "covered_80":bool(covered),
        "interval_low_80":low,
        "interval_high_80":high,
        "direction_hit":direction,
        "over_probability":p,
    }


def grade_b_receipts(
    b_receipts:list[dict[str,Any]],
    *,
    matched_a:Mapping[str,dict[str,Any]],
    completed_games:set[str],
    outcome_pbp_games:set[str],
    actuals:Mapping[tuple[str,str,str],float],
    participation:Mapping[tuple[str,str],int],
)->tuple[pd.DataFrame,dict[str,int]]:
    rows=[]
    audit={
        "not_final":0,
        "missing_final_pbp":0,
        "missing_participation":0,
        "zero_offense_snaps_void":0,
        "graded":0,
        "graded_with_a_pair":0,
    }
    for b in b_receipts:
        game_id=str(b["game_id"])
        if game_id not in completed_games:
            audit["not_final"]+=1
            continue
        if game_id not in outcome_pbp_games:
            audit["missing_final_pbp"]+=1
            continue
        player_id=str(b["player_id"])
        snaps=participation.get((game_id,player_id))
        if snaps is None:
            audit["missing_participation"]+=1
            continue
        if int(snaps)<=0:
            audit["zero_offense_snaps_void"]+=1
            continue

        prop=str(b["prop_type"])
        actual=float(actuals.get((game_id,player_id,prop),0.0))
        line=float(b["market"]["line"])
        push=math.isclose(actual,line,rel_tol=0.0,abs_tol=1e-12)
        outcome=None if push else float(actual>line)

        v1=_score_distribution(b["v1"],actual,line,outcome)
        sb=_score_distribution(b["shadow_b"],actual,line,outcome)

        source_id=str(b["source_forecast_id"])
        a=matched_a.get(source_id)
        a_metrics=None
        if a is not None:
            a_metrics=_score_distribution(a["shadow_a"],actual,line,outcome)
            audit["graded_with_a_pair"]+=1

        row={
            "source_forecast_id":source_id,
            "source_season":int(b["source_season"]),
            "source_week":int(b["source_week"]),
            "game_id":game_id,
            "player_id":player_id,
            "prop_type":prop,
            "actual_result":actual,
            "market_line":line,
            "push":bool(push),
            "has_shadow_a_pair":a is not None,
            "over_outcome":outcome,
        }
        for prefix,metrics in (("v1",v1),("shadow_b",sb)):
            for key,value in metrics.items():
                row[f"{prefix}_{key}"]=value
        row["b_minus_v1_crps"]=sb["crps"]-v1["crps"]
        row["b_minus_v1_abs_error"]=sb["abs_error"]-v1["abs_error"]
        row["b_minus_v1_brier"]=sb["brier"]-v1["brier"] if outcome is not None else math.nan
        row["b_minus_v1_log_loss"]=sb["log_loss"]-v1["log_loss"] if outcome is not None else math.nan
        row["b_minus_v1_interval_score_80"]=sb["interval_score_80"]-v1["interval_score_80"]
        row["b_minus_v1_coverage_80"]=float(sb["covered_80"])-float(v1["covered_80"])
        row["b_minus_v1_direction_hit"]=(
            sb["direction_hit"]-v1["direction_hit"]
            if outcome is not None and math.isfinite(sb["direction_hit"]) and math.isfinite(v1["direction_hit"])
            else math.nan
        )
        if a_metrics is not None:
            for key,value in a_metrics.items():
                row[f"shadow_a_{key}"]=value
            row["b_minus_a_crps"]=sb["crps"]-a_metrics["crps"]
            row["b_minus_a_abs_error"]=sb["abs_error"]-a_metrics["abs_error"]
            row["b_minus_a_brier"]=sb["brier"]-a_metrics["brier"] if outcome is not None else math.nan
            row["b_minus_a_log_loss"]=sb["log_loss"]-a_metrics["log_loss"] if outcome is not None else math.nan
            row["b_minus_a_interval_score_80"]=sb["interval_score_80"]-a_metrics["interval_score_80"]
            row["b_minus_a_coverage_80"]=float(sb["covered_80"])-float(a_metrics["covered_80"])
            row["b_minus_a_direction_hit"]=(
                sb["direction_hit"]-a_metrics["direction_hit"]
                if outcome is not None and math.isfinite(sb["direction_hit"]) and math.isfinite(a_metrics["direction_hit"])
                else math.nan
            )
        rows.append(row)
    audit["graded"]=len(rows)
    return pd.DataFrame(rows),audit


def _mean(frame: pd.DataFrame,column: str)->float|None:
    if column not in frame or frame.empty:
        return None
    values=pd.to_numeric(frame[column],errors="coerce").dropna()
    return float(values.mean()) if len(values) else None


def _ci(frame: pd.DataFrame,column: str,seed: int)->list[float|None]:
    if column not in frame or frame.empty:
        return [None,None]
    return shadow_a_grader.cluster_ci(frame,column,seed=seed,replicates=BOOTSTRAP_REPLICATES)


def summarize(frame: pd.DataFrame, *, comparison: str, seed: int)->dict[str,Any]:
    if comparison not in {"b_vs_a","b_vs_v1"}:
        raise ShadowBGradingError("invalid comparison")
    if comparison=="b_vs_a":
        work=frame[frame["has_shadow_a_pair"]].copy()
        ref="shadow_a"
        diff="b_minus_a"
    else:
        work=frame.copy()
        ref="v1"
        diff="b_minus_v1"
    if work.empty:
        return {"n":0,"comparison":comparison}

    decided=work[~work["push"]].copy()
    result={
        "comparison":comparison,
        "n":int(len(work)),
        "decided_n":int(len(decided)),
        "unique_games":int(work["game_id"].astype(str).nunique()),
        "unique_players":int(work["player_id"].astype(str).nunique()),
        "unique_weeks":int(work[["source_season","source_week"]].drop_duplicates().shape[0]),
        f"{ref}_crps":_mean(work,f"{ref}_crps"),
        "shadow_b_crps":_mean(work,"shadow_b_crps"),
        "shadow_b_minus_reference_crps":_mean(work,f"{diff}_crps"),
        "crps_difference_ci95":_ci(work,f"{diff}_crps",seed),
        f"{ref}_fair_line_mae":_mean(work,f"{ref}_abs_error"),
        "shadow_b_fair_line_mae":_mean(work,"shadow_b_abs_error"),
        "shadow_b_minus_reference_mae":_mean(work,f"{diff}_abs_error"),
        "mae_difference_ci95":_ci(work,f"{diff}_abs_error",seed+1000),
        f"{ref}_interval_score_80":_mean(work,f"{ref}_interval_score_80"),
        "shadow_b_interval_score_80":_mean(work,"shadow_b_interval_score_80"),
        "shadow_b_minus_reference_interval_score_80":_mean(work,f"{diff}_interval_score_80"),
        "interval_score_difference_ci95":_ci(work,f"{diff}_interval_score_80",seed+2000),
        f"{ref}_coverage_80":_mean(work,f"{ref}_covered_80"),
        "shadow_b_coverage_80":_mean(work,"shadow_b_covered_80"),
        "shadow_b_minus_reference_coverage_80":_mean(work,f"{diff}_coverage_80"),
        "coverage_difference_ci95":_ci(work,f"{diff}_coverage_80",seed+3000),
        f"{ref}_brier":_mean(decided,f"{ref}_brier"),
        "shadow_b_brier":_mean(decided,"shadow_b_brier"),
        "shadow_b_minus_reference_brier":_mean(decided,f"{diff}_brier"),
        "brier_difference_ci95":_ci(decided,f"{diff}_brier",seed+4000),
        f"{ref}_log_loss":_mean(decided,f"{ref}_log_loss"),
        "shadow_b_log_loss":_mean(decided,"shadow_b_log_loss"),
        "shadow_b_minus_reference_log_loss":_mean(decided,f"{diff}_log_loss"),
        "log_loss_difference_ci95":_ci(decided,f"{diff}_log_loss",seed+5000),
        f"{ref}_direction_accuracy":_mean(decided,f"{ref}_direction_hit"),
        "shadow_b_direction_accuracy":_mean(decided,"shadow_b_direction_hit"),
        "shadow_b_minus_reference_direction_accuracy":_mean(decided,f"{diff}_direction_hit"),
        "direction_accuracy_difference_ci95":_ci(decided,f"{diff}_direction_hit",seed+6000),
        f"{ref}_calibration":shadow_a_grader.calibration_table(decided,f"{ref}_over_probability"),
        "shadow_b_calibration":shadow_a_grader.calibration_table(decided,"shadow_b_over_probability"),
    }
    if comparison=="b_vs_a":
        threshold={
            "decided_props_at_least_300":result["decided_n"]>=MIN_DECIDED_PROPS,
            "unique_games_at_least_100":result["unique_games"]>=MIN_UNIQUE_GAMES,
            "weeks_at_least_8":result["unique_weeks"]>=MIN_WEEKS,
            "no_material_crps_degradation_vs_shadow_a":(
                result["shadow_b_minus_reference_crps"] is not None
                and result["shadow_b_minus_reference_crps"]<=0.0
            ),
        }
        threshold["sample_size_conditions_met"]=all([
            threshold["decided_props_at_least_300"],
            threshold["unique_games_at_least_100"],
            threshold["weeks_at_least_8"],
        ])
        result["minimum_discussion_threshold"]=threshold
    result["automatic_promotion_authorized"]=False
    return result


def concentration(frame: pd.DataFrame)->dict[str,Any]:
    work=frame[frame["has_shadow_a_pair"]].copy()
    if work.empty:
        return {}
    total=len(work)
    by_week=work.groupby(["source_season","source_week"]).size().sort_values(ascending=False)
    by_player=work.groupby("player_id").size().sort_values(ascending=False)
    return {
        "largest_week_share":float(by_week.iloc[0]/total),
        "largest_player_share":float(by_player.iloc[0]/total),
        "largest_week":list(by_week.index[0]),
        "largest_player_id":str(by_player.index[0]),
        "prop_counts":work["prop_type"].value_counts().to_dict(),
    }


def run(a_ledger: Path,b_ledger: Path,output_dir: Path)->dict[str,Any]:
    a_receipts=shadow_a_grader.read_receipts(a_ledger)
    b_receipts=read_b_receipts(b_ledger)
    if not b_receipts:
        raise ShadowBGradingError("no prospective Shadow B receipts")
    matched_a,pair_audit=match_a_receipts(a_receipts,b_receipts)

    seasons=sorted({int(row["source_season"]) for row in b_receipts})
    bundle=load_core_data(seasons)
    bundle=load_advanced_data(bundle,seasons)
    schedules=bundle.schedules.to_pandas() if hasattr(bundle.schedules,"to_pandas") else bundle.schedules.copy()
    pbp=bundle.pbp.to_pandas() if hasattr(bundle.pbp,"to_pandas") else bundle.pbp.copy()
    pbp,scramble_audit=normalize_nflverse_scramble_semantics(pbp)
    players=nfl.load_players()
    players=players.to_pandas() if hasattr(players,"to_pandas") else players.copy()
    normalized_snaps,snap_identity_audit=normalize_snap_counts_player_ids(bundle.snap_counts,players)
    if normalized_snaps is None or normalized_snaps.empty:
        raise ShadowBGradingError(f"snap identity normalization failed: {snap_identity_audit}")
    participation,participation_audit=shadow_a_grader.offense_participation(normalized_snaps)
    completed=shadow_a_grader._completed_games(schedules)
    outcome_pbp_games,outcome_pbp_audit=shadow_a_grader.complete_outcome_pbp_games(pbp)
    actuals=shadow_a_grader.actual_player_yards(pbp)

    graded,eligibility_audit=grade_b_receipts(
        b_receipts,
        matched_a=matched_a,
        completed_games=completed,
        outcome_pbp_games=outcome_pbp_games,
        actuals=actuals,
        participation=participation,
    )
    output_dir.mkdir(parents=True,exist_ok=True)

    if graded.empty:
        result={
            "contract_version":CONTRACT_VERSION,
            "shadow_a_grading_contract":SHADOW_A_GRADING_CONTRACT,
            "shadow_b_receipt_contract":SHADOW_B_RECEIPT_CONTRACT,
            "shadow_b_version":SHADOW_B_VERSION,
            "b_receipt_count":len(b_receipts),
            "matched_a_receipt_count":pair_audit["matched"],
            "graded_count":0,
            "status":"NO_GRADED_RECEIPTS_YET",
            "pair_audit":pair_audit,
            "eligibility_audit":eligibility_audit,
            "automatic_promotion_authorized":False,
        }
        (output_dir/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(result,indent=2,sort_keys=True))
        return result

    by_prop={}
    for idx,prop in enumerate(SUPPORTED_PROPS):
        part=graded[graded["prop_type"].eq(prop)].copy()
        by_prop[prop]={
            "b_vs_a":summarize(part,comparison="b_vs_a",seed=BOOTSTRAP_SEED+idx*20000),
            "b_vs_v1":summarize(part,comparison="b_vs_v1",seed=BOOTSTRAP_SEED+10000+idx*20000),
        }

    result={
        "contract_version":CONTRACT_VERSION,
        "shadow_a_grading_contract":SHADOW_A_GRADING_CONTRACT,
        "shadow_b_receipt_contract":SHADOW_B_RECEIPT_CONTRACT,
        "shadow_b_version":SHADOW_B_VERSION,
        "b_receipt_count":len(b_receipts),
        "matched_a_receipt_count":pair_audit["matched"],
        "graded_count":int(len(graded)),
        "graded_with_a_pair":int(graded["has_shadow_a_pair"].sum()),
        "overall":{
            "b_vs_a":summarize(graded,comparison="b_vs_a",seed=BOOTSTRAP_SEED+50000),
            "b_vs_v1":summarize(graded,comparison="b_vs_v1",seed=BOOTSTRAP_SEED+60000),
        },
        "by_prop":by_prop,
        "concentration":concentration(graded),
        "pair_audit":pair_audit,
        "eligibility_audit":eligibility_audit,
        "outcome_source_audit":{
            "pbp_normalization":scramble_audit,
            "snap_identity":snap_identity_audit,
            "participation":participation_audit,
            "outcome_pbp":outcome_pbp_audit,
        },
        "grading_policy":{
            "primary_comparison":"Shadow B vs Shadow A",
            "supporting_comparison":"Shadow B vs V1",
            "push_policy":"exclude pushes from Brier/log loss/directional accuracy; retain for CRPS/MAE/interval metrics",
            "bootstrap_replicates":BOOTSTRAP_REPLICATES,
            "bootstrap_unit":"game_id",
            "minimum_decided_props":MIN_DECIDED_PROPS,
            "minimum_unique_games":MIN_UNIQUE_GAMES,
            "minimum_weeks":MIN_WEEKS,
        },
        "automatic_promotion_authorized":False,
    }
    graded.to_csv(output_dir/"graded_rows.csv",index=False)
    (output_dir/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    return result


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--shadow-a-ledger",type=Path,required=True)
    parser.add_argument("--shadow-b-ledger",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.shadow_a_ledger,args.shadow_b_ledger,args.output_dir)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Grade immutable LevLine Props 2.0 Shadow A receipts after games are final."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))

from nfl_forecast.data import load_advanced_data, load_core_data  # noqa:E402
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids  # noqa:E402
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics  # noqa:E402

CONTRACT_VERSION="levline-props-v2-football-shadow-grading-v0.1.0"
RECEIPT_CONTRACT_VERSION="levline-props-v2-football-shadow-a-v0.1.0"
SHADOW_VERSION="P2-SHADOW-A-DEFENSE-v0.1.0"
SUPPORTED_PROPS=("rushing_yards","receiving_yards")
CALIBRATION_EDGES=np.linspace(0.0,1.0,11)
BOOTSTRAP_REPLICATES=5000
BOOTSTRAP_SEED=20260919
MIN_DECIDED_PROPS=300
MIN_UNIQUE_GAMES=100
MIN_WEEKS=8
EPS=1e-12


class ShadowGradingError(ValueError):
    pass


def _canon(value: Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    )


def _sha(value: Any)->str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def read_receipts(path: Path)->list[dict[str,Any]]:
    if not path.is_file():
        raise ShadowGradingError(f"receipt ledger not found: {path}")
    rows=[]
    seen=set()
    for line_number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),start=1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ShadowGradingError(f"invalid JSONL at line {line_number}") from exc
        if not isinstance(row,dict):
            raise ShadowGradingError(f"receipt line {line_number} is not an object")
        if row.get("contract_version")!=RECEIPT_CONTRACT_VERSION:
            raise ShadowGradingError("unexpected receipt contract version")
        if row.get("shadow_version")!=SHADOW_VERSION:
            raise ShadowGradingError("unexpected shadow version")
        shadow_id=str(row.get("shadow_id") or "")
        if not shadow_id or shadow_id in seen:
            raise ShadowGradingError(f"invalid/duplicate shadow_id: {shadow_id!r}")
        seen.add(shadow_id)
        governance=row.get("governance")
        if not isinstance(governance,Mapping):
            raise ShadowGradingError("receipt missing governance")
        if governance.get("production_authorized") is not False:
            raise ShadowGradingError("prospective receipt cannot be production authorized")
        if int(governance.get("target_week_outcomes_used",-1))!=0:
            raise ShadowGradingError("prospective receipt used target-week outcomes")
        if str(row.get("prop_type") or "") not in SUPPORTED_PROPS:
            raise ShadowGradingError("unsupported prospective prop type")
        validate_distribution(row["v1"]["empirical_distribution"])
        validate_distribution(row["shadow_a"]["empirical_distribution"])
        rows.append(row)
    return rows


def validate_distribution(snapshot: Mapping[str,Any])->None:
    if not isinstance(snapshot,Mapping):
        raise ShadowGradingError("empirical distribution must be an object")
    support=np.asarray(snapshot.get("support"),dtype=float)
    counts=np.asarray(snapshot.get("counts"),dtype=int)
    n=int(snapshot.get("sample_count",-1))
    if n<=0 or support.ndim!=1 or counts.ndim!=1 or len(support)!=len(counts) or len(support)==0:
        raise ShadowGradingError("invalid empirical distribution dimensions")
    if not np.isfinite(support).all() or np.any(counts<=0) or int(counts.sum())!=n:
        raise ShadowGradingError("invalid empirical distribution values")
    if np.any(np.diff(support)<=0):
        raise ShadowGradingError("empirical support must be strictly increasing")
    material={
        "sample_count":n,
        "support":[float(x) for x in support.tolist()],
        "counts":[int(x) for x in counts.tolist()],
    }
    supplied=str(snapshot.get("sha256") or "")
    if supplied!=_sha(material):
        raise ShadowGradingError("empirical distribution SHA-256 mismatch")


def empirical_crps(snapshot: Mapping[str,Any], observation: float)->float:
    validate_distribution(snapshot)
    x=np.asarray(snapshot["support"],dtype=float)
    p=np.asarray(snapshot["counts"],dtype=float)/float(snapshot["sample_count"])
    y=float(observation)
    first=float(np.sum(p*np.abs(x-y)))
    cumulative_p=0.0
    cumulative_px=0.0
    half_pairwise=0.0
    for value,prob in zip(x,p):
        half_pairwise+=float(prob)*(float(value)*cumulative_p-cumulative_px)
        cumulative_p+=float(prob)
        cumulative_px+=float(prob)*float(value)
    return float(max(0.0,first-half_pairwise))


def interval_score(interval: Mapping[str,Any], observation: float)->tuple[float,bool]:
    if not isinstance(interval,Mapping):
        raise ShadowGradingError("prediction interval missing")
    low=float(interval["low"])
    high=float(interval["high"])
    level=float(interval["coverage"])
    if not (math.isfinite(low) and math.isfinite(high) and low<=high and 0.0<level<1.0):
        raise ShadowGradingError("invalid prediction interval")
    alpha=1.0-level
    y=float(observation)
    penalty=0.0
    if y<low:
        penalty=(2.0/alpha)*(low-y)
    elif y>high:
        penalty=(2.0/alpha)*(y-high)
    return float((high-low)+penalty),bool(low<=y<=high)


def _completed_games(schedule: pd.DataFrame)->set[str]:
    work=schedule.copy()
    complete=pd.Series(False,index=work.index)
    if "result" in work.columns:
        result=pd.to_numeric(work["result"],errors="coerce")
        complete=complete|result.notna()
    if {"home_score","away_score"}.issubset(work.columns):
        home=pd.to_numeric(work["home_score"],errors="coerce")
        away=pd.to_numeric(work["away_score"],errors="coerce")
        complete=complete|(home.notna()&away.notna())
    if not bool(complete.any()):
        raise ShadowGradingError("schedule source exposes no finalized games")
    return set(work.loc[complete,"game_id"].astype(str))


def offense_participation(snap_counts: pd.DataFrame)->tuple[dict[tuple[str,str],int],dict[str,Any]]:
    snap_col=next(
        (c for c in ("offense_snaps","offensive_snaps","off_snaps") if c in snap_counts.columns),
        None,
    )
    if snap_col is None or "game_id" not in snap_counts.columns or "player_id" not in snap_counts.columns:
        raise ShadowGradingError("snap-count source missing offense snaps/game_id/player_id")
    work=snap_counts.copy()
    work["player_id"]=work["player_id"].astype("string").fillna("").str.strip()
    work["_snaps"]=pd.to_numeric(work[snap_col],errors="coerce")
    work=work[
        work["game_id"].notna()
        & work["player_id"].ne("")
        & work["_snaps"].notna()
    ].copy()
    grouped=(
        work.groupby(["game_id","player_id"],as_index=False,sort=False)
        .agg(offense_snaps=("_snaps","max"))
    )
    participation={
        (str(row.game_id),str(row.player_id)):int(max(0.0,float(row.offense_snaps)))
        for row in grouped.itertuples(index=False)
    }
    return participation,{
        "participation_rows":int(len(participation)),
        "positive_snap_rows":int(sum(value>0 for value in participation.values())),
    }


def actual_player_yards(pbp: pd.DataFrame)->dict[tuple[str,str,str],float]:
    required={"game_id"}
    if not required.issubset(pbp.columns):
        raise ShadowGradingError("PBP missing game_id")
    out:dict[tuple[str,str,str],float]={}
    specs={
        "rushing_yards":(
            next((c for c in ("rusher_player_id","rusher_id") if c in pbp.columns),None),
            "rushing_yards" if "rushing_yards" in pbp.columns else "yards_gained",
            pd.to_numeric(pbp.get("rush_attempt",0),errors="coerce").fillna(0).eq(1),
        ),
        "receiving_yards":(
            next((c for c in ("receiver_player_id","receiver_id") if c in pbp.columns),None),
            "receiving_yards" if "receiving_yards" in pbp.columns else "yards_gained",
            pd.to_numeric(pbp.get("complete_pass",0),errors="coerce").fillna(0).eq(1),
        ),
    }
    for prop,(id_col,yards_col,mask) in specs.items():
        if id_col is None or yards_col not in pbp.columns:
            raise ShadowGradingError(f"PBP missing {prop} identity/yardage")
        ids=pbp[id_col].astype("string").fillna("").str.strip()
        yards=pd.to_numeric(pbp[yards_col],errors="coerce")
        frame=pd.DataFrame({
            "game_id":pbp["game_id"].astype(str),
            "player_id":ids,
            "yards":yards,
        })
        frame=frame[mask & ids.ne("") & yards.notna()].copy()
        grouped=frame.groupby(["game_id","player_id"],sort=False)["yards"].sum()
        for (game_id,player_id),value in grouped.items():
            out[(str(game_id),str(player_id),prop)]=float(value)
    return out


def grade_receipts(
    receipts:list[dict[str,Any]],
    *,
    completed_games:set[str],
    actuals:Mapping[tuple[str,str,str],float],
    participation:Mapping[tuple[str,str],int],
)->tuple[pd.DataFrame,dict[str,int]]:
    rows=[]
    audit={
        "not_final":0,
        "missing_participation":0,
        "zero_offense_snaps_void":0,
        "graded":0,
    }
    for receipt in receipts:
        game_id=str(receipt["game_id"])
        if game_id not in completed_games:
            audit["not_final"]+=1
            continue
        player_id=str(receipt["player_id"])
        snaps=participation.get((game_id,player_id))
        if snaps is None:
            audit["missing_participation"]+=1
            continue
        if int(snaps)<=0:
            audit["zero_offense_snaps_void"]+=1
            continue
        prop=str(receipt["prop_type"])
        actual=float(actuals.get((game_id,player_id,prop),0.0))
        line=float(receipt["market"]["line"])
        push=math.isclose(actual,line,rel_tol=0.0,abs_tol=1e-12)
        outcome=None if push else float(actual>line)

        v1=receipt["v1"]
        shadow=receipt["shadow_a"]
        v1_crps=empirical_crps(v1["empirical_distribution"],actual)
        shadow_crps=empirical_crps(shadow["empirical_distribution"],actual)
        v1_interval,v1_covered=interval_score(v1["prediction_interval"],actual)
        shadow_interval,shadow_covered=interval_score(shadow["prediction_interval"],actual)

        v1_p=float(v1["over_probability"])
        shadow_p=float(shadow["over_probability"])
        if not (0.0<=v1_p<=1.0 and 0.0<=shadow_p<=1.0):
            raise ShadowGradingError("over probability outside [0,1]")

        if outcome is None:
            v1_brier=shadow_brier=v1_log=shadow_log=math.nan
            v1_dir=shadow_dir=math.nan
        else:
            v1_brier=(v1_p-outcome)**2
            shadow_brier=(shadow_p-outcome)**2
            v1_pc=min(max(v1_p,EPS),1.0-EPS)
            shadow_pc=min(max(shadow_p,EPS),1.0-EPS)
            v1_log=-(outcome*math.log(v1_pc)+(1.0-outcome)*math.log(1.0-v1_pc))
            shadow_log=-(outcome*math.log(shadow_pc)+(1.0-outcome)*math.log(1.0-shadow_pc))
            v1_side=1.0 if float(v1["fair_line"])>line else 0.0 if float(v1["fair_line"])<line else math.nan
            shadow_side=1.0 if float(shadow["fair_line"])>line else 0.0 if float(shadow["fair_line"])<line else math.nan
            v1_dir=float(v1_side==outcome) if math.isfinite(v1_side) else math.nan
            shadow_dir=float(shadow_side==outcome) if math.isfinite(shadow_side) else math.nan

        rows.append({
            "shadow_id":receipt["shadow_id"],
            "source_season":int(receipt["source_season"]),
            "source_week":int(receipt["source_week"]),
            "game_id":game_id,
            "player_id":player_id,
            "prop_type":prop,
            "actual_result":actual,
            "market_line":line,
            "push":bool(push),
            "v1_crps":v1_crps,
            "shadow_crps":shadow_crps,
            "shadow_minus_v1_crps":shadow_crps-v1_crps,
            "v1_abs_error":abs(float(v1["fair_line"])-actual),
            "shadow_abs_error":abs(float(shadow["fair_line"])-actual),
            "shadow_minus_v1_abs_error":abs(float(shadow["fair_line"])-actual)-abs(float(v1["fair_line"])-actual),
            "v1_brier":v1_brier,
            "shadow_brier":shadow_brier,
            "shadow_minus_v1_brier":shadow_brier-v1_brier if outcome is not None else math.nan,
            "v1_log_loss":v1_log,
            "shadow_log_loss":shadow_log,
            "shadow_minus_v1_log_loss":shadow_log-v1_log if outcome is not None else math.nan,
            "v1_interval_score_80":v1_interval,
            "shadow_interval_score_80":shadow_interval,
            "v1_covered_80":v1_covered,
            "shadow_covered_80":shadow_covered,
            "v1_direction_hit":v1_dir,
            "shadow_direction_hit":shadow_dir,
            "v1_over_probability":v1_p,
            "shadow_over_probability":shadow_p,
            "over_outcome":outcome,
            "source_signal_state":receipt.get("source_signal_state"),
            "source_quality_state":(
                receipt.get("source_data_quality",{}).get("state")
                if isinstance(receipt.get("source_data_quality"),Mapping)
                else None
            ),
        })
    audit["graded"]=len(rows)
    return pd.DataFrame(rows),audit


def cluster_ci(frame: pd.DataFrame,column:str,*,seed:int,replicates:int=BOOTSTRAP_REPLICATES)->list[float|None]:
    usable=frame[["game_id",column]].copy()
    usable[column]=pd.to_numeric(usable[column],errors="coerce")
    usable=usable[usable[column].notna()]
    grouped=(
        usable.assign(game_id=usable["game_id"].astype(str))
        .groupby("game_id",sort=True)[column]
        .agg(["sum","count"])
    )
    if len(grouped)<2:
        return [None,None]
    sums=grouped["sum"].to_numpy(dtype=float)
    counts=grouped["count"].to_numpy(dtype=float)
    rng=np.random.default_rng(seed)
    values=np.empty(int(replicates),dtype=float)
    n_games=len(grouped)
    for i in range(int(replicates)):
        sampled=rng.integers(0,n_games,size=n_games)
        denominator=float(counts[sampled].sum())
        values[i]=float(sums[sampled].sum()/denominator)
    return [float(np.quantile(values,.025)),float(np.quantile(values,.975))]


def calibration_table(frame:pd.DataFrame,probability_col:str)->list[dict[str,Any]]:
    decided=frame[frame["over_outcome"].notna()].copy()
    if decided.empty:
        return []
    p=pd.to_numeric(decided[probability_col],errors="coerce")
    y=pd.to_numeric(decided["over_outcome"],errors="coerce")
    bins=pd.cut(p,bins=CALIBRATION_EDGES,include_lowest=True,right=True,duplicates="drop")
    result=[]
    for interval,indexes in decided.groupby(bins,observed=False).groups.items():
        idx=list(indexes)
        if not idx:
            continue
        result.append({
            "bin":str(interval),
            "n":int(len(idx)),
            "mean_probability":float(p.loc[idx].mean()),
            "observed_over_rate":float(y.loc[idx].mean()),
        })
    return result


def summarize(frame:pd.DataFrame,*,seed:int)->dict[str,Any]:
    if frame.empty:
        return {"n":0}
    decided=frame[~frame["push"]].copy()
    summary={
        "n":int(len(frame)),
        "decided_n":int(len(decided)),
        "unique_games":int(frame["game_id"].astype(str).nunique()),
        "unique_players":int(frame["player_id"].astype(str).nunique()),
        "unique_weeks":int(frame[["source_season","source_week"]].drop_duplicates().shape[0]),
        "v1_crps":float(frame["v1_crps"].mean()),
        "shadow_crps":float(frame["shadow_crps"].mean()),
        "shadow_minus_v1_crps":float(frame["shadow_minus_v1_crps"].mean()),
        "crps_difference_ci95":cluster_ci(frame,"shadow_minus_v1_crps",seed=seed),
        "v1_fair_line_mae":float(frame["v1_abs_error"].mean()),
        "shadow_fair_line_mae":float(frame["shadow_abs_error"].mean()),
        "shadow_minus_v1_mae":float(frame["shadow_minus_v1_abs_error"].mean()),
        "mae_difference_ci95":cluster_ci(frame,"shadow_minus_v1_abs_error",seed=seed+1000),
        "v1_interval_score_80":float(frame["v1_interval_score_80"].mean()),
        "shadow_interval_score_80":float(frame["shadow_interval_score_80"].mean()),
        "v1_coverage_80":float(frame["v1_covered_80"].astype(float).mean()),
        "shadow_coverage_80":float(frame["shadow_covered_80"].astype(float).mean()),
        "v1_brier":float(decided["v1_brier"].mean()) if len(decided) else None,
        "shadow_brier":float(decided["shadow_brier"].mean()) if len(decided) else None,
        "shadow_minus_v1_brier":float(decided["shadow_minus_v1_brier"].mean()) if len(decided) else None,
        "brier_difference_ci95":cluster_ci(decided,"shadow_minus_v1_brier",seed=seed+2000) if len(decided) else [None,None],
        "v1_log_loss":float(decided["v1_log_loss"].mean()) if len(decided) else None,
        "shadow_log_loss":float(decided["shadow_log_loss"].mean()) if len(decided) else None,
        "shadow_minus_v1_log_loss":float(decided["shadow_minus_v1_log_loss"].mean()) if len(decided) else None,
        "v1_direction_accuracy":float(decided["v1_direction_hit"].mean()) if len(decided) else None,
        "shadow_direction_accuracy":float(decided["shadow_direction_hit"].mean()) if len(decided) else None,
        "v1_calibration":calibration_table(decided,"v1_over_probability"),
        "shadow_calibration":calibration_table(decided,"shadow_over_probability"),
    }
    summary["minimum_discussion_threshold"]={
        "decided_props_at_least_300":summary["decided_n"]>=MIN_DECIDED_PROPS,
        "unique_games_at_least_100":summary["unique_games"]>=MIN_UNIQUE_GAMES,
        "weeks_at_least_8":summary["unique_weeks"]>=MIN_WEEKS,
        "no_material_crps_degradation":summary["shadow_minus_v1_crps"]<=0.0,
    }
    summary["minimum_discussion_threshold"]["sample_size_conditions_met"]=all([
        summary["minimum_discussion_threshold"]["decided_props_at_least_300"],
        summary["minimum_discussion_threshold"]["unique_games_at_least_100"],
        summary["minimum_discussion_threshold"]["weeks_at_least_8"],
    ])
    summary["automatic_promotion_authorized"]=False
    return summary


def concentration_diagnostics(frame:pd.DataFrame)->dict[str,Any]:
    if frame.empty:
        return {}
    total=len(frame)
    by_week=frame.groupby(["source_season","source_week"]).size().sort_values(ascending=False)
    by_player=frame.groupby("player_id").size().sort_values(ascending=False)
    return {
        "largest_week_share":float(by_week.iloc[0]/total),
        "largest_player_share":float(by_player.iloc[0]/total),
        "largest_week":list(by_week.index[0]) if len(by_week) else None,
        "largest_player_id":str(by_player.index[0]) if len(by_player) else None,
        "prop_counts":frame["prop_type"].value_counts().to_dict(),
    }


def run(ledger:Path,output_dir:Path)->dict[str,Any]:
    receipts=read_receipts(ledger)
    if not receipts:
        raise ShadowGradingError("no prospective Shadow A receipts")
    seasons=sorted({int(row["source_season"]) for row in receipts})
    bundle=load_core_data(seasons)
    bundle=load_advanced_data(bundle,seasons)
    schedules=bundle.schedules.to_pandas() if hasattr(bundle.schedules,"to_pandas") else bundle.schedules.copy()
    pbp=bundle.pbp.to_pandas() if hasattr(bundle.pbp,"to_pandas") else bundle.pbp.copy()
    pbp,scramble_audit=normalize_nflverse_scramble_semantics(pbp)
    players=nfl.load_players()
    players=players.to_pandas() if hasattr(players,"to_pandas") else players.copy()
    normalized_snaps,snap_identity_audit=normalize_snap_counts_player_ids(
        bundle.snap_counts,players
    )
    if normalized_snaps is None or normalized_snaps.empty:
        raise ShadowGradingError(f"snap identity normalization failed: {snap_identity_audit}")
    participation,participation_audit=offense_participation(normalized_snaps)
    completed=_completed_games(schedules)
    actuals=actual_player_yards(pbp)
    graded,eligibility_audit=grade_receipts(
        receipts,
        completed_games=completed,
        actuals=actuals,
        participation=participation,
    )

    output_dir.mkdir(parents=True,exist_ok=True)
    if graded.empty:
        result={
            "contract_version":CONTRACT_VERSION,
            "receipt_contract_version":RECEIPT_CONTRACT_VERSION,
            "shadow_version":SHADOW_VERSION,
            "receipt_count":len(receipts),
            "graded_count":0,
            "ungraded_count":len(receipts),
            "status":"NO_GRADED_RECEIPTS_YET",
            "eligibility_audit":eligibility_audit,
            "outcome_source_audit":{
                "pbp_normalization":scramble_audit,
                "snap_identity":snap_identity_audit,
                "participation":participation_audit,
            },
            "automatic_promotion_authorized":False,
        }
        (output_dir/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(result,indent=2,sort_keys=True))
        return result

    by_prop={}
    for idx,prop in enumerate(SUPPORTED_PROPS):
        part=graded[graded["prop_type"].eq(prop)].copy()
        by_prop[prop]=summarize(part,seed=BOOTSTRAP_SEED+idx*10000) if not part.empty else {"n":0}

    result={
        "contract_version":CONTRACT_VERSION,
        "receipt_contract_version":RECEIPT_CONTRACT_VERSION,
        "shadow_version":SHADOW_VERSION,
        "receipt_count":len(receipts),
        "graded_count":int(len(graded)),
        "ungraded_count":int(len(receipts)-len(graded)),
        "overall":summarize(graded,seed=BOOTSTRAP_SEED+50000),
        "by_prop":by_prop,
        "concentration":concentration_diagnostics(graded),
        "eligibility_audit":eligibility_audit,
        "outcome_source_audit":{
            "pbp_normalization":scramble_audit,
            "snap_identity":snap_identity_audit,
            "participation":participation_audit,
        },
        "grading_policy":{
            "push_policy":"exclude pushes from Brier/log loss/directional accuracy; retain for CRPS/MAE/interval metrics",
            "calibration_edges":[float(x) for x in CALIBRATION_EDGES.tolist()],
            "bootstrap_replicates":BOOTSTRAP_REPLICATES,
            "bootstrap_unit":"game_id",
            "minimum_decided_props":MIN_DECIDED_PROPS,
            "minimum_unique_games":MIN_UNIQUE_GAMES,
            "minimum_weeks":MIN_WEEKS,
        },
        "automatic_promotion_authorized":False,
    }
    graded.to_csv(output_dir/"graded_rows.csv",index=False)
    (output_dir/"summary.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(result,indent=2,sort_keys=True))
    return result


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.ledger,args.output_dir)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

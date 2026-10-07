"""Outcome-only, no-fitting prospective evaluator for frozen Candidate C vs locked F-ST."""
from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
import math
import numpy as np
from research.post_week4_phase4.c_shadow import (
    CANDIDATE_ID, CONTRACT_ID, PRODUCTION_ID, iso_utc, number, hexsha,
)

MIN_GAMES=200
MIN_WEEKS=14
BOOTSTRAP_SAMPLES=2000
BOOTSTRAP_SEED=26


def _metrics(y, p):
    y=np.asarray(y,dtype=int)
    p=np.asarray(p,dtype=float)
    if not np.isfinite(p).all() or not ((p>0)&(p<1)).all():
        raise ValueError("Invalid prospective probability")
    return {
        "games":len(y),"correct":int(((p>=.5)==y).sum()),
        "accuracy":float(np.mean((p>=.5)==y)),
        "brier":float(np.mean((p-y)**2)),
        "log_loss":float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p))),
    }


def evaluate(scored_records: list[dict], official_results: list[dict]) -> dict:
    """Every game is paired and result-independent; no changes to candidate model."""
    if not isinstance(scored_records,list) or not isinstance(official_results,list):
        raise ValueError("Expected lists of frozen records and official results")
    predictions={}
    for row in scored_records:
        if row.get("candidate_id")!=CANDIDATE_ID or row.get("contract")!=CONTRACT_ID:
            raise ValueError("Unknown prospective record identity")
        if row.get("fst_candidate_id")!=PRODUCTION_ID or row.get("production_changed") is not False:
            raise ValueError("Production model identity mismatch")
        game=row.get("game_id")
        if not isinstance(game,str) or game in predictions:
            raise ValueError("Duplicate/invalid frozen prediction")
        season,week=row.get("season"),row.get("week")
        if (isinstance(season,bool) or not isinstance(season,int) or season<2026 or
            isinstance(week,bool) or not isinstance(week,int) or not 1<=week<=18 or
            game!=f"{season}_{week:02d}_{row.get(\'away_team\')}_{row.get(\'home_team\')}"):
            raise ValueError("Frozen game/week/team identity mismatch")
        for k in ("input_snapshot_sha256","frozen_model_sha256","source_sha256","schedule_sha256"):
            hexsha(row.get(k),k)
        lock=iso_utc(row.get("fst_lock_timestamp_utc"),"lock")
        captured=iso_utc(row.get("snapshot_captured_utc"),"capture")
        observed=iso_utc(row.get("source_observed_utc"),"observed")
        kickoff=iso_utc(row.get("kickoff_utc"),"kickoff")
        if not observed<=captured<=lock<kickoff or (lock-captured).total_seconds()>7200:
            raise ValueError("Stored prediction not qualified before official lock")
        for k in ("candidate_home_prob","fst_home_prob","market_home_prob"):
            number(row.get(k),k,prob=True)
        predictions[game]=row
    official={}
    for row in official_results:
        game=row.get("game_id")
        if not isinstance(game,str) or game in official:
            raise ValueError("Duplicate outcome identity")
        if row.get("source_type")!="verified_official_game_result":
            raise ValueError("Outcome not independently verified")
        hexsha(row.get("source_sha256"),"result source")
        n1=number(row.get("home_score"),"home_score")
        n2=number(row.get("away_score"),"away_score")
        if n1<0 or n2<0 or not n1.is_integer() or not n2.is_integer():
            raise ValueError("Invalid official score")
        official[game]=row
    extra=set(official)-set(predictions)
    if extra:
        raise ValueError("Unmatched postgame results cannot create retroactive predictions")
    completed=[]
    ties=[]
    pending=[]
    models=set(r["frozen_model_sha256"] for r in predictions.values())
    if len(models)>1:
        raise ValueError("Changed frozen C model mid-prospective evaluation")
    for game,row in predictions.items():
        result=official.get(game)
        if result is None:
            pending.append(game)
            continue
        kickoff=iso_utc(row["kickoff_utc"],"kickoff")
        observed=iso_utc(result.get("result_observed_utc"),"result observed")
        if observed < kickoff+timedelta(hours=3):
            raise ValueError("Postgame result observed too early")
        if result.get("season")!=row.get("season") or result.get("week")!=row.get("week"):
            raise ValueError("Outcome season/week mismatch")
        h=int(result["home_score"]);a=int(result["away_score"])
        if h==a:
            ties.append(game)
            continue
        completed.append((row,int(h>a)))
    report={
        "candidate_id":CANDIDATE_ID,"status":"AWAITING_ELIGIBLE_LOCKS",
        "captured_predictions":len(predictions),"graded_non_tie_games":len(completed),
        "pending_games":len(pending),"pending_game_ids":sorted(pending),
        "ties_excluded":len(ties),"tied_game_ids":sorted(ties),
        "weeks":len(set((r["season"],r["week"]) for r,y in completed)),
        "minimum_games":MIN_GAMES,"minimum_weeks":MIN_WEEKS,
        "promotion_authorized":False,"production_changed":False,
        "model_tuning_from_2026_outcomes":False,
    }
    if not completed:
        return report
    rows=[x[0] for x in completed]
    y=np.asarray([x[1] for x in completed],dtype=int)
    c=np.asarray([r["candidate_home_prob"] for r in rows],dtype=float)
    f=np.asarray([r["fst_home_prob"] for r in rows],dtype=float)
    m=np.asarray([r["market_home_prob"] for r in rows],dtype=float)
    cgood=(c>=.5)==y
    fgood=(f>=.5)==y
    switch=(c>=.5)!=(f>=.5)
    win=int((cgood&~fgood).sum())
    lose=int((fgood&~cgood).sum())
    if win+lose!=int(switch.sum()):
        raise RuntimeError("Paired switch identity failure")
    report.update({
        "status":"ACCUMULATING_EVIDENCE","candidate":_metrics(y,c),
        "fst":_metrics(y,f),"market":_metrics(y,m),
        "candidate_only_correct":win,"fst_only_correct":lose,
        "switches":int(switch.sum()),
        "switch_win_rate":float(win/int(switch.sum())) if switch.any() else None,
        "accuracy_delta":float(np.mean(cgood)-np.mean(fgood)),
        "brier_delta":float(np.mean((c-y)**2)-np.mean((f-y)**2)),
        "log_loss_delta":float(_metrics(y,c)["log_loss"]-_metrics(y,f)["log_loss"]),
    })
    weeks=defaultdict(list)
    for k,r in enumerate(rows):
        weeks[(r["season"],r["week"])].append(k)
    summary={k:{"games":len(ids),"candidate_only_correct":int((cgood[ids]&~fgood[ids]).sum()),
                "fst_only_correct":int((fgood[ids]&~cgood[ids]).sum())}
             for k,ids in weeks.items()}
    report["per_week"]={f"{season}-W{week:02d}":val for (season,week),val in sorted(summary.items())}
    # Only begin formal inference when the contract's sample size is met.
    if len(completed)<MIN_GAMES or len(weeks)<MIN_WEEKS:
        return report
    keys=list(weeks.keys())
    groups={key:np.asarray(weeks[key],dtype=int) for key in keys}
    rng=np.random.default_rng(BOOTSTRAP_SEED)
    draws=[]
    for _ in range(BOOTSTRAP_SAMPLES):
        sampled=rng.choice(len(keys),size=len(keys),replace=True)
        positions=np.concatenate([groups[keys[i]] for i in sampled])
        draws.append(float((cgood[positions].astype(int)-fgood[positions].astype(int)).mean()))
    lo,hi=np.quantile(draws,[.025,.975])
    by_season=defaultdict(list)
    for k,r in enumerate(rows):
        by_season[r["season"]].append(k)
    season_deltas={
        str(season):int(cgood[ids].sum()-fgood[ids].sum())
        for season,ids in by_season.items()
    }
    loo={
        f"{season}-W{week:02d}":int((cgood[np.setdiff1d(np.arange(len(y)),ids)].sum()-
                                    fgood[np.setdiff1d(np.arange(len(y)),ids)].sum()))
        for (season,week),ids in sorted(groups.items())
    }
    brier_alert=report["brier_delta"]>0.0025
    signal=(report["accuracy_delta"]>0 and lo>0 and all(v>=0 for v in loo.values()) and
            not brier_alert and report["candidate"]["brier"]<.25 and
            report["candidate"]["log_loss"]<math.log(2))
    report.update({
        "status":"FORMAL_REVIEW_ELIGIBLE",
        "week_block_accuracy_delta_ci95":[float(lo),float(hi)],
        "bootstrap_samples":BOOTSTRAP_SAMPLES,
        "season_correct_delta":season_deltas,
        "leave_one_week_out_correct_delta":loo,
        "probability_brier_alert":brier_alert,
        "scientific_preliminary_gate_met":bool(signal),
        "promotion_authorized":False,
    })
    return report

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CONTRACT_VERSION="levline-props-v2-signed-rushing-pregame-v0.1.0"
EVALUATION_SEASONS=(2023,2024,2025)


def cluster_ci(frame,column,seed=20262918,replicates=5000):
    games=np.asarray(sorted(frame["game_id"].astype(str).unique()))
    grouped={g:frame[frame["game_id"].astype(str).eq(g)] for g in games}
    rng=np.random.default_rng(seed)
    vals=np.empty(replicates,dtype=float)
    for i in range(replicates):
        sampled=rng.choice(games,size=len(games),replace=True)
        boot=pd.concat([grouped[g] for g in sampled],ignore_index=True)
        vals[i]=float(boot[column].mean())
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()

    paths=sorted(args.input_dir.rglob("*_forecast_level.csv"))
    if not paths:
        raise RuntimeError("no signed-rushing forecast artifacts")

    frame=pd.concat([pd.read_csv(p) for p in paths],ignore_index=True)
    if set(frame["contract_version"].astype(str))!={CONTRACT_VERSION}:
        raise RuntimeError("unexpected signed-rushing contract version")
    seasons=set(frame["season"].astype(int))
    if seasons!=set(EVALUATION_SEASONS):
        raise RuntimeError(f"missing evaluation seasons: {seasons}")

    by_season={}
    for season,g in frame.groupby("season",sort=True):
        by_season[str(int(season))]={
            "n":int(len(g)),
            "v1_crps":float(g["v1_crps"].mean()),
            "challenger_crps":float(g["challenger_crps"].mean()),
            "challenger_minus_v1_crps":float(g["challenger_minus_v1_crps"].mean()),
            "v1_mae":float(g["v1_abs_error"].mean()),
            "challenger_mae":float(g["challenger_abs_error"].mean()),
            "challenger_minus_v1_mae":float(g["challenger_minus_v1_abs_error"].mean()),
            "v1_coverage_80":float(g["v1_covered_80"].astype(float).mean()),
            "challenger_coverage_80":float(g["challenger_covered_80"].astype(float).mean()),
        }

    aggregate={
        "n":int(len(frame)),
        "unique_games":int(frame["game_id"].astype(str).nunique()),
        "unique_players":int(frame["player_id"].astype(str).nunique()),
        "v1_crps":float(frame["v1_crps"].mean()),
        "challenger_crps":float(frame["challenger_crps"].mean()),
        "challenger_minus_v1_crps":float(frame["challenger_minus_v1_crps"].mean()),
        "crps_difference_ci95":cluster_ci(frame,"challenger_minus_v1_crps"),
        "v1_fair_line_mae":float(frame["v1_abs_error"].mean()),
        "challenger_fair_line_mae":float(frame["challenger_abs_error"].mean()),
        "challenger_minus_v1_mae":float(frame["challenger_minus_v1_abs_error"].mean()),
        "mae_difference_ci95":cluster_ci(frame,"challenger_minus_v1_abs_error",seed=20263918),
        "v1_coverage_80":float(frame["v1_covered_80"].astype(float).mean()),
        "challenger_coverage_80":float(frame["challenger_covered_80"].astype(float).mean()),
        "by_season":by_season,
    }

    improving=sum(v["challenger_minus_v1_crps"]<0 for v in by_season.values())
    coverage_delta=aggregate["challenger_coverage_80"]-aggregate["v1_coverage_80"]
    gate={
        "pooled_crps_improves":aggregate["challenger_minus_v1_crps"]<0,
        "pooled_mae_improves":aggregate["challenger_minus_v1_mae"]<0,
        "at_least_two_seasons_crps_improve":improving>=2,
        "crps_ci_upper_nonpositive":aggregate["crps_difference_ci95"][1]<=0,
        "coverage_not_worse_by_more_than_1_5pp":coverage_delta>=-0.015,
        "coverage_delta":float(coverage_delta),
        "improving_season_count":int(improving),
    }
    gate["passed"]=all([
        gate["pooled_crps_improves"],
        gate["pooled_mae_improves"],
        gate["at_least_two_seasons_crps_improve"],
        gate["crps_ci_upper_nonpositive"],
        gate["coverage_not_worse_by_more_than_1_5pp"],
    ])

    result={
        "contract_version":CONTRACT_VERSION,
        "aggregate":aggregate,
        "advance_gate":gate,
        "retrospective_development_only":True,
        "production_authorized":False,
        "completed_2026_outcomes_used":0,
    }
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"summary.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    frame.to_csv(args.output_dir/"paired_rows.csv",index=False)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Run signed-event distribution component isolation on 2023-2025."""

import argparse
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))

from nfl_forecast.data import load_core_data
from run_dynamic_role_backtest import normalize_historical_pbp
from signed_event_distribution import (
    CONTRACT_VERSION,
    build_event_rows,
    evaluate_component_season,
)


EVALUATION_SEASONS=(2023,2024,2025)
HISTORY_START=2021
BOOTSTRAP_REPLICATES=3000


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def _positions(players: pd.DataFrame)->dict[str,str]:
    id_col=next((c for c in ("gsis_id","player_id") if c in players.columns),None)
    pos_col=next((c for c in ("position","position_group") if c in players.columns),None)
    if id_col is None or pos_col is None:
        raise RuntimeError("players table missing stable ID/position")
    frame=players[[id_col,pos_col]].copy()
    frame[id_col]=frame[id_col].astype("string").fillna("").str.strip()
    frame[pos_col]=frame[pos_col].astype("string").fillna("").str.upper().str.strip()
    frame=frame[frame[id_col].ne("") & frame[pos_col].isin({"QB","RB","WR","TE"})]
    frame=frame.drop_duplicates(id_col,keep="last")
    return dict(zip(frame[id_col].astype(str),frame[pos_col].astype(str)))


def clustered_ci(frame: pd.DataFrame, column: str, *, seed: int)->list[float]:
    games=np.asarray(sorted(frame["game_id"].astype(str).unique()))
    if len(games)<2:
        return [None,None]
    grouped={g:frame[frame["game_id"].astype(str).eq(g)] for g in games}
    rng=np.random.default_rng(seed)
    vals=np.empty(BOOTSTRAP_REPLICATES,dtype=float)
    for i in range(BOOTSTRAP_REPLICATES):
        sampled=rng.choice(games,size=len(games),replace=True)
        boot=pd.concat([grouped[g] for g in sampled],ignore_index=True)
        vals[i]=float(boot[column].mean())
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--simulations",type=int,default=5000)
    args=parser.parse_args()

    seasons=list(range(HISTORY_START,max(EVALUATION_SEASONS)+1))
    bundle=load_core_data(seasons)
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    players=_pandas(nfl.load_players())
    events=build_event_rows(pbp,_positions(players))
    events=events[
        events["season"].between(HISTORY_START,max(EVALUATION_SEASONS))
    ].copy()
    if events.empty:
        raise RuntimeError("no signed-yardage event rows")

    args.output_dir.mkdir(parents=True,exist_ok=True)
    summaries={}
    scored_all=[]
    for season in EVALUATION_SEASONS:
        scored,summary=evaluate_component_season(
            events,evaluation_season=season,simulations=args.simulations
        )
        summary["signed_minus_gamma_crps_ci95"]=clustered_ci(
            scored,"signed_minus_gamma_crps",seed=20260918+season
        )
        summaries[str(season)]=summary
        scored_all.append(scored.assign(evaluation_season=season))
        scored.to_csv(args.output_dir/f"{season}_scored_rows.csv",index=False)

    all_rows=pd.concat(scored_all,ignore_index=True)
    aggregate={
        "contract_version":CONTRACT_VERSION,
        "n":int(len(all_rows)),
        "unique_games":int(all_rows["game_id"].astype(str).nunique()),
        "gamma_crps":float(all_rows["gamma_crps"].mean()),
        "signed_crps":float(all_rows["signed_crps"].mean()),
        "signed_minus_gamma_crps":float(all_rows["signed_minus_gamma_crps"].mean()),
        "signed_minus_gamma_crps_ci95":clustered_ci(
            all_rows,"signed_minus_gamma_crps",seed=20261918
        ),
        "gamma_interval_score_80":float(all_rows["gamma_interval_score_80"].mean()),
        "signed_interval_score_80":float(all_rows["signed_interval_score_80"].mean()),
        "gamma_coverage_80":float(all_rows["gamma_covered_80"].astype(float).mean()),
        "signed_coverage_80":float(all_rows["signed_covered_80"].astype(float).mean()),
        "by_event_type":{
            event:{
                "n":int(len(part)),
                "gamma_crps":float(part["gamma_crps"].mean()),
                "signed_crps":float(part["signed_crps"].mean()),
                "signed_minus_gamma_crps":float(part["signed_minus_gamma_crps"].mean()),
                "signed_minus_gamma_crps_ci95":clustered_ci(
                    part,"signed_minus_gamma_crps",seed=20262918+i
                ),
                "gamma_coverage_80":float(part["gamma_covered_80"].astype(float).mean()),
                "signed_coverage_80":float(part["signed_covered_80"].astype(float).mean()),
            }
            for i,(event,part) in enumerate(all_rows.groupby("event_type",sort=True))
        },
        "by_season":summaries,
        "source_audit":{
            "pbp_normalization":pbp_audit,
            "event_rows":int(len(events)),
            "negative_event_rate":{
                event:float((part["yards"]<0).mean())
                for event,part in events.groupby("event_type",sort=True)
            },
        },
        "component_isolation_only":True,
        "conditioned_on_actual_event_count":True,
        "pregame_prop_forecast":False,
        "prop_outcomes_used_for_fit":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    (args.output_dir/"summary.json").write_text(
        json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps({
        "n":aggregate["n"],
        "gamma_crps":aggregate["gamma_crps"],
        "signed_crps":aggregate["signed_crps"],
        "signed_minus_gamma_crps":aggregate["signed_minus_gamma_crps"],
        "signed_minus_gamma_crps_ci95":aggregate["signed_minus_gamma_crps_ci95"],
        "gamma_coverage_80":aggregate["gamma_coverage_80"],
        "signed_coverage_80":aggregate["signed_coverage_80"],
    },indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

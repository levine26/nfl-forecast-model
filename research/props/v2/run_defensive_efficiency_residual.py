from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))

from nfl_forecast.data import load_core_data
from run_dynamic_role_backtest import normalize_historical_pbp
from defensive_efficiency_residual import (
    CONTRACT_VERSION,
    EVENT_TYPES,
    build_component_rows,
    build_event_rows,
    clustered_mae_difference_ci,
    score_season,
)

HISTORY_START=2019
EVALUATION_SEASONS=(2023,2024,2025)


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


def _pooled(frame):
    return {
        "n":int(len(frame)),
        "unique_games":int(frame["game_id"].astype(str).nunique()),
        "unique_players":int(frame["player_id"].astype(str).nunique()),
        "baseline_conditional_total_mae":float(frame["baseline_abs_error"].mean()),
        "challenger_conditional_total_mae":float(frame["challenger_abs_error"].mean()),
        "challenger_minus_baseline_total_mae":float(
            (frame["challenger_abs_error"]-frame["baseline_abs_error"]).mean()
        ),
        "baseline_efficiency_mae":float(frame["baseline_efficiency_abs_error"].mean()),
        "challenger_efficiency_mae":float(frame["challenger_efficiency_abs_error"].mean()),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--bootstrap-replicates",type=int,default=3000)
    args=parser.parse_args()

    bundle=load_core_data(range(HISTORY_START,max(EVALUATION_SEASONS)+1))
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    players=_pandas(nfl.load_players())
    events=build_event_rows(pbp,_positions(players))
    events=events[events["season"].between(HISTORY_START,max(EVALUATION_SEASONS))].copy()
    rows=build_component_rows(events)
    if rows.empty:
        raise RuntimeError("no defensive-efficiency component rows")

    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows.to_csv(args.output_dir/"component_rows.csv",index=False)
    results={}
    all_scored=[]
    for event_index,event_type in enumerate(EVENT_TYPES):
        season_summaries={}
        event_frames=[]
        for season in EVALUATION_SEASONS:
            scored,summary=score_season(
                rows,event_type=event_type,evaluation_season=season
            )
            summary["mae_difference_ci95"]=clustered_mae_difference_ci(
                scored,
                replicates=args.bootstrap_replicates,
                seed=20260918+event_index*100+season,
            )
            season_summaries[str(season)]=summary
            event_frames.append(scored.assign(evaluation_season=season))
            scored.to_csv(args.output_dir/f"{event_type}_{season}_scored.csv",index=False)
        combined=pd.concat(event_frames,ignore_index=True)
        aggregate=_pooled(combined)
        aggregate["mae_difference_ci95"]=clustered_mae_difference_ci(
            combined,
            replicates=args.bootstrap_replicates,
            seed=20261918+event_index,
        )
        aggregate["by_season"]=season_summaries
        improving=sum(
            season_summaries[str(season)]["challenger_minus_baseline_total_mae"]<0
            for season in EVALUATION_SEASONS
        )
        ci=aggregate["mae_difference_ci95"]
        aggregate["advance_gate"]={
            "pooled_mae_improves":aggregate["challenger_minus_baseline_total_mae"]<0,
            "at_least_two_seasons_improve":improving>=2,
            "clustered_ci_upper_nonpositive":ci[1] is not None and ci[1]<=0,
            "improving_season_count":int(improving),
        }
        aggregate["advance_gate"]["passed"]=all([
            aggregate["advance_gate"]["pooled_mae_improves"],
            aggregate["advance_gate"]["at_least_two_seasons_improve"],
            aggregate["advance_gate"]["clustered_ci_upper_nonpositive"],
        ])
        results[event_type]=aggregate
        all_scored.append(combined)

    summary={
        "contract_version":CONTRACT_VERSION,
        "evaluation_seasons":list(EVALUATION_SEASONS),
        "by_event_type":results,
        "source_audit":{
            "pbp_normalization":pbp_audit,
            "event_rows":int(len(events)),
            "component_rows":int(len(rows)),
        },
        "component_isolation_only":True,
        "conditioned_on_actual_event_count":True,
        "pregame_prop_forecast":False,
        "sportsbook_data_used":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    (args.output_dir/"summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

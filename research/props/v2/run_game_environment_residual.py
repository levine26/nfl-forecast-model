from __future__ import annotations

"""Run the preregistered team-level game-environment residual experiment."""

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
from nfl_forecast.props_opportunity import rolling_origin_team_diagnostics
from nfl_forecast.props_upstream import build_lagged_props_history
from run_dynamic_role_backtest import (
    canonical_schedule,
    load_game_line_source,
    map_events_to_schedule,
    normalize_historical_pbp,
)
from game_environment_residual import (
    CONTRACT_VERSION,
    clustered_difference_interval,
    evaluate_environment_season,
    prepare_environment_rows,
)


BOOK_ID=30
EVALUATION_SEASONS=(2023,2024,2025)
HISTORY_START=2021


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def open_game_environment(seasons, bundle)->tuple[pd.DataFrame,dict]:
    rows=[]
    audit={}
    for season in seasons:
        raw,source_audit=load_game_line_source(int(season))
        schedule=canonical_schedule(bundle,int(season))
        event_map,map_audit=map_events_to_schedule(raw,schedule)

        work=raw[
            raw["book_id"].eq(BOOK_ID)
            & raw["period"].astype(str).str.lower().eq("event")
            & raw["type"].astype(str).str.lower().isin({"spread","total"})
        ].copy()
        work["value"]=pd.to_numeric(work["value"],errors="coerce")
        work=work[work["value"].notna()].copy()
        if "is_live" in work.columns:
            is_live=work["is_live"].astype("string").fillna("").str.lower()
            work=work[~is_live.isin({"true","1","yes"})].copy()

        season_rows=0
        excluded=0
        for event_id,group in work.groupby("event_id",sort=False):
            try:
                event=int(event_id)
            except (TypeError,ValueError):
                excluded+=1
                continue
            mapped=event_map.get(event)
            if mapped is None:
                excluded+=1
                continue
            game_id=str(mapped["game_id"])
            home=str(mapped["home_team"])
            away=str(mapped["away_team"])
            total_values=group.loc[
                group["type"].astype(str).str.lower().eq("total"),"value"
            ].dropna()
            if total_values.empty:
                excluded+=1
                continue
            total=float(total_values.median())

            spreads=group[group["type"].astype(str).str.lower().eq("spread")].copy()
            spread_map={}
            for team,tg in spreads.groupby("team",sort=False):
                team=str(team).upper().replace("JAC","JAX").replace("LA","LAR")
                vals=pd.to_numeric(tg["value"],errors="coerce").dropna()
                if len(vals):
                    spread_map[team]=float(vals.median())
            if home not in spread_map or away not in spread_map:
                excluded+=1
                continue
            # A standard two-sided spread should be symmetric. Large disagreement fails closed.
            if abs(spread_map[home]+spread_map[away])>0.25:
                excluded+=1
                continue

            rows.extend([
                {
                    "game_id":game_id,"season":int(season),"week":int(mapped["week"]),
                    "team":home,"team_spread":spread_map[home],"game_total":total,
                },
                {
                    "game_id":game_id,"season":int(season),"week":int(mapped["week"]),
                    "team":away,"team_spread":spread_map[away],"game_total":total,
                },
            ])
            season_rows+=2
        audit[str(season)]={
            "source":source_audit,
            "event_mapping":map_audit,
            "book_id":BOOK_ID,
            "book_label":"OPEN",
            "team_rows":season_rows,
            "excluded_events":excluded,
            "historical_exact_publication_timestamp_claimed":False,
        }
    return pd.DataFrame(rows),audit


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--bootstrap-replicates",type=int,default=3000)
    args=parser.parse_args()

    seasons=list(range(HISTORY_START,max(EVALUATION_SEASONS)+1))
    bundle=load_core_data(seasons)
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    players=_pandas(nfl.load_players())

    # Build a complete pre-2026 historical opportunity table, then ask the existing opportunity
    # engine for one-step-ahead team-volume forecasts. No target player-prop result is involved.
    history=build_lagged_props_history(
        pbp,players,season=2026,week=1
    )
    diagnostics=rolling_origin_team_diagnostics(
        history.team_history,
        history.player_history,
        minimum_prior_games=3,
        half_life_games=8.0,
        exclude_season=None,
    )
    diagnostics=diagnostics[
        diagnostics["season"].between(HISTORY_START,max(EVALUATION_SEASONS))
    ].copy()
    market_state,market_audit=open_game_environment(seasons,bundle)
    rows=prepare_environment_rows(diagnostics,market_state)
    if rows.empty:
        raise RuntimeError("no game-environment rows after PIT source join")

    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows.to_csv(args.output_dir/"joined_component_rows.csv",index=False)

    season_summaries={}
    scored_frames=[]
    for season in EVALUATION_SEASONS:
        scored,summary=evaluate_environment_season(rows,evaluation_season=season)
        summary["team_plays_mae_diff_ci95"]=clustered_difference_interval(
            scored,"challenger_play_abs_error","baseline_play_abs_error",
            replicates=args.bootstrap_replicates,seed=20260918+season,
        )
        summary["dropback_rate_mae_diff_ci95"]=clustered_difference_interval(
            scored,"challenger_dropback_abs_error","baseline_dropback_abs_error",
            replicates=args.bootstrap_replicates,seed=20261918+season,
        )
        season_summaries[str(season)]=summary
        scored_frames.append(scored.assign(evaluation_season=season))
        scored.to_csv(args.output_dir/f"{season}_scored_rows.csv",index=False)

    all_scored=pd.concat(scored_frames,ignore_index=True)
    aggregate={
        "contract_version":CONTRACT_VERSION,
        "n":int(len(all_scored)),
        "unique_games":int(all_scored["game_id"].astype(str).nunique()),
        "baseline_team_plays_mae":float(all_scored["baseline_play_abs_error"].mean()),
        "challenger_team_plays_mae":float(all_scored["challenger_play_abs_error"].mean()),
        "challenger_minus_baseline_team_plays_mae":float(
            (all_scored["challenger_play_abs_error"]-all_scored["baseline_play_abs_error"]).mean()
        ),
        "baseline_dropback_rate_mae":float(all_scored["baseline_dropback_abs_error"].mean()),
        "challenger_dropback_rate_mae":float(all_scored["challenger_dropback_abs_error"].mean()),
        "challenger_minus_baseline_dropback_rate_mae":float(
            (all_scored["challenger_dropback_abs_error"]-all_scored["baseline_dropback_abs_error"]).mean()
        ),
        "team_plays_mae_diff_ci95":clustered_difference_interval(
            all_scored,"challenger_play_abs_error","baseline_play_abs_error",
            replicates=args.bootstrap_replicates,seed=20262918,
        ),
        "dropback_rate_mae_diff_ci95":clustered_difference_interval(
            all_scored,"challenger_dropback_abs_error","baseline_dropback_abs_error",
            replicates=args.bootstrap_replicates,seed=20263918,
        ),
        "by_season":season_summaries,
        "source_audit":{
            "pbp_normalization":pbp_audit,
            "history":history.audit,
            "game_lines":market_audit,
        },
        "prop_outcomes_used":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    (args.output_dir/"summary.json").write_text(
        json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps({
        "n":aggregate["n"],
        "baseline_team_plays_mae":aggregate["baseline_team_plays_mae"],
        "challenger_team_plays_mae":aggregate["challenger_team_plays_mae"],
        "team_plays_mae_diff_ci95":aggregate["team_plays_mae_diff_ci95"],
        "baseline_dropback_rate_mae":aggregate["baseline_dropback_rate_mae"],
        "challenger_dropback_rate_mae":aggregate["challenger_dropback_rate_mae"],
        "dropback_rate_mae_diff_ci95":aggregate["dropback_rate_mae_diff_ci95"],
    },indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

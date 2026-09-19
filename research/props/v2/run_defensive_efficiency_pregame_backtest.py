from __future__ import annotations

"""Paired true-pregame ablation for opponent defensive efficiency residuals."""

import argparse
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from defensive_efficiency_pregame import (
    CONTRACT_VERSION,
    apply_defensive_efficiency_overlay,
    build_defense_delta_lookup,
)
from defensive_efficiency_residual import (
    build_component_rows,
    build_event_rows,
    fit_residual,
)
from nfl_forecast.challenger_props_simulation import (
    build_game_input_from_upstream,
    evaluate_distribution,
    simulate_game,
)
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from nfl_forecast.props_upstream import (
    build_empirical_scoring_context,
    build_game_upstream_package,
    build_lagged_props_history,
    fit_pre2026_efficiency_priors,
    residual_efficiency_by_team_from_empirical_priors,
)
from run_dynamic_role_backtest import (
    _pandas,
    _team,
    build_game_stats_and_participation,
    build_market_listed_player_state,
    canonical_schedule,
    load_game_line_source,
    load_market_source,
    map_events_to_schedule,
    market_observations,
    normalize_historical_pbp,
    roster_metadata,
    sanitize_efficiency_history_for_frozen_validator,
    seed_for_game,
)

ROUTE_PRIORS={"RB":0.55,"WR":0.90,"TE":0.75}
PRIMARY_BOOK=30
MODE_TO_PROP={"rushing":"rushing_yards","receiving":"receiving_yards"}
OPPORTUNITY_KEYS=("active","pass_attempts","routes","targets","receptions","carries")


def _positions(players: pd.DataFrame)->dict[str,str]:
    id_col=next((c for c in ("gsis_id","player_id") if c in players.columns),None)
    pos_col=next((c for c in ("position","position_group") if c in players.columns),None)
    if id_col is None or pos_col is None:
        raise RuntimeError("players table missing stable ID/position")
    work=players[[id_col,pos_col]].copy()
    work[id_col]=work[id_col].astype("string").fillna("").str.strip()
    work[pos_col]=work[pos_col].astype("string").fillna("").str.upper().str.strip()
    work=work[work[id_col].ne("") & work[pos_col].isin({"QB","RB","WR","TE"})]
    work=work.drop_duplicates(id_col,keep="last")
    return dict(zip(work[id_col].astype(str),work[pos_col].astype(str)))


def empirical_crps(samples: np.ndarray, observation: float) -> float:
    values=np.asarray(samples,dtype=float)
    values=values[np.isfinite(values)]
    if values.size==0:
        raise RuntimeError("CRPS requires finite samples")
    ordered=np.sort(values)
    n=ordered.size
    first=float(np.mean(np.abs(ordered-float(observation))))
    weights=2.0*np.arange(n,dtype=float)-float(n)+1.0
    half_pairwise=float(np.dot(weights,ordered)/float(n*n))
    return float(max(0.0,first-half_pairwise))


def interval_score(samples: np.ndarray, observation: float, level: float=.80):
    values=np.asarray(samples,dtype=float)
    alpha=1.0-float(level)
    lo=float(np.quantile(values,alpha/2.0))
    hi=float(np.quantile(values,1.0-alpha/2.0))
    y=float(observation)
    penalty=0.0
    if y<lo:
        penalty=(2.0/alpha)*(lo-y)
    elif y>hi:
        penalty=(2.0/alpha)*(y-hi)
    return float((hi-lo)+penalty),bool(lo<=y<=hi)


def cluster_ci(frame,column,seed,replicates=3000):
    games=np.asarray(sorted(frame["game_id"].astype(str).unique()))
    if len(games)<2:
        return [None,None]
    grouped={g:frame[frame["game_id"].astype(str).eq(g)] for g in games}
    rng=np.random.default_rng(seed)
    vals=np.empty(int(replicates),dtype=float)
    for i in range(int(replicates)):
        sampled=rng.choice(games,size=len(games),replace=True)
        boot=pd.concat([grouped[g] for g in sampled],ignore_index=True)
        vals[i]=float(boot[column].mean())
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]


def run_season(*,season:int,mode:str,simulations:int):
    mode=str(mode).strip().lower()
    if mode not in MODE_TO_PROP:
        raise ValueError(f"unsupported mode {mode}")
    prop_type=MODE_TO_PROP[mode]
    history_start=2021
    seasons=list(range(history_start,int(season)+1))
    bundle=load_core_data(seasons)
    bundle=load_advanced_data(bundle,seasons)
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    players=_pandas(nfl.load_players())
    snap_counts,snap_identity_audit=normalize_snap_counts_player_ids(bundle.snap_counts,players)

    market,market_source_audit=load_market_source(season)
    game_lines,game_line_source_audit=load_game_line_source(season)
    schedule=canonical_schedule(bundle,season)
    roster=roster_metadata(market,book_id=PRIMARY_BOOK,require_genuine_open=True)
    event_map,event_map_audit=map_events_to_schedule(game_lines,schedule)
    observations,market_pair_audit=market_observations(
        market,book_id=PRIMARY_BOOK,require_genuine_open=True
    )
    observations=observations[
        observations["event_id"].isin(event_map)
        & observations["prop_type"].astype(str).eq(prop_type)
    ].copy()

    actual_stats,participation,participation_audit=build_game_stats_and_participation(
        pbp,snap_counts
    )
    trained_through=int(season)-1
    fitted_priors=fit_pre2026_efficiency_priors(
        pbp,players,trained_through_season=trained_through
    )
    position_priors=fitted_priors["efficiency_position_priors"]

    event_rows=build_event_rows(pbp,_positions(players))
    component_rows=build_component_rows(event_rows)
    fit=fit_residual(
        component_rows,event_type=mode,trained_through_season=trained_through
    ).to_dict()
    defense_lookup=build_defense_delta_lookup(component_rows)

    obs_by_event={int(e):g.copy() for e,g in observations.groupby("event_id")}
    roster_by_event={int(e):g.copy() for e,g in roster.groupby("event_id")}
    exclusions=defaultdict(int)
    adapter_totals=defaultdict(int)
    results=[]

    for week in range(1,19):
        events=sorted(
            e for e in obs_by_event
            if e in event_map and int(event_map[e]["week"])==week
        )
        if not events:
            continue
        lagged=build_lagged_props_history(pbp,players,season=season,week=week)
        lagged,adapter=sanitize_efficiency_history_for_frozen_validator(lagged)
        for k,v in adapter.items():
            adapter_totals[k]+=int(v)
        teams=sorted({
            _team(event_map[e]["home_team"]) for e in events
        }|{
            _team(event_map[e]["away_team"]) for e in events
        })
        scoring=build_empirical_scoring_context(
            pbp,teams=teams,season=season,week=week,
            trained_through_season=trained_through,
        )["scoring_context_by_team"]

        for event_id in events:
            mapped=event_map[event_id]
            game_id=str(mapped["game_id"])
            event_rows_for_game=roster_by_event.get(event_id)
            if event_rows_for_game is None or event_rows_for_game.empty:
                exclusions["missing_event_roster"]+=len(obs_by_event[event_id])
                continue
            state,qb_overrides,state_audit=build_market_listed_player_state(
                event_rows_for_game,mapped
            )
            if state is None:
                exclusions[str(state_audit.get("reason","player_state_failed"))]+=len(
                    obs_by_event[event_id]
                )
                continue
            game_teams=[_team(mapped["home_team"]),_team(mapped["away_team"])]
            residual=residual_efficiency_by_team_from_empirical_priors(
                game_teams,fitted_priors
            )

            try:
                package=build_game_upstream_package(
                    player_state=state,
                    history=lagged,
                    game_id=game_id,
                    season=season,
                    week=week,
                    forecast_timestamp=(
                        pd.Timestamp(mapped["kickoff"])-pd.Timedelta(seconds=1)
                    ).isoformat(),
                    route_prior_means=ROUTE_PRIORS,
                    availability_priors={},
                    position_efficiency_priors=position_priors,
                    scoring_context_by_team=scoring,
                    residual_efficiency_by_team=residual,
                    source_status="qualified",
                    prior_model_trained_through_season=trained_through,
                    primary_qb_by_team=qb_overrides,
                )
                game_input=build_game_input_from_upstream(
                    home_team=_team(mapped["home_team"]),
                    away_team=_team(mapped["away_team"]),
                    opportunity_projections=package.opportunity_projections,
                    efficiency_player_parameters=package.efficiency_player_parameters,
                    team_td_parameters=package.team_td_parameters,
                    residual_efficiency_by_team=package.residual_efficiency_by_team,
                )
                baseline=simulate_game(
                    game_input,simulations=int(simulations),seed=seed_for_game(game_id)
                )
                challenger=deepcopy(baseline)
                overlay=apply_defensive_efficiency_overlay(
                    challenger,game_input,game_id=game_id,mode=mode,fit=fit,
                    defense_delta_lookup=defense_lookup,
                )
                if overlay["opportunity_arrays_modified"]!=0:
                    raise RuntimeError("efficiency overlay modified opportunities")
            except Exception as exc:
                exclusions[f"game_build_or_simulation:{type(exc).__name__}"]+=len(
                    obs_by_event[event_id]
                )
                continue

            for _,obs in obs_by_event[event_id].iterrows():
                player_id=str(obs["player_id"])
                if player_id not in baseline.player_stats:
                    exclusions["market_player_not_simulated"]+=1
                    continue
                meta=participation.get((game_id,player_id))
                if meta is None:
                    exclusions["participation_unavailable"]+=1
                    continue
                if int(meta.get("offense_snaps",0))<=0:
                    exclusions["zero_offensive_snaps_void"]+=1
                    continue
                if (game_id,str(game_input.players[
                    next(i for i,p in enumerate(game_input.players) if p.player_id==player_id)
                ].opponent),mode) not in defense_lookup:
                    exclusions["missing_defense_state"]+=1
                    continue

                line=float(obs["market_line"])
                actual=float(actual_stats.get((game_id,player_id),{}).get(prop_type,0.0))
                b_samples=baseline.player_stats[player_id][prop_type]
                c_samples=challenger.player_stats[player_id][prop_type]

                opportunities_identical=all(
                    np.array_equal(
                        baseline.player_stats[player_id][k],
                        challenger.player_stats[player_id][k],
                    )
                    for k in OPPORTUNITY_KEYS
                )
                if not opportunities_identical:
                    raise RuntimeError("paired opportunity arrays differ")

                b_dist=evaluate_distribution(
                    b_samples,market_line=line,discrete=False,interval_level=.80
                )
                c_dist=evaluate_distribution(
                    c_samples,market_line=line,discrete=False,interval_level=.80
                )
                b_crps=empirical_crps(b_samples,actual)
                c_crps=empirical_crps(c_samples,actual)
                b_is,b_cov=interval_score(b_samples,actual)
                c_is,c_cov=interval_score(c_samples,actual)
                outcome="OVER" if actual>line else "UNDER" if actual<line else "PUSH"
                b_side="OVER" if b_dist.levline_fair_line>line else "UNDER" if b_dist.levline_fair_line<line else None
                c_side="OVER" if c_dist.levline_fair_line>line else "UNDER" if c_dist.levline_fair_line<line else None

                def grade(side):
                    if side is None or outcome=="PUSH":
                        return None
                    return "WIN" if side==outcome else "LOSS"

                results.append({
                    "contract_version":CONTRACT_VERSION,
                    "mode":mode,
                    "season":int(season),
                    "week":int(week),
                    "game_id":game_id,
                    "player_id":player_id,
                    "market_line":line,
                    "actual_result":actual,
                    "v1_fair_line":float(b_dist.levline_fair_line),
                    "challenger_fair_line":float(c_dist.levline_fair_line),
                    "v1_abs_error":abs(float(b_dist.levline_fair_line)-actual),
                    "challenger_abs_error":abs(float(c_dist.levline_fair_line)-actual),
                    "challenger_minus_v1_abs_error":abs(float(c_dist.levline_fair_line)-actual)-abs(float(b_dist.levline_fair_line)-actual),
                    "v1_crps":b_crps,
                    "challenger_crps":c_crps,
                    "challenger_minus_v1_crps":c_crps-b_crps,
                    "v1_interval_score_80":b_is,
                    "challenger_interval_score_80":c_is,
                    "v1_covered_80":b_cov,
                    "challenger_covered_80":c_cov,
                    "v1_grading_result":grade(b_side),
                    "challenger_grading_result":grade(c_side),
                    "opportunity_arrays_identical":opportunities_identical,
                })

    frame=pd.DataFrame(results)
    if frame.empty:
        raise RuntimeError("no paired defensive-efficiency pregame rows")
    decided=frame[
        frame["v1_grading_result"].isin(["WIN","LOSS"])
        & frame["challenger_grading_result"].isin(["WIN","LOSS"])
    ]
    summary={
        "contract_version":CONTRACT_VERSION,
        "mode":mode,
        "season":int(season),
        "trained_through_season":trained_through,
        "n":int(len(frame)),
        "unique_games":int(frame["game_id"].nunique()),
        "unique_players":int(frame["player_id"].nunique()),
        "v1_crps":float(frame["v1_crps"].mean()),
        "challenger_crps":float(frame["challenger_crps"].mean()),
        "challenger_minus_v1_crps":float(frame["challenger_minus_v1_crps"].mean()),
        "crps_difference_ci95":cluster_ci(
            frame,"challenger_minus_v1_crps",20260918+season
        ),
        "v1_fair_line_mae":float(frame["v1_abs_error"].mean()),
        "challenger_fair_line_mae":float(frame["challenger_abs_error"].mean()),
        "challenger_minus_v1_mae":float(frame["challenger_minus_v1_abs_error"].mean()),
        "mae_difference_ci95":cluster_ci(
            frame,"challenger_minus_v1_abs_error",20261918+season
        ),
        "v1_interval_score_80":float(frame["v1_interval_score_80"].mean()),
        "challenger_interval_score_80":float(frame["challenger_interval_score_80"].mean()),
        "v1_coverage_80":float(frame["v1_covered_80"].mean()),
        "challenger_coverage_80":float(frame["challenger_covered_80"].mean()),
        "decided_n":int(len(decided)),
        "v1_direction_accuracy":float(decided["v1_grading_result"].eq("WIN").mean()) if len(decided) else None,
        "challenger_direction_accuracy":float(decided["challenger_grading_result"].eq("WIN").mean()) if len(decided) else None,
        "all_opportunity_arrays_identical":bool(frame["opportunity_arrays_identical"].all()),
        "fit":fit,
        "source_audit":{
            "pbp_normalization":pbp_audit,
            "snap_identity":snap_identity_audit,
            "market_source":market_source_audit,
            "game_line_source":game_line_source_audit,
            "event_mapping":event_map_audit,
            "market_pairing":market_pair_audit,
            "participation":participation_audit,
            "efficiency_history_adapter":dict(adapter_totals),
            "exclusions":dict(exclusions),
        },
        "target_game_events_used_for_fit":0,
        "target_game_yards_used_for_fit":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    return frame,summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--season",type=int,choices=[2023,2024,2025],required=True)
    parser.add_argument("--mode",choices=["rushing","receiving"],required=True)
    parser.add_argument("--simulations",type=int,default=5000)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    frame,summary=run_season(
        season=args.season,mode=args.mode,simulations=args.simulations
    )
    args.output_dir.mkdir(parents=True,exist_ok=True)
    frame.to_csv(args.output_dir/f"{args.mode}_{args.season}_forecast_level.csv",index=False)
    (args.output_dir/f"{args.mode}_{args.season}_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__=="__main__":
    main()

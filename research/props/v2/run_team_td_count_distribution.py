from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))

from nfl_forecast.data import load_core_data
from run_dynamic_role_backtest import normalize_historical_pbp
from team_td_count_distribution import (
    CONTRACT_VERSION,
    build_strict_prior_means,
    build_team_game_td_counts,
    clustered_crps_difference_ci,
    score_season,
)

HISTORY_START=2018
EVALUATION_SEASONS=(2023,2024,2025)


def _pooled(frame: pd.DataFrame)->dict:
    return {
        "n":int(len(frame)),
        "unique_games":int(frame["game_id"].astype(str).nunique()),
        "poisson_crps":float(frame["poisson_crps"].mean()),
        "nb_crps":float(frame["nb_crps"].mean()),
        "nb_minus_poisson_crps":float((frame["nb_crps"]-frame["poisson_crps"]).mean()),
        "poisson_log_loss":float(frame["poisson_log_loss"].mean()),
        "nb_log_loss":float(frame["nb_log_loss"].mean()),
        "nb_minus_poisson_log_loss":float(
            (frame["nb_log_loss"]-frame["poisson_log_loss"]).mean()
        ),
        "poisson_coverage_80":float(frame["poisson_covered_80"].mean()),
        "nb_coverage_80":float(frame["nb_covered_80"].mean()),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--bootstrap-replicates",type=int,default=3000)
    args=parser.parse_args()

    bundle=load_core_data(range(HISTORY_START,max(EVALUATION_SEASONS)+1))
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    team_games=build_team_game_td_counts(pbp)
    team_games=team_games[
        team_games["season"].between(HISTORY_START,max(EVALUATION_SEASONS))
    ].copy()
    rows=build_strict_prior_means(team_games)
    if rows.empty:
        raise RuntimeError("no team touchdown count rows")

    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows.to_csv(args.output_dir/"component_rows.csv",index=False)

    seasons={}
    frames=[]
    for season in EVALUATION_SEASONS:
        scored,summary=score_season(rows,evaluation_season=season)
        summary["crps_difference_ci95"]=clustered_crps_difference_ci(
            scored,
            replicates=args.bootstrap_replicates,
            seed=20260918+season,
        )
        seasons[str(season)]=summary
        frames.append(scored.assign(evaluation_season=season))
        scored.to_csv(args.output_dir/f"{season}_scored.csv",index=False)

    combined=pd.concat(frames,ignore_index=True)
    aggregate=_pooled(combined)
    aggregate["crps_difference_ci95"]=clustered_crps_difference_ci(
        combined,
        replicates=args.bootstrap_replicates,
        seed=20261918,
    )
    improving=sum(
        seasons[str(season)]["nb_minus_poisson_crps"]<0
        for season in EVALUATION_SEASONS
    )
    ci=aggregate["crps_difference_ci95"]
    gate={
        "pooled_crps_improves":aggregate["nb_minus_poisson_crps"]<0,
        "at_least_two_seasons_improve":improving>=2,
        "clustered_ci_upper_nonpositive":ci[1] is not None and ci[1]<=0,
        "pooled_log_loss_not_worse":aggregate["nb_minus_poisson_log_loss"]<=0,
        "improving_season_count":int(improving),
    }
    gate["passed"]=all([
        gate["pooled_crps_improves"],
        gate["at_least_two_seasons_improve"],
        gate["clustered_ci_upper_nonpositive"],
        gate["pooled_log_loss_not_worse"],
    ])

    result={
        "contract_version":CONTRACT_VERSION,
        "evaluation_seasons":list(EVALUATION_SEASONS),
        "aggregate":aggregate,
        "by_season":seasons,
        "advance_gate":gate,
        "source_audit":{
            "pbp_normalization":pbp_audit,
            "team_game_rows":int(len(team_games)),
            "component_rows":int(len(rows)),
        },
        "same_expected_mean_for_both_models":True,
        "player_prop_outcomes_used":0,
        "sportsbook_data_used":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    (args.output_dir/"summary.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

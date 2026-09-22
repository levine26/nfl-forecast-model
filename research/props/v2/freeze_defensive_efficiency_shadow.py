from __future__ import annotations

"""Freeze final pre-2026 defensive-efficiency coefficients for prospective Props shadow use."""

import argparse
import json
from pathlib import Path
import sys

import nflreadpy as nfl

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from defensive_efficiency_residual import (
    CONTRACT_VERSION as COMPONENT_CONTRACT_VERSION,
    build_component_rows,
    build_event_rows,
    fit_residual,
)
from run_dynamic_role_backtest import _pandas, normalize_historical_pbp
from nfl_forecast.data import load_core_data

SHADOW_CONTRACT_VERSION="levline-props-v2-defensive-efficiency-shadow-v0.1.0"
TRAINED_THROUGH_SEASON=2025
HISTORY_START=2019


def _positions(players):
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


def freeze(output: Path)->dict:
    bundle=load_core_data(range(HISTORY_START,TRAINED_THROUGH_SEASON+1))
    pbp,pbp_audit=normalize_historical_pbp(bundle.pbp)
    players=_pandas(nfl.load_players())
    events=build_event_rows(pbp,_positions(players))
    rows=build_component_rows(events)
    fits={
        event_type:fit_residual(
            rows,event_type=event_type,trained_through_season=TRAINED_THROUGH_SEASON
        ).to_dict()
        for event_type in ("rushing","receiving")
    }
    result={
        "contract_version":SHADOW_CONTRACT_VERSION,
        "component_contract_version":COMPONENT_CONTRACT_VERSION,
        "trained_through_season":TRAINED_THROUGH_SEASON,
        "history_start_season":HISTORY_START,
        "fits":fits,
        "fit_population":{
            "event_rows":int(len(events)),
            "component_rows":int(len(rows)),
        },
        "source_audit":{"pbp_normalization":pbp_audit},
        "completed_2026_outcomes_used":0,
        "prop_outcomes_used":0,
        "sportsbook_results_used":0,
        "production_authorized":False,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    return result


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    freeze(args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

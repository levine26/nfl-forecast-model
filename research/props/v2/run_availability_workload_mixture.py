from __future__ import annotations

"""Run season-forward historical availability/workload mixture evaluation."""

import argparse
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(Path(__file__).resolve().parent))

from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from availability_workload_mixture import (
    CONTRACT_VERSION,
    build_workload_examples,
    evaluate_season_forward,
    normalize_injury_designations,
    normalize_snap_history,
)


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--evaluation-season",type=int,required=True)
    parser.add_argument("--history-start",type=int,default=2012)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()

    season=int(args.evaluation_season)
    if season >= 2026:
        raise ValueError("completed 2026 outcomes are prohibited")
    if season < 2014:
        raise ValueError("evaluation season requires at least two prior history seasons")
    seasons=list(range(int(args.history_start),season+1))

    injuries=_pandas(nfl.load_injuries(seasons))
    raw_snaps=_pandas(nfl.load_snap_counts(seasons))
    players=_pandas(nfl.load_players())
    snaps,snap_identity_audit=normalize_snap_counts_player_ids(raw_snaps,players)
    if snaps is None or snaps.empty:
        raise RuntimeError("snap-count identity normalization produced no usable rows")

    injury_rows,injury_audit=normalize_injury_designations(
        injuries,max_season=season
    )
    snap_rows,snap_audit=normalize_snap_history(
        snaps,max_season=season
    )
    examples,example_audit=build_workload_examples(injury_rows,snap_rows)
    if examples.empty:
        raise RuntimeError("no workload examples available")

    scored,summary=evaluate_season_forward(
        examples,evaluation_season=season
    )
    summary["source_audit"]={
        "injuries":injury_audit,
        "snap_identity":snap_identity_audit,
        "snap_history":snap_audit,
        "examples":example_audit,
    }
    summary["source_notes"]={
        "injuries":"nflverse historical injury designations; retrospective development only",
        "snaps":"nflverse/PFR snap counts normalized to stable GSIS identity",
        "historical_publication_timestamp_claimed":False,
    }
    assert summary["contract_version"]==CONTRACT_VERSION
    assert summary["completed_2026_outcomes_used"]==0
    assert summary["prop_outcomes_used_for_fit_or_evaluation"]==0
    assert summary["production_authorized"] is False

    args.output_dir.mkdir(parents=True,exist_ok=True)
    scored.to_csv(args.output_dir/f"{season}_scored_rows.csv",index=False)
    (args.output_dir/f"{season}_summary.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps({
        "season":season,
        "n":summary["n"],
        "mixture_workload_mae":summary["mixture_workload_mae"],
        "active_only_workload_mae":summary["active_only_workload_mae"],
        "mixture_minus_active_only_mae":summary["mixture_minus_active_only_mae"],
        "mixture_active_brier":summary["mixture_active_brier"],
        "active_only_brier":summary["active_only_brier"],
    },indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

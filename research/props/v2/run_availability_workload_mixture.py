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

from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from availability_workload_mixture import build_workload_observations, fit_workload_mixture


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--start-season",type=int,default=2021)
    p.add_argument("--end-season",type=int,default=2025)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    if args.end_season>2025:
        raise ValueError("availability workload fit may not use completed 2026 outcomes")
    seasons=list(range(args.start_season,args.end_season+1))
    injuries=_pandas(nfl.load_injuries(seasons))
    raw_snaps=_pandas(nfl.load_snap_counts(seasons))
    players=_pandas(nfl.load_players())
    snaps,snap_audit=normalize_snap_counts_player_ids(raw_snaps,players)
    if snaps is None or snaps.empty:
        raise RuntimeError("stable-ID snap history unavailable")
    schedules=pd.read_csv(
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        low_memory=False,
    )
    schedules=schedules[schedules["season"].isin(seasons)].copy()
    observations,audit=build_workload_observations(
        injuries,snaps,schedules,trained_through_season=args.end_season
    )
    fitted=fit_workload_mixture(observations)
    fitted["source_audit"]={
        **audit,
        "snap_identity":snap_audit,
        "seasons":seasons,
    }
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    observations.to_csv(out/"workload_observations.csv",index=False)
    (out/"workload_mixture.json").write_text(
        json.dumps(fitted,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    report=[
        "# Props 2.0 Availability / Workload Mixture",
        "",
        "**RETROSPECTIVE MECHANISM RESEARCH — NO PROP OUTCOMES USED**",
        "",
        f"Eligible observations: {fitted['n_observations']}",
        f"Active observations: {fitted['n_active']}",
        f"Observed OUT rate: {100*fitted['out_rate']:.2f}%",
        "",
        "## Active workload states",
        "",
    ]
    for state,row in fitted["active_state_parameters"].items():
        report.append(
            f"- {state}: weight={row['mixture_weight']:.3f}, "
            f"median ratio={row['median_workload_ratio']:.3f}, n={row['n_assigned']}"
        )
    report.extend([
        "",
        "Diagnostic gate only; this does not authorize simulation integration or production.",
        "",
    ])
    (out/"report.md").write_text("\n".join(report),encoding="utf-8")
    print((out/"report.md").read_text())
    return 0


if __name__=="__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))

from td_count_distribution_v2 import evaluate_td_count_families


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def build_team_games(pbp:pd.DataFrame)->pd.DataFrame:
    work=pbp.copy()
    if "season_type" in work.columns:
        work=work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["team"]=work["posteam"].astype("string").fillna("").str.upper().str.strip()
    pass_td=pd.to_numeric(work.get("pass_touchdown",0),errors="coerce").fillna(0).eq(1)
    rush_td=pd.to_numeric(work.get("rush_touchdown",0),errors="coerce").fillna(0).eq(1)
    # One offensive touchdown event per scoring play even if upstream flags overlap unexpectedly.
    work["_off_td"]=(pass_td|rush_td).astype(int)
    rows=(
        work[work["game_id"].notna() & work["team"].ne("")]
        .groupby(["season","game_id","team"],as_index=False,sort=False)["_off_td"].sum()
        .rename(columns={"_off_td":"offensive_tds"})
    )
    return rows


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    seasons=[2021,2022,2023,2024,2025]
    pbp=_pandas(nfl.load_pbp(seasons))
    team_games=build_team_games(pbp)
    result=evaluate_td_count_families(team_games)
    result["source_audit"]={
        "seasons":seasons,
        "team_game_rows":int(len(team_games)),
        "games":int(team_games["game_id"].nunique()),
    }
    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    (out/"td_count_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    team_games.groupby(["season"],as_index=False).agg(
        team_game_rows=("offensive_tds","size"),
        mean_tds=("offensive_tds","mean"),
        variance_tds=("offensive_tds","var"),
    ).to_csv(out/"td_count_summary.csv",index=False)
    agg=result["aggregate"]
    report=[
        "# Props 2.0 Team TD Count Distribution Study","",
        "**RETROSPECTIVE MECHANISM EVIDENCE — PLAYER TD ALLOCATION UNCHANGED**","",
        f"N test team-games: {agg['n']}","",
        f"- Log loss: Poisson {agg['poisson']['log_loss']:.5f}, NB {agg['negative_binomial']['log_loss']:.5f}",
        f"- Brier: Poisson {agg['poisson']['brier']:.5f}, NB {agg['negative_binomial']['brier']:.5f}",
        f"- CRPS: Poisson {agg['poisson']['crps']:.5f}, NB {agg['negative_binomial']['crps']:.5f}",
    ]
    (out/"report.md").write_text("\n".join(report),encoding="utf-8")
    print((out/"report.md").read_text())
    return 0


if __name__=="__main__":
    raise SystemExit(main())

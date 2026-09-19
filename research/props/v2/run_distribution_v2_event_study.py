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

from distribution_v2_event_study import evaluate_rolling_event_distributions


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def _position_map(players:pd.DataFrame)->dict[str,str]:
    id_col=next((c for c in ("gsis_id","player_id","nflverse_id") if c in players.columns),None)
    pos_col=next((c for c in ("position","position_group") if c in players.columns),None)
    if id_col is None or pos_col is None:
        raise RuntimeError("player identity lacks stable id/position")
    work=players[[id_col,pos_col]].copy()
    work["id"]=work[id_col].astype("string").fillna("").str.strip()
    work["pos"]=work[pos_col].astype("string").fillna("").str.upper().str.strip()
    work=work[work["id"].ne("") & work["pos"].isin({"QB","RB","WR","TE"})]
    counts=work.groupby("id")["pos"].nunique()
    safe=set(counts[counts.eq(1)].index)
    return work[work["id"].isin(safe)].drop_duplicates("id",keep="last").set_index("id")["pos"].to_dict()


def build_events(pbp:pd.DataFrame,players:pd.DataFrame)->pd.DataFrame:
    pos=_position_map(players)
    work=pbp.copy()
    if "season_type" in work.columns:
        work=work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    rows=[]
    rush=pd.to_numeric(work.get("rush_attempt",0),errors="coerce").fillna(0).eq(1)
    rusher=work.get("rusher_player_id",work.get("rusher_id",pd.Series("",index=work.index))).astype("string").fillna("").str.strip()
    rush_yards=pd.to_numeric(work.get("rushing_yards"),errors="coerce")
    for idx in work.index[rush & rush_yards.notna()]:
        pid=str(rusher.loc[idx]); position=pos.get(pid)
        if position:
            rows.append({"season":int(work.at[idx,"season"]),"event_kind":"rushing","position":position,"yards":float(rush_yards.loc[idx])})
    complete=pd.to_numeric(work.get("complete_pass",0),errors="coerce").fillna(0).eq(1)
    receiver=work.get("receiver_player_id",work.get("receiver_id",pd.Series("",index=work.index))).astype("string").fillna("").str.strip()
    rec_yards=pd.to_numeric(work.get("receiving_yards"),errors="coerce")
    for idx in work.index[complete & rec_yards.notna()]:
        pid=str(receiver.loc[idx]); position=pos.get(pid)
        if position:
            rows.append({"season":int(work.at[idx,"season"]),"event_kind":"receiving","position":position,"yards":float(rec_yards.loc[idx])})
    return pd.DataFrame(rows)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    seasons=[2021,2022,2023,2024,2025]
    pbp=_pandas(nfl.load_pbp(seasons))
    players=_pandas(nfl.load_players())
    events=build_events(pbp,players)
    result=evaluate_rolling_event_distributions(events)
    result["source_audit"]={
        "seasons":seasons,
        "event_rows":int(len(events)),
        "rushing_events":int((events["event_kind"]=="rushing").sum()),
        "receiving_events":int((events["event_kind"]=="receiving").sum()),
    }
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    events.groupby(["season","event_kind","position"],as_index=False).agg(
        n=("yards","size"),mean=("yards","mean"),sd=("yards","std"),
        min=("yards","min"),max=("yards","max"),
    ).to_csv(out/"event_summary.csv",index=False)
    (out/"distribution_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    agg=result["aggregate"]
    report=[
        "# Props 2.0 Event Distribution V2 Study","",
        "**RETROSPECTIVE MECHANISM EVIDENCE — NOT PRODUCTION**","",
        f"Test events: {agg['n_test']}",
        f"Negative events observed: {agg['negative_event_count']}","",
        "## Aggregate proper-score comparison","",
        f"- CRPS: empirical {agg['empirical_mixture']['crps']:.4f} vs Gamma {agg['nonnegative_gamma']['crps']:.4f}",
        f"- Bin log loss: empirical {agg['empirical_mixture']['bin_log_loss']:.4f} vs Gamma {agg['nonnegative_gamma']['bin_log_loss']:.4f}",
        f"- Bin Brier: empirical {agg['empirical_mixture']['bin_brier']:.4f} vs Gamma {agg['nonnegative_gamma']['bin_brier']:.4f}",
        "",
        "This study tests event-distribution support/shape only; it does not establish player-prop forecast improvement.",
    ]
    (out/"report.md").write_text("\n".join(report),encoding="utf-8")
    print((out/"report.md").read_text())
    return 0


if __name__=="__main__":
    raise SystemExit(main())

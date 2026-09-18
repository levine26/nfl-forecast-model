from __future__ import annotations

"""Audit nflverse historical participation for route/target research.

This audit intentionally stops before calling any field a route. It inventories the exact
historical schema and determines which fields can support on-field/dropback participation
research. 2023+ releases are historical-only for this program because their source release
latency is postseason.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import pandas as pd

CONTRACT_VERSION="levline-props-v2-route-target-source-audit-v0.1.0"


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame,"to_pandas") else frame


def _field_groups(columns:list[str])->dict[str,list[str]]:
    lowered={c:c.lower() for c in columns}
    keys={
        "offense_players":("offense","off_player","offense_player"),
        "formation_personnel":("formation","personnel"),
        "route_like":("route","pattern"),
        "motion":("motion",),
        "box":("box",),
        "alignment":("slot","wide","alignment"),
        "ids":("player_id","gsis","nflverse_game_id","play_id","game_id"),
    }
    out={}
    for label,tokens in keys.items():
        out[label]=sorted(
            c for c,lc in lowered.items() if any(token in lc for token in tokens)
        )
    return out


def summarize(frame:pd.DataFrame,season:int)->dict[str,Any]:
    columns=[str(c) for c in frame.columns]
    game_col=next((c for c in ("nflverse_game_id","game_id","old_game_id") if c in frame.columns),None)
    play_col="play_id" if "play_id" in frame.columns else None
    return {
        "season":int(season),
        "rows":int(len(frame)),
        "columns":columns,
        "field_groups":_field_groups(columns),
        "unique_games":int(frame[game_col].astype(str).nunique()) if game_col else None,
        "unique_plays":int(frame[[game_col,play_col]].drop_duplicates().shape[0])
            if game_col and play_col else None,
        "duplicate_game_play_rows":int(frame.duplicated([game_col,play_col]).sum())
            if game_col and play_col else None,
        "null_fraction":{
            c:float(frame[c].isna().mean())
            for c in columns
            if any(token in c.lower() for token in ("offense","route","personnel","formation","player"))
        },
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--season",type=int,action="append",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    audits=[]
    failures=[]
    for season in args.season:
        try:
            frame=_pandas(nfl.load_participation([season]))
            audits.append(summarize(frame,season))
        except Exception as exc:
            failures.append({
                "season":int(season),
                "error_type":type(exc).__name__,
                "error":str(exc)[:500],
            })
    result={
        "contract_version":CONTRACT_VERSION,
        "research_only":True,
        "production_authorized":False,
        "audits":audits,
        "failures":failures,
        "source_latency_boundary":{
            "pre_2023":"NFL NGS via nflverse historical participation",
            "2023_plus":"FTN via nflverse; documented as released after all postseason games complete",
            "qualified_as_live_2026_route_feed":False,
        },
        "route_semantics_boundary":(
            "No field is called an actual route until its documented semantics establish that. "
            "On-field participation on a dropback is a participation proxy, not automatically a route."
        ),
        "game_outcomes_used":0,
        "completed_2026_outcomes_used":0,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if audits else 2


if __name__=="__main__":
    raise SystemExit(main())

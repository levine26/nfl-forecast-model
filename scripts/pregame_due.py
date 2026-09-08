from __future__ import annotations

"""Cheap DST-safe gate for FINAL forecast refreshes."""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def kickoff_utc(gameday: str, gametime: str) -> datetime:
    local=datetime.strptime(f"{gameday[:10]} {gametime[:5]}","%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--feed",default="outputs/this_week.csv"); ap.add_argument("--min-minutes",type=int,default=45); ap.add_argument("--max-minutes",type=int,default=165); args=ap.parse_args()
    now=datetime.now(timezone.utc); path=Path(args.feed); due=[]
    if path.exists():
        with path.open(newline="",encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try: ko=kickoff_utc(row.get("gameday",""),row.get("gametime",""))
                except Exception: continue
                mins=(ko-now).total_seconds()/60
                if args.min_minutes<=mins<=args.max_minutes: due.append((row.get("game_id") or f"{row.get('away_team')}@{row.get('home_team')}",mins))
    print("due=true" if due else "due=false")
    for gid,mins in due: print(f"{gid}: {mins:.0f} minutes to kickoff")


if __name__=="__main__": main()

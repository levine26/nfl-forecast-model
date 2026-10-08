from __future__ import annotations

"""Cheap DST-safe gate for FINAL forecast refreshes.

The gate is only an optimization. write_outputs is the authority that creates
immutable locks within the T-120 window, including legitimate late locks.
"""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


OFFICIAL_LOCK_STATUSES = {"LOCKED", "RECOVERED_MISSED_LOCK"}


def kickoff_utc(gameday: str, gametime: str) -> datetime:
    local = datetime.strptime(
        f"{gameday[:10]} {gametime[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def locked_game_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not {"game_id", "lock_status"}.issubset(reader.fieldnames):
            raise ValueError(f"Malformed official prediction history: {path}")
        return {
            row["game_id"]
            for row in reader
            if row.get("game_id") and row.get("lock_status") in OFFICIAL_LOCK_STATUSES
        }


def due_games(
    feed: Path,
    history: Path,
    now_utc: datetime,
    min_minutes: float = 0,
    max_minutes: float = 165,
) -> list[tuple[str, float]]:
    """Return unlocked games eligible for a pregame model refresh.

    The final model can begin before T-120 to finish within the window, and
    still run up to kickoff if delayed. It must never fabricate a prior lock.
    """
    locked = locked_game_ids(history)
    if not feed.exists():
        return []
    due: list[tuple[str, float]] = []
    with feed.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            gid = row.get("game_id") or f"{row.get('away_team')}@{row.get('home_team')}"
            if gid in locked:
                continue
            try:
                kickoff = kickoff_utc(row.get("gameday", ""), row.get("gametime", ""))
            except (TypeError, ValueError):
                continue
            minutes = (kickoff - now_utc).total_seconds() / 60
            if 0.0 < minutes and min_minutes <= minutes <= max_minutes:
                due.append((gid, minutes))
    return due


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default="outputs/this_week.csv")
    ap.add_argument("--history", default="outputs/prediction_history.csv")
    ap.add_argument("--min-minutes", type=float, default=0)
    ap.add_argument("--max-minutes", type=float, default=165)
    args = ap.parse_args()
    due = due_games(
        Path(args.feed),
        Path(args.history),
        datetime.now(timezone.utc),
        args.min_minutes,
        args.max_minutes,
    )
    print("due=true" if due else "due=false")
    for gid, minutes in due:
        print(f"{gid}: {minutes:.0f} minutes to kickoff")


if __name__ == "__main__":
    main()

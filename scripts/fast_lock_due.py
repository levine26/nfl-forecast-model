from __future__ import annotations

"""Dependency-free T-120 eligibility check for a fast immutable lock runner."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from scripts.pregame_due import due_games


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--history", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    if not args.feed.exists() or not args.history.exists():
        raise SystemExit("Canonical forecast or official history missing; refusing silent lock check")
    games = due_games(args.feed, args.history, datetime.now(timezone.utc), 0.0, 120.0)
    due = bool(games)
    print(f"due={str(due).lower()}")
    for gid, minutes in games:
        print(f"{gid}: {minutes:.2f} minutes to kickoff; eligible for immutable snapshot")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"due={str(due).lower()}\n")


if __name__ == "__main__":
    main()

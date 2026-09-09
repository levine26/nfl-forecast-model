from __future__ import annotations

"""CLI for the fail-closed pregame lock publication postcondition."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nfl_forecast.lock_verify import verify_pregame_locks
from nfl_forecast.publish import LOCK_WINDOW_MINUTES


def _as_utc(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="outputs/this_week.csv")
    parser.add_argument("--history", default="outputs/prediction_history.csv")
    parser.add_argument("--now-utc", default=None, help="ISO-8601 UTC timestamp; defaults to current time")
    parser.add_argument("--lock-window-minutes", type=float, default=LOCK_WINDOW_MINUTES)
    args = parser.parse_args()

    feed_path = Path(args.feed)
    history_path = Path(args.history)
    if not feed_path.exists():
        raise SystemExit(f"Missing current forecast feed: {feed_path}")
    current = pd.read_csv(feed_path)
    official = pd.read_csv(history_path) if history_path.exists() else pd.DataFrame()
    now_utc = _as_utc(args.now_utc)
    eligible = verify_pregame_locks(current, official, now_utc, args.lock_window_minutes)
    if eligible:
        print("verified locked games:", ", ".join(eligible))
    else:
        print("no games currently inside the official T-120 lock window")


if __name__ == "__main__":
    main()

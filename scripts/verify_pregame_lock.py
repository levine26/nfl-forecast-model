from __future__ import annotations

"""Fail closed if a pregame FINAL run finishes inside T-120 without a lock.

This is a publication postcondition, not a forecasting rule. ``publish.write_outputs``
remains the only code that creates official locks. This verifier only proves that
an eligible game has exactly one coherent immutable row before the workflow is
allowed to publish successfully.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nfl_forecast.publish import LOCK_WINDOW_MINUTES, kickoff_utc


def _as_utc(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def verify_pregame_locks(
    current: pd.DataFrame,
    official: pd.DataFrame,
    now_utc: datetime,
    lock_window_minutes: float = LOCK_WINDOW_MINUTES,
) -> list[str]:
    """Return eligible game ids after validating their official lock rows."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    failures: list[str] = []
    eligible: list[str] = []

    if not official.empty and "game_id" in official.columns:
        counts = official["game_id"].astype(str).value_counts()
        duplicates = sorted(counts[counts > 1].index.tolist())
        if duplicates:
            failures.append(f"duplicate official game ids: {duplicates}")

    for _, row in current.iterrows():
        gid = str(row.get("game_id") or "")
        if not gid:
            continue
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        minutes = (kickoff - now_utc).total_seconds() / 60.0
        if not (0.0 < minutes <= lock_window_minutes):
            continue
        eligible.append(gid)

        if official.empty or "game_id" not in official.columns:
            failures.append(f"{gid}: no official history exists at T-{minutes:.1f}")
            continue
        match = official[official["game_id"].astype(str).eq(gid)]
        if len(match) != 1:
            failures.append(f"{gid}: expected exactly one official row at T-{minutes:.1f}, found {len(match)}")
            continue
        locked = match.iloc[0]
        if str(locked.get("lock_status")) != "LOCKED":
            failures.append(f"{gid}: official row is not LOCKED")
        if pd.isna(locked.get("final_home_prob")) or not str(locked.get("pick") or "").strip():
            failures.append(f"{gid}: locked probability/pick is missing")
        try:
            lock_time = _as_utc(str(locked.get("lock_timestamp_utc")))
            lock_minutes = (kickoff - lock_time).total_seconds() / 60.0
            if not (0.0 < lock_minutes <= lock_window_minutes):
                failures.append(f"{gid}: stored lock time is outside T-120 ({lock_minutes:.1f} minutes)")
        except Exception as exc:
            failures.append(f"{gid}: invalid lock timestamp ({exc})")

    if failures:
        raise RuntimeError("Pregame lock postcondition failed: " + "; ".join(failures))
    return eligible


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

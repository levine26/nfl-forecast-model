from __future__ import annotations

"""Read-only freshness gate for the independent versioned official lock worker.

When the latest *published* frozen F-ST snapshot is too old to be eligible,
request the existing market refresh before attempting a lock. This script
never recalculates numbers, changes existing locks, accepts a stale snapshot,
or supplies research-candidate inputs to production.
"""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.pregame_due import kickoff_utc
from nfl_forecast.lock_policy import official_lock_target_minutes

MAX_AGE_MINUTES = 90.0
LOCK_WINDOW_MINUTES = 120.0


class LockPreparationError(ValueError):
    """The canonical inputs cannot safely select a refresh path."""


def _timestamp(raw: Any) -> datetime:
    try:
        stamp = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise LockPreparationError(f"Invalid forecast timestamp: {raw!r}") from exc
    if stamp.tzinfo is None:
        raise LockPreparationError(f"Naive forecast timestamp: {raw!r}")
    return stamp.astimezone(timezone.utc)


def stale_due_games(
    current: list[dict[str, Any]],
    history: list[dict[str, Any]],
    *,
    now_utc: datetime,
    max_age_minutes: float = MAX_AGE_MINUTES,
) -> list[str]:
    """Identify genuinely due, unlocked games whose canonical cache aged out."""
    if now_utc.tzinfo is None:
        raise LockPreparationError("Current time must be timezone-aware")
    if not current:
        raise LockPreparationError("Empty current canonical slate")
    if max_age_minutes <= 0:
        raise LockPreparationError("Invalid maximum cache age")
    now = now_utc.astimezone(timezone.utc)

    ids = [str(row.get("game_id") or "") for row in current]
    if not all(ids) or len(set(ids)) != len(ids):
        raise LockPreparationError("Missing/duplicate canonical game IDs")
    locked_ids = [str(row.get("game_id") or "") for row in history]
    if not all(locked_ids) or len(set(locked_ids)) != len(locked_ids):
        raise LockPreparationError("Missing/duplicate historic game IDs")
    locked = set(locked_ids)

    stale: list[str] = []
    for row in current:
        gid = str(row["game_id"])
        if gid in locked:
            continue
        try:
            kickoff = kickoff_utc(str(row["gameday"]), str(row["gametime"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise LockPreparationError(f"{gid}: invalid kickoff") from exc
        minutes_to_kickoff = (kickoff - now).total_seconds() / 60.0
        if not 0.0 < minutes_to_kickoff <= official_lock_target_minutes(row):
            continue

        generated = _timestamp(row.get("prediction_timestamp_utc"))
        age_minutes = (now - generated).total_seconds() / 60.0
        if age_minutes < -0.1:
            raise LockPreparationError(
                f"{gid}: canonical timestamp is in the future ({age_minutes:.2f} minutes)"
            )
        if age_minutes > max_age_minutes:
            stale.append(gid)
    return stale


def _rows(path: Path, *, allow_empty: bool = False) -> list[dict[str, str]]:
    if not path.is_file():
        raise LockPreparationError(f"Missing canonical file: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "game_id" not in reader.fieldnames:
            raise LockPreparationError(f"Malformed canonical CSV: {path}")
        rows = list(reader)
    if not rows and not allow_empty:
        raise LockPreparationError(f"Empty canonical CSV: {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    try:
        stale = stale_due_games(
            _rows(args.output_dir / "this_week.csv"),
            _rows(args.output_dir / "prediction_history.csv", allow_empty=True),
            now_utc=datetime.now(timezone.utc),
        )
    except LockPreparationError as exc:
        parser.exit(1, f"FAIL CLOSED: official-lock freshness preflight: {exc}\n")
    print("action=refresh" if stale else "action=lock")
    if stale:
        print("Stale canonical snapshots for due unlocked games: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

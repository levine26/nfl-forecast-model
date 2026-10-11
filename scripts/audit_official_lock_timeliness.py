from __future__ import annotations

from nfl_forecast.official_lock_policy import official_lock_policy_name, official_lock_target_minutes

"""Read-only official lock timeliness receipt; no predictions or locks are mutated."""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


IDENTITY = "F-ST-01-FROZEN-2026"
TARGET_MINUTES = 120.0
ALLOWED_LATENESS_MINUTES = 10.0


def _utc(value: object) -> datetime:
    stamp = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp must be timezone aware")
    return stamp.astimezone(timezone.utc)


def audit_history(rows: list[dict[str, Any]], *, season: int | None = None, week: int | None = None) -> dict[str, Any]:
    """Classify each immutable lock against the deadline in effect for that game."""
    reviewed = []
    seen: set[str] = set()
    for row in rows:
        if str(row.get("lock_status")) != "LOCKED":
            continue
        if season is not None and str(row.get("season")) != str(season):
            continue
        if week is not None and str(row.get("week")) != str(week):
            continue
        gid = str(row.get("game_id") or "")
        if not gid or gid in seen:
            raise ValueError(f"missing/duplicate official lock game ID: {gid}")
        seen.add(gid)
        try:
            kickoff = _utc(row.get("kickoff_utc"))
            actual = _utc(row.get("lock_timestamp_utc"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{gid}: malformed official lock time: {exc}") from exc
        minutes = (kickoff - actual).total_seconds() / 60.0
        # Older pre-policy receipts and synthetic tests may not carry a
        # gameday field; infer its Eastern schedule date from the immutable
        # kickoff timestamp, not from the current date or run time.
        scheduled_day = (row.get('gameday') or kickoff.astimezone(ZoneInfo('America/New_York')).date())
        target_minutes = official_lock_target_minutes(scheduled_day)
        delay = target_minutes - minutes
        classification = (
            "premature" if delay < -0.1 else
            "on_time" if delay <= ALLOWED_LATENESS_MINUTES else
            "late" if minutes > 0 else "at_or_after_kickoff"
        )
        reviewed.append({
            "game_id": gid,
            "scheduled_lock_utc": (kickoff-timedelta(minutes=target_minutes)).isoformat(),
            "target_minutes_before_kickoff": target_minutes,
            "lock_policy": official_lock_policy_name(scheduled_day), 
            "actual_lock_utc": actual.isoformat(),
            "minutes_before_kickoff": round(minutes, 4),
            "minutes_late_vs_target": round(delay, 4),
            "minutes_late_vs_t120": round(delay, 4) if target_minutes == TARGET_MINUTES else None,
            "classification": classification,
        })
    groups = {state: sum(x["classification"] == state for x in reviewed)
              for state in ("on_time", "late", "at_or_after_kickoff", "premature")}
    return {
        "forecast_path_identity": IDENTITY,
        "official_lock_target_minutes": (
            reviewed[0]["target_minutes_before_kickoff"] if reviewed and
            len({x["target_minutes_before_kickoff"] for x in reviewed}) == 1 else None
        ),
        "supported_lock_targets_minutes": [60.0, 120.0],
        "allowed_timing_lateness_minutes": ALLOWED_LATENESS_MINUTES,
        "season": season,
        "week": week,
        "locked_count": len(reviewed),
        "counts": groups,
        "games": reviewed,
        "all_locks_on_time": len(reviewed) > 0 and groups["on_time"] == len(reviewed),
        "warning": "Historical late receipts are preserved as originally recorded. This diagnostic never creates or backdates predictions.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--history", type=Path, default=Path("outputs/prediction_history.csv"))
    p.add_argument("--output", type=Path, default=Path("outputs/official_lock_timeliness.json"))
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--week", type=int)
    args = p.parse_args()
    with args.history.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    report = audit_history(rows, season=args.season, week=args.week)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for entry in report["games"]:
        if entry["classification"] != "on_time":
            print(f"::warning title=Official lock timing::{entry['game_id']}: {entry['classification']} ({entry['minutes_late_vs_target']:.1f} minutes after T-{entry['target_minutes_before_kickoff']:g})")
    print(f"Official per-game deadline audit: {report['counts']} -> {args.output}")


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Create and preserve the Sunday Signal weekend editorial roster.

Production forecast outputs legitimately contract as games kick off. Editorial publication
must not use those contracting files as its roster authority. This helper defines the
weekend slate as the active NFL week's Saturday/Sunday/Monday games, using the union of
current live rows and immutable same-week locks. Once the weekend boundary is reached,
the roster is frozen for that season/week and survives later output contraction.
"""

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _frame_identity(frame: pd.DataFrame) -> tuple[int, int] | None:
    if frame.empty:
        return None
    if "season" not in frame.columns or "week" not in frame.columns:
        raise RuntimeError("forecast source is missing season/week")
    identities = {
        (int(season), int(week))
        for season, week in zip(frame["season"], frame["week"])
        if not pd.isna(season) and not pd.isna(week)
    }
    if len(identities) != 1:
        raise RuntimeError(f"forecast source must identify exactly one season/week; found {sorted(identities)}")
    return next(iter(identities))


def _existing_identity(payload: dict) -> tuple[int, int] | None:
    season = payload.get("season")
    week = payload.get("week")
    if season is None or week is None:
        return None
    return int(season), int(week)


def _weekend_start(rows: pd.DataFrame, tz: ZoneInfo) -> datetime:
    if rows.empty or "gameday" not in rows.columns:
        raise RuntimeError("cannot determine weekend boundary without gameday rows")
    parsed_dates = [date.fromisoformat(str(value)) for value in rows["gameday"] if str(value)]
    if not parsed_dates:
        raise RuntimeError("cannot determine weekend boundary from empty gameday values")

    sunday_counts = Counter(d for d in parsed_dates if d.weekday() == 6)
    if sunday_counts:
        sunday = max(sunday_counts, key=lambda d: (sunday_counts[d], d))
    else:
        counts = Counter(parsed_dates)
        primary = max(counts, key=lambda d: (counts[d], d))
        sunday = primary + timedelta(days=(6 - primary.weekday()) % 7)

    saturday = sunday - timedelta(days=1)
    return datetime.combine(saturday, time.min, tzinfo=tz)


def build_roster(
    current: pd.DataFrame,
    official: pd.DataFrame,
    existing: dict,
    *,
    now_utc: datetime,
    timezone_name: str = "America/Los_Angeles",
) -> dict:
    current_identity = _frame_identity(current)
    existing_identity = _existing_identity(existing)

    if current_identity is not None:
        season, week = current_identity
    elif existing_identity is not None:
        season, week = existing_identity
    else:
        official_identity = _frame_identity(official)
        if official_identity is None:
            raise RuntimeError("cannot identify active season/week")
        season, week = official_identity

    if existing_identity == (season, week) and bool(existing.get("frozen")):
        game_ids = [str(gid) for gid in existing.get("game_ids") or []]
        if not game_ids:
            raise RuntimeError("frozen editorial roster contains no game IDs")
        return existing

    current_week = current.copy()
    if not current_week.empty:
        current_week = current_week[
            (current_week["season"].astype(int) == season)
            & (current_week["week"].astype(int) == week)
        ]

    official_week = official.copy()
    if not official_week.empty:
        if "lock_status" in official_week.columns:
            official_week = official_week[
                official_week["lock_status"].fillna("").astype(str).str.upper().eq("LOCKED")
            ]
        official_week = official_week[
            (official_week["season"].astype(int) == season)
            & (official_week["week"].astype(int) == week)
        ]

    candidates = pd.concat([current_week, official_week], ignore_index=True, sort=False)
    if candidates.empty:
        raise RuntimeError("no current or immutable rows are available for the active week")
    if "game_id" not in candidates.columns or "gameday" not in candidates.columns:
        raise RuntimeError("candidate editorial rows are missing game_id/gameday")

    candidates = candidates.drop_duplicates(subset=["game_id"], keep="first")
    tz = ZoneInfo(timezone_name)
    weekend_start_local = _weekend_start(candidates, tz)
    weekend_start_date = weekend_start_local.date()

    weekend = candidates[
        candidates["gameday"].astype(str).map(lambda value: date.fromisoformat(value) >= weekend_start_date)
    ].copy()
    if weekend.empty:
        raise RuntimeError("derived weekend editorial roster is empty")

    weekend["_gameday"] = weekend["gameday"].astype(str)
    weekend["_gametime"] = weekend.get("gametime", pd.Series("", index=weekend.index)).fillna("").astype(str)
    weekend["_game_id"] = weekend["game_id"].astype(str)
    weekend = weekend.sort_values(["_gameday", "_gametime", "_game_id"])
    game_ids = weekend["_game_id"].tolist()
    if len(game_ids) != len(set(game_ids)):
        raise RuntimeError("derived weekend editorial roster contains duplicate game IDs")

    frozen = now_utc.astimezone(tz) >= weekend_start_local
    return {
        "schema_version": 1,
        "season": season,
        "week": week,
        "timezone": timezone_name,
        "weekend_start_local": weekend_start_local.isoformat(),
        "frozen": frozen,
        "generated_utc": now_utc.astimezone(timezone.utc).isoformat(),
        "game_ids": game_ids,
        "policy": (
            "Weekend editorial roster is Saturday/Sunday/Monday for the active NFL week, "
            "derived from current rows plus immutable same-week locks and frozen once the "
            "weekend boundary is reached."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--official", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument("--roster", type=Path, default=Path("inputs/sunday_signal/editorial_slate_roster.json"))
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument("--now")
    args = parser.parse_args()

    current = pd.read_csv(args.current) if args.current.exists() else pd.DataFrame()
    official = pd.read_csv(args.official) if args.official.exists() else pd.DataFrame()
    existing = {}
    if args.roster.exists():
        existing = json.loads(args.roster.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise SystemExit("existing editorial roster must be a JSON object")

    payload = build_roster(
        current,
        official,
        existing,
        now_utc=_now(args.now),
        timezone_name=args.timezone,
    )
    args.roster.parent.mkdir(parents=True, exist_ok=True)
    args.roster.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"editorial weekend roster OK: season={payload['season']} week={payload['week']} "
        f"games={len(payload['game_ids'])} frozen={payload['frozen']} -> {args.roster}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

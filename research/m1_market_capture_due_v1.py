from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m1_market_contract_v1 import due_fixed_horizons, latest_prekick_due


def kickoff_utc(gameday: object, gametime: object) -> datetime:
    local = datetime.strptime(
        f"{str(gameday)[:10]} {str(gametime)[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def due_rows(feed: Path, now_utc: datetime) -> list[tuple[str, str]]:
    if not feed.exists():
        return []
    result: list[tuple[str, str]] = []
    with feed.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
            except Exception:
                continue
            game_id = str(row.get("game_id") or "unknown")
            for horizon in due_fixed_horizons(kickoff, now_utc):
                result.append((game_id, horizon["horizon"]))
            if latest_prekick_due(kickoff, now_utc):
                result.append((game_id, "LATEST_PREKICK"))
    return result


def preparation_rows(
    feed: Path, now_utc: datetime, lookahead_minutes: float
) -> list[tuple[str, str]]:
    """Return horizons due now or entering their frozen window during lookahead.

    This is only a workflow preparation signal.  The capture process continues to
    use the unmodified frozen due_* contract at request time, so lookahead can
    never admit an early or late market observation.
    """
    if lookahead_minutes <= 0:
        return due_rows(feed, now_utc)
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    # Sampling each minute is sufficient because the frozen windows are several
    # minutes wide; include the exact endpoint for non-integral lookaheads.
    whole_minutes = int(lookahead_minutes)
    offsets = [float(i) for i in range(whole_minutes + 1)]
    if not offsets or offsets[-1] < lookahead_minutes:
        offsets.append(lookahead_minutes)
    for offset in offsets:
        probe = now_utc + timedelta(minutes=offset)
        for row in due_rows(feed, probe):
            if row not in seen:
                seen.add(row)
                result.append(row)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lookahead-minutes",
        type=float,
        default=0.0,
        help="Preparation-only lookahead; does not change capture admissibility.",
    )
    args = parser.parse_args()
    feed = Path("outputs/this_week.csv")
    now = datetime.now(timezone.utc)
    rows = preparation_rows(feed, now, args.lookahead_minutes)
    print("due=true" if rows else "due=false")
    for game_id, horizon in rows:
        print(f"{game_id} {horizon}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HORIZONS = {"T-120m": 120, "T-60m": 60, "T-30m": 30}
TOLERANCE_MINUTES = 7.5


def kickoff_utc(gameday: str, gametime: str) -> datetime:
    local_time = datetime.strptime(
        f"{gameday[:10]} {gametime[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local_time.astimezone(timezone.utc)


def due_rows(feed: Path, now: datetime) -> list[tuple[str, str, float]]:
    result = []
    if not feed.exists():
        return result
    with feed.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                kickoff = kickoff_utc(row.get("gameday", ""), row.get("gametime", ""))
            except Exception:
                continue
            for label, minutes in HORIZONS.items():
                target = kickoff - timedelta(minutes=minutes)
                timing_error = (now - target).total_seconds() / 60.0
                if abs(timing_error) <= TOLERANCE_MINUTES:
                    result.append((row.get("game_id", "unknown"), label, timing_error))
    return result


def main() -> None:
    rows = due_rows(Path("outputs/this_week.csv"), datetime.now(timezone.utc))
    print("due=true" if rows else "due=false")
    for game_id, horizon, error in rows:
        print(f"{game_id} {horizon} timing_error_minutes={error:.2f}")


if __name__ == "__main__":
    main()

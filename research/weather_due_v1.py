from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


HORIZONS = {
    "T-72h": 72 * 60,
    "T-24h": 24 * 60,
    "T-6h": 6 * 60,
    "T-120m": 120,
    "T-60m": 60,
    "T-30m": 30,
}
TOLERANCE_MINUTES = 7.5


def kickoff_utc(gameday: str, gametime: str) -> datetime:
    local = datetime.strptime(f"{gameday[:10]} {gametime[:5]}", "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo("America/New_York")
    )
    return local.astimezone(timezone.utc)


def main() -> None:
    now = datetime.now(timezone.utc)
    path = Path("outputs/this_week.csv")
    due = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    kickoff = kickoff_utc(row.get("gameday", ""), row.get("gametime", ""))
                except Exception:
                    continue
                if kickoff <= now:
                    continue
                for label, minutes in HORIZONS.items():
                    target = kickoff - timedelta(minutes=minutes)
                    error = (now - target).total_seconds() / 60.0
                    if abs(error) <= TOLERANCE_MINUTES:
                        due.append((row.get("game_id", "unknown"), label, error))
    print("due=true" if due else "due=false")
    for game_id, horizon, error in due:
        print(f"{game_id} {horizon} timing_error_minutes={error:.2f}")


if __name__ == "__main__":
    main()

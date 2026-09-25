from __future__ import annotations

import csv
from datetime import datetime, timezone
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


def main() -> None:
    rows = due_rows(Path("outputs/this_week.csv"), datetime.now(timezone.utc))
    print("due=true" if rows else "due=false")
    for game_id, horizon in rows:
        print(f"{game_id} {horizon}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

MIN_MINUTES_TO_KICKOFF = 20.0
MAX_MINUTES_TO_KICKOFF = 100.0


def kickoff_utc(gameday: str, gametime: str) -> datetime:
    local = datetime.strptime(
        f"{gameday[:10]} {gametime[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def due_games(feed: Path, now: datetime) -> list[dict[str, object]]:
    if not feed.exists():
        return []
    current = now.astimezone(timezone.utc)
    rows: list[dict[str, object]] = []
    with feed.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                kickoff = kickoff_utc(row.get("gameday", ""), row.get("gametime", ""))
            except Exception:
                continue
            minutes = (kickoff - current).total_seconds() / 60.0
            if MIN_MINUTES_TO_KICKOFF <= minutes <= MAX_MINUTES_TO_KICKOFF:
                rows.append(
                    {
                        "game_id": row.get("game_id") or f"{row.get('away_team')}@{row.get('home_team')}",
                        "away_team": row.get("away_team"),
                        "home_team": row.get("home_team"),
                        "kickoff_utc": kickoff.isoformat(),
                        "minutes_to_kickoff": minutes,
                    }
                )
    rows.sort(key=lambda item: (float(item["minutes_to_kickoff"]), str(item["game_id"])))
    return rows


def main() -> None:
    games = due_games(Path("outputs/this_week.csv"), datetime.now(timezone.utc))
    print("due=true" if games else "due=false")
    for game in games:
        print(f"{game['game_id']}: {float(game['minutes_to_kickoff']):.2f} minutes to kickoff")


if __name__ == "__main__":
    main()

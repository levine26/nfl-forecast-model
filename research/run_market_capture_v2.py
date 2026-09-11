from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from research.market_capture_contract_v2 import (
    LEDGER_IDENTITY_COLUMNS,
    MIN_CONSENSUS_BOOKS,
    QUALIFYING_CLOSE_ROW_TYPE,
)
from research.market_capture_v2 import consensus_row, due_horizons, normalize_bookmaker


API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
EXPECTED_REQUEST_COST = 3  # h2h + spreads + totals in one region
MAX_EVENT_KICKOFF_DELTA_MINUTES = 30.0
TEAM_ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def kickoff_utc(gameday: object, gametime: object) -> datetime:
    local = datetime.strptime(
        f"{str(gameday)[:10]} {str(gametime)[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def _parse_provider_kickoff(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _match_event(
    events: list[dict],
    *,
    away_team: str,
    home_team: str,
    kickoff_timestamp_utc: datetime,
) -> dict | None:
    """Resolve one provider event by team identity and kickoff-time proximity.

    Team identity alone is insufficient because the endpoint can contain a later
    rematch. Missing provider kickoff times and ambiguous candidates fail closed.
    """
    target = kickoff_timestamp_utc.astimezone(timezone.utc)
    candidates: list[tuple[float, dict]] = []
    for event in events:
        matchup = (
            TEAM_ABBR.get(str(event.get("away_team"))),
            TEAM_ABBR.get(str(event.get("home_team"))),
        )
        if matchup != (away_team, home_team):
            continue
        provider_kickoff = _parse_provider_kickoff(event.get("commence_time"))
        if provider_kickoff is None:
            continue
        delta_minutes = abs((provider_kickoff - target).total_seconds()) / 60.0
        if delta_minutes <= MAX_EVENT_KICKOFF_DELTA_MINUTES:
            candidates.append((delta_minutes, event))
    if len(candidates) != 1:
        return None
    return candidates[0][1]


def _status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _header_int(response: requests.Response, name: str) -> int | None:
    value = response.headers.get(name)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _captured_pairs(path: Path) -> set[tuple[str, str]]:
    """Return only horizons closed by a qualifying multi-book consensus row.

    Book rows, one-book consensus rows, and legacy ledgers without a source_count
    field never close a horizon. They remain append-only evidence and the collector
    may retry while the preregistered timing window is still open.
    """
    if not path.exists():
        return set()
    try:
        frame = pd.read_csv(
            path,
            usecols=lambda c: c in {"game_id", "horizon", "row_type", "source_count"},
        )
    except Exception:
        return set()
    required = {"game_id", "horizon", "row_type", "source_count"}
    if not required.issubset(frame.columns):
        return set()
    source_count = pd.to_numeric(frame["source_count"], errors="coerce")
    frame = frame[
        frame["row_type"].eq(QUALIFYING_CLOSE_ROW_TYPE)
        & source_count.ge(MIN_CONSENSUS_BOOKS)
    ]
    return set(zip(frame["game_id"].astype(str), frame["horizon"].astype(str)))


def due_pairs(slate: pd.DataFrame, now_utc: datetime, captured: set[tuple[str, str]]) -> list[dict]:
    due: list[dict] = []
    for _, row in slate.iterrows():
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        for horizon in due_horizons(kickoff, now_utc):
            pair = (str(row.get("game_id")), horizon["horizon"])
            if pair in captured:
                continue
            due.append(
                {
                    "game_id": pair[0],
                    "home_team": str(row.get("home_team")),
                    "away_team": str(row.get("away_team")),
                    "kickoff_timestamp_utc": kickoff,
                    **horizon,
                }
            )
    return due


def capture(
    *,
    slate_path: str = "outputs/this_week.csv",
    ledger_path: str = "research_outputs/market_capture_v2/market_snapshots.csv",
    status_path: str = "research_outputs/market_capture_v2/status.json",
    quota_reserve: int = 50,
    now_utc: datetime | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    slate_file = Path(slate_path)
    ledger_file = Path(ledger_path)
    status_file = Path(status_path)

    if not slate_file.exists():
        return {"status": "skipped", "reason": "missing_slate", "external_request_made": False}

    slate = pd.read_csv(slate_file)
    due = due_pairs(slate, now, _captured_pairs(ledger_file))
    if not due:
        return {"status": "skipped", "reason": "no_uncaptured_horizon_due", "external_request_made": False}

    previous = _status(status_file)
    remaining = previous.get("quota_remaining")
    if remaining is not None and int(remaining) < int(quota_reserve) + EXPECTED_REQUEST_COST:
        return {
            "status": "skipped",
            "reason": "free_quota_reserve_reached",
            "quota_remaining": int(remaining),
            "required_credits": EXPECTED_REQUEST_COST,
            "external_request_made": False,
        }

    api_key = os.getenv("THE_ODDS_API_KEY", "").strip()
    if not api_key:
        return {"status": "skipped", "reason": "missing_api_key", "external_request_made": False}

    response = requests.get(
        API_URL,
        params={
            "apiKey": api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
        timeout=20,
    )
    response.raise_for_status()
    events = response.json()
    if not isinstance(events, list):
        raise RuntimeError("The Odds API response must be a list of events")

    rows: list[dict] = []
    missed: list[str] = []
    for item in due:
        event = _match_event(
            events,
            away_team=item["away_team"],
            home_team=item["home_team"],
            kickoff_timestamp_utc=item["kickoff_timestamp_utc"],
        )
        if not event:
            missed.append(f"{item['game_id']}:{item['horizon']}:event_identity_unresolved")
            continue
        book_rows = []
        for bookmaker in event.get("bookmakers", []):
            row = normalize_bookmaker(
                event=event,
                bookmaker=bookmaker,
                game_id=item["game_id"],
                home_team=item["home_team"],
                away_team=item["away_team"],
                horizon=item["horizon"],
                target_timestamp_utc=item["target_timestamp_utc"],
                request_timestamp_utc=now,
                kickoff_timestamp_utc=item["kickoff_timestamp_utc"],
            )
            if row:
                book_rows.append(row)
        rows.extend(book_rows)
        consensus = consensus_row(book_rows)
        if consensus and int(consensus.get("source_count", 0)) >= MIN_CONSENSUS_BOOKS:
            rows.append(consensus)
        else:
            missed.append(f"{item['game_id']}:{item['horizon']}:insufficient_books")

    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if ledger_file.exists():
        try:
            old = pd.read_csv(ledger_file)
            new = pd.concat([old, new], ignore_index=True, sort=False)
        except Exception:
            pass
    if not new.empty:
        # Append-only at the request-attempt level. A horizon may be retried after
        # an insufficient-book attempt; request_timestamp_utc therefore belongs in
        # identity. Once a qualified consensus exists, _captured_pairs closes it.
        new = new.drop_duplicates(list(LEDGER_IDENTITY_COLUMNS), keep="first")
        new.to_csv(ledger_file, index=False)

    result = {
        "status": "captured" if rows else "skipped",
        "reason": None if rows else "no_qualified_market_rows",
        "request_timestamp_utc": now.isoformat(),
        "due_pairs": len(due),
        "rows_added_this_request": len(rows),
        "missed": missed,
        "external_request_made": True,
        "quota_used": _header_int(response, "x-requests-used"),
        "quota_remaining": _header_int(response, "x-requests-remaining"),
        "quota_last_request_cost": _header_int(response, "x-requests-last"),
        "expected_request_cost": EXPECTED_REQUEST_COST,
        "quota_reserve": int(quota_reserve),
        "free_tier_only": True,
        "historical_endpoint_used": False,
        "research_only": True,
        "production_changed": False,
    }
    status_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", default="outputs/this_week.csv")
    parser.add_argument("--ledger", default="research_outputs/market_capture_v2/market_snapshots.csv")
    parser.add_argument("--status", default="research_outputs/market_capture_v2/status.json")
    parser.add_argument("--quota-reserve", type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(capture(
        slate_path=args.slate,
        ledger_path=args.ledger,
        status_path=args.status,
        quota_reserve=args.quota_reserve,
    ), indent=2))


if __name__ == "__main__":
    main()

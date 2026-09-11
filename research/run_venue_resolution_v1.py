from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import requests

from research.venue_resolution_v1 import (
    VenueResolutionError,
    choose_exact_candidate,
    normalize_name,
    resolve_game_venue,
    unresolved_game_venue,
)


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "LevLine-Sunday-Signal-research/1.0 (https://github.com/levine26/nfl-forecast-model)"


def _request_json(session: requests.Session, params: dict[str, Any]) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = session.get(WIKIDATA_API, params=params, headers=headers, timeout=20)
            if response.status_code in {429, 503} and attempt == 0:
                retry_after = response.headers.get("Retry-After", "2")
                try:
                    delay = min(30.0, max(1.0, float(retry_after)))
                except ValueError:
                    delay = 2.0
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.0)
                continue
    raise RuntimeError(f"Wikidata request failed: {last_error}")


def _search(session: requests.Session, stadium: str) -> list[dict[str, Any]]:
    payload = _request_json(session, {
        "action": "wbsearchentities",
        "search": stadium,
        "language": "en",
        "uselang": "en",
        "type": "item",
        "limit": 10,
        "format": "json",
        "maxlag": 5,
    })
    return list(payload.get("search") or [])


def _entity(session: requests.Session, qid: str) -> dict[str, Any]:
    payload = _request_json(session, {
        "action": "wbgetentities",
        "ids": qid,
        "props": "labels|claims",
        "languages": "en",
        "format": "json",
        "maxlag": 5,
    })
    entity = (payload.get("entities") or {}).get(qid)
    if not isinstance(entity, dict) or entity.get("missing") is not None:
        raise VenueResolutionError(f"Wikidata entity {qid} unavailable")
    return entity


def _upcoming_schedule(season: int, today: date) -> list[dict[str, Any]]:
    rows = nfl.load_schedules(seasons=season).to_dicts()
    upcoming = []
    for row in rows:
        raw = str(row.get("gameday") or "")[:10]
        try:
            gameday = date.fromisoformat(raw)
        except ValueError:
            continue
        if gameday >= today and row.get("game_id"):
            upcoming.append(row)
    return upcoming


def resolve_season(*, season: int, output_path: str, now_utc: datetime | None = None) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    schedule_retrieved = now.isoformat()
    schedule = _upcoming_schedule(season, now.date())
    session = requests.Session()
    cache: dict[str, tuple[list[dict[str, Any]], dict[str, Any] | None, str | None]] = {}
    receipts: list[dict[str, Any]] = []

    for row in schedule:
        stadium = str(row.get("stadium") or "").strip()
        key = normalize_name(stadium)
        if not key:
            receipts.append(unresolved_game_venue(
                schedule_row=row,
                reason="schedule stadium is missing",
                schedule_retrieved_at_utc=schedule_retrieved,
                attempted_at_utc=datetime.now(timezone.utc).isoformat(),
            ))
            continue

        if key not in cache:
            try:
                search_rows = _search(session, stadium)
                candidate = choose_exact_candidate(stadium, search_rows)
                entity = _entity(session, candidate.qid)
                cache[key] = (search_rows, entity, None)
            except (VenueResolutionError, RuntimeError) as exc:
                cache[key] = ([], None, str(exc))
            time.sleep(0.2)

        search_rows, entity, error = cache[key]
        attempted = datetime.now(timezone.utc).isoformat()
        if error or entity is None:
            receipts.append(unresolved_game_venue(
                schedule_row=row,
                reason=error or "Wikidata entity unavailable",
                schedule_retrieved_at_utc=schedule_retrieved,
                attempted_at_utc=attempted,
            ))
            continue
        try:
            receipts.append(resolve_game_venue(
                schedule_row=row,
                search_rows=search_rows,
                entity=entity,
                schedule_retrieved_at_utc=schedule_retrieved,
                wikidata_retrieved_at_utc=attempted,
            ))
        except VenueResolutionError as exc:
            receipts.append(unresolved_game_venue(
                schedule_row=row,
                reason=str(exc),
                schedule_retrieved_at_utc=schedule_retrieved,
                attempted_at_utc=attempted,
            ))

    resolved = sum(row.get("status") == "resolved" for row in receipts)
    unresolved = len(receipts) - resolved
    payload = {
        "schema_version": "levline-game-venue-registry-v1",
        "season": season,
        "generated_utc": now.isoformat(),
        "schedule_retrieved_at_utc": schedule_retrieved,
        "status": "complete" if receipts and unresolved == 0 else "partial" if resolved else "blocked",
        "resolved_games": resolved,
        "unresolved_games": unresolved,
        "research_only": True,
        "production_authorized": False,
        "games": receipts,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--output", default="research_outputs/venues/game_venues_2026.json")
    args = parser.parse_args()
    result = resolve_season(season=args.season, output_path=args.output)
    print(json.dumps({
        "status": result["status"],
        "resolved_games": result["resolved_games"],
        "unresolved_games": result["unresolved_games"],
        "production_authorized": result["production_authorized"],
    }, indent=2))


if __name__ == "__main__":
    main()

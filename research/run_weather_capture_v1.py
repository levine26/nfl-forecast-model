from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import nflreadpy as nfl
import requests

from research.weather_capture_v1 import (
    WeatherCaptureError,
    due_horizons,
    normalize_nws_forecast,
    unavailable_weather_snapshot,
)


NWS_POINTS = "https://api.weather.gov/points/{lat},{lon}"
USER_AGENT = "LevLine-Sunday-Signal-research/1.0 (https://github.com/levine26/nfl-forecast-model)"


def _request_json(session: requests.Session, url: str) -> dict[str, Any]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json, application/json",
        "Accept-Encoding": "gzip, deflate",
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = session.get(url, headers=headers, timeout=20)
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
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
    raise RuntimeError(f"NWS request failed for {url}: {last_error}")


def kickoff_utc(row: dict[str, Any]) -> datetime:
    local = datetime.strptime(
        f"{str(row.get('gameday'))[:10]} {str(row.get('gametime'))[:5]}",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def _load_venue_registry(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(row.get("game_id")): row
        for row in payload.get("games", [])
        if row.get("game_id")
    }


def _captured_pairs(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    pairs = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") == "captured" and row.get("game_id") and row.get("horizon"):
            pairs.add((str(row["game_id"]), str(row["horizon"])))
    return pairs


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _upcoming_schedule(season: int, now: datetime) -> list[dict[str, Any]]:
    rows = nfl.load_schedules(seasons=season).to_dicts()
    upcoming = []
    for row in rows:
        try:
            kickoff = kickoff_utc(row)
        except Exception:
            continue
        if kickoff > now and row.get("game_id"):
            row = dict(row)
            row["_kickoff_utc"] = kickoff
            upcoming.append(row)
    return upcoming


def capture(
    *,
    season: int,
    venue_registry_path: str,
    ledger_path: str,
    status_path: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    venue_registry = _load_venue_registry(Path(venue_registry_path))
    ledger = Path(ledger_path)
    captured = _captured_pairs(ledger)
    due = []
    for row in _upcoming_schedule(season, now):
        for horizon in due_horizons(row["_kickoff_utc"], now):
            pair = (str(row["game_id"]), str(horizon["horizon"]))
            if pair not in captured:
                due.append((row, horizon))

    if not due:
        result = {
            "status": "skipped",
            "reason": "no_uncaptured_weather_horizon_due",
            "request_timestamp_utc": now.isoformat(),
            "captured": 0,
            "unavailable": 0,
            "research_only": True,
            "production_changed": False,
        }
        Path(status_path).parent.mkdir(parents=True, exist_ok=True)
        Path(status_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    session = requests.Session()
    point_cache: dict[tuple[float, float], tuple[str, str]] = {}
    rows: list[dict[str, Any]] = []
    captured_count = 0
    unavailable_count = 0

    for schedule_row, horizon in due:
        game_id = str(schedule_row["game_id"])
        kickoff = schedule_row["_kickoff_utc"]
        venue = venue_registry.get(game_id)
        common = {
            "game_id": game_id,
            "kickoff_timestamp_utc": kickoff.isoformat(),
            "horizon": horizon["horizon"],
            "target_timestamp_utc": horizon["target_timestamp_utc"].isoformat(),
            "retrieval_timestamp_utc": now.isoformat(),
        }
        if not venue or venue.get("status") != "resolved":
            rows.append(unavailable_weather_snapshot(
                **common,
                reason="qualified game-specific venue receipt unavailable",
                venue_receipt=venue,
            ))
            unavailable_count += 1
            continue
        try:
            lat = float(venue["latitude"])
            lon = float(venue["longitude"])
            cache_key = (round(lat, 5), round(lon, 5))
            if cache_key not in point_cache:
                points_url = NWS_POINTS.format(lat=cache_key[0], lon=cache_key[1])
                point_payload = _request_json(session, points_url)
                hourly_url = str((point_payload.get("properties") or {}).get("forecastHourly") or "")
                if not hourly_url.startswith("https://api.weather.gov/"):
                    raise RuntimeError("NWS points response did not expose a qualified hourly forecast URL")
                point_cache[cache_key] = (points_url, hourly_url)
                time.sleep(0.15)
            points_url, hourly_url = point_cache[cache_key]
            hourly_payload = _request_json(session, hourly_url)
            rows.append(normalize_nws_forecast(
                **common,
                venue_receipt=venue,
                points_url=points_url,
                hourly_url=hourly_url,
                hourly_payload=hourly_payload,
            ))
            captured_count += 1
            time.sleep(0.15)
        except (RuntimeError, WeatherCaptureError, KeyError, TypeError, ValueError) as exc:
            rows.append(unavailable_weather_snapshot(
                **common,
                reason=str(exc),
                venue_receipt=venue,
            ))
            unavailable_count += 1

    _append_jsonl(ledger, rows)
    result = {
        "status": "captured" if captured_count else "unavailable",
        "request_timestamp_utc": now.isoformat(),
        "due_game_horizons": len(due),
        "captured": captured_count,
        "unavailable": unavailable_count,
        "research_only": True,
        "production_changed": False,
    }
    status = Path(status_path)
    status.parent.mkdir(parents=True, exist_ok=True)
    status.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--venues", default="research_outputs/venues/game_venues_2026.json")
    parser.add_argument("--ledger", default="research_outputs/weather/weather_snapshots.jsonl")
    parser.add_argument("--status", default="research_outputs/weather/status.json")
    args = parser.parse_args()
    print(json.dumps(capture(
        season=args.season,
        venue_registry_path=args.venues,
        ledger_path=args.ledger,
        status_path=args.status,
    ), indent=2))


if __name__ == "__main__":
    main()

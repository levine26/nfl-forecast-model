from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import time
from typing import Any, Callable

import requests

from nfl_forecast.context import fetch_coaching_staff, utc_now


NEGATIVE_CACHE_TTL_SECONDS = 60 * 60
CURRENT_STAFF_TTL_SECONDS = 7 * 24 * 60 * 60
REQUEST_INTERVAL_SECONDS = 0.12
CURRENT_RETRY_DELAY_SECONDS = 0.4


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _age_seconds(entry: dict[str, Any] | None, now: datetime) -> float | None:
    if not entry or not entry.get("fetched_at"):
        return None
    try:
        fetched = datetime.fromisoformat(str(entry["fetched_at"]))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        return max(0.0, (now - fetched).total_seconds())
    except Exception:
        return None


def load_coaching_history(
    teams: list[str],
    season: int,
    cache_path: str | Path,
    lookback: int = 4,
    session=requests,
    *,
    negative_cache_ttl_seconds: float = NEGATIVE_CACHE_TTL_SECONDS,
    current_staff_ttl_seconds: float = CURRENT_STAFF_TTL_SECONDS,
    request_interval_seconds: float = REQUEST_INTERVAL_SECONDS,
    current_retry_delay_seconds: float = CURRENT_RETRY_DELAY_SECONDS,
    fetcher: Callable[..., tuple[dict[str, Any] | None, str]] | None = None,
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, Any]]:
    """Load coaching history without letting transient source failures poison the cache.

    Successful historical entries are immutable. Current-season successes are refreshed
    weekly. Negative entries are retried after a short TTL, including historical pages,
    because a prior request failure is not evidence that a season page does not exist.
    Current-season misses get one paced retry in the same run.
    """
    cache_path = Path(cache_path)
    cache: dict[str, Any] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    fetch = fetcher or fetch_coaching_staff
    now = datetime.now(timezone.utc)
    changed = False
    history: dict[str, dict[int, dict[str, Any]]] = {}
    pages_missing = 0
    refresh_attempts = 0
    negative_entries_retried = 0
    current_retry_recoveries = 0
    last_request_at: float | None = None

    def paced_fetch(team: str, year: int):
        nonlocal last_request_at, refresh_attempts
        if last_request_at is not None and request_interval_seconds > 0:
            elapsed = time.monotonic() - last_request_at
            if elapsed < request_interval_seconds:
                time.sleep(request_interval_seconds - elapsed)
        data, source_url = fetch(team, year, session=session)
        last_request_at = time.monotonic()
        refresh_attempts += 1
        return data, source_url

    for raw_team in sorted(set(teams)):
        team = _norm_team(raw_team)
        history[team] = {}
        for year in range(season, max(season - lookback - 1, 2019), -1):
            key = f"{team}:{year}"
            entry = cache.get(key)
            age = _age_seconds(entry, now)
            data = (entry or {}).get("data")

            refresh = entry is None or age is None
            if entry is not None and data is None and age is not None:
                refresh = age >= negative_cache_ttl_seconds
                if refresh:
                    negative_entries_retried += 1
            elif entry is not None and data is not None and year == season and age is not None:
                refresh = age >= current_staff_ttl_seconds

            if refresh:
                data, _ = paced_fetch(team, year)
                if data is None and year == season:
                    if current_retry_delay_seconds > 0:
                        time.sleep(current_retry_delay_seconds)
                    retry_data, _ = paced_fetch(team, year)
                    if retry_data is not None:
                        data = retry_data
                        current_retry_recoveries += 1
                cache[key] = {"fetched_at": utc_now(), "data": data}
                entry = cache[key]
                changed = True

            data = (entry or {}).get("data")
            if data:
                history[team][year] = data
            else:
                pages_missing += 1

    if changed:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")

    status = {
        "status": "healthy" if pages_missing < max(2, len(teams)) else "degraded",
        "as_of": utc_now(),
        "source": "Wikipedia season pages",
        "pages_missing": pages_missing,
        "refresh_attempts": refresh_attempts,
        "negative_entries_retried": negative_entries_retried,
        "current_retry_recoveries": current_retry_recoveries,
        "negative_cache_ttl_minutes": int(negative_cache_ttl_seconds / 60),
    }
    return history, status

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import time
from typing import Any, Callable
from urllib.parse import quote

from bs4 import BeautifulSoup
import requests

from nfl_forecast.context import TEAM_META, utc_now


NEGATIVE_CACHE_TTL_SECONDS = 60 * 60
CURRENT_STAFF_TTL_SECONDS = 7 * 24 * 60 * 60
REQUEST_INTERVAL_SECONDS = 0.12
CURRENT_RETRY_DELAY_SECONDS = 0.4
WIKIPEDIA_ROOT = "https://en.wikipedia.org/wiki/"
COACHING_CACHE_VERSION = 2


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _page_title(team: str, season: int) -> str | None:
    meta = TEAM_META.get(_norm_team(team))
    if not meta:
        return None
    return f"{season} {meta['name']} season"


def _clean_cell(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip(" ,")


def _label(text: str) -> str:
    text = re.sub(r"[^a-z ]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _valid_staff_name(value: str | None) -> bool:
    text = _clean_cell(str(value or ""))
    if not text:
        return False
    lowered = text.lower()
    if "=" in text or any(token in lowered for token in ("general_manager", "owner =", "president =")):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _extract_staff_table(soup: BeautifulSoup) -> dict[str, str | None]:
    """Fill coordinator roles from rendered season-page staff tables.

    Many NFL season-page infoboxes omit coordinators even though the rendered Staff
    table contains them. We intentionally parse only explicit role lines such as
    "Offensive coordinator – Name" rather than guessing from the surrounding prose.
    """
    result: dict[str, str | None] = {"head_coach": None, "off_coach": None, "def_coach": None}
    patterns = [
        ("head_coach", re.compile(r"^head coach\s*[-–—:]\s*(.+)$", re.I)),
        ("off_coach", re.compile(r"^offensive coordinator\s*[-–—:]\s*(.+)$", re.I)),
        ("def_coach", re.compile(r"^defensive coordinator\s*[-–—:]\s*(.+)$", re.I)),
    ]

    candidate_tables = []
    for table in soup.find_all("table"):
        text = _clean_cell(table.get_text(" ", strip=True))
        if not text:
            continue
        lower = text.lower()
        if "offensive coordinator" in lower or "defensive coordinator" in lower or " head coach " in f" {lower} ":
            candidate_tables.append(table)

    for table in candidate_tables:
        # Individual list items/cells preserve the role/name line better than the
        # table's concatenated text. Fall back to line-split table text if needed.
        chunks = []
        for node in table.find_all(["li", "td", "th"]):
            text = _clean_cell(node.get_text(" ", strip=True))
            if text and text not in chunks:
                chunks.append(text)
        chunks.extend(
            line for line in (_clean_cell(x) for x in table.get_text("\n", strip=True).splitlines())
            if line and line not in chunks
        )
        for chunk in chunks:
            for key, pattern in patterns:
                match = pattern.match(chunk)
                if not match:
                    continue
                value = _clean_cell(match.group(1))
                if _valid_staff_name(value) and result[key] is None:
                    result[key] = value
    return result


def fetch_coaching_staff(team: str, season: int, session=requests) -> tuple[dict[str, Any] | None, str]:
    """Read staff from rendered season pages, using explicit staff tables as fallback.

    The infobox is preferred when it contains clean values. Historical pages often
    omit coordinators there, so explicit rendered Staff-table role lines fill the
    missing fields. This remains a staff-identity source; tactical impact is derived
    separately from FTN/nflverse football data.
    """
    team = _norm_team(team)
    title = _page_title(team, season)
    if title is None:
        return None, WIKIPEDIA_ROOT
    source_url = WIKIPEDIA_ROOT + quote(title.replace(" ", "_"))
    try:
        r = session.get(
            source_url,
            timeout=20,
            headers={"User-Agent": "nfl-forecast-model/1.0 (public research project)"},
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
    except Exception:
        return None, source_url

    result: dict[str, Any] = {
        "team": team,
        "season": season,
        "source_url": source_url,
        "head_coach": None,
        "off_coach": None,
        "def_coach": None,
    }

    table = soup.select_one("table.infobox")
    if table is not None:
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th is None or td is None:
                continue
            label = _label(th.get_text(" ", strip=True))
            value = _clean_cell(td.get_text(" ", strip=True))
            if not _valid_staff_name(value):
                continue
            if label in {"coach", "head coach"} or label.endswith(" head coach"):
                result["head_coach"] = value
            elif label in {"off coach", "offensive coach", "offensive coordinator"}:
                result["off_coach"] = value
            elif label in {"def coach", "defensive coach", "defensive coordinator"}:
                result["def_coach"] = value

    table_staff = _extract_staff_table(soup)
    for key in ("head_coach", "off_coach", "def_coach"):
        if not _valid_staff_name(result.get(key)) and _valid_staff_name(table_staff.get(key)):
            result[key] = table_staff[key]

    if not any(result.get(k) for k in ("head_coach", "off_coach", "def_coach")):
        return None, source_url
    return result, source_url


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

    Successful historical entries are immutable *within the current parser version*.
    When parsing improves, successful older cache rows refresh once so previously
    omitted coordinator roles can be recovered. Current-season successes refresh weekly.
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
    parser_version_refreshes = 0
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
            elif entry is not None and data is not None:
                cached_version = int((entry or {}).get("parser_version") or 0)
                if cached_version < COACHING_CACHE_VERSION:
                    refresh = True
                    parser_version_refreshes += 1
                elif year == season and age is not None:
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
                cache[key] = {
                    "fetched_at": utc_now(),
                    "parser_version": COACHING_CACHE_VERSION,
                    "data": data,
                }
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
        "source": "Wikipedia season-page rendered infoboxes + explicit staff tables",
        "pages_missing": pages_missing,
        "refresh_attempts": refresh_attempts,
        "negative_entries_retried": negative_entries_retried,
        "current_retry_recoveries": current_retry_recoveries,
        "parser_version": COACHING_CACHE_VERSION,
        "parser_version_refreshes": parser_version_refreshes,
        "negative_cache_ttl_minutes": int(negative_cache_ttl_seconds / 60),
    }
    return history, status

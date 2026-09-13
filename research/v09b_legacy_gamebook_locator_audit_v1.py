from __future__ import annotations

"""Audit 2012-2016 official NFLGSIS Game Book locator coverage.

The archived nflgame schedule is used only as a discovery crosswalk for legacy gamekey.
Canonical game membership comes from nflverse schedules and label authority remains the
first-party NFLGSIS Game Book document.
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import nflreadpy as nfl
import requests

EXPECTED_GAMES = {2012: 256, 2013: 256, 2014: 256, 2015: 256, 2016: 256}
CROSSWALK_URL = "https://raw.githubusercontent.com/BurntSushi/nflgame/master/nflgame/schedule.json"

# nflgame preserves historical franchise abbreviations while nflverse normalizes several
# franchises to modern canonical abbreviations. This crosswalk is identity-only; it does
# not use outcomes, participation, or any game-day label information.
LEGACY_TEAM_ALIASES = {
    "JAC": "JAX",
    "SD": "LAC",
    "STL": "LA",
    "OAK": "LV",
}


def _canonical_team(value: object) -> str:
    team = str(value or "").strip().upper()
    return LEGACY_TEAM_ALIASES.get(team, team)


def legacy_gamebook_url(season: int, week: int, gamekey: str) -> str:
    return f"https://www.nflgsis.com/{season}/Reg/{int(week):02d}/{gamekey}/Gamebook.pdf"


def _canonical_games(season: int) -> list[dict[str, object]]:
    frame = nfl.load_schedules(seasons=[season])
    rows = frame.to_dicts() if hasattr(frame, "to_dicts") else frame.to_pandas().to_dict("records")
    games = [row for row in rows if str(row.get("game_type")) == "REG"]
    games.sort(key=lambda row: (int(row["week"]), str(row["game_id"])))
    if len(games) != EXPECTED_GAMES[season]:
        raise RuntimeError(f"canonical schedule count mismatch for {season}: {len(games)}")
    return games


def _crosswalk_games(payload: object) -> list[object]:
    """Return the archived schedule rows while failing closed on an unknown shape."""
    if isinstance(payload, dict):
        games = payload.get("games")
        if not isinstance(games, list):
            raise ValueError("legacy discovery crosswalk object is missing list-valued 'games'")
        return games
    if isinstance(payload, list):
        # Retain compatibility with any pinned historical mirror that stores the games
        # array directly, while making the currently observed top-level object explicit.
        return payload
    raise ValueError("legacy discovery crosswalk has unsupported JSON shape")


def load_discovery_crosswalk(
    session: requests.Session,
    timeout: float,
) -> dict[tuple[int, int, str, str], dict[str, object]]:
    response = session.get(CROSSWALK_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    out: dict[tuple[int, int, str, str], dict[str, object]] = {}
    for item in _crosswalk_games(payload):
        if not isinstance(item, list) or len(item) != 2 or not isinstance(item[1], dict):
            continue
        row = item[1]
        if str(row.get("season_type")) != "REG":
            continue
        try:
            year = int(row.get("year"))
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if year not in EXPECTED_GAMES:
            continue
        away = _canonical_team(row.get("away"))
        home = _canonical_team(row.get("home"))
        if not away or not home:
            continue
        key = (year, week, away, home)
        if key in out:
            raise RuntimeError(f"duplicate legacy discovery crosswalk key: {key}")
        out[key] = row
    return out


@dataclass(frozen=True)
class LegacyLocatorRow:
    season: int
    week: int
    game_id: str
    away_team: str
    home_team: str
    gamekey: str | None
    crosswalk_match: bool
    gamebook_url: str | None
    http_status: int | None
    content_type: str | None
    qualified_locator: bool
    error: str | None


def audit_season(
    season: int,
    *,
    timeout: float = 20.0,
    attempts: int = 3,
    delay_seconds: float = 0.05,
) -> dict[str, object]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"season must be one of {sorted(EXPECTED_GAMES)}")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; source-qualification)"})
    crosswalk = load_discovery_crosswalk(session, timeout)
    rows: list[LegacyLocatorRow] = []

    for game in _canonical_games(season):
        away = _canonical_team(game["away_team"])
        home = _canonical_team(game["home_team"])
        key = (season, int(game["week"]), away, home)
        match = crosswalk.get(key)
        raw_gamekey = None if match is None else match.get("gamekey")
        gamekey = None if raw_gamekey in (None, "") else str(raw_gamekey)
        url = None if not gamekey else legacy_gamebook_url(season, int(game["week"]), gamekey)
        status: int | None = None
        content_type: str | None = None
        error: str | None = None
        if match is None:
            error = "legacy discovery crosswalk missing canonical game"
        elif not gamekey:
            error = "legacy discovery crosswalk missing gamekey"
        else:
            last_exc: Exception | None = None
            for attempt in range(attempts):
                try:
                    response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                    status = response.status_code
                    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                    response.close()
                    if status >= 500 and attempt + 1 < attempts:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    break
                except requests.RequestException as exc:
                    last_exc = exc
                    if attempt + 1 < attempts:
                        time.sleep(0.5 * (attempt + 1))
            if status is None:
                error = f"request failed: {last_exc}"
            elif status != 200:
                error = f"Game Book HTTP {status}"
            elif content_type != "application/pdf":
                error = f"unexpected Game Book content type: {content_type!r}"

        qualified = error is None and status == 200 and content_type == "application/pdf"
        rows.append(
            LegacyLocatorRow(
                season=season,
                week=int(game["week"]),
                game_id=str(game["game_id"]),
                away_team=away,
                home_team=home,
                gamekey=gamekey,
                crosswalk_match=match is not None,
                gamebook_url=url,
                http_status=status,
                content_type=content_type,
                qualified_locator=qualified,
                error=error,
            )
        )
        if delay_seconds:
            time.sleep(delay_seconds)

    qualified_count = sum(row.qualified_locator for row in rows)
    crosswalk_count = sum(row.crosswalk_match for row in rows)
    return {
        "audit_version": 1,
        "season": season,
        "canonical_games": len(rows),
        "expected_games": EXPECTED_GAMES[season],
        "crosswalk_matches": crosswalk_count,
        "crosswalk_coverage_rate": crosswalk_count / len(rows),
        "qualified_gamebook_locators": qualified_count,
        "locator_coverage_rate": qualified_count / len(rows),
        "all_crosswalk_rows_qualified": crosswalk_count == EXPECTED_GAMES[season],
        "all_gamebook_locators_qualified": qualified_count == EXPECTED_GAMES[season],
        "discovery_crosswalk_is_label_authority": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "rows": [asdict(row) for row in rows],
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True, type=int, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, timeout=args.timeout, attempts=args.attempts, delay_seconds=args.delay_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2, sort_keys=True))
    if result["all_crosswalk_rows_qualified"] is not True or result["all_gamebook_locators_qualified"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

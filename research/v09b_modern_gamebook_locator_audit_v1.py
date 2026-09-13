from __future__ import annotations

"""Audit first-party NFL Game Book locator coverage for 2017-2021.

Research-only. This module does not parse player labels and does not fit a model.
It proves whether every canonical regular-season game can be mapped to exactly one
first-party Game Book document from an NFL-owned discovery surface.
"""

import argparse
import html as html_lib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import nflreadpy as nfl
import requests
from bs4 import BeautifulSoup

EXPECTED_GAMES = {2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272}
ALLOWED_DOCUMENT_HOSTS = {"static.www.nfl.com"}
ALLOWED_GAME_CENTER_HOSTS = {"www.nfl.com", "nfl.com"}
TEAM_SLUGS = {
    "ARI": "cardinals", "ATL": "falcons", "BAL": "ravens", "BUF": "bills",
    "CAR": "panthers", "CHI": "bears", "CIN": "bengals", "CLE": "browns",
    "DAL": "cowboys", "DEN": "broncos", "DET": "lions", "GB": "packers",
    "HOU": "texans", "IND": "colts", "JAX": "jaguars", "KC": "chiefs",
    "LAC": "chargers", "LA": "rams", "LV": "raiders", "MIA": "dolphins",
    "MIN": "vikings", "NE": "patriots", "NO": "saints", "NYG": "giants",
    "NYJ": "jets", "OAK": "raiders", "PHI": "eagles", "PIT": "steelers",
    "SEA": "seahawks", "SF": "49ers", "TB": "buccaneers", "TEN": "titans",
}


def team_slug(team: str, season: int) -> str:
    team = str(team).upper()
    if team == "WAS":
        return "redskins" if season <= 2019 else "football-team"
    if team not in TEAM_SLUGS:
        raise ValueError(f"unmapped team abbreviation: {team}")
    return TEAM_SLUGS[team]


def game_center_url(*, season: int, week: int, away_team: str, home_team: str) -> str:
    away = team_slug(away_team, season)
    home = team_slug(home_team, season)
    return f"https://www.nfl.com/games/{away}-at-{home}-{season}-reg-{int(week)}"


def week_schedule_url(*, season: int, week: int) -> str:
    return f"https://www.nfl.com/schedules/{season}/by-week/week-{int(week)}"


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def extract_game_center_links(
    html: str,
    *,
    schedule_url: str,
    season: int,
    week: int,
    away_team: str,
    home_team: str,
) -> list[str]:
    """Resolve exact historical Game Center URLs from an NFL week schedule page.

    Some historical NFL Game Center URLs carry opaque suffixes that cannot be derived
    from season/week/team identity. The first-party NFL schedule page is therefore an
    authorized locator-discovery surface; it is not label authority.
    """
    away = team_slug(away_team, season)
    home = team_slug(home_team, season)
    expected_path = f"/games/{away}-at-{home}-{season}-reg-{int(week)}"
    soup = BeautifulSoup(html, "html.parser")
    matches: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(schedule_url, str(anchor["href"]).strip())
        parsed = urlparse(href)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_GAME_CENTER_HOSTS:
            continue
        path = parsed.path.rstrip("/")
        if path == expected_path or path.startswith(expected_path + "-"):
            matches.append(href)
    return _dedupe(matches)


def _embedded_first_party_pdf_links(html: str) -> list[str]:
    """Extract explicit first-party Game Center PDF URLs from serialized page bytes.

    This is a fallback discovery surface only. It is used only when the rendered page
    exposes no visible Download Game Book anchor.
    """
    normalized = html_lib.unescape(html).replace("\\u002F", "/").replace("\\/", "/")
    pattern = re.compile(
        r"https://static\.www\.nfl\.com/[^\s\"'<>]+?\.pdf(?:\?[^\s\"'<>]*)?",
        flags=re.IGNORECASE,
    )
    return _dedupe(
        match.group(0)
        for match in pattern.finditer(normalized)
        if "/gamecenter/" in match.group(0).lower()
    )


def extract_gamebook_evidence(html: str, base_url: str) -> tuple[list[str], str]:
    """Resolve a Game Book with anchor-first, embedded-fallback precedence.

    The visible Download Game Book anchor is the authoritative locator surface whenever
    present. Serialized page state may contain other historical Game Center PDFs, so it
    must never be combined with a valid rendered anchor.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors: list[str] = []
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.stripped_strings).lower()
        if "download game book" not in text:
            continue
        anchors.append(urljoin(base_url, str(anchor["href"]).strip()))
    anchors = _dedupe(anchors)
    if anchors:
        return anchors, "download_anchor"

    embedded = _embedded_first_party_pdf_links(html)
    if embedded:
        return embedded, "embedded_first_party_pdf"
    return [], "none"


def extract_gamebook_links(html: str, base_url: str) -> list[str]:
    return extract_gamebook_evidence(html, base_url)[0]


def is_allowed_document_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_DOCUMENT_HOSTS


@dataclass(frozen=True)
class LocatorRow:
    season: int
    week: int
    game_id: str
    old_game_id: str | None
    away_team: str
    home_team: str
    guessed_game_center_url: str
    game_center_url: str
    game_center_resolution_method: str
    schedule_fallback_url: str | None
    schedule_fallback_status: int | None
    game_center_status: int | None
    gamebook_links_found: int
    gamebook_extraction_method: str
    gamebook_url: str | None
    gamebook_host_allowed: bool
    gamebook_status: int | None
    gamebook_content_type: str | None
    qualified_locator: bool
    error: str | None


def _request(session: requests.Session, url: str, *, timeout: float, attempts: int) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            if response.status_code >= 500 and attempt + 1 < attempts:
                response.close()
                time.sleep(0.5 * (attempt + 1))
                continue
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"request failed after {attempts} attempts: {url}: {last_error}")


def _canonical_games(season: int) -> list[dict[str, object]]:
    frame = nfl.load_schedules(seasons=[season])
    if hasattr(frame, "to_dicts"):
        rows = frame.to_dicts()
    else:
        rows = frame.to_pandas().to_dict("records")
    games = [row for row in rows if str(row.get("game_type")) == "REG"]
    games.sort(key=lambda row: (int(row["week"]), str(row["game_id"])))
    expected = EXPECTED_GAMES[season]
    if len(games) != expected:
        raise RuntimeError(f"canonical schedule count mismatch for {season}: {len(games)} != {expected}")
    return games


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
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    rows: list[LocatorRow] = []
    schedule_cache: dict[int, tuple[str, int, str]] = {}

    for game in _canonical_games(season):
        week = int(game["week"])
        away = str(game["away_team"])
        home = str(game["home_team"])
        guessed_center = game_center_url(season=season, week=week, away_team=away, home_team=home)
        center = guessed_center
        resolution_method = "deterministic_slug"
        schedule_fallback: str | None = None
        schedule_status: int | None = None
        center_status: int | None = None
        links: list[str] = []
        extraction_method = "none"
        book_status: int | None = None
        content_type: str | None = None
        book_url: str | None = None
        host_ok = False
        error: str | None = None
        try:
            response = _request(session, center, timeout=timeout, attempts=attempts)
            center_status = response.status_code
            center_html = response.text if response.ok else ""
            response.close()

            if center_status == 404:
                schedule_fallback = week_schedule_url(season=season, week=week)
                if week not in schedule_cache:
                    schedule_response = _request(
                        session, schedule_fallback, timeout=timeout, attempts=attempts
                    )
                    schedule_status = schedule_response.status_code
                    schedule_html = schedule_response.text if schedule_response.ok else ""
                    schedule_response.close()
                    schedule_cache[week] = (schedule_fallback, schedule_status, schedule_html)
                else:
                    schedule_fallback, schedule_status, schedule_html = schedule_cache[week]

                if schedule_status != 200:
                    error = f"week schedule HTTP {schedule_status} after game center HTTP 404"
                else:
                    center_candidates = extract_game_center_links(
                        schedule_html,
                        schedule_url=schedule_fallback,
                        season=season,
                        week=week,
                        away_team=away,
                        home_team=home,
                    )
                    if len(center_candidates) != 1:
                        error = (
                            "expected exactly one first-party Game Center fallback, "
                            f"found {len(center_candidates)}"
                        )
                    else:
                        center = center_candidates[0]
                        resolution_method = "first_party_week_schedule_fallback"
                        response = _request(session, center, timeout=timeout, attempts=attempts)
                        center_status = response.status_code
                        center_html = response.text if response.ok else ""
                        response.close()

            if error is None:
                if center_status != 200:
                    error = f"game center HTTP {center_status}"
                else:
                    links, extraction_method = extract_gamebook_evidence(center_html, center)
                    if len(links) != 1:
                        error = f"expected exactly one Game Book link, found {len(links)}"
                    else:
                        book_url = links[0]
                        host_ok = is_allowed_document_url(book_url)
                        if not host_ok:
                            error = f"non-first-party Game Book host: {urlparse(book_url).hostname}"
                        else:
                            book = _request(session, book_url, timeout=timeout, attempts=attempts)
                            book_status = book.status_code
                            content_type = (book.headers.get("content-type") or "").split(";")[0].strip().lower()
                            book.close()
                            if book_status != 200:
                                error = f"Game Book HTTP {book_status}"
                            elif content_type != "application/pdf":
                                error = f"unexpected Game Book content type: {content_type!r}"
        except Exception as exc:  # fail closed into row diagnostics
            error = f"{type(exc).__name__}: {exc}"

        qualified = bool(
            error is None
            and center_status == 200
            and len(links) == 1
            and book_url
            and host_ok
            and book_status == 200
            and content_type == "application/pdf"
        )
        rows.append(LocatorRow(
            season=season,
            week=week,
            game_id=str(game["game_id"]),
            old_game_id=None if game.get("old_game_id") is None else str(game.get("old_game_id")),
            away_team=away,
            home_team=home,
            guessed_game_center_url=guessed_center,
            game_center_url=center,
            game_center_resolution_method=resolution_method,
            schedule_fallback_url=schedule_fallback,
            schedule_fallback_status=schedule_status,
            game_center_status=center_status,
            gamebook_links_found=len(links),
            gamebook_extraction_method=extraction_method,
            gamebook_url=book_url,
            gamebook_host_allowed=host_ok,
            gamebook_status=book_status,
            gamebook_content_type=content_type,
            qualified_locator=qualified,
            error=error,
        ))
        if delay_seconds:
            time.sleep(delay_seconds)

    qualified_count = sum(row.qualified_locator for row in rows)
    fallback_count = sum(
        row.game_center_resolution_method == "first_party_week_schedule_fallback" for row in rows
    )
    embedded_count = sum("embedded_first_party_pdf" in row.gamebook_extraction_method for row in rows)
    result = {
        "audit_version": 2,
        "season": season,
        "canonical_games": len(rows),
        "expected_games": EXPECTED_GAMES[season],
        "qualified_gamebook_locators": qualified_count,
        "locator_coverage_rate": qualified_count / len(rows) if rows else 0.0,
        "first_party_schedule_fallbacks_used": fallback_count,
        "embedded_first_party_pdf_resolutions_used": embedded_count,
        "all_gamebook_locators_qualified": qualified_count == EXPECTED_GAMES[season],
        "week_schedule_is_label_authority": False,
        "game_center_is_label_authority": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "rows": [asdict(row) for row in rows],
    }
    return result


def write_result(result: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(
        args.season,
        timeout=args.timeout,
        attempts=args.attempts,
        delay_seconds=args.delay_seconds,
    )
    write_result(result, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2, sort_keys=True))
    if result["all_gamebook_locators_qualified"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Discovery-only inventory of historical first-party club game-day media surfaces.

For one season, this module starts from each club's official historical schedule page,
derives regular-season game-day pages, and inventories first-party media anchors such as
GAME RELEASE, ROSTER, DEPTH CHART, FLIP CARD, and GAME NOTES. Coverage rates are purely
descriptive. The module never downloads those media documents, constructs membership,
resolves identity, or fits a model.
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-GAME-DAY-MEDIA-SURFACE-DISCOVERY-V1"
STATIC_CLUB_HOST = "static.clubs.nfl.com"
MEDIA_CLASSES: dict[str, tuple[str, ...]] = {
    "game_release": ("GAME RELEASE",),
    "roster": ("ROSTER", "ROSTERS"),
    "depth_chart": ("DEPTH CHART", "DEPTH"),
    "flip_card": ("FLIP CARD",),
    "game_notes": ("GAME NOTES",),
}
STAGE_RE = re.compile(r"^(?:reg-)?week(?:[1-9]|1[0-8])$", re.I)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def team_hosts(domains: list[str]) -> set[str]:
    result: set[str] = set()
    for domain in domains:
        base = str(domain).strip().lower().removeprefix("www.")
        if not base:
            continue
        result.add(base)
        result.add(f"www.{base}")
    return result


def _canonical_https(url: str) -> str:
    parsed = urlparse(str(url))
    path = parsed.path or "/"
    return urlunparse(("https", (parsed.hostname or "").lower(), path, "", "", ""))


def canonical_regular_game_base(
    href: str,
    *,
    page_url: str,
    season: int,
    allowed_hosts: set[str],
) -> str | None:
    absolute = urljoin(page_url, str(href or "").strip())
    parsed = urlparse(absolute)
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in allowed_hosts:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    try:
        idx = parts.index("game-day")
    except ValueError:
        return None
    if len(parts) < idx + 4:
        return None
    if parts[idx + 1] != str(int(season)):
        return None
    stage = parts[idx + 2]
    if STAGE_RE.fullmatch(stage) is None:
        return None
    slug = parts[idx + 3]
    if not slug:
        return None
    path = "/" + "/".join(parts[: idx + 4]) + "/"
    return urlunparse(("https", (parsed.hostname or "").lower(), path, "", "", ""))


def extract_schedule_game_bases(
    html: str,
    *,
    page_url: str,
    season: int,
    allowed_hosts: set[str],
) -> list[str]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    values: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        base = canonical_regular_game_base(
            str(anchor.get("href") or ""),
            page_url=page_url,
            season=season,
            allowed_hosts=allowed_hosts,
        )
        if base is not None:
            values.add(base)
    return sorted(values)


def classify_media_anchor(text: str) -> list[str]:
    visible = normalize_text(text)
    classes: list[str] = []
    for media_class, markers in MEDIA_CLASSES.items():
        if any(marker in visible for marker in markers):
            classes.append(media_class)
    return classes


def extract_first_party_media_links(
    html: str,
    *,
    page_url: str,
    allowed_hosts: set[str],
) -> dict[str, list[dict[str, str]]]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    output: dict[str, list[dict[str, str]]] = {key: [] for key in MEDIA_CLASSES}
    seen: dict[str, set[tuple[str, str]]] = {key: set() for key in MEDIA_CLASSES}
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        classes = classify_media_anchor(text)
        if not classes:
            continue
        absolute = urljoin(page_url, str(anchor.get("href") or "").strip())
        parsed = urlparse(absolute)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() != "https":
            continue
        if host != STATIC_CLUB_HOST and host not in allowed_hosts:
            continue
        canonical = _canonical_https(absolute)
        for media_class in classes:
            key = (text, canonical)
            if key in seen[media_class]:
                continue
            seen[media_class].add(key)
            if len(output[media_class]) < 20:
                output[media_class].append({"text": text, "url": canonical, "host": host})
    return output


def _get(url: str, *, timeout: float) -> Any:
    return requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-game-day-media-discovery/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )


def inspect_schedule_attempt(
    *,
    team: str,
    season: int,
    domain: str,
    domains: list[str],
    timeout: float,
) -> dict[str, Any]:
    hosts = team_hosts(domains)
    base_domain = str(domain).strip().lower().removeprefix("www.")
    requested = f"https://www.{base_domain}/schedule/{int(season)}/"
    row: dict[str, Any] = {
        "team": team,
        "season": int(season),
        "domain": base_domain,
        "requested_url": requested,
        "final_url": None,
        "http_status": None,
        "final_host_allowed": False,
        "regular_game_day_bases": [],
        "regular_game_day_base_count": 0,
        "error": None,
    }
    try:
        response = _get(requested, timeout=timeout)
        row["http_status"] = int(response.status_code)
        row["final_url"] = str(response.url)
        parsed = urlparse(str(response.url))
        row["final_host_allowed"] = parsed.scheme.lower() == "https" and (parsed.hostname or "").lower() in hosts
        if not row["final_host_allowed"]:
            row["error"] = f"final redirect escaped team allowlist: {(parsed.hostname or '').lower()}"
            return row
        if int(response.status_code) >= 400:
            row["error"] = f"HTTP {response.status_code}"
            return row
        bases = extract_schedule_game_bases(
            response.text,
            page_url=str(response.url),
            season=season,
            allowed_hosts=hosts,
        )
        row["regular_game_day_bases"] = bases
        row["regular_game_day_base_count"] = len(bases)
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return row


def inspect_game_page(
    *,
    team: str,
    season: int,
    game_url: str,
    domains: list[str],
    timeout: float,
) -> dict[str, Any]:
    hosts = team_hosts(domains)
    row: dict[str, Any] = {
        "team": team,
        "season": int(season),
        "game_day_url": game_url,
        "final_url": None,
        "http_status": None,
        "final_host_allowed": False,
        "fetch_success": False,
        "error": None,
        "media_links": {key: [] for key in MEDIA_CLASSES},
        "media_class_present": {key: False for key in MEDIA_CLASSES},
    }
    try:
        response = _get(game_url, timeout=timeout)
        row["http_status"] = int(response.status_code)
        row["final_url"] = str(response.url)
        parsed = urlparse(str(response.url))
        row["final_host_allowed"] = parsed.scheme.lower() == "https" and (parsed.hostname or "").lower() in hosts
        if not row["final_host_allowed"]:
            row["error"] = f"final redirect escaped team allowlist: {(parsed.hostname or '').lower()}"
            return row
        if int(response.status_code) >= 400:
            row["error"] = f"HTTP {response.status_code}"
            return row
        links = extract_first_party_media_links(
            response.text,
            page_url=str(response.url),
            allowed_hosts=hosts,
        )
        row["fetch_success"] = True
        row["media_links"] = links
        row["media_class_present"] = {key: bool(values) for key, values in links.items()}
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return row


def audit_season(
    contract_path: Path,
    *,
    season: int,
    timeout: float,
    workers: int,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    if season not in [int(x) for x in contract["seasons"]]:
        raise ValueError(f"unsupported season: {season}")

    teams: dict[str, list[str]] = {str(k): list(v) for k, v in contract["teams"].items()}
    schedule_attempts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 32))) as pool:
        future_map = {}
        for team, domains in sorted(teams.items()):
            for domain in domains:
                fut = pool.submit(
                    inspect_schedule_attempt,
                    team=team,
                    season=season,
                    domain=domain,
                    domains=domains,
                    timeout=timeout,
                )
                future_map[fut] = (team, domain)
        for future in as_completed(future_map):
            schedule_attempts.append(future.result())
    schedule_attempts.sort(key=lambda x: (x["team"], x["domain"]))

    chosen_schedule_by_team: dict[str, dict[str, Any] | None] = {}
    for team in sorted(teams):
        candidates = [row for row in schedule_attempts if row["team"] == team]
        usable = [row for row in candidates if row["final_host_allowed"] is True and row["http_status"] is not None and int(row["http_status"]) < 400]
        usable.sort(key=lambda row: (-int(row["regular_game_day_base_count"]), str(row["requested_url"])))
        chosen_schedule_by_team[team] = usable[0] if usable else None

    team_schedule_rows: list[dict[str, Any]] = []
    game_tasks: list[tuple[str, str]] = []
    expected_per_team = 17 if season == 2021 else 16
    for team in sorted(teams):
        chosen = chosen_schedule_by_team[team]
        bases = list(chosen["regular_game_day_bases"]) if chosen else []
        team_schedule_rows.append(
            {
                "team": team,
                "season": season,
                "schedule_surface_available": chosen is not None,
                "chosen_schedule_url": chosen["final_url"] if chosen else None,
                "discovered_regular_game_day_pages": len(bases),
                "expected_regular_team_games": expected_per_team,
                "missing_expected_regular_team_games_diagnostic": max(0, expected_per_team - len(bases)),
                "extra_discovered_regular_game_pages_diagnostic": max(0, len(bases) - expected_per_team),
                "schedule_attempts": len([row for row in schedule_attempts if row["team"] == team]),
            }
        )
        for base in bases:
            game_tasks.append((team, base))

    game_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        future_map = {
            pool.submit(
                inspect_game_page,
                team=team,
                season=season,
                game_url=url,
                domains=teams[team],
                timeout=timeout,
            ): (team, url)
            for team, url in game_tasks
        }
        for future in as_completed(future_map):
            game_rows.append(future.result())
    game_rows.sort(key=lambda x: (x["team"], x["game_day_url"]))

    for schedule_row in team_schedule_rows:
        team = str(schedule_row["team"])
        rows = [row for row in game_rows if row["team"] == team]
        fetched = [row for row in rows if row["fetch_success"] is True]
        schedule_row["game_pages_fetch_success"] = len(fetched)
        schedule_row["game_pages_fetch_failure"] = len(rows) - len(fetched)
        for media_class in MEDIA_CLASSES:
            count = sum(1 for row in fetched if row["media_class_present"][media_class] is True)
            schedule_row[f"{media_class}_page_count"] = count
            schedule_row[f"{media_class}_coverage_fraction_of_fetched_pages"] = count / len(fetched) if fetched else 0.0

    expected_team_games = int(contract["expected_regular_season_team_games_by_season"][str(season)])
    discovered_team_games = len(game_tasks)
    fetched_team_games = sum(1 for row in game_rows if row["fetch_success"] is True)
    class_counts = {
        media_class: sum(1 for row in game_rows if row["fetch_success"] is True and row["media_class_present"][media_class] is True)
        for media_class in MEDIA_CLASSES
    }
    accounting_pass = bool(
        len(team_schedule_rows) == 32
        and len({row["team"] for row in team_schedule_rows}) == 32
        and len(schedule_attempts) == sum(len(domains) for domains in teams.values())
        and len(game_rows) == discovered_team_games
    )

    return {
        "discovery_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "expected_regular_season_team_games": expected_team_games,
        "team_seasons_reported": len(team_schedule_rows),
        "schedule_domain_attempts_reported": len(schedule_attempts),
        "schedule_surfaces_available": sum(1 for row in team_schedule_rows if row["schedule_surface_available"] is True),
        "discovered_regular_season_team_game_pages": discovered_team_games,
        "missing_expected_regular_season_team_games_diagnostic": max(0, expected_team_games - discovered_team_games),
        "extra_discovered_regular_season_team_games_diagnostic": max(0, discovered_team_games - expected_team_games),
        "game_day_pages_fetch_success": fetched_team_games,
        "game_day_pages_fetch_failure": len(game_rows) - fetched_team_games,
        "media_class_page_counts": class_counts,
        "media_class_coverage_fraction_of_fetched_pages": {
            key: (value / fetched_team_games if fetched_team_games else 0.0)
            for key, value in class_counts.items()
        },
        "discovery_accounting_integrity_pass": accounting_pass,
        "team_schedule_results": team_schedule_rows,
        "schedule_attempts": schedule_attempts,
        "game_day_results": game_rows,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_roster_depth_locator_coverage_qualified": False,
        "source_bytes_qualified_by_this_diagnostic": False,
        "source_chronology_qualified": False,
        "transaction_reconciliation_performed": False,
        "game_day_membership_constructed": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "third_party_authority_used": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "absence_from_inactive_used_as_positive": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(
        args.contract,
        season=args.season,
        timeout=args.timeout,
        workers=args.workers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"team_schedule_results", "schedule_attempts", "game_day_results"}}, indent=2, sort_keys=True))
    if result["discovery_accounting_integrity_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

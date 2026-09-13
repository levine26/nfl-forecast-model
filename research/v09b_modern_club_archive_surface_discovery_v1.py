from __future__ import annotations

"""Discovery-only inventory of standardized first-party club archive surfaces.

This module intentionally stops before game-level locator qualification. It probes a frozen
set of standardized official club URL patterns for 2017-2021 and reports whether pages expose
first-party links visibly labelled as roster/depth documents. Missing pages and network errors
are retained; hit rate has no qualification authority.
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-CLUB-ARCHIVE-SURFACE-DISCOVERY-V1"
STATIC_CLUB_HOST = "static.clubs.nfl.com"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def allowed_team_hosts(domains: list[str]) -> set[str]:
    hosts: set[str] = set()
    for domain in domains:
        d = str(domain).strip().lower().removeprefix("www.")
        if not d:
            continue
        hosts.add(d)
        hosts.add(f"www.{d}")
    return hosts


def valid_roster_depth_anchor(
    *,
    text: str,
    href: str,
    page_url: str,
    team_hosts: set[str],
) -> dict[str, str] | None:
    visible = normalize_text(text)
    if "ROSTER" not in visible or "DEPTH" not in visible:
        return None
    absolute = urljoin(page_url, str(href or "").strip())
    parsed = urlparse(absolute)
    if parsed.scheme.lower() != "https":
        return None
    host = (parsed.hostname or "").lower()
    if host != STATIC_CLUB_HOST and host not in team_hosts:
        return None
    return {"text": " ".join(str(text or "").split()), "url": absolute, "host": host}


def inspect_archive_html(
    html: str,
    *,
    page_url: str,
    season: int,
    team_hosts: set[str],
) -> dict[str, Any]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    visible_text = " ".join(soup.stripped_strings)
    season_text_present = str(int(season)) in visible_text
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for anchor in soup.find_all("a", href=True):
        row = valid_roster_depth_anchor(
            text=anchor.get_text(" ", strip=True),
            href=str(anchor.get("href") or ""),
            page_url=page_url,
            team_hosts=team_hosts,
        )
        if row is None:
            continue
        key = (row["text"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        matches.append(row)
    return {
        "season_text_present": season_text_present,
        "roster_depth_anchor_count": len(matches),
        "matching_anchor_examples": matches[:25],
        "archive_surface_hit": bool(season_text_present and matches),
    }


def _fetch_attempt(
    task: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    team_hosts = allowed_team_hosts(list(task["team_domains"]))
    url = str(task["url"])
    result: dict[str, Any] = {
        "team": str(task["team"]),
        "season": int(task["season"]),
        "base_domain": str(task["base_domain"]),
        "path_template": str(task["path_template"]),
        "requested_url": url,
        "final_url": None,
        "http_status": None,
        "content_type": None,
        "final_host_allowed": False,
        "season_text_present": False,
        "roster_depth_anchor_count": 0,
        "matching_anchor_examples": [],
        "archive_surface_hit": False,
        "error": None,
    }
    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-club-archive-discovery/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        result["http_status"] = int(response.status_code)
        result["final_url"] = str(response.url)
        result["content_type"] = str(response.headers.get("content-type", ""))
        final = urlparse(str(response.url))
        final_host = (final.hostname or "").lower()
        result["final_host_allowed"] = final.scheme.lower() == "https" and final_host in team_hosts
        if not result["final_host_allowed"]:
            result["error"] = f"final redirect escaped team allowlist: {final_host}"
            return result
        if int(response.status_code) >= 400:
            result["error"] = f"HTTP {response.status_code}"
            return result
        inspected = inspect_archive_html(
            response.text,
            page_url=str(response.url),
            season=int(task["season"]),
            team_hosts=team_hosts,
        )
        result.update(inspected)
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return result


def build_tasks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    paths = list(contract["standardized_path_candidates"])
    for team, domains in sorted(contract["teams"].items()):
        for season in contract["seasons"]:
            for domain in domains:
                base = str(domain).strip().lower().removeprefix("www.")
                for path_template in paths:
                    path = str(path_template).format(season=int(season))
                    tasks.append(
                        {
                            "team": team,
                            "season": int(season),
                            "team_domains": list(domains),
                            "base_domain": base,
                            "path_template": str(path_template),
                            "url": f"https://www.{base}{path}",
                        }
                    )
    return tasks


def run_discovery(contract_path: Path, *, timeout: float, workers: int) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    tasks = build_tasks(contract)
    attempts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        future_map = {pool.submit(_fetch_attempt, task, timeout=timeout): task for task in tasks}
        for future in as_completed(future_map):
            attempts.append(future.result())
    attempts.sort(key=lambda row: (row["team"], row["season"], row["base_domain"], row["path_template"]))

    pair_rows: list[dict[str, Any]] = []
    missing_pairs: list[str] = []
    for team in sorted(contract["teams"]):
        for season in contract["seasons"]:
            rows = [row for row in attempts if row["team"] == team and row["season"] == int(season)]
            hits = [row for row in rows if row["archive_surface_hit"] is True]
            hits.sort(
                key=lambda row: (
                    -int(row["roster_depth_anchor_count"]),
                    str(row.get("requested_url") or ""),
                )
            )
            best = hits[0] if hits else None
            pair = {
                "team": team,
                "season": int(season),
                "candidate_attempts": len(rows),
                "successful_http_attempts": sum(1 for row in rows if row["http_status"] is not None and int(row["http_status"]) < 400 and row["final_host_allowed"] is True),
                "network_or_http_error_attempts": sum(1 for row in rows if row["error"] is not None),
                "archive_surface_hits": len(hits),
                "archive_surface_discovered": best is not None,
                "best_archive_url": best["final_url"] if best else None,
                "best_roster_depth_anchor_count": int(best["roster_depth_anchor_count"]) if best else 0,
                "best_matching_anchor_examples": list(best["matching_anchor_examples"]) if best else [],
            }
            pair_rows.append(pair)
            if best is None:
                missing_pairs.append(f"{team}|{season}")

    expected_pairs = int(contract["required_accounting"]["team_season_pairs"])
    expected_attempts = len(tasks)
    discovered_pairs = sum(1 for row in pair_rows if row["archive_surface_discovered"] is True)
    escaped_redirects = [row for row in attempts if row["final_url"] is not None and row["final_host_allowed"] is False]
    accounting_pass = bool(
        len(pair_rows) == expected_pairs
        and len(attempts) == expected_attempts
        and len({(row["team"], row["season"]) for row in pair_rows}) == expected_pairs
    )
    return {
        "discovery_version": 1,
        "contract_id": CONTRACT_ID,
        "expected_team_season_pairs": expected_pairs,
        "team_season_pairs_reported": len(pair_rows),
        "expected_candidate_attempts": expected_attempts,
        "candidate_attempts_reported": len(attempts),
        "archive_surface_team_season_hits": discovered_pairs,
        "archive_surface_team_season_missing": len(missing_pairs),
        "archive_surface_discovery_fraction_diagnostic_only": discovered_pairs / expected_pairs if expected_pairs else 0.0,
        "missing_team_season_pairs": missing_pairs,
        "redirect_escape_attempts": len(escaped_redirects),
        "attempts_with_network_or_http_error": sum(1 for row in attempts if row["error"] is not None),
        "discovery_accounting_integrity_pass": accounting_pass,
        "team_season_results": pair_rows,
        "attempts": attempts,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_roster_depth_locator_coverage_qualified": False,
        "all_2592_team_game_partitions_tested": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_discovery(args.contract, timeout=args.timeout, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"attempts", "team_season_results"}}, indent=2, sort_keys=True))
    if result["discovery_accounting_integrity_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

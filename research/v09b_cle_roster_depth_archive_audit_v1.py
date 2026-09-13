from __future__ import annotations

"""Full 2017-2021 Cleveland weekly Roster & Depth source-coverage audit.

The audit follows only the already-qualified CLE delegation chain:
Browns season archive -> exact weekly Rosters & Depth viewer -> direct Full Document PDF.
It qualifies at most weekly snapshot source coverage. It never constructs kickoff eligibility.
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_modern_roster_depth_source_probe_v2 import (
    CURRENT_ROSTER_MARKERS,
    PRACTICE_MARKER,
    RESERVE_MARKERS,
    choose_pregame_roster_date,
    extract_pdf_text,
    marker_lines,
    pdf_magic_valid,
    roster_as_of_candidates,
    sha256_bytes,
)

CONTRACT_ID = "V09B-CLE-ROSTER-DEPTH-ARCHIVE-AUDIT-V1"
ARCHIVE_HOST = "browns.1rmg.com"
DOCUMENT_HOST = "media.browns.1rmg.com"
ROSTER_LINK_TEXT = "ROSTERS & DEPTH"
FULL_DOCUMENT_TEXT = "FULL DOCUMENT"
WEEK_PATH_RE = re.compile(r"^/season/(?P<season>\d{4})/regular-season/week-(?P<week>\d+)/rosters-depth/?$", re.I)
WEEK_DATE_RE_TEMPLATE = r"\b(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s+(\d{{1,2}})/(\d{{1,2}}).*?\bWEEK\s+{week}\b"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def _host(url: str) -> str:
    return (urlparse(str(url)).hostname or "").lower()


def _validate_https_host(url: str, host: str) -> None:
    parsed = urlparse(str(url))
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() != host:
        raise ValueError(f"unexpected URL provenance: {url}")


def _get(url: str, *, host: str, timeout: float, accept: str) -> Any:
    _validate_https_host(url, host)
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-CLE-roster-depth-audit/1.0)",
            "Accept": accept,
        },
    )
    response.raise_for_status()
    _validate_https_host(str(response.url), host)
    return response


def _game_date_near_anchor(anchor: Any, *, season: int, week: int) -> date | None:
    pattern = re.compile(WEEK_DATE_RE_TEMPLATE.format(week=week), re.I)
    node = anchor
    for _ in range(12):
        node = getattr(node, "parent", None)
        if node is None:
            break
        text = _normalize(node.get_text(" ", strip=True))
        match = pattern.search(text)
        if not match:
            continue
        month, day = (int(x) for x in match.groups())
        year = season + 1 if month <= 2 else season
        return date(year, month, day)
    return None


def discover_week_viewers(html: str, *, archive_url: str, season: int) -> tuple[list[dict[str, Any]], int]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    week_counts: dict[int, int] = {}
    for anchor in soup.find_all("a", href=True):
        if _normalize(anchor.get_text(" ", strip=True)) != ROSTER_LINK_TEXT:
            continue
        absolute = urljoin(archive_url, str(anchor.get("href") or ""))
        if _host(absolute) != ARCHIVE_HOST:
            continue
        match = WEEK_PATH_RE.match(urlparse(absolute).path)
        if not match or int(match.group("season")) != season:
            continue
        week = int(match.group("week"))
        game_date = _game_date_near_anchor(anchor, season=season, week=week)
        rows.append(
            {
                "season": season,
                "week": week,
                "game_date": game_date.isoformat() if game_date else None,
                "viewer_url": absolute,
            }
        )
        week_counts[week] = week_counts.get(week, 0) + 1
    duplicate_week_links = sum(max(0, count - 1) for count in week_counts.values())
    return sorted(rows, key=lambda row: int(row["week"])), duplicate_week_links


def full_document_link(viewer_html: str, *, viewer_url: str) -> tuple[str | None, int]:
    soup = BeautifulSoup(viewer_html, "html.parser")
    matches: list[str] = []
    for anchor in soup.find_all("a", href=True):
        if _normalize(anchor.get_text(" ", strip=True)) != FULL_DOCUMENT_TEXT:
            continue
        absolute = urljoin(viewer_url, str(anchor.get("href") or ""))
        if _host(absolute) != DOCUMENT_HOST:
            continue
        matches.append(absolute)
    unique = list(dict.fromkeys(matches))
    return (unique[0] if len(unique) == 1 else None), len(unique)


def audit_week(row: dict[str, Any], *, timeout: float, window_lines: int, maximum_age_days: int) -> dict[str, Any]:
    viewer_url = str(row["viewer_url"])
    viewer_response = _get(viewer_url, host=ARCHIVE_HOST, timeout=timeout, accept="text/html,application/xhtml+xml")
    document_url, document_link_count = full_document_link(viewer_response.text, viewer_url=str(viewer_response.url))
    if document_url is None:
        raise RuntimeError(f"expected exactly one direct Full Document link, found {document_link_count}")
    pdf_response = _get(document_url, host=DOCUMENT_HOST, timeout=timeout, accept="application/pdf,*/*")
    raw = pdf_response.content
    if not pdf_magic_valid(raw):
        raise RuntimeError("Full Document does not have PDF magic")
    text = extract_pdf_text(raw)
    lines = text.splitlines()
    current = marker_lines(lines, CURRENT_ROSTER_MARKERS)
    practice = marker_lines(lines, (PRACTICE_MARKER,))
    reserve = marker_lines(lines, RESERVE_MARKERS)
    candidates = roster_as_of_candidates(lines, current, window_lines=window_lines)
    if not row.get("game_date"):
        chosen = None
    else:
        chosen = choose_pregame_roster_date(
            candidates,
            game_date=date.fromisoformat(str(row["game_date"])),
            maximum_age_days=maximum_age_days,
        )
    semantic_pass = bool(current and practice and reserve and chosen is not None)
    return {
        **row,
        "viewer_final_url": str(viewer_response.url),
        "viewer_http_status": int(viewer_response.status_code),
        "viewer_raw_sha256": sha256_bytes(viewer_response.content),
        "full_document_link_count": document_link_count,
        "document_requested_url": document_url,
        "document_final_url": str(pdf_response.url),
        "document_http_status": int(pdf_response.status_code),
        "document_raw_bytes": len(raw),
        "document_raw_sha256": sha256_bytes(raw),
        "pdf_magic_valid": True,
        "current_roster_marker_count": len(current),
        "practice_squad_marker_count": len(practice),
        "reserve_marker_count": len(reserve),
        "chosen_pregame_roster_snapshot": chosen,
        "semantic_structure_pass": bool(current and practice and reserve),
        "fresh_snapshot_pass": chosen is not None,
        "weekly_snapshot_source_gate_pass": semantic_pass,
    }


def audit_season(contract: dict[str, Any], season: int, *, timeout: float) -> dict[str, Any]:
    expected = int(contract["expected_regular_season_games_by_season"][str(season)])
    archive_url = str(contract["source_chain"]["season_archive_url_template"]).format(season=season)
    archive = _get(archive_url, host=ARCHIVE_HOST, timeout=timeout, accept="text/html,application/xhtml+xml")
    viewers, duplicate_week_links = discover_week_viewers(archive.text, archive_url=str(archive.url), season=season)
    window_lines = int(contract["semantic_requirements"]["roster_date_search_window_lines"])
    max_age = int(contract["semantic_requirements"]["maximum_snapshot_age_days"])
    weeks: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for row in viewers:
        try:
            weeks.append(audit_week(row, timeout=timeout, window_lines=window_lines, maximum_age_days=max_age))
        except Exception as exc:
            errors.append({
                "season": str(season),
                "week": str(row.get("week")),
                "viewer_url": str(row.get("viewer_url")),
                "error": f"{type(exc).__name__}: {exc}",
            })
    week_numbers = [int(row["week"]) for row in viewers]
    exact_count = len(viewers) == expected and len(set(week_numbers)) == expected and duplicate_week_links == 0
    all_week_pass = len(weeks) == expected and all(row["weekly_snapshot_source_gate_pass"] for row in weeks)
    season_gate = bool(exact_count and not errors and all_week_pass)
    return {
        "audit_version": 1,
        "contract_id": CONTRACT_ID,
        "club": "CLE",
        "season": season,
        "expected_regular_season_games": expected,
        "archive_url": archive_url,
        "archive_final_url": str(archive.url),
        "archive_http_status": int(archive.status_code),
        "archive_raw_sha256": sha256_bytes(archive.content),
        "viewer_links_discovered": len(viewers),
        "unique_week_numbers_discovered": len(set(week_numbers)),
        "week_numbers_discovered": sorted(set(week_numbers)),
        "duplicate_week_links": duplicate_week_links,
        "week_rows_completed": len(weeks),
        "source_errors": errors,
        "semantic_pass_weeks": sum(bool(row["semantic_structure_pass"]) for row in weeks),
        "fresh_snapshot_pass_weeks": sum(bool(row["fresh_snapshot_pass"]) for row in weeks),
        "weekly_snapshot_source_pass_weeks": sum(bool(row["weekly_snapshot_source_gate_pass"]) for row in weeks),
        "document_sha_collisions": len(weeks) - len({row["document_raw_sha256"] for row in weeks}),
        "weeks": weeks,
        "season_snapshot_source_coverage_gate_pass": season_gate,
        "cle_weekly_snapshot_source_coverage_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    if args.season not in [int(x) for x in contract["seasons"]]:
        raise ValueError("season outside frozen audit")
    result = audit_season(contract, args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "weeks"}, indent=2, sort_keys=True))
    if result["season_snapshot_source_coverage_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

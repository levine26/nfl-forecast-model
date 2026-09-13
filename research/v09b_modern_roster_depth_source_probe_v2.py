from __future__ import annotations

"""Semantic viability probe for direct first-party weekly Roster & Depth PDFs.

V1's generic Game Release contract is preserved as failed evidence. V2 narrows the source
class to direct week-specific roster/depth PDFs explicitly linked by official club archive
pages. This probe tests source provenance and snapshot semantics only; it never constructs
game-day membership, resolves player identity, or fits a model.
"""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-ROSTER-DEPTH-SOURCE-PROBE-V2"
CURRENT_ROSTER_MARKERS = ("NUMERICAL ROSTER", "ALPHABETICAL ROSTER", "ROSTER BY POSITION")
PRACTICE_MARKER = "PRACTICE SQUAD"
RESERVE_MARKERS = (
    "RESERVE/INJURED",
    "INJURED RESERVE",
    "RESERVE/PUP",
    "RESERVE/COVID-19",
    "RESERVE/NFI",
    "RESERVE/NON-FOOTBALL INJURY",
    "RESERVE/NON-FOOTBALL ILLNESS",
)
AS_OF_FULL_MONTH_RE = re.compile(
    r"\bAS\s+OF\s+(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+"
    r"(\d{1,2}),\s*(\d{4})\b",
    re.I,
)
AS_OF_NUMERIC_RE = re.compile(r"\bAS\s+OF\s+(\d{1,2})/(\d{1,2})/(\d{2,4})\b", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_url(url: str) -> str:
    parsed = urlparse(str(url))
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _validate_https_host(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("source URL must use https")
    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts:
        raise ValueError(f"source host is not allowlisted: {host}")


def pdf_magic_valid(raw: bytes) -> bool:
    return raw.startswith(b"%PDF-")


def extract_pdf_text(raw: bytes) -> str:
    proc = subprocess.run(
        ["pdftotext", "-layout", "-", "-"],
        input=raw,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {proc.stderr.decode('utf-8', errors='replace')[:500]}")
    text = proc.stdout.decode("utf-8", errors="replace")
    if not text.strip():
        raise RuntimeError("pdftotext returned empty text")
    return text


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def marker_lines(lines: list[str], markers: tuple[str, ...]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        normalized = _normalize_line(line)
        for marker in markers:
            if marker in normalized:
                found.append({"line_index": idx, "marker": marker, "line": line.strip()[:500]})
                break
    return found


def _parse_as_of_from_line(line: str) -> list[date]:
    values: list[date] = []
    for match in AS_OF_FULL_MONTH_RE.finditer(line):
        month, day, year = match.groups()
        values.append(datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date())
    for match in AS_OF_NUMERIC_RE.finditer(line):
        month, day, year = match.groups()
        year_i = int(year)
        if year_i < 100:
            year_i += 2000
        values.append(date(year_i, int(month), int(day)))
    return values


def roster_as_of_candidates(
    lines: list[str],
    current_roster_markers: list[dict[str, Any]],
    *,
    window_lines: int,
) -> list[dict[str, Any]]:
    candidates: dict[tuple[int, str, int], dict[str, Any]] = {}
    for marker in current_roster_markers:
        marker_idx = int(marker["line_index"])
        start = max(0, marker_idx - window_lines)
        end = min(len(lines), marker_idx + window_lines + 1)
        for line_idx in range(start, end):
            for value in _parse_as_of_from_line(lines[line_idx]):
                distance = abs(line_idx - marker_idx)
                key = (line_idx, value.isoformat(), marker_idx)
                candidates[key] = {
                    "date": value.isoformat(),
                    "line_index": line_idx,
                    "line": lines[line_idx].strip()[:500],
                    "distance_from_roster_marker_lines": distance,
                    "roster_marker": marker["marker"],
                    "roster_marker_line_index": marker_idx,
                }
    return sorted(
        candidates.values(),
        key=lambda row: (int(row["distance_from_roster_marker_lines"]), str(row["date"]), int(row["line_index"])),
    )


def choose_pregame_roster_date(
    candidates: list[dict[str, Any]],
    *,
    game_date: date,
    maximum_age_days: int,
) -> dict[str, Any] | None:
    eligible: list[tuple[int, int, dict[str, Any]]] = []
    for row in candidates:
        value = date.fromisoformat(str(row["date"]))
        age = (game_date - value).days
        if 0 <= age <= maximum_age_days:
            eligible.append((age, int(row["distance_from_roster_marker_lines"]), row))
    if not eligible:
        return None
    age, _, row = min(eligible, key=lambda item: (item[0], item[1]))
    return {**row, "snapshot_age_days": age}


def _fetch(session: Any, url: str, *, timeout: float, accept: str) -> Any:
    response = session.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-roster-depth-probe/2.0)",
            "Accept": accept,
        },
    )
    response.raise_for_status()
    return response


def archive_link_evidence(
    sample: dict[str, Any],
    *,
    timeout: float,
    archive_hosts: set[str],
    pdf_hosts: set[str],
    session: Any = requests,
) -> dict[str, Any]:
    archive_url = str(sample["archive_url"])
    source_url = str(sample["source_url"])
    expected_text = _normalize_line(str(sample["archive_link_text"]))
    _validate_https_host(archive_url, archive_hosts)
    _validate_https_host(source_url, pdf_hosts)
    response = _fetch(session, archive_url, timeout=timeout, accept="text/html,application/xhtml+xml")
    final_archive_url = str(response.url)
    _validate_https_host(final_archive_url, archive_hosts)
    soup = BeautifulSoup(response.text, "html.parser")
    matches: list[dict[str, str]] = []
    target = _canonical_url(source_url)
    for anchor in soup.find_all("a", href=True):
        text = _normalize_line(anchor.get_text(" ", strip=True))
        if text != expected_text:
            continue
        absolute = urljoin(final_archive_url, str(anchor.get("href") or ""))
        try:
            _validate_https_host(absolute, pdf_hosts)
        except ValueError:
            continue
        matches.append({"text": anchor.get_text(" ", strip=True), "url": absolute})
    exact = [row for row in matches if _canonical_url(row["url"]) == target]
    return {
        "archive_requested_url": archive_url,
        "archive_final_url": final_archive_url,
        "archive_http_status": int(response.status_code),
        "expected_archive_link_text": str(sample["archive_link_text"]),
        "matching_archive_link_count": len(matches),
        "exact_source_link_count": len(exact),
        "exact_source_link_present": len(exact) == 1,
        "matching_archive_links": matches[:20],
    }


def probe_sample(
    sample: dict[str, Any],
    *,
    timeout: float,
    archive_hosts: set[str],
    pdf_hosts: set[str],
    window_lines: int,
    maximum_age_days: int,
    session: Any = requests,
) -> dict[str, Any]:
    provenance = archive_link_evidence(
        sample,
        timeout=timeout,
        archive_hosts=archive_hosts,
        pdf_hosts=pdf_hosts,
        session=session,
    )
    source_url = str(sample["source_url"])
    response = _fetch(session, source_url, timeout=timeout, accept="application/pdf,*/*")
    final_url = str(response.url)
    _validate_https_host(final_url, pdf_hosts)
    raw = response.content
    if not pdf_magic_valid(raw):
        raise RuntimeError("direct roster/depth source does not have PDF magic")
    text = extract_pdf_text(raw)
    lines = text.splitlines()
    current = marker_lines(lines, CURRENT_ROSTER_MARKERS)
    practice = marker_lines(lines, (PRACTICE_MARKER,))
    reserve = marker_lines(lines, RESERVE_MARKERS)
    candidates = roster_as_of_candidates(lines, current, window_lines=window_lines)
    chosen = choose_pregame_roster_date(
        candidates,
        game_date=date.fromisoformat(str(sample["game_date"])),
        maximum_age_days=maximum_age_days,
    )
    gate_pass = bool(
        provenance["exact_source_link_present"] is True
        and current
        and practice
        and reserve
        and chosen is not None
    )
    return {
        "season": int(sample["season"]),
        "club": str(sample["club"]),
        "game_id": str(sample["game_id"]),
        "game_date": str(sample["game_date"]),
        **provenance,
        "source_requested_url": source_url,
        "source_final_url": final_url,
        "source_host": urlparse(final_url).hostname,
        "content_type": str(response.headers.get("content-type", "")),
        "raw_bytes": len(raw),
        "raw_sha256": sha256_bytes(raw),
        "pdf_magic_valid": pdf_magic_valid(raw),
        "current_roster_marker_count": len(current),
        "current_roster_marker_examples": current[:20],
        "practice_squad_marker_count": len(practice),
        "practice_squad_marker_examples": practice[:20],
        "reserve_marker_count": len(reserve),
        "reserve_marker_examples": reserve[:20],
        "roster_as_of_candidates": candidates[:50],
        "chosen_pregame_roster_snapshot": chosen,
        "snapshot_within_maximum_age": chosen is not None,
        "semantic_viability_gate_pass": gate_pass,
        "coverage_claimed": False,
        "game_day_membership_constructed": False,
        "identity_resolution_performed": False,
        "model_fit_performed": False,
    }


def run_probe(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    samples = list(contract["fixed_cross_era_samples"])
    archive_hosts = {str(x).lower() for x in contract["source_requirements"]["archive_hosts_allowed"]}
    pdf_hosts = {str(x).lower() for x in contract["source_requirements"]["pdf_hosts_allowed"]}
    window_lines = int(contract["semantic_markers"]["roster_date_search_window_lines_around_current_roster_marker"])
    maximum_age_days = int(contract["semantic_markers"]["maximum_snapshot_age_days_for_viability"])
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for sample in samples:
        try:
            rows.append(
                probe_sample(
                    sample,
                    timeout=timeout,
                    archive_hosts=archive_hosts,
                    pdf_hosts=pdf_hosts,
                    window_lines=window_lines,
                    maximum_age_days=maximum_age_days,
                )
            )
        except Exception as exc:
            errors.append(
                {
                    "season": str(sample.get("season")),
                    "club": str(sample.get("club")),
                    "game_id": str(sample.get("game_id")),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    all_pass = len(rows) == 5 and not errors and all(row["semantic_viability_gate_pass"] for row in rows)
    return {
        "probe_version": 2,
        "contract_id": CONTRACT_ID,
        "sample_count_expected": 5,
        "sample_count_completed": len(rows),
        "source_errors": errors,
        "samples": rows,
        "source_class_semantic_viability_probe_pass": all_pass,
        "all_team_game_locator_coverage_tested": False,
        "game_day_membership_constructed": False,
        "same_day_transactions_reconciled": False,
        "standard_elevations_reconciled": False,
        "inactive_lists_reconciled": False,
        "probe_has_coverage_authority": False,
        "probe_has_membership_authority": False,
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
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_probe(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2, sort_keys=True))
    if result["source_class_semantic_viability_probe_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

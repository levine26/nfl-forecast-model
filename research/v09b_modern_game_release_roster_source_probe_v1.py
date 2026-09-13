from __future__ import annotations

"""Semantic-viability probe for first-party weekly Game Release roster snapshots.

This is deliberately not a locator audit and not a roster-membership constructor. It tests
five frozen cross-era first-party PDFs for three properties only: a week-specific release,
a current roster section, and explicitly separated non-current-roster populations, with a
parseable roster `as of` date no more than seven days before the target game.
"""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

CONTRACT_ID = "V09B-MODERN-GAME-RELEASE-ROSTER-SOURCE-PROBE-V1"
ALLOWED_HOSTS = {"static.clubs.nfl.com"}
RELEASE_MARKERS = ("GAME RELEASE", "WEEKLY RELEASE", "WEEKLY PRESS RELEASE")
CURRENT_ROSTER_MARKERS = ("NUMERICAL ROSTER", "ALPHABETICAL ROSTER", "ROSTERS & DEPTH CHART")
EXCLUDED_MARKERS = (
    "PRACTICE SQUAD",
    "RESERVE/INJURED",
    "INJURED RESERVE",
    "RESERVE/PUP",
    "RESERVE/COVID-19",
    "RESERVE/NFI",
    "RESERVE/NON FOOTBALL INJURY",
)
AS_OF_RE = re.compile(
    r"\bAS\s+OF\s+(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+"
    r"(\d{1,2}),\s*(\d{4})\b",
    re.I,
)
AS_OF_NUMERIC_RE = re.compile(r"\bAS\s+OF\s+(\d{1,2})/(\d{1,2})/(\d{2,4})\b", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("source URL must use https")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"source host is not first-party allowlisted: {parsed.hostname}")


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


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().upper()


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
    for match in AS_OF_RE.finditer(line):
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
    roster_markers: list[dict[str, Any]],
    *,
    window_lines: int,
) -> list[dict[str, Any]]:
    candidates: dict[tuple[int, str], dict[str, Any]] = {}
    for marker in roster_markers:
        idx = int(marker["line_index"])
        start = max(0, idx - window_lines)
        end = min(len(lines), idx + window_lines + 1)
        for line_idx in range(start, end):
            line = lines[line_idx]
            for value in _parse_as_of_from_line(line):
                key = (line_idx, value.isoformat())
                distance = abs(line_idx - idx)
                current = candidates.get(key)
                row = {
                    "date": value.isoformat(),
                    "line_index": line_idx,
                    "distance_from_roster_marker_lines": distance,
                    "line": line.strip()[:500],
                    "roster_marker": marker["marker"],
                    "roster_marker_line_index": idx,
                }
                if current is None or distance < int(current["distance_from_roster_marker_lines"]):
                    candidates[key] = row
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
    age, _, chosen = min(eligible, key=lambda item: (item[0], item[1]))
    return {**chosen, "snapshot_age_days": age}


def fetch_pdf(url: str, *, timeout: float) -> tuple[bytes, str, str]:
    validate_source_url(url)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "LevLine-V09B-game-release-roster-source-probe/1.0"},
    )
    response.raise_for_status()
    final_url = str(response.url)
    validate_source_url(final_url)
    raw = response.content
    if not pdf_magic_valid(raw):
        raise RuntimeError("source does not have PDF magic")
    return raw, final_url, str(response.headers.get("content-type", ""))


def probe_sample(sample: dict[str, Any], *, timeout: float, window_lines: int, maximum_age_days: int) -> dict[str, Any]:
    raw, final_url, content_type = fetch_pdf(str(sample["source_url"]), timeout=timeout)
    text = extract_pdf_text(raw)
    lines = text.splitlines()
    releases = marker_lines(lines, RELEASE_MARKERS)
    roster_markers = marker_lines(lines, CURRENT_ROSTER_MARKERS)
    excluded = marker_lines(lines, EXCLUDED_MARKERS)
    candidates = roster_as_of_candidates(lines, roster_markers, window_lines=window_lines)
    target_game_date = date.fromisoformat(str(sample["game_date"]))
    chosen = choose_pregame_roster_date(
        candidates,
        game_date=target_game_date,
        maximum_age_days=maximum_age_days,
    )

    gate_pass = bool(releases and roster_markers and excluded and chosen is not None)
    return {
        "season": int(sample["season"]),
        "club": str(sample["club"]),
        "game_id": str(sample["game_id"]),
        "game_date": str(sample["game_date"]),
        "source_description": str(sample["source_description"]),
        "requested_url": str(sample["source_url"]),
        "final_url": final_url,
        "source_host": urlparse(final_url).hostname,
        "content_type": content_type,
        "raw_bytes": len(raw),
        "raw_sha256": sha256_bytes(raw),
        "pdf_magic_valid": pdf_magic_valid(raw),
        "release_marker_count": len(releases),
        "release_marker_examples": releases[:10],
        "current_roster_marker_count": len(roster_markers),
        "current_roster_marker_examples": roster_markers[:20],
        "excluded_population_marker_count": len(excluded),
        "excluded_population_marker_examples": excluded[:20],
        "roster_as_of_candidates": candidates[:50],
        "chosen_pregame_roster_snapshot": chosen,
        "snapshot_within_maximum_age": chosen is not None,
        "semantic_viability_gate_pass": gate_pass,
        "game_day_membership_constructed": False,
        "coverage_claimed": False,
        "identity_resolution_performed": False,
        "model_fit_performed": False,
    }


def run_probe(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    samples = list(contract["fixed_cross_era_samples"])
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
        "probe_version": 1,
        "contract_id": CONTRACT_ID,
        "sample_count_expected": 5,
        "sample_count_completed": len(rows),
        "source_errors": errors,
        "all_five_samples_semantically_viable": all_pass,
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

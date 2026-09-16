from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import polars as pl
import requests
from bs4 import BeautifulSoup

from research.levline4_2026_official_club_roster_surface_probe_v1 import (
    PROFILE_PATH_RE,
    capture_team,
    host_allowed,
    normalize_header,
    sha256_bytes,
)
from research.levline4_prospective_inactive_gsis_resolver_v1 import (
    SOURCE_FIELDS,
    SOURCE_PROJECTION_SHA256,
    normalize_name,
    normalize_team,
)

CONTRACT_PATH = Path(
    "research/levline4_2026_official_club_roster_identity_corroboration_v2_contract.json"
)
V1_CONTRACT_PATH = Path(
    "research/levline4_2026_official_club_roster_surface_probe_v1_contract.json"
)
DEFAULT_OUTPUT = Path(
    "research_outputs/levline4_2026_official_club_roster_identity_corroboration_v2"
)
CONTRACT_ID = "LEVLINE-4-2026-OFFICIAL-CLUB-ROSTER-IDENTITY-CORROBORATION-V2"
EXACT_HEADERS = ("Player", "#", "Pos", "HT", "WT", "Age", "Exp", "College")
V1_COMPLETED_AT = datetime.fromisoformat("2026-09-16T17:20:11.766387+00:00")


def parse_utc(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone aware")
    return parsed.astimezone(timezone.utc)


def normalize_jersey(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if text.isascii() and text.isdigit():
        return str(int(text))
    return text.upper()


def wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1.0 + (z * z / total)
    center = p + (z * z / (2.0 * total))
    adjustment = z * math.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total)))
    return (center - adjustment) / denominator


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text())
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected V2 contract id")
    if contract.get("status") != "PREREGISTERED_BEFORE_FIRST_V2_VALIDATION_EXECUTION":
        raise ValueError("V2 contract is not preregistered")
    projection = contract.get("frozen_week2_identity_projection") or {}
    if projection.get("projection_sha256") != SOURCE_PROJECTION_SHA256:
        raise ValueError("frozen Week 2 projection SHA drifted")
    if tuple(projection.get("projection_fields") or ()) != SOURCE_FIELDS:
        raise ValueError("frozen Week 2 projection fields drifted")
    if projection.get("status_fields_available_to_v2") is not False:
        raise ValueError("status fields may not be available to V2")
    return contract


def load_clubs() -> tuple[dict[str, str], str]:
    contract = json.loads(V1_CONTRACT_PATH.read_text())
    clubs = dict(contract["source_discovery"]["clubs"])
    if len(clubs) != 32:
        raise ValueError("V1 club host universe is not exactly 32 teams")
    return clubs, str(contract["source_discovery"]["roster_path"])


def parse_official_roster_html(
    team: str,
    host: str,
    final_url: str,
    captured_at_utc: str,
    raw: bytes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(raw, "lxml")
    raw_sha = sha256_bytes(raw)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    selected_tables = 0

    for table_index, table in enumerate(soup.find_all("table")):
        headers = tuple(normalize_header(th.get_text(" ", strip=True)) for th in table.find_all("th"))
        if headers != EXACT_HEADERS:
            continue
        selected_tables += 1
        for row_index, tr in enumerate(table.find_all("tr")):
            cells = tr.find_all("td")
            if not cells:
                continue
            rendered = [normalize_header(cell.get_text(" ", strip=True)) for cell in cells]
            issue: str | None = None
            if len(rendered) != 8:
                issue = f"cell_count:{len(rendered)}"
            else:
                name = rendered[0]
                position = rendered[2]
                if not name:
                    issue = "blank_player_name"
                elif not position:
                    issue = "blank_position"

            profile_urls: set[str] = set()
            for anchor in tr.find_all("a", href=True):
                href = str(anchor.get("href") or "").strip()
                absolute = urljoin(final_url, href)
                parsed = urlparse(absolute)
                if not PROFILE_PATH_RE.match(parsed.path):
                    continue
                normalized_url = absolute.split("#", 1)[0].split("?", 1)[0]
                if not host_allowed(normalized_url, host):
                    issue = issue or "profile_url_left_frozen_host"
                    continue
                profile_urls.add(normalized_url)
            if len(profile_urls) != 1:
                issue = issue or f"unique_profile_url_count:{len(profile_urls)}"

            if issue is not None:
                errors.append(
                    {
                        "team": team,
                        "table_index": table_index,
                        "row_index": row_index,
                        "issue": issue,
                    }
                )
                continue

            name, jersey, position = rendered[0], rendered[1], rendered[2]
            rows.append(
                {
                    "team": team,
                    "player_name_rendered": name,
                    "normalized_name": normalize_name(name),
                    "jersey_rendered": jersey,
                    "normalized_jersey": normalize_jersey(jersey),
                    "position_rendered": position,
                    "profile_url": next(iter(profile_urls)),
                    "final_url": final_url,
                    "captured_at_utc": captured_at_utc,
                    "raw_html_sha256": raw_sha,
                }
            )

    duplicate_names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row["normalized_name"])
        if key in seen:
            duplicate_names.append(key)
        seen.add(key)

    summary = {
        "team": team,
        "selected_exact_header_tables": selected_tables,
        "parsed_rows": len(rows),
        "malformed_rows": len(errors),
        "duplicate_team_normalized_names": sorted(set(duplicate_names)),
        "minimum_rows_gate_pass": len(rows) >= 70,
        "all_selected_nonempty_rows_parse_gate_pass": len(errors) == 0,
        "duplicate_name_gate_pass": len(duplicate_names) == 0,
        "selected_table_gate_pass": selected_tables > 0,
        "parser_team_gate_pass": (
            selected_tables > 0
            and len(rows) >= 70
            and len(errors) == 0
            and len(duplicate_names) == 0
        ),
        "errors": errors,
    }
    return rows, summary


def build_week2_candidate_index(frame: pl.DataFrame) -> dict[tuple[str, str], dict[str, set[str]]]:
    if tuple(frame.columns) != SOURCE_FIELDS:
        raise RuntimeError("identity projection fields do not match frozen source contract")
    index: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in frame.to_dicts():
        if int(row.get("season") or -1) != 2026:
            continue
        if str(row.get("game_type") or "") != "REG":
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if week != 2:
            continue
        team = normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not team or not gsis:
            continue
        aliases = {
            normalize_name(f"{str(row.get('first_name') or '').strip()} {str(row.get('last_name') or '').strip()}"),
            normalize_name(f"{str(row.get('football_name') or '').strip()} {str(row.get('last_name') or '').strip()}"),
        }
        jersey = normalize_jersey(row.get("jersey_number"))
        for alias in aliases:
            if alias:
                index[(team, alias)][gsis].add(jersey)
    return index


def audit_cross_publication(
    official_rows: list[dict[str, Any]],
    candidate_index: dict[tuple[str, str], dict[str, set[str]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    audited_rows: list[dict[str, Any]] = []
    exact_unique = 0
    unmatched = 0
    ambiguous = 0
    jersey_auditable = 0
    jersey_agreement = 0
    candidate_jersey_conflicts = 0

    for row in official_rows:
        candidates = candidate_index.get((str(row["team"]), str(row["normalized_name"])), {})
        candidate_ids = sorted(candidates)
        state: str
        resolved: str | None = None
        weekly_jerseys: list[str] = []
        agreement: bool | None = None

        if len(candidate_ids) == 0:
            state = "UNMATCHED_UNKNOWN"
            unmatched += 1
        elif len(candidate_ids) > 1:
            state = "AMBIGUOUS_UNQUALIFIED"
            ambiguous += 1
        else:
            state = "EXACT_UNIQUE"
            exact_unique += 1
            resolved = candidate_ids[0]
            weekly_jerseys = sorted(j for j in candidates[resolved] if j)
            official_jersey = str(row["normalized_jersey"])
            if official_jersey and len(weekly_jerseys) == 1:
                jersey_auditable += 1
                agreement = official_jersey == weekly_jerseys[0]
                if agreement:
                    jersey_agreement += 1
            elif len(weekly_jerseys) > 1:
                candidate_jersey_conflicts += 1

        audited_rows.append(
            {
                **row,
                "candidate_state": state,
                "candidate_gsis_ids": candidate_ids,
                "resolved_gsis_id": resolved,
                "weekly_candidate_jerseys": weekly_jerseys,
                "jersey_agreement": agreement,
                "status_used": False,
                "fuzzy_matching_used": False,
                "manual_override_used": False,
            }
        )

    total = len(official_rows)
    coverage = exact_unique / total if total else 0.0
    agreement_rate = jersey_agreement / jersey_auditable if jersey_auditable else 0.0
    summary = {
        "official_rows": total,
        "exact_unique_week2_name_candidates": exact_unique,
        "unmatched_official_rows": unmatched,
        "ambiguous_weekly_name_candidates": ambiguous,
        "exact_unique_name_coverage": coverage,
        "jersey_auditable_rows": jersey_auditable,
        "jersey_agreement_rows": jersey_agreement,
        "jersey_disagreement_rows": jersey_auditable - jersey_agreement,
        "candidate_jersey_conflicts": candidate_jersey_conflicts,
        "jersey_agreement_rate": agreement_rate,
        "jersey_agreement_wilson95_lower": wilson_lower(jersey_agreement, jersey_auditable),
    }
    return audited_rows, summary


def evaluate_gates(
    *,
    team_summaries: list[dict[str, Any]],
    capture_errors: list[dict[str, Any]],
    audit_summary: dict[str, Any],
    contract: dict[str, Any],
    canonical_first_execution: bool,
) -> dict[str, bool]:
    thresholds = contract["fresh_validation_gates"]
    parser_pass = (
        canonical_first_execution
        and len(team_summaries) == 32
        and not capture_errors
        and all(bool(row["parser_team_gate_pass"]) for row in team_summaries)
    )
    gates = {
        "canonical_first_execution": canonical_first_execution,
        "all_32_parser_gates": parser_pass,
        "minimum_exact_unique_week2_name_candidates": (
            audit_summary["exact_unique_week2_name_candidates"]
            >= int(thresholds["minimum_exact_unique_week2_name_candidates"])
        ),
        "minimum_exact_unique_name_coverage": (
            audit_summary["exact_unique_name_coverage"]
            >= float(thresholds["minimum_exact_unique_name_coverage_of_official_rows"])
        ),
        "minimum_jersey_auditable_rows": (
            audit_summary["jersey_auditable_rows"]
            >= int(thresholds["minimum_jersey_auditable_rows"])
        ),
        "minimum_jersey_agreement_rate": (
            audit_summary["jersey_agreement_rate"]
            >= float(thresholds["minimum_jersey_agreement_rate"])
        ),
        "minimum_wilson_95_lower_bound": (
            audit_summary["jersey_agreement_wilson95_lower"]
            >= float(thresholds["minimum_wilson_95_lower_bound_for_jersey_agreement"])
        ),
    }
    gates["fresh_validation_pass"] = all(gates.values())
    return gates


def run_validation(
    projection_path: Path,
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    get: Callable[..., object] = requests.get,
    canonical_first_execution: bool | None = None,
) -> dict[str, Any]:
    contract = load_contract()
    clubs, roster_path = load_clubs()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if canonical_first_execution is None:
        canonical_first_execution = (
            os.environ.get("GITHUB_EVENT_NAME") == "push"
            and os.environ.get("GITHUB_RUN_ATTEMPT", "") == "1"
        )

    projection_raw = projection_path.read_bytes()
    projection_sha = sha256_bytes(projection_raw)
    if projection_sha != SOURCE_PROJECTION_SHA256:
        raise RuntimeError(
            f"identity projection sha256 mismatch: {projection_sha} != {SOURCE_PROJECTION_SHA256}"
        )
    frame = pl.read_parquet(projection_path)
    candidate_index = build_week2_candidate_index(frame)

    all_rows: list[dict[str, Any]] = []
    team_summaries: list[dict[str, Any]] = []
    capture_errors: list[dict[str, Any]] = []
    fresh_after_v1 = True

    for team, host in clubs.items():
        try:
            capture_record, raw, _ = capture_team(team, host, roster_path, get=get)
            captured_at = str(capture_record["captured_at_utc"])
            if parse_utc(captured_at) <= V1_COMPLETED_AT:
                fresh_after_v1 = False
                raise RuntimeError("capture_not_fresh_after_v1")
            if not bool(capture_record["http_success"]):
                raise RuntimeError(f"http_status:{capture_record['http_status']}")
            raw_path = raw_dir / f"{team}.html"
            raw_path.write_bytes(raw)
            rows, summary = parse_official_roster_html(
                team, host, str(capture_record["final_url"]), captured_at, raw
            )
            team_summaries.append({**capture_record, **summary})
            all_rows.extend(rows)
        except Exception as exc:
            capture_errors.append(
                {
                    "team": team,
                    "host": host,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    audited_rows, audit_summary = audit_cross_publication(all_rows, candidate_index)
    gates = evaluate_gates(
        team_summaries=team_summaries,
        capture_errors=capture_errors,
        audit_summary=audit_summary,
        contract=contract,
        canonical_first_execution=bool(canonical_first_execution and fresh_after_v1),
    )
    passed = bool(gates["fresh_validation_pass"])

    (output_dir / "team_parser_summaries.json").write_text(
        json.dumps(team_summaries, indent=2, sort_keys=True) + "\n"
    )
    with (output_dir / "official_roster_rows.jsonl").open("w") as fh:
        for row in sorted(all_rows, key=lambda r: (r["team"], r["normalized_name"])):
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (output_dir / "corroboration_rows.jsonl").open("w") as fh:
        for row in sorted(audited_rows, key=lambda r: (r["team"], r["normalized_name"])):
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    receipt = {
        "schema_version": "levline4-2026-official-club-roster-identity-corroboration-v2",
        "contract_id": CONTRACT_ID,
        "status": "PASS" if passed else "FAIL",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        "canonical_first_execution": bool(canonical_first_execution),
        "fresh_capture_after_v1": fresh_after_v1,
        "source_projection_sha256": projection_sha,
        "captured_team_count": len(team_summaries),
        "capture_errors": capture_errors,
        "parsed_official_rows": len(all_rows),
        "audit_summary": audit_summary,
        "gates": gates,
        "official_club_roster_identity_metadata_parser_qualified": passed,
        "week2_exact_unique_name_plus_jersey_corroboration_rule_qualified": passed,
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
        "general_2026_player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_state_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "f_st_01_frozen_2026_unchanged": True,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_validation(args.projection_path, args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

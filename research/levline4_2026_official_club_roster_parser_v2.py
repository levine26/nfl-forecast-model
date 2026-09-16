from __future__ import annotations

"""Held-out V2 parser for official NFL club roster metadata surfaces.

V1 is a discovery-only source-surface probe. This module freezes the V2 row grammar
before a new held-out 32-club capture. It extracts only identity-adjacent surface
metadata and never interprets roster section/status, health, availability, depth role,
or production/model semantics.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from research import levline4_2026_official_club_roster_surface_probe_v1 as v1

CONTRACT_PATH = Path("research/levline4_2026_official_club_roster_parser_v2_contract.json")
V1_CONTRACT_PATH = Path("research/levline4_2026_official_club_roster_surface_probe_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_official_club_roster_parser_v2")
EXACT_HEADERS = ("Player", "#", "Pos", "HT", "WT", "Age", "Exp", "College")
PROFILE_PATH_RE = re.compile(r"^/team/players-roster/[^/?#]+/?$")
MIN_ROWS_PER_TEAM = 70


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "LEVLINE-4-2026-OFFICIAL-CLUB-ROSTER-PARSER-V2"
    assert contract["status"] == "PREREGISTERED_HELD_OUT_SOURCE_PARSER_QUALIFICATION"
    assert tuple(contract["frozen_parser"]["table_header_vector_must_equal"]) == EXACT_HEADERS
    assert contract["frozen_parser"]["minimum_parsed_rows_per_team"] == MIN_ROWS_PER_TEAM
    assert contract["qualification_gate"]["post_result_threshold_relaxation_allowed"] is False
    assert contract["authority_if_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert contract["authority_if_gate_passes"]["production_authorized"] is False
    return contract


def load_frozen_hosts(path: Path = V1_CONTRACT_PATH) -> tuple[dict[str, str], str]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "LEVLINE-4-2026-OFFICIAL-CLUB-ROSTER-SURFACE-PROBE-V1":
        raise RuntimeError("unexpected V1 source contract")
    clubs = dict(contract["source_discovery"]["clubs"])
    if len(clubs) != 32:
        raise RuntimeError("V1 frozen host set is not 32 clubs")
    return clubs, str(contract["source_discovery"]["roster_path"])


def _profile_path_from_href(href: str) -> str | None:
    path = urlparse(str(href or "").strip()).path
    if not PROFILE_PATH_RE.fullmatch(path):
        return None
    if not path.endswith("/"):
        path += "/"
    return path


def parse_team_html(
    *,
    team: str,
    source_url: str,
    final_url: str,
    captured_at_utc: str,
    raw_html: bytes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse only rows inside exact V2 roster tables.

    Invalid candidate rows are recorded as errors and omitted from the projection. Any
    such error later fails the qualification gate. Section headings are never read.
    """

    soup = BeautifulSoup(raw_html, "lxml")
    raw_sha = v1.sha256_bytes(raw_html)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    exact_table_count = 0
    candidate_row_count = 0

    for table_index, table in enumerate(soup.find_all("table")):
        headers = tuple(normalize_text(th.get_text(" ", strip=True)) for th in table.find_all("th"))
        if headers != EXACT_HEADERS:
            continue
        exact_table_count += 1
        for row_index, tr in enumerate(table.find_all("tr")):
            cells = tr.find_all("td", recursive=False)
            if not cells:
                continue
            candidate_row_count += 1
            if len(cells) != 8:
                errors.append(
                    {
                        "table_index": table_index,
                        "row_index": row_index,
                        "error": "row_cell_count_not_8",
                        "observed_cell_count": len(cells),
                    }
                )
                continue

            player_cell = cells[0]
            profile_paths = sorted(
                {
                    path
                    for anchor in player_cell.find_all("a", href=True)
                    if (path := _profile_path_from_href(str(anchor.get("href", "")))) is not None
                }
            )
            if len(profile_paths) != 1:
                errors.append(
                    {
                        "table_index": table_index,
                        "row_index": row_index,
                        "error": "profile_path_not_exactly_one_unique",
                        "profile_paths": profile_paths,
                    }
                )
                continue

            name_nodes = player_cell.find_all("span", class_="nfl-o-roster__player-name")
            if len(name_nodes) != 1:
                errors.append(
                    {
                        "table_index": table_index,
                        "row_index": row_index,
                        "error": "canonical_name_span_count_not_1",
                        "observed_count": len(name_nodes),
                    }
                )
                continue
            name_node = name_nodes[0]
            visible_name = normalize_text(name_node.get_text(" ", strip=True))
            canonical_data_name = normalize_text(name_node.get("data-name", ""))
            jersey = normalize_text(cells[1].get_text(" ", strip=True))
            position = normalize_text(cells[2].get_text(" ", strip=True))

            if not visible_name:
                errors.append({"table_index": table_index, "row_index": row_index, "error": "empty_visible_name"})
                continue
            if not canonical_data_name:
                errors.append({"table_index": table_index, "row_index": row_index, "error": "empty_canonical_data_name"})
                continue
            if not position:
                errors.append({"table_index": table_index, "row_index": row_index, "error": "empty_position"})
                continue

            rows.append(
                {
                    "team": team,
                    "visible_name": visible_name,
                    "canonical_data_name": canonical_data_name,
                    "jersey_number": jersey,
                    "position": position,
                    "profile_path": profile_paths[0],
                    "source_url": source_url,
                    "final_url": final_url,
                    "captured_at_utc": captured_at_utc,
                    "raw_html_sha256": raw_sha,
                }
            )

    profile_counts = Counter(str(row["profile_path"]) for row in rows)
    duplicate_profile_paths = sorted(path for path, count in profile_counts.items() if count > 1)
    diagnostics = {
        "team": team,
        "raw_html_sha256": raw_sha,
        "raw_html_bytes": len(raw_html),
        "exact_roster_table_count": exact_table_count,
        "candidate_row_count": candidate_row_count,
        "parsed_row_count": len(rows),
        "empty_jersey_row_count": sum(1 for row in rows if not row["jersey_number"]),
        "duplicate_profile_paths": duplicate_profile_paths,
        "duplicate_profile_path_count": len(duplicate_profile_paths),
        "parse_errors": errors,
        "parse_error_count": len(errors),
        "minimum_rows_gate_pass": len(rows) >= MIN_ROWS_PER_TEAM,
        "parser_team_gate_pass": (
            exact_table_count > 0
            and len(rows) >= MIN_ROWS_PER_TEAM
            and len(errors) == 0
            and len(duplicate_profile_paths) == 0
        ),
    }
    return rows, diagnostics


def _failed_http_diagnostics(team: str, raw_html: bytes, status_code: int) -> dict[str, Any]:
    return {
        "team": team,
        "raw_html_sha256": v1.sha256_bytes(raw_html),
        "raw_html_bytes": len(raw_html),
        "exact_roster_table_count": 0,
        "candidate_row_count": 0,
        "parsed_row_count": 0,
        "empty_jersey_row_count": 0,
        "duplicate_profile_paths": [],
        "duplicate_profile_path_count": 0,
        "parse_errors": [{"error": "http_status_not_success", "http_status": int(status_code)}],
        "parse_error_count": 1,
        "minimum_rows_gate_pass": False,
        "parser_team_gate_pass": False,
    }


def capture_and_parse_team(
    team: str,
    host: str,
    roster_path: str,
    *,
    get: Callable[..., object] = requests.get,
) -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    source_url = f"https://{host}{roster_path}"
    captured_at = v1.utc_now()
    result = v1.request_with_frozen_redirects(source_url, host, get=get)
    if not v1.host_allowed(result.url, host):
        raise RuntimeError(f"final_url_left_frozen_host:{result.url}")
    http_success = 200 <= result.status_code < 300
    if http_success:
        rows, parser_diagnostics = parse_team_html(
            team=team,
            source_url=source_url,
            final_url=result.url,
            captured_at_utc=captured_at,
            raw_html=result.content,
        )
    else:
        rows = []
        parser_diagnostics = _failed_http_diagnostics(team, result.content, result.status_code)
    record = {
        "team": team,
        "host": host,
        "source_url": source_url,
        "final_url": result.url,
        "captured_at_utc": captured_at,
        "http_status": result.status_code,
        "http_success": http_success,
        "content_type": result.headers.get("Content-Type") or result.headers.get("content-type") or "",
        **parser_diagnostics,
    }
    return record, result.content, rows


def run_held_out_capture(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    get: Callable[..., object] = requests.get,
) -> dict[str, Any]:
    contract = load_contract()
    clubs, roster_path = load_frozen_hosts()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    team_diagnostics: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    source_errors: list[dict[str, Any]] = []

    for team, host in clubs.items():
        try:
            diagnostic, raw, rows = capture_and_parse_team(team, host, roster_path, get=get)
            (raw_dir / f"{team}.html").write_bytes(raw)
            team_diagnostics.append(diagnostic)
            projection_rows.extend(rows)
        except Exception as exc:
            source_errors.append(
                {
                    "team": team,
                    "host": host,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    expected_teams = set(clubs)
    observed_teams = {str(row["team"]) for row in team_diagnostics}
    http_success_teams = {str(row["team"]) for row in team_diagnostics if row.get("http_success") is True}
    parser_pass_teams = {str(row["team"]) for row in team_diagnostics if row.get("parser_team_gate_pass") is True}
    total_parse_errors = sum(int(row.get("parse_error_count", 0)) for row in team_diagnostics)
    total_duplicate_profiles = sum(int(row.get("duplicate_profile_path_count", 0)) for row in team_diagnostics)

    gate_pass = (
        observed_teams == expected_teams
        and http_success_teams == expected_teams
        and parser_pass_teams == expected_teams
        and not source_errors
        and total_parse_errors == 0
        and total_duplicate_profiles == 0
    )

    (output_dir / "team_diagnostics.json").write_text(
        json.dumps(sorted(team_diagnostics, key=lambda row: row["team"]), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "roster_metadata.jsonl").open("w", encoding="utf-8") as handle:
        for row in sorted(projection_rows, key=lambda r: (r["team"], r["profile_path"])):
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    receipt = {
        "schema_version": "levline4-2026-official-club-roster-parser-v2-held-out",
        "contract_id": contract["contract_id"],
        "status": "PASS" if gate_pass else "FAIL",
        "held_out_capture_completed_at_utc": v1.utc_now(),
        "discovery_workflow_run_id": contract["discovery_evidence"]["workflow_run_id"],
        "discovery_artifact_id": contract["discovery_evidence"]["artifact_id"],
        "expected_team_count": 32,
        "captured_team_count": len(observed_teams),
        "http_success_team_count": len(http_success_teams),
        "parser_gate_pass_team_count": len(parser_pass_teams),
        "parsed_row_count": len(projection_rows),
        "minimum_parsed_rows_observed": min((int(row["parsed_row_count"]) for row in team_diagnostics), default=0),
        "maximum_parsed_rows_observed": max((int(row["parsed_row_count"]) for row in team_diagnostics), default=0),
        "empty_jersey_row_count": sum(int(row["empty_jersey_row_count"]) for row in team_diagnostics),
        "parse_error_count": total_parse_errors,
        "duplicate_profile_path_count": total_duplicate_profiles,
        "source_errors": source_errors,
        "held_out_parser_gate_pass": gate_pass,
        "official_club_roster_metadata_parser_qualified": gate_pass,
        "official_club_roster_source_is_independent_gsis_ground_truth": False,
        "player_identity_to_gsis_qualified": False,
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
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_held_out_capture(args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

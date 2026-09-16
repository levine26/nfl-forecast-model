from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research import levline4_2026_official_club_roster_surface_probe_v1 as v1

CONTRACT_PATH = Path("research/levline4_2026_official_club_roster_row_parser_v2_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_official_club_roster_row_parser_v2")
EXPECTED_HEADERS = ("Player", "#", "Pos", "HT", "WT", "Age", "Exp", "College")
PROJECTION_FIELDS = (
    "team",
    "player_name_rendered",
    "jersey_number_rendered",
    "position_rendered",
    "profile_url",
    "source_url",
    "final_url",
    "captured_at_utc",
    "raw_html_sha256",
)


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_profile_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") + "/"
    return f"https://{parsed.hostname}{path}"


def parse_team_rows(
    *,
    team: str,
    host: str,
    source_url: str,
    final_url: str,
    captured_at_utc: str,
    raw: bytes,
) -> tuple[list[dict], dict]:
    soup = BeautifulSoup(raw, "lxml")
    raw_sha = sha256_bytes(raw)
    rows: list[dict] = []
    errors: list[dict] = []
    exact_tables = 0
    seen_profile_urls: set[str] = set()

    for table_ordinal, table in enumerate(soup.find_all("table")):
        headers = tuple(normalize_text(th.get_text(" ", strip=True)) for th in table.find_all("th"))
        if headers != EXPECTED_HEADERS:
            continue
        exact_tables += 1
        for row_ordinal, tr in enumerate(table.find_all("tr")):
            cells = tr.find_all("td", recursive=False)
            if not cells:
                continue
            if len(cells) != 8:
                errors.append({
                    "kind": "row_width",
                    "table_ordinal": table_ordinal,
                    "row_ordinal": row_ordinal,
                    "observed_cells": len(cells),
                })
                continue

            values = [normalize_text(cell.get_text(" ", strip=True)) for cell in cells]
            player_name, jersey_number, position = values[0], values[1], values[2]
            if not player_name:
                errors.append({"kind": "empty_player_name", "table_ordinal": table_ordinal, "row_ordinal": row_ordinal})
                continue
            if not position:
                errors.append({"kind": "empty_position", "table_ordinal": table_ordinal, "row_ordinal": row_ordinal})
                continue

            matching_urls: set[str] = set()
            for anchor in cells[0].find_all("a", href=True):
                href = str(anchor.get("href", "")).strip()
                absolute = urljoin(final_url, href)
                parsed = urlparse(absolute)
                if not v1.PROFILE_PATH_RE.match(parsed.path):
                    continue
                if not v1.host_allowed(absolute, host):
                    errors.append({
                        "kind": "off_host_profile_url",
                        "table_ordinal": table_ordinal,
                        "row_ordinal": row_ordinal,
                        "url": absolute,
                    })
                    continue
                matching_urls.add(canonical_profile_url(absolute))

            if len(matching_urls) != 1:
                errors.append({
                    "kind": "profile_url_cardinality",
                    "table_ordinal": table_ordinal,
                    "row_ordinal": row_ordinal,
                    "observed_unique_urls": len(matching_urls),
                })
                continue
            profile_url = next(iter(matching_urls))
            if profile_url in seen_profile_urls:
                errors.append({
                    "kind": "duplicate_profile_url_within_team",
                    "table_ordinal": table_ordinal,
                    "row_ordinal": row_ordinal,
                    "profile_url": profile_url,
                })
                continue
            seen_profile_urls.add(profile_url)

            row = {
                "team": team,
                "player_name_rendered": player_name,
                "jersey_number_rendered": jersey_number,
                "position_rendered": position,
                "profile_url": profile_url,
                "source_url": source_url,
                "final_url": final_url,
                "captured_at_utc": captured_at_utc,
                "raw_html_sha256": raw_sha,
            }
            assert tuple(row) == PROJECTION_FIELDS
            rows.append(row)

    parser_pass = exact_tables >= 1 and len(rows) >= 50 and not errors
    diagnostic = {
        "team": team,
        "raw_html_sha256": raw_sha,
        "exact_header_tables": exact_tables,
        "parsed_identity_rows": len(rows),
        "blank_jersey_rows": sum(1 for row in rows if not row["jersey_number_rendered"]),
        "row_parse_errors": len(errors),
        "error_examples": errors[:50],
        "duplicate_profile_urls": sum(1 for error in errors if error["kind"] == "duplicate_profile_url_within_team"),
        "parser_pass": parser_pass,
        "roster_section_or_status_selected": False,
        "roster_section_or_status_interpreted": False,
    }
    return rows, diagnostic


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "LEVLINE-4-2026-OFFICIAL-CLUB-ROSTER-ROW-PARSER-V2"
    assert contract["status"] == "PREREGISTERED_HELD_OUT_LIVE_ROW_PARSER_QUALIFICATION"
    assert tuple(contract["frozen_parser"]["qualifying_table_header_vector_exact"]) == EXPECTED_HEADERS
    assert tuple(contract["status_free_projection"]["allowed_fields"]) == PROJECTION_FIELDS
    assert contract["source_lineage"]["underlying_source_independence_between_club_pages_and_nflverse_weekly_rosters_established"] is False
    assert contract["authority"]["production_authorized"] is False
    return contract


def run_capture(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    get: Callable[..., object] = requests.get,
) -> dict:
    contract = load_contract()
    v1_contract = v1.load_contract()
    clubs: dict[str, str] = v1_contract["source_discovery"]["clubs"]
    roster_path: str = v1_contract["source_discovery"]["roster_path"]

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    diagnostics: list[dict] = []
    errors: list[dict] = []
    http_success_teams: set[str] = set()

    for team, host in clubs.items():
        source_url = f"https://{host}{roster_path}"
        try:
            captured_at = v1.utc_now()
            result = v1.request_with_frozen_redirects(source_url, host, get=get)
            raw = result.content
            (raw_dir / f"{team}.html").write_bytes(raw)
            if not (200 <= result.status_code < 300):
                errors.append({"team": team, "kind": "http_status", "status": result.status_code})
                continue
            http_success_teams.add(team)
            rows, diagnostic = parse_team_rows(
                team=team,
                host=host,
                source_url=source_url,
                final_url=result.url,
                captured_at_utc=captured_at,
                raw=raw,
            )
            diagnostics.append(diagnostic)
            all_rows.extend(rows)
        except Exception as exc:
            errors.append({"team": team, "kind": "capture_exception", "error_type": type(exc).__name__, "error": str(exc)})

    diagnostics_by_team = {row["team"]: row for row in diagnostics}
    team_parser_pass_count = sum(1 for row in diagnostics if row["parser_pass"])
    total_row_parse_errors = sum(int(row["row_parse_errors"]) for row in diagnostics)
    duplicate_profile_urls = sum(int(row["duplicate_profile_urls"]) for row in diagnostics)
    minimum_rows = min((int(row["parsed_identity_rows"]) for row in diagnostics), default=0)
    expected_teams = set(clubs)

    projection_path = output_dir / "identity_rows.jsonl"
    with projection_path.open("w", encoding="utf-8") as fh:
        for row in sorted(all_rows, key=lambda r: (r["team"], r["profile_url"])):
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / "team_parser_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gate_pass = (
        len(http_success_teams) == 32
        and set(diagnostics_by_team) == expected_teams
        and team_parser_pass_count == 32
        and total_row_parse_errors == 0
        and duplicate_profile_urls == 0
        and len(all_rows) >= 1600
        and minimum_rows >= 50
        and not errors
    )
    receipt = {
        "schema_version": "levline4-2026-official-club-roster-row-parser-v2-execution",
        "contract_id": contract["contract_id"],
        "status": "PASS" if gate_pass else "FAIL",
        "executed_at_utc": v1.utc_now(),
        "expected_team_count": 32,
        "http_success_team_count": len(http_success_teams),
        "team_parser_pass_count": team_parser_pass_count,
        "parsed_identity_rows": len(all_rows),
        "minimum_rows_observed_per_team": minimum_rows,
        "total_row_parse_errors": total_row_parse_errors,
        "duplicate_profile_urls": duplicate_profile_urls,
        "blank_jersey_rows": sum(1 for row in all_rows if not row["jersey_number_rendered"]),
        "identity_projection_sha256": hashlib.sha256(projection_path.read_bytes()).hexdigest(),
        "identity_projection_fields": list(PROJECTION_FIELDS),
        "parser_qualification_gate_pass": gate_pass,
        "real_execution_is_self_qualifying": False,
        "official_club_roster_identity_row_parser_qualified": False,
        "underlying_source_independence_from_nflverse_established": False,
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
        "general_2026_player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_state_authorized": False,
        "availability_probability_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "f_st_01_frozen_2026_unchanged": True,
        "errors": errors,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_capture(args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

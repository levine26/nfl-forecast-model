#!/usr/bin/env python3
"""LevLine 4 browser-context NGS player-ID resolver V3 (research only).

The preregistered contract controls target selection, browser transport,
resolution, pass gates, and authority. V3 changes only transport relative to V2:
queries are issued through the public NFL NGS player-ID lookup page's own browser
context. No credentials, manual headers, alternate queries, fuzzy matching, or
same-version repair are allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GSIS_RE = re.compile(r"^00-[0-9]{7}$")
PLAYER_SEARCH_HOST = "api.ngs.nfl.com"
PLAYER_SEARCH_PATH = "/league/player/search"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def clean(value: Any) -> str:
    return str(value or "").strip()


def int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]+", text):
        return None
    return int(text)


def selection_key(row: dict[str, Any]) -> str:
    fields = [
        clean(row.get("team")),
        clean(row.get("visible_name")),
        clean(row.get("position")),
        clean(row.get("jersey_number")),
        clean(row.get("profile_path")),
    ]
    return sha256_bytes("\x1f".join(fields).encode("utf-8"))


def row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        clean(row.get("team")),
        clean(row.get("visible_name")),
        clean(row.get("profile_path")),
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: row is not an object")
        rows.append(value)
    return rows


def select_targets(
    rows: Iterable[dict[str, Any]], contract: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = contract["target_selection"]
    sentinel_norms = {normalize_name(x) for x in cfg["v1_sentinel_visible_name_exclusions"]}
    eligible = [
        dict(row)
        for row in rows
        if clean(row.get("visible_name"))
        and clean(row.get("team"))
        and clean(row.get("position"))
        and normalize_name(row.get("visible_name")) not in sentinel_norms
    ]

    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_team[clean(row["team"])].append(row)

    coverage: list[dict[str, Any]] = []
    for team in sorted(by_team):
        ordered = sorted(
            by_team[team],
            key=lambda row: (
                selection_key(row),
                clean(row.get("visible_name")),
                clean(row.get("profile_path")),
            ),
        )
        coverage.extend(ordered[:2])

    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_name[normalize_name(row.get("visible_name"))].append(row)
    ambiguity_groups = {
        name: group
        for name, group in by_name.items()
        if len({clean(row.get("team")).upper() for row in group}) > 1
    }
    ambiguity = [
        row
        for name in sorted(ambiguity_groups)
        for row in sorted(
            ambiguity_groups[name],
            key=lambda item: (
                clean(item.get("team")),
                clean(item.get("visible_name")),
                clean(item.get("profile_path")),
            ),
        )
    ]

    coverage_ids = {row_identity(row) for row in coverage}
    ambiguity_ids = {row_identity(row) for row in ambiguity}
    overlap_ids = coverage_ids & ambiguity_ids

    target_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in coverage:
        rid = row_identity(row)
        target_map[rid] = row
        strata[rid].append("coverage")
    for row in ambiguity:
        rid = row_identity(row)
        target_map[rid] = row
        strata[rid].append("source_name_ambiguity")

    targets: list[dict[str, Any]] = []
    for rid in sorted(target_map):
        row = dict(target_map[rid])
        row["_strata"] = strata[rid]
        row["_selection_key_sha256"] = selection_key(row)
        row["_normalized_visible_name"] = normalize_name(row["visible_name"])
        targets.append(row)

    diagnostics = {
        "eligible_row_count": len(eligible),
        "team_count": len(by_team),
        "coverage_target_count": len(coverage),
        "source_name_ambiguity_group_count": len(ambiguity_groups),
        "source_name_ambiguity_target_count": len(ambiguity),
        "overlap_count": len(overlap_ids),
        "total_target_count": len(targets),
        "ambiguity_groups": {
            name: [
                {
                    "team": clean(row.get("team")),
                    "visible_name": clean(row.get("visible_name")),
                    "position": clean(row.get("position")),
                    "jersey_number": clean(row.get("jersey_number")),
                    "profile_path": clean(row.get("profile_path")),
                }
                for row in sorted(
                    group,
                    key=lambda item: (
                        clean(item.get("team")),
                        clean(item.get("visible_name")),
                        clean(item.get("profile_path")),
                    ),
                )
            ]
            for name, group in sorted(ambiguity_groups.items())
        },
    }
    assert diagnostics["team_count"] == cfg["coverage_stratum"]["expected_team_count"]
    assert diagnostics["coverage_target_count"] == cfg["coverage_stratum"]["expected_target_count"]
    assert diagnostics["source_name_ambiguity_group_count"] == cfg["source_name_ambiguity_stratum"]["expected_duplicate_name_group_count"]
    assert diagnostics["source_name_ambiguity_target_count"] == cfg["source_name_ambiguity_stratum"]["expected_target_count"]
    assert diagnostics["overlap_count"] == cfg["expected_overlap_count"]
    assert diagnostics["total_target_count"] == cfg["expected_total_target_count"]
    return targets, diagnostics


def matches_player_search_response(url: str, exact_visible_name: str) -> bool:
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != PLAYER_SEARCH_HOST:
        return False
    if parsed.path != PLAYER_SEARCH_PATH:
        return False
    terms = urllib.parse.parse_qs(parsed.query, keep_blank_values=True).get("term", [])
    return len(terms) == 1 and terms[0] == exact_visible_name


def parse_players_body(status: int | None, body: bytes) -> tuple[dict[str, Any] | None, bool, str | None]:
    if status != 200:
        return None, False, f"http_status_{status}" if status is not None else "no_matching_browser_response"
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return None, False, f"json_parse_error:{type(exc).__name__}"
    if not isinstance(parsed, dict) or not isinstance(parsed.get("players"), list):
        return parsed if isinstance(parsed, dict) else None, False, "http_200_without_object_players_array"
    if not all(isinstance(player, dict) for player in parsed["players"]):
        return parsed, False, "players_array_contains_non_object"
    return parsed, True, None


def candidate_projection(player: dict[str, Any]) -> dict[str, Any]:
    return {
        "displayName": player.get("displayName"),
        "teamAbbr": player.get("teamAbbr"),
        "position": player.get("position"),
        "positionGroup": player.get("positionGroup"),
        "uniformNumber": player.get("uniformNumber"),
        "jerseyNumber": player.get("jerseyNumber"),
        "gsisId": player.get("gsisId"),
        "nflId": player.get("nflId"),
        "esbId": player.get("esbId"),
        "smartId": player.get("smartId"),
        "status": player.get("status"),
        "statusShortDescription": player.get("statusShortDescription"),
    }


def resolve_target(target: dict[str, Any], response_json: dict[str, Any] | None) -> dict[str, Any]:
    players = response_json.get("players", []) if isinstance(response_json, dict) else []
    target_name = normalize_name(target["visible_name"])
    target_team = clean(target["team"]).upper()
    matches = [
        player
        for player in players
        if isinstance(player, dict)
        and normalize_name(player.get("displayName")) == target_name
        and clean(player.get("teamAbbr")).upper() == target_team
    ]
    unique_name_team_candidate = len(matches) == 1
    candidate = matches[0] if unique_name_team_candidate else None
    gsis = clean(candidate.get("gsisId")) if candidate else ""
    gsis_valid = bool(GSIS_RE.fullmatch(gsis)) if candidate else False
    resolved = bool(candidate and gsis_valid)

    ngs_jersey = None
    if candidate:
        ngs_jersey = int_or_none(candidate.get("uniformNumber"))
        if ngs_jersey is None:
            ngs_jersey = int_or_none(candidate.get("jerseyNumber"))
    official_jersey = int_or_none(target.get("jersey_number"))
    comparable = resolved and official_jersey is not None and ngs_jersey is not None

    return {
        "normalized_target_name": target_name,
        "target_team": target_team,
        "response_player_count": len(players),
        "name_plus_team_match_count": len(matches),
        "matching_candidates": [candidate_projection(player) for player in matches],
        "unique_name_plus_team_candidate": unique_name_team_candidate,
        "selected_gsis_id": gsis if resolved else None,
        "selected_candidate_gsis_raw": gsis if candidate else None,
        "selected_candidate_gsis_valid": gsis_valid,
        "resolved": resolved,
        "official_jersey_int": official_jersey,
        "ngs_jersey_int": ngs_jersey,
        "jersey_comparable": comparable,
        "jersey_agrees": (official_jersey == ngs_jersey) if comparable else None,
        "selected_candidate": candidate_projection(candidate) if candidate else None,
    }


def evaluate_gates(
    targets: list[dict[str, Any]],
    results: list[dict[str, Any]],
    contract: dict[str, Any],
    *,
    page_loaded: bool,
    query_input_count: int,
) -> tuple[dict[str, Any], dict[str, bool], bool]:
    cfg = contract["frozen_pass_gates"]
    by_id = {tuple(result["target_row_identity"]): result for result in results}
    coverage_ids = [row_identity(target) for target in targets if "coverage" in target["_strata"]]
    ambiguity_ids = [row_identity(target) for target in targets if "source_name_ambiguity" in target["_strata"]]
    coverage_results = [by_id[rid] for rid in coverage_ids]
    ambiguity_results = [by_id[rid] for rid in ambiguity_ids]

    all_parseable = all(result["http_status"] == 200 and result["parseable_players_array"] for result in results)
    coverage_resolved = [result for result in coverage_results if result["resolved"]]
    ambiguity_resolved = [result for result in ambiguity_results if result["resolved"]]
    invalid_selected = [
        result for result in results
        if result["unique_name_plus_team_candidate"] and not result["selected_candidate_gsis_valid"]
    ]
    multiple_matches = [result for result in results if result["name_plus_team_match_count"] > 1]

    gsis_to_rows: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for result in results:
        if result["resolved"]:
            gsis_to_rows[result["selected_gsis_id"]].append(tuple(result["target_row_identity"]))
    duplicate_assignments = {
        gsis: ids for gsis, ids in gsis_to_rows.items() if len(set(ids)) > 1
    }

    comparable = [result for result in coverage_resolved if result["jersey_comparable"]]
    agreements = [result for result in comparable if result["jersey_agrees"]]
    coverage_resolution_fraction = len(coverage_resolved) / len(coverage_results) if coverage_results else 0.0
    ambiguity_resolution_fraction = len(ambiguity_resolved) / len(ambiguity_results) if ambiguity_results else 0.0
    comparable_fraction = len(comparable) / len(coverage_resolved) if coverage_resolved else 0.0
    agreement_fraction = len(agreements) / len(comparable) if comparable else 0.0

    metrics = {
        "target_count": len(results),
        "page_loaded": page_loaded,
        "query_input_count": query_input_count,
        "all_http_200_parseable_players_array": all_parseable,
        "coverage_target_count": len(coverage_results),
        "coverage_unique_resolution_count": len(coverage_resolved),
        "coverage_unique_resolution_fraction": coverage_resolution_fraction,
        "source_name_ambiguity_target_count": len(ambiguity_results),
        "source_name_ambiguity_unique_resolution_count": len(ambiguity_resolved),
        "source_name_ambiguity_unique_resolution_fraction": ambiguity_resolution_fraction,
        "invalid_selected_gsis_count": len(invalid_selected),
        "duplicate_selected_gsis_across_distinct_target_rows_count": len(duplicate_assignments),
        "same_target_multiple_name_plus_team_candidate_count": len(multiple_matches),
        "resolved_coverage_jersey_comparable_count": len(comparable),
        "resolved_coverage_jersey_comparable_fraction": comparable_fraction,
        "resolved_coverage_jersey_agreement_count": len(agreements),
        "resolved_coverage_jersey_agreement_fraction": agreement_fraction,
        "duplicate_selected_gsis_assignments": {
            gsis: [list(rid) for rid in ids]
            for gsis, ids in sorted(duplicate_assignments.items())
        },
    }
    gates = {
        "page_loaded_and_unique_query_input": page_loaded and query_input_count == 1,
        "all_70_targets_browser_http_200_parseable_players_array": all_parseable and len(results) == 70,
        "coverage_unique_resolution_minimum": (
            len(coverage_resolved) >= cfg["coverage_stratum_unique_resolution_minimum_count"]
            and coverage_resolution_fraction >= cfg["coverage_stratum_unique_resolution_minimum_fraction"]
        ),
        "source_name_ambiguity_unique_resolution_required": (
            len(ambiguity_resolved) == cfg["source_name_ambiguity_stratum_unique_resolution_required_count"]
            and ambiguity_resolution_fraction == cfg["source_name_ambiguity_stratum_unique_resolution_required_fraction"]
        ),
        "invalid_selected_gsis_zero": len(invalid_selected) <= cfg["invalid_selected_gsis_count_allowed"],
        "duplicate_selected_gsis_zero": len(duplicate_assignments) <= cfg["duplicate_selected_gsis_across_distinct_target_rows_allowed"],
        "same_target_multiple_name_plus_team_candidate_zero": len(multiple_matches) <= cfg["same_target_multiple_name_plus_team_candidate_count_allowed"],
        "resolved_coverage_jersey_comparable_minimum": comparable_fraction >= cfg["resolved_coverage_jersey_comparable_minimum_fraction"],
        "resolved_coverage_jersey_agreement_minimum": agreement_fraction >= cfg["resolved_coverage_jersey_agreement_minimum_fraction"],
    }
    return metrics, gates, all(gates.values())


def run_probe(contract_path: Path, roster_path: Path, output_dir: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    response_dir = output_dir / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["schema_version"] != "levline4-2026-ngs-player-id-browser-heldout-v3-contract":
        raise ValueError("unexpected contract schema")

    roster_sha = sha256_file(roster_path)
    roster_cfg = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    expected_roster_sha = roster_cfg["roster_metadata_sha256"]
    if roster_sha != expected_roster_sha:
        raise ValueError(f"roster metadata hash mismatch: {roster_sha} != {expected_roster_sha}")
    rows = load_jsonl(roster_path)
    if len(rows) != roster_cfg["row_count"]:
        raise ValueError(f"roster row count mismatch: {len(rows)} != {roster_cfg['row_count']}")

    targets, selection_diag = select_targets(rows, contract)
    (output_dir / "target_selection.json").write_text(
        json.dumps(
            {
                "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v3-target-selection",
                "contract_id": contract["contract_id"],
                "source_roster_metadata_sha256": roster_sha,
                "selection_diagnostics": selection_diag,
                "targets": targets,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (output_dir / "contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    browser_cfg = contract["browser_transport"]
    page_loaded = False
    query_input_count = 0
    browser_error: str | None = None
    results: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=browser_cfg["context_user_agent"],
            locale=browser_cfg["context_locale"],
        )
        page = context.new_page()
        input_locator = None
        try:
            page.goto(
                browser_cfg["page_url"],
                wait_until=browser_cfg["page_load_wait_until"],
                timeout=browser_cfg["page_load_timeout_ms"],
            )
            page.wait_for_timeout(browser_cfg["post_load_settle_ms"])
            page_loaded = True
            input_locator = page.get_by_placeholder(
                browser_cfg["query_input_placeholder_exact"], exact=True
            )
            query_input_count = input_locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"

        for idx, target in enumerate(targets, 1):
            exact_name = clean(target["visible_name"])
            response_url = None
            status = None
            content_type = None
            body = b""
            browser_action_error = browser_error
            requested_at = utc_now()

            if browser_error is None and input_locator is not None and query_input_count == 1:
                try:
                    with page.expect_response(
                        lambda r, name=exact_name: matches_player_search_response(r.url, name),
                        timeout=browser_cfg["response_timeout_ms"],
                    ) as response_info:
                        input_locator.fill(exact_name)
                        input_locator.press("Enter")
                    response = response_info.value
                    response_url = response.url
                    status = int(response.status)
                    content_type = str(response.headers.get("content-type", ""))
                    body = response.body()
                except Exception as exc:
                    browser_action_error = f"{type(exc).__name__}: {exc}"

            response_rel = f"responses/target_{idx:03d}.json"
            (output_dir / response_rel).write_bytes(body)
            parsed, parseable, semantic_error = parse_players_body(status, body)
            if browser_action_error:
                semantic_error = f"browser_action_error:{browser_action_error}"
            resolution = resolve_target(target, parsed if parseable else None)
            results.append({
                "target_index": idx,
                "target_row_identity": list(row_identity(target)),
                "target_visible_name": exact_name,
                "target_team": clean(target["team"]),
                "target_position": clean(target["position"]),
                "target_jersey_number": clean(target.get("jersey_number")),
                "target_profile_path": clean(target.get("profile_path")),
                "target_strata": target["_strata"],
                "selection_key_sha256": target["_selection_key_sha256"],
                "requested_at_utc": requested_at,
                "browser_action": "fill_exact_visible_name_then_press_enter_once",
                "browser_action_error": browser_action_error,
                "response_url": response_url,
                "http_status": status,
                "content_type": content_type,
                "parseable_players_array": parseable,
                "semantic_error": semantic_error,
                "response_relpath": response_rel,
                "response_bytes": len(body),
                "response_sha256": sha256_bytes(body),
                **resolution,
            })
        browser.close()

    with (output_dir / "target_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

    metrics, gates, passed = evaluate_gates(
        targets,
        results,
        contract,
        page_loaded=page_loaded,
        query_input_count=query_input_count,
    )
    authority_key = (
        "authority_if_and_only_if_all_v3_gates_pass"
        if passed
        else "authority_if_any_v3_gate_fails"
    )
    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v3-receipt",
        "contract_id": contract["contract_id"],
        "captured_at_utc": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "source_roster_metadata_sha256": roster_sha,
        "target_selection": selection_diag,
        "browser_transport": {
            "page_url": browser_cfg["page_url"],
            "page_loaded": page_loaded,
            "query_input_count": query_input_count,
            "browser_error": browser_error,
            "manual_headers_or_credentials_used": False,
            "browser_storage_state_persisted": False,
            "direct_http_fallback_used": False,
            "explicit_retry_used": False,
        },
        "metrics": metrics,
        "gates": gates,
        "authority": contract[authority_key],
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "f_st_01_frozen_2026_unchanged": True,
        "research_only": True,
        "production_paths_changed": False,
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--roster-metadata", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_probe(args.contract, args.roster_metadata, args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

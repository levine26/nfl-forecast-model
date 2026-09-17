from __future__ import annotations

"""Prospective Week 2 official-inactive -> NGS GSIS application V1.

Research-only. The frozen contract is authoritative. This module deliberately does not
estimate an availability probability, attach player value, modify a forecast, or use NGS
status fields. Each real Week 2 Sunday due cohort receives at most one canonical
player-level attempt.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import polars as pl
from bs4 import BeautifulSoup, Tag

from research.inactive_article_player_parser_v1 import (
    HEADING_TAGS,
    _first_list_before_next_heading,
    _heading_team,
    parse_inactive_article_html,
)
from research.levline4_prospective_inactive_execution_v1 import (
    CANDIDATE_SOURCE_KIND,
    _due_teams,
    _latest_due_observation,
    _week_from_due_games,
)
from research.run_levline4_prospective_inactive_execution_v1 import cohort_is_sunday_eastern
from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as base
from research import levline4_2026_ngs_player_id_browser_heldout_v7 as v7
from research import levline4_2026_ngs_player_id_browser_heldout_v8 as v8

CONTRACT_ID = "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-NGS-APPLICATION-V1"
SUPPORTED_WEEK = 2
ROSTER_METADATA_SHA256 = "90c3974677862b8838acf2afaf6bec07087ce9784a7ab01491d8dcfd1f41489f"
GLOBAL_PROJECTION_SHA256 = "023d7e5b652f56c1b41c432f394d81da60e2ab4df287daeb3baa1be76d6f2603"
V8_ARTIFACT_ID = 10481385995
V8_RUN_ID = 35183093816
V8_HEAD_SHA = "4dbe2f94ffd2d30aac600747ce5fa7e1c29cec93"
V8_ARTIFACT_DIGEST = "sha256:b462438d7c6d6cdb292c634b264fafc151c9929f23b931ff36017e86e34199aa"
GSIS_RE = base.GSIS_RE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{number}") from exc
    return out


def append_jsonl_unique(path: Path, row: dict[str, Any], key: str) -> None:
    existing = read_jsonl(path)
    value = str(row.get(key) or "")
    if not value:
        raise ValueError(f"missing unique key {key}")
    if any(str(item.get(key) or "") == value for item in existing):
        raise ValueError(f"duplicate {key}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected application contract_id")
    if contract.get("status") != "PREREGISTERED_BEFORE_FIRST_WEEK2_REAL_TARGET_EXPOSURE":
        raise ValueError("application contract status drifted")
    return contract


def verify_v8_preservation(path: Path) -> dict[str, Any]:
    preserved = json.loads(path.read_text(encoding="utf-8"))
    assert int(preserved["source_actions_artifact_id"]) == V8_ARTIFACT_ID
    assert int(preserved["source_workflow_run_id"]) == V8_RUN_ID
    assert preserved["source_head_sha"] == V8_HEAD_SHA
    assert preserved["actions_artifact_digest"] == V8_ARTIFACT_DIGEST
    assert preserved["canonical_result"] == "PASS"
    authority_key = (
        "bounded_official_roster_to_ngs_gsis_candidate_bridge_qualified"
        if "bounded_official_roster_to_ngs_gsis_candidate_bridge_qualified" in preserved
        else "official_roster_to_ngs_gsis_candidate_bridge_qualified_for_separately_preregistered_heldout_application"
    )
    assert preserved[authority_key] is True
    assert preserved["production_authorized"] is False
    return preserved


def cohort_key(due_games: Iterable[dict[str, Any]]) -> str:
    game_ids = sorted(str(game.get("game_id") or "") for game in due_games)
    if not game_ids or any(not game_id for game_id in game_ids):
        raise ValueError("due games require nonempty game_id")
    payload = "|".join([CONTRACT_ID, str(SUPPORTED_WEEK), ",".join(game_ids)]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def structural_team_set(raw: bytes) -> set[str]:
    """Read recognized team sections without extracting player-level content."""
    soup = BeautifulSoup(raw.decode("utf-8", errors="replace"), "html.parser")
    teams: set[str] = set()
    for heading in soup.find_all(list(HEADING_TAGS)):
        if not isinstance(heading, Tag):
            continue
        team = _heading_team(heading)
        if team and _first_list_before_next_heading(heading) is not None:
            teams.add(team)
    return teams


def select_structural_article(
    archive_dir: Path,
    observation: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    due_games = list(observation.get("due_games") or [])
    due_teams = _due_teams(due_games)
    matches: list[dict[str, Any]] = []
    for source in observation.get("sources") or []:
        if source.get("source_kind") != CANDIDATE_SOURCE_KIND:
            continue
        if int(source.get("http_status", 999)) >= 400:
            continue
        relpath = str(source.get("raw_object_relpath") or "")
        expected_sha = str(source.get("raw_body_sha256") or "").lower()
        if not relpath or len(expected_sha) != 64:
            continue
        path = archive_dir / relpath
        if not path.exists():
            raise FileNotFoundError(f"captured inactive article missing: {path}")
        with gzip.open(path, "rb") as handle:
            raw = handle.read()
        observed_sha = sha256_bytes(raw)
        if observed_sha != expected_sha:
            raise RuntimeError(f"inactive article SHA mismatch: {relpath}")
        teams = structural_team_set(raw)
        if due_teams.issubset(teams):
            matches.append(
                {
                    "source": dict(source),
                    "raw": raw,
                    "raw_sha256": observed_sha,
                    "structural_teams": sorted(teams),
                }
            )
    distinct = sorted({item["raw_sha256"] for item in matches})
    if not distinct:
        return None, []
    if len(distinct) != 1:
        raise RuntimeError(f"multiple distinct structurally matching inactive articles: {distinct}")
    same_body = [item for item in matches if item["raw_sha256"] == distinct[0]]
    selected = sorted(same_body, key=lambda item: str(item["source"].get("url") or ""))[0]
    return selected, matches


def load_roster_metadata(path: Path) -> list[dict[str, Any]]:
    if base.sha256_file(path) != ROSTER_METADATA_SHA256:
        raise RuntimeError("official roster metadata SHA drifted")
    rows = base.load_jsonl(path)
    if len(rows) != 2463:
        raise RuntimeError(f"official roster row count drifted: {len(rows)}")
    return rows


def canonical_roster_enrichment(
    team: str,
    rendered_name: str,
    roster_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    team = base.clean(team).upper()
    target_key = base.name_key(rendered_name)
    candidates: list[dict[str, Any]] = []
    for row in roster_rows:
        if base.clean(row.get("team")).upper() != team:
            continue
        visible_key = base.name_key(row.get("visible_name"))
        canonical_query = v7.canonical_query_name(row.get("canonical_data_name"))
        canonical_key = base.name_key(canonical_query) if canonical_query else ""
        if target_key and target_key in {visible_key, canonical_key}:
            candidates.append(
                {
                    "team": team,
                    "visible_name": base.clean(row.get("visible_name")),
                    "canonical_data_name": base.clean(row.get("canonical_data_name")),
                    "canonical_query_name": canonical_query,
                    "visible_name_key": visible_key,
                    "canonical_name_key": canonical_key or None,
                }
            )
    unique = len(candidates) == 1
    selected = candidates[0] if unique else None
    return {
        "target_team": team,
        "target_rendered_name": base.clean(rendered_name),
        "target_name_key": target_key,
        "matching_roster_row_count": len(candidates),
        "matching_roster_rows": candidates,
        "unique_enrichment": unique,
        "canonical_data_name": selected["canonical_data_name"] if selected else None,
        "canonical_query_name": selected["canonical_query_name"] if selected else None,
        "position_used": False,
        "jersey_used": False,
        "profile_path_used": False,
        "status_used": False,
        "roster_match_resolves_gsis": False,
    }


def application_query_plan(rendered_name: str, enrichment: dict[str, Any]) -> list[tuple[str, str]]:
    pseudo_target = {
        "visible_name": rendered_name,
        "canonical_data_name": (
            enrichment.get("canonical_data_name") if enrichment.get("unique_enrichment") else None
        ),
    }
    return v8.query_plan(pseudo_target)


def resolve_payload(
    *,
    team: str,
    rendered_name: str,
    enrichment: dict[str, Any],
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    players = payload.get("players", []) if isinstance(payload, dict) else []
    visible_key = base.name_key(rendered_name)
    canonical_query = enrichment.get("canonical_query_name") if enrichment.get("unique_enrichment") else None
    canonical_key = base.name_key(canonical_query) if canonical_query else ""
    allowed_keys = {visible_key}
    if canonical_key:
        allowed_keys.add(canonical_key)
    target_team = base.clean(team).upper()
    primary = [
        player
        for player in players
        if isinstance(player, dict)
        and base.name_key(player.get("displayName")) in allowed_keys
        and base.team_matches(target_team, player.get("teamAbbr"))
    ]
    ambiguous = len(primary) > 1
    candidate = primary[0] if len(primary) == 1 else None
    gsis = base.clean(candidate.get("gsisId")) if candidate else ""
    gsis_valid = bool(candidate and GSIS_RE.fullmatch(gsis))
    resolved = bool(candidate and gsis_valid)
    selected_key = base.name_key(candidate.get("displayName")) if candidate else ""
    if candidate and canonical_key and selected_key == canonical_key and canonical_key != visible_key:
        representation = "source_canonical"
    elif candidate and selected_key == visible_key:
        representation = "rendered"
    elif candidate and canonical_key and selected_key == canonical_key:
        representation = "source_canonical_same_semantic_key"
    else:
        representation = None
    return {
        "target_rendered_name_key": visible_key,
        "target_source_canonical_query_name": canonical_query,
        "target_source_canonical_name_key": canonical_key or None,
        "target_allowed_name_keys": sorted(allowed_keys),
        "target_team": target_team,
        "response_player_count": len(players),
        "primary_candidate_count": len(primary),
        "primary_candidates": [base.candidate_projection(player) for player in primary],
        "ambiguous": ambiguous,
        "tiebreak_applied": False,
        "selected_candidate": base.candidate_projection(candidate) if candidate else None,
        "selected_candidate_gsis_raw": gsis if candidate else None,
        "selected_candidate_gsis_valid": gsis_valid,
        "selected_gsis_id": gsis if resolved else None,
        "selected_name_representation": representation,
        "resolved": resolved,
    }


def load_global_index(path: Path) -> dict[str, set[str]]:
    raw = path.read_bytes()
    observed_sha = sha256_bytes(raw)
    if observed_sha != GLOBAL_PROJECTION_SHA256:
        raise RuntimeError(f"global projection SHA mismatch: {observed_sha}")
    frame = pl.read_parquet(path)
    required = {"gsis_id", "display_name"}
    if not required.issubset(frame.columns):
        raise RuntimeError("global projection missing gsis_id/display_name")
    forbidden = {"latest_team", "status", "last_season", "jersey_number"}
    if forbidden & set(frame.columns):
        raise RuntimeError("global audit projection contains forbidden team/status fields")
    index: dict[str, set[str]] = defaultdict(set)
    for row in frame.select(["gsis_id", "display_name"]).to_dicts():
        key = base.name_key(row.get("display_name"))
        gsis = base.clean(row.get("gsis_id"))
        if key and gsis:
            index[key].add(gsis)
    return index


def audit_results(
    results: Iterable[dict[str, Any]],
    global_index: dict[str, set[str]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for result in results:
        selected = result.get("selected_candidate") or {}
        display_key = base.name_key(selected.get("displayName")) if selected else ""
        candidates = sorted(global_index.get(display_key, set())) if display_key else []
        resolved = result.get("selected_gsis_id")
        if not resolved:
            state = "APPLICATION_NOT_RESOLVED"
        elif len(candidates) == 1 and candidates[0] == resolved:
            state = "CROSS_SOURCE_CORROBORATED"
        elif len(candidates) == 1 and candidates[0] != resolved:
            state = "CROSS_SOURCE_CONTRADICTION"
        else:
            state = "NOT_AUDITABLE"
        output.append(
            {
                "target_id": result["target_id"],
                "team": result["team"],
                "player_name_rendered": result["player_name_rendered"],
                "application_gsis_id": resolved,
                "selected_ngs_display_name_key": display_key or None,
                "global_display_name_candidate_gsis_ids": candidates,
                "audit_state": state,
                "global_source_used_as_fallback": False,
                "global_source_used_for_selection": False,
            }
        )
    return output


def evaluate(
    *,
    target_rows: list[dict[str, Any]],
    results: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    source_sha_verified: bool,
    all_due_teams_present: bool,
    page_loaded: bool,
    query_input_count: int,
    contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bool], bool]:
    attempts = [attempt for result in results for attempt in result["query_attempts"]]
    resolved = [result for result in results if result["resolved"]]
    ambiguous = [result for result in results if result["ambiguous"]]
    invalid = [
        result
        for result in results
        if result["selected_candidate"] is not None and not result["selected_candidate_gsis_valid"]
    ]
    gsis_to_targets: dict[str, list[str]] = defaultdict(list)
    for result in resolved:
        gsis_to_targets[str(result["selected_gsis_id"])].append(str(result["target_id"]))
    duplicates = {
        gsis: ids for gsis, ids in gsis_to_targets.items() if len(set(ids)) > 1
    }
    contradictions = [audit for audit in audits if audit["audit_state"] == "CROSS_SOURCE_CONTRADICTION"]
    target_ids = [str(row["target_id"]) for row in target_rows]
    result_ids = [str(row["target_id"]) for row in results]
    accounted = (
        len(target_ids) == len(set(target_ids))
        and len(result_ids) == len(set(result_ids))
        and set(target_ids) == set(result_ids)
    )
    resolution_fraction = len(resolved) / len(target_rows) if target_rows else 0.0
    every_transport_ok = bool(attempts) and all(
        attempt["http_status"] == 200 and attempt["parseable_players_array"]
        for attempt in attempts
    )
    cfg = contract["frozen_per_cohort_pass_gates"]
    metrics = {
        "target_count": len(target_rows),
        "resolved_count": len(resolved),
        "resolved_fraction": resolution_fraction,
        "ambiguous_target_count": len(ambiguous),
        "unresolved_nonambiguous_count": len(target_rows) - len(resolved) - len(ambiguous),
        "executed_query_attempt_count": len(attempts),
        "all_executed_query_attempts_http_200_parseable_players_array": every_transport_ok,
        "invalid_selected_gsis_count": len(invalid),
        "duplicate_selected_gsis_across_distinct_inactive_rows_count": len(duplicates),
        "duplicate_selected_gsis_assignments": duplicates,
        "cross_source_contradiction_count": len(contradictions),
        "cross_source_audit_counts": dict(Counter(audit["audit_state"] for audit in audits)),
        "targets_accounted_exactly_once": accounted,
    }
    gates = {
        "selected_raw_article_sha_verified": source_sha_verified,
        "all_due_teams_present_in_parsed_article": all_due_teams_present,
        "target_count_positive": len(target_rows) > 0,
        "every_target_accounted_exactly_once": accounted,
        "page_loaded_and_unique_query_input_required": page_loaded and query_input_count == 1,
        "every_executed_query_attempt_http_200_parseable_players_array": every_transport_ok,
        "unique_resolution_minimum_fraction": (
            resolution_fraction >= float(cfg["unique_resolution_minimum_fraction"])
        ),
        "ambiguous_target_count_allowed": (
            len(ambiguous) <= int(cfg["ambiguous_target_count_allowed"])
        ),
        "invalid_selected_gsis_count_allowed": (
            len(invalid) <= int(cfg["invalid_selected_gsis_count_allowed"])
        ),
        "duplicate_selected_gsis_across_distinct_inactive_rows_allowed": (
            len(duplicates)
            <= int(cfg["duplicate_selected_gsis_across_distinct_inactive_rows_allowed"])
        ),
        "unique_cross_source_different_gsis_contradictions_allowed": (
            len(contradictions)
            <= int(cfg["unique_cross_source_different_gsis_contradictions_allowed"])
        ),
    }
    return metrics, gates, all(gates.values())


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def frozen_authority(contract: dict[str, Any], passed: bool) -> dict[str, Any]:
    key = "authority_if_per_cohort_passes" if passed else "authority_if_any_per_cohort_gate_fails"
    return dict(contract[key])


def _canonical_index(output_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("cohort_key")): row
        for row in read_jsonl(output_dir / "canonical_results.jsonl")
        if row.get("cohort_key")
    }


def run_application(
    *,
    contract_path: Path,
    archive_dir: Path,
    roster_metadata_path: Path,
    global_projection_path: Path,
    v8_preservation_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    verify_v8_preservation(v8_preservation_path)
    observation = _latest_due_observation(archive_dir)
    if observation is None:
        return {
            "contract_id": CONTRACT_ID,
            "status": "WAITING_NO_DUE_CAPTURE",
            "target_empirical_boundary_crossed": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    due_games = list(observation.get("due_games") or [])
    week = _week_from_due_games(due_games)
    if week != SUPPORTED_WEEK or not cohort_is_sunday_eastern(due_games):
        return {
            "contract_id": CONTRACT_ID,
            "status": "SKIPPED_OUTSIDE_SUPPORTED_WEEK2_SUNDAY",
            "week": week,
            "target_empirical_boundary_crossed": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
    key = cohort_key(due_games)
    previous = _canonical_index(output_dir).get(key)
    if previous:
        return {
            "contract_id": CONTRACT_ID,
            "status": "SKIPPED_CANONICAL_COHORT_ALREADY_FROZEN",
            "cohort_key": key,
            "canonical_status": previous.get("status"),
            "canonical_attempt_id": previous.get("attempt_id"),
            "target_empirical_boundary_crossed": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    try:
        selected, structural_matches = select_structural_article(archive_dir, observation)
    except Exception as exc:
        return {
            "contract_id": CONTRACT_ID,
            "status": "PRE_TARGET_TECHNICAL_FAIL",
            "cohort_key": key,
            "error": f"{type(exc).__name__}: {exc}",
            "target_empirical_boundary_crossed": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
    if selected is None:
        return {
            "contract_id": CONTRACT_ID,
            "status": "WAITING_NO_STRUCTURALLY_MATCHING_ARTICLE",
            "cohort_key": key,
            "captured_at_utc": observation.get("captured_at_utc"),
            "target_empirical_boundary_crossed": False,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    # The qualified player parser invocation below is the frozen empirical boundary.
    attempt_id = hashlib.sha256(
        "|".join([CONTRACT_ID, key, selected["raw_sha256"]]).encode("utf-8")
    ).hexdigest()
    cohort_dir = output_dir / "cohorts" / key
    cohort_dir.mkdir(parents=True, exist_ok=True)
    boundary_time = utc_now()
    source_receipt = {
        "contract_id": CONTRACT_ID,
        "cohort_key": key,
        "attempt_id": attempt_id,
        "boundary_crossed_at_utc": boundary_time,
        "archive_observation_captured_at_utc": observation.get("captured_at_utc"),
        "due_game_ids": sorted(str(game.get("game_id") or "") for game in due_games),
        "selected_source_url": selected["source"].get("url"),
        "selected_raw_object_relpath": selected["source"].get("raw_object_relpath"),
        "selected_raw_body_sha256": selected["raw_sha256"],
        "selected_structural_teams": selected["structural_teams"],
        "structural_matching_source_records": len(structural_matches),
        "target_empirical_boundary_crossed": True,
    }
    (cohort_dir / "source_receipt.json").write_text(
        json.dumps(source_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    def freeze_failure(status: str, error: str, **extra: Any) -> dict[str, Any]:
        receipt = {
            **source_receipt,
            "schema_version": "levline4-2026-week2-inactive-ngs-application-v1-receipt",
            "status": status,
            "error": error,
            "scientific_pass": False,
            "metrics": extra.pop("metrics", {}),
            "gates": extra.pop("gates", {}),
            "authority": frozen_authority(contract, False),
            "completed_2026_outcomes_used_for_design_or_selection": 0,
            "postgame_participation_used": False,
            "week2_inactive_execution_evidence_used_for_design": False,
            "future_information_used_to_repair_point_in_time_state": False,
            "f_st_01_frozen_2026_unchanged": True,
            "research_only": True,
            "production_paths_changed": False,
            **extra,
        }
        (cohort_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        append_jsonl_unique(output_dir / "canonical_results.jsonl", receipt, "cohort_key")
        return receipt

    try:
        parsed = parse_inactive_article_html(
            selected["raw"],
            source_url=str(selected["source"].get("url") or ""),
            captured_at_utc=str(observation.get("captured_at_utc") or ""),
            raw_html_sha256=selected["raw_sha256"],
        )
    except Exception as exc:
        return freeze_failure("POST_TARGET_TECHNICAL_FAIL", f"{type(exc).__name__}: {exc}")

    due_teams = _due_teams(due_games)
    target_rows = [dict(row) for row in parsed.rows if str(row.get("team")) in due_teams]
    observed_teams = {str(row.get("team")) for row in target_rows}
    all_due_teams_present = due_teams.issubset(observed_teams)
    if not target_rows or not all_due_teams_present:
        write_jsonl(cohort_dir / "target_rows.jsonl", target_rows)
        return freeze_failure(
            "SCIENTIFIC_FAIL",
            "qualified parser output did not contain a positive complete due-cohort target population",
            parsed_article_audit=parsed.audit,
        )

    roster_rows = load_roster_metadata(roster_metadata_path)
    seen_ids: set[str] = set()
    enrichments: list[dict[str, Any]] = []
    for row in target_rows:
        rendered = str(row["player_name_rendered"]).strip()
        team = str(row["team"]).strip().upper()
        target_id = hashlib.sha256(
            "|".join(
                [CONTRACT_ID, key, team, base.name_key(rendered), selected["raw_sha256"]]
            ).encode("utf-8")
        ).hexdigest()
        if target_id in seen_ids:
            return freeze_failure("POST_TARGET_TECHNICAL_FAIL", f"duplicate target_id: {target_id}")
        seen_ids.add(target_id)
        row["target_id"] = target_id
        row["cohort_key"] = key
        enrichment = canonical_roster_enrichment(team, rendered, roster_rows)
        enrichment["target_id"] = target_id
        enrichments.append(enrichment)
    write_jsonl(cohort_dir / "target_rows.jsonl", target_rows)
    write_jsonl(cohort_dir / "roster_enrichment.jsonl", enrichments)
    enrichment_by_id = {row["target_id"]: row for row in enrichments}

    browser_cfg = contract["frozen_ngs_query_and_resolution"]
    page_loaded = False
    query_input_count = 0
    browser_error: str | None = None
    results: list[dict[str, Any]] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="LevLine-Research/1.0 (+https://github.com/levine26/nfl-forecast-model)",
                locale="en-US",
            )
            page = context.new_page()
            locator = None
            try:
                page.goto(
                    browser_cfg["page_url"],
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                page.wait_for_timeout(1500)
                page_loaded = True
                locator = page.get_by_placeholder("Search By Name (min 3 chars)", exact=True)
                query_input_count = locator.count()
            except Exception as exc:
                browser_error = f"{type(exc).__name__}: {exc}"

            responses_dir = cohort_dir / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            for target_index, target in enumerate(target_rows, 1):
                target_id = target["target_id"]
                rendered = str(target["player_name_rendered"])
                team = str(target["team"])
                enrichment = enrichment_by_id[target_id]
                planned: list[dict[str, Any]] = []
                attempts: list[dict[str, Any]] = []
                chosen_payload: dict[str, Any] | None = None
                action_error = browser_error
                may_execute_next = browser_error is None and locator is not None and query_input_count == 1
                for query_kind, query in application_query_plan(rendered, enrichment):
                    valid = v8.grammar_valid(query)
                    plan_item = {
                        "query_kind": query_kind,
                        "query": query,
                        "grammar_valid": valid,
                        "disposition": None,
                    }
                    if not valid:
                        plan_item["disposition"] = "skipped_pre_dispatch_query_grammar"
                        planned.append(plan_item)
                        continue
                    if not may_execute_next:
                        plan_item["disposition"] = "not_executed_after_stop"
                        planned.append(plan_item)
                        continue
                    plan_item["disposition"] = "executed"
                    planned.append(plan_item)
                    body = b""
                    status = None
                    response_url = None
                    content_type = None
                    attempt_error = None
                    try:
                        with page.expect_response(
                            lambda response, expected=query: base.matches_player_search_response(
                                response.url, expected
                            ),
                            timeout=15000,
                        ) as response_info:
                            locator.fill(query)
                            locator.press("Enter")
                        response = response_info.value
                        response_url = response.url
                        status = int(response.status)
                        content_type = str(response.headers.get("content-type", ""))
                        body = response.body()
                    except Exception as exc:
                        attempt_error = f"{type(exc).__name__}: {exc}"
                        action_error = attempt_error
                    attempt_index = len(attempts) + 1
                    relpath = f"responses/target_{target_index:03d}_attempt_{attempt_index}.json"
                    (cohort_dir / relpath).write_bytes(body)
                    parsed_body, parseable, semantic_error = base.parse_players_body(status, body)
                    player_count = (
                        len(parsed_body.get("players", []))
                        if parseable and isinstance(parsed_body, dict)
                        else 0
                    )
                    attempts.append(
                        {
                            "attempt_index": attempt_index,
                            "query_kind": query_kind,
                            "query": query,
                            "response_url": response_url,
                            "http_status": status,
                            "content_type": content_type,
                            "parseable_players_array": parseable,
                            "player_count": player_count,
                            "semantic_error": semantic_error,
                            "browser_action_error": attempt_error,
                            "response_relpath": relpath,
                            "response_bytes": len(body),
                            "response_sha256": sha256_bytes(body),
                        }
                    )
                    if attempt_error or not parseable:
                        may_execute_next = False
                    elif player_count > 0:
                        chosen_payload = parsed_body
                        may_execute_next = False
                    else:
                        may_execute_next = True

                resolution = resolve_payload(
                    team=team,
                    rendered_name=rendered,
                    enrichment=enrichment,
                    payload=chosen_payload,
                )
                results.append(
                    {
                        "target_index": target_index,
                        "target_id": target_id,
                        "cohort_key": key,
                        "team": team,
                        "player_name_rendered": rendered,
                        "position_rendered": target.get("position_rendered"),
                        "emergency_third_qb": bool(target.get("emergency_third_qb")),
                        "raw_evidence_sha256": selected["raw_sha256"],
                        "source_known_by_utc": target.get("source_known_by_utc"),
                        "roster_enrichment_unique": bool(enrichment.get("unique_enrichment")),
                        "browser_action_error": action_error,
                        "planned_query_representations": planned,
                        "query_attempts": attempts,
                        **resolution,
                    }
                )
            browser.close()
    except Exception as exc:
        write_jsonl(cohort_dir / "target_results.jsonl", results)
        return freeze_failure(
            "POST_TARGET_TECHNICAL_FAIL",
            f"{type(exc).__name__}: {exc}",
            parsed_article_audit=parsed.audit,
            partial_result_count=len(results),
        )

    write_jsonl(cohort_dir / "target_results.jsonl", results)

    try:
        global_index = load_global_index(global_projection_path)
        audits = audit_results(results, global_index)
    except Exception as exc:
        return freeze_failure(
            "POST_TARGET_TECHNICAL_FAIL",
            f"global audit failed: {type(exc).__name__}: {exc}",
            parsed_article_audit=parsed.audit,
        )
    write_jsonl(cohort_dir / "global_audit.jsonl", audits)

    metrics, gates, passed = evaluate(
        target_rows=target_rows,
        results=results,
        audits=audits,
        source_sha_verified=True,
        all_due_teams_present=all_due_teams_present,
        page_loaded=page_loaded,
        query_input_count=query_input_count,
        contract=contract,
    )
    receipt = {
        **source_receipt,
        "schema_version": "levline4-2026-week2-inactive-ngs-application-v1-receipt",
        "status": "PASS" if passed else "SCIENTIFIC_FAIL",
        "scientific_pass": passed,
        "parsed_article_audit": parsed.audit,
        "browser_transport": {
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
        "authority": frozen_authority(contract, passed),
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "future_information_used_to_repair_point_in_time_state": False,
        "f_st_01_frozen_2026_unchanged": True,
        "research_only": True,
        "production_paths_changed": False,
    }
    (cohort_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    append_jsonl_unique(output_dir / "canonical_results.jsonl", receipt, "cohort_key")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=Path("research_outputs/inactive_article_source_archive_v1"),
    )
    parser.add_argument("--roster-metadata", type=Path, required=True)
    parser.add_argument("--global-projection", type=Path, required=True)
    parser.add_argument("--v8-preservation", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/levline4_prospective_inactive_ngs_v1"),
    )
    args = parser.parse_args()
    receipt = run_application(
        contract_path=args.contract,
        archive_dir=args.archive_dir,
        roster_metadata_path=args.roster_metadata,
        global_projection_path=args.global_projection,
        v8_preservation_path=args.v8_preservation,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt.get("status") in {
        "SCIENTIFIC_FAIL",
        "POST_TARGET_TECHNICAL_FAIL",
        "PRE_TARGET_TECHNICAL_FAIL",
    }:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

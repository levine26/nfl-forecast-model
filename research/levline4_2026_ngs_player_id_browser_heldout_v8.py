#!/usr/bin/env python3
"""LevLine 4 NGS browser-context held-out resolver V8 (research only).

V8 retains frozen V7 identity semantics and adds exactly one preregistered
transport rule: planned query representations that fail the frozen first-party
NGS term grammar are skipped before dispatch, without rewriting characters.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as base
from research import levline4_2026_ngs_player_id_browser_heldout_v7 as v7

TERM_RE = re.compile(r"^[a-zA-Z\s'.-]+$")


def grammar_valid(value: Any) -> bool:
    return bool(TERM_RE.fullmatch(base.clean(value)))


def selection_key(row: dict[str, Any], contract: dict[str, Any]) -> str:
    cfg = contract["target_selection"]
    fields = [
        base.clean(row.get("team")),
        base.clean(row.get("visible_name")),
        base.clean(row.get("position")),
        base.clean(row.get("jersey_number")),
        base.clean(row.get("profile_path")),
    ]
    payload = cfg["selection_salt"] + "\x1e" + "\x1f".join(fields)
    return base.sha256_bytes(payload.encode("utf-8"))


def query_plan(target: dict[str, Any]) -> list[tuple[str, str]]:
    """Generate frozen V7 representations plus the pre-execution V8 addendum."""
    visible = base.clean(target.get("visible_name"))
    plan: list[tuple[str, str]] = [("exact_visible_name", visible)]
    stripped = base.strip_terminal_suffix(visible)
    if stripped and stripped != visible:
        plan.append(("terminal_suffix_stripped", stripped))
    canonical = v7.canonical_query_name(target.get("canonical_data_name"))
    canonical_required_by_addendum = bool(
        canonical
        and canonical != visible
        and not grammar_valid(visible)
        and grammar_valid(canonical)
    )
    if (
        canonical
        and canonical not in {query for _, query in plan}
        and (
            base.name_key(canonical) != base.name_key(visible)
            or canonical_required_by_addendum
        )
    ):
        plan.append(("source_canonical_name", canonical))
    surname = base.surname_only(visible)
    if surname and surname not in {query for _, query in plan}:
        plan.append(("surname_only", surname))
    return plan[:4]


def select_targets(
    rows: Iterable[dict[str, Any]],
    contract: dict[str, Any],
    v3_selection: dict[str, Any],
    v5_selection: dict[str, Any],
    v6_selection: dict[str, Any],
    v7_selection: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = contract["target_selection"]
    prior_inputs = (
        (v3_selection, 70),
        (v5_selection, 74),
        (v6_selection, 78),
        (v7_selection, 103),
    )
    prior_sets: list[set[tuple[str, str, str]]] = []
    for selection, expected in prior_inputs:
        targets = list(selection.get("targets", []))
        assert len(targets) == expected
        prior_sets.append({base.row_identity(row) for row in targets})
    for i in range(len(prior_sets)):
        for j in range(i + 1, len(prior_sets)):
            assert not (prior_sets[i] & prior_sets[j])
    prior = set().union(*prior_sets)

    sentinels = {
        base.base_normalize(name)
        for name in cfg["exclusions"]["normalized_v1_sentinel_visible_names"]
    }
    eligible = [
        dict(row)
        for row in rows
        if base.clean(row.get("team"))
        and base.clean(row.get("visible_name"))
        and base.clean(row.get("position"))
        and base.base_normalize(row.get("visible_name")) not in sentinels
        and base.row_identity(row) not in prior
    ]
    assert len(eligible) == cfg["expected_eligible_row_count"]

    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_team[base.clean(row["team"])].append(row)

    def order(row: dict[str, Any]):
        return (
            selection_key(row, contract),
            base.clean(row.get("visible_name")),
            base.clean(row.get("profile_path")),
        )

    coverage: list[dict[str, Any]] = []
    for team in sorted(by_team):
        coverage.extend(
            sorted(by_team[team], key=order)[: cfg["coverage_stratum"]["per_team_count"]]
        )
    alias = sorted(by_team[cfg["team_alias_ari_stratum"]["team"]], key=order)[
        : cfg["team_alias_ari_stratum"]["expected_target_count"]
    ]

    regexes = [
        re.compile(expr, re.I if "Jr" in expr else 0)
        for expr in cfg["source_name_variant_stratum"]["source_only_regexes"]
    ]
    variant_all = [
        row for row in eligible
        if any(rx.search(base.clean(row.get("visible_name"))) for rx in regexes)
    ]
    assert len(variant_all) == cfg["source_name_variant_stratum"]["expected_eligible_count"]
    variants = sorted(
        variant_all,
        key=lambda row: (
            selection_key(row, contract), base.clean(row["team"]),
            base.clean(row["visible_name"]), base.clean(row.get("profile_path")),
        ),
    )[: cfg["source_name_variant_stratum"]["expected_target_count"]]

    canonical_all: list[dict[str, Any]] = []
    grammar_stress: list[dict[str, Any]] = []
    for row in eligible:
        canonical = v7.canonical_query_name(row.get("canonical_data_name"))
        if canonical and base.name_key(canonical) != base.name_key(row.get("visible_name")):
            canonical_all.append(row)
        if (
            not grammar_valid(row.get("visible_name"))
            and canonical
            and grammar_valid(canonical)
        ):
            grammar_stress.append(row)
    assert len(canonical_all) == cfg["canonical_name_variant_stratum"]["expected_eligible_count"]
    canonical = sorted(
        canonical_all,
        key=lambda row: (
            selection_key(row, contract), base.clean(row["team"]),
            base.clean(row["visible_name"]), base.clean(row.get("profile_path")),
        ),
    )[: cfg["canonical_name_variant_stratum"]["expected_target_count"]]
    assert len(grammar_stress) == cfg["query_grammar_stress_stratum"]["expected_eligible_count"]
    assert len(grammar_stress) == cfg["query_grammar_stress_stratum"]["expected_target_count"]

    ordered_strata = (
        "coverage", "team_alias_ari", "source_name_variant",
        "canonical_name_variant", "query_grammar_stress",
    )
    subsets = (
        ("coverage", coverage),
        ("team_alias_ari", alias),
        ("source_name_variant", variants),
        ("canonical_name_variant", canonical),
        ("query_grammar_stress", grammar_stress),
    )
    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    target_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for name, subset in subsets:
        for row in subset:
            rid = base.row_identity(row)
            target_map[rid] = row
            strata[rid].append(name)

    targets: list[dict[str, Any]] = []
    for rid in sorted(target_map):
        row = dict(target_map[rid])
        canonical_query = v7.canonical_query_name(row.get("canonical_data_name"))
        row["_strata"] = [name for name in ordered_strata if name in strata[rid]]
        row["_selection_key_sha256"] = selection_key(row, contract)
        row["_canonical_query_name"] = canonical_query
        row["_visible_query_grammar_valid"] = grammar_valid(row.get("visible_name"))
        row["_canonical_query_grammar_valid"] = bool(canonical_query and grammar_valid(canonical_query))
        targets.append(row)

    sets = {name: {base.row_identity(row) for row in subset} for name, subset in subsets}
    pairwise: dict[str, int] = {}
    for i, left in enumerate(ordered_strata):
        for right in ordered_strata[i + 1:]:
            pairwise[f"{left}_and_{right}"] = len(sets[left] & sets[right])

    identities = [
        [base.clean(row["team"]), base.clean(row["visible_name"]), base.clean(row.get("profile_path"))]
        for row in targets
    ]
    projection = [
        {
            "team": base.clean(row["team"]),
            "visible_name": base.clean(row["visible_name"]),
            "canonical_data_name": base.clean(row.get("canonical_data_name")),
            "canonical_query_name": base.clean(row.get("_canonical_query_name")),
            "visible_query_grammar_valid": row["_visible_query_grammar_valid"],
            "canonical_query_grammar_valid": row["_canonical_query_grammar_valid"],
            "position": base.clean(row.get("position")),
            "jersey_number": base.clean(row.get("jersey_number")),
            "profile_path": base.clean(row.get("profile_path")),
            "strata": row["_strata"],
            "selection_key_sha256": row["_selection_key_sha256"],
        }
        for row in targets
    ]
    diagnostics = {
        "eligible_row_count": len(eligible),
        "team_count": len(by_team),
        "coverage_target_count": len(coverage),
        "team_alias_ari_target_count": len(alias),
        "source_name_variant_eligible_count": len(variant_all),
        "source_name_variant_target_count": len(variants),
        "canonical_name_variant_eligible_count": len(canonical_all),
        "canonical_name_variant_target_count": len(canonical),
        "query_grammar_stress_eligible_count": len(grammar_stress),
        "query_grammar_stress_target_count": len(grammar_stress),
        "total_target_count": len(targets),
        "pairwise_overlap_counts": pairwise,
        "sorted_row_identity_sha256": base.canonical_sha(identities),
        "target_projection_sha256": base.canonical_sha(projection),
    }
    assert diagnostics["team_count"] == cfg["coverage_stratum"]["expected_team_count"]
    assert diagnostics["coverage_target_count"] == cfg["coverage_stratum"]["expected_target_count"]
    assert diagnostics["pairwise_overlap_counts"] == cfg["expected_pairwise_overlap_counts"]
    assert diagnostics["total_target_count"] == cfg["expected_total_target_count"]
    assert diagnostics["sorted_row_identity_sha256"] == cfg["expected_sorted_row_identity_sha256"]
    assert diagnostics["target_projection_sha256"] == cfg["expected_target_projection_sha256"]
    assert not ({base.row_identity(row) for row in targets} & prior)
    return targets, diagnostics


def evaluate_gates(
    targets: list[dict[str, Any]],
    results: list[dict[str, Any]],
    contract: dict[str, Any],
    page_loaded: bool,
    query_input_count: int,
) -> tuple[dict[str, Any], dict[str, bool], bool, dict[str, bool]]:
    metrics, gates, _old_passed, _old_conditional = v7.evaluate_gates(
        targets, results, contract, page_loaded, query_input_count
    )
    by_id = {tuple(result["target_row_identity"]): result for result in results}
    stress = [
        by_id[base.row_identity(target)]
        for target in targets if "query_grammar_stress" in target["_strata"]
    ]
    visible_skipped = [
        result for result in stress
        if any(
            item["query_kind"] == "exact_visible_name"
            and item["disposition"] == "skipped_pre_dispatch_query_grammar"
            for item in result["planned_query_representations"]
        )
    ]
    canonical_executed = [
        result for result in stress
        if any(attempt["query_kind"] == "source_canonical_name" for attempt in result["query_attempts"])
    ]
    stress_resolved = [result for result in stress if result["resolved"]]
    den = len(stress)
    metrics.update({
        "query_grammar_stress_target_count": den,
        "query_grammar_stress_visible_skip_count": len(visible_skipped),
        "query_grammar_stress_source_canonical_execution_count": len(canonical_executed),
        "query_grammar_stress_unique_resolution_count": len(stress_resolved),
        "query_grammar_stress_unique_resolution_fraction": len(stress_resolved) / den if den else 0.0,
    })
    cfg = contract["frozen_pass_gates"]
    gates.update({
        "query_grammar_stress_visible_skip_required": len(visible_skipped) == cfg["query_grammar_stress_visible_skip_required_count"],
        "query_grammar_stress_source_canonical_execution_required": len(canonical_executed) == cfg["query_grammar_stress_source_canonical_execution_required_count"],
        "query_grammar_stress_unique_resolution_required": (
            len(stress_resolved) == cfg["query_grammar_stress_unique_resolution_required_count"]
            and (len(stress_resolved) / den if den else 0.0) == cfg["query_grammar_stress_unique_resolution_required_fraction"]
        ),
    })
    passed = all(gates.values())
    conditional = {
        "ari_az_team_alias_qualified": passed and metrics.get("team_alias_ari_selected_ngs_az_count", 0) > 0,
        "source_canonical_name_representation_qualified": passed and metrics.get("source_canonical_query_success_count", 0) > 0,
        "query_fallback_semantics_qualified": passed and metrics.get("fallback_success_count", 0) > 0,
        "multiple_candidate_tiebreak_qualified": passed and metrics.get("tiebreak_success_count", 0) > 0,
        "query_grammar_guard_qualified": passed and len(visible_skipped) == den and len(canonical_executed) == den and len(stress_resolved) == den,
    }
    return metrics, gates, passed, conditional


def run_probe(
    contract_path: Path,
    roster_path: Path,
    v3_selection_path: Path,
    v5_selection_path: Path,
    v6_selection_path: Path,
    v7_selection_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "responses").mkdir(parents=True, exist_ok=True)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["schema_version"] != "levline4-2026-ngs-player-id-browser-heldout-v8-contract":
        raise ValueError("unexpected V8 contract schema")
    rows = base.load_jsonl(roster_path)
    selections = [json.loads(path.read_text(encoding="utf-8")) for path in (
        v3_selection_path, v5_selection_path, v6_selection_path, v7_selection_path
    )]
    roster_cfg = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    if base.sha256_file(roster_path) != roster_cfg["roster_metadata_sha256"] or len(rows) != roster_cfg["row_count"]:
        raise ValueError("roster source mismatch")
    evidence_keys = (
        "ngs_browser_heldout_v3", "ngs_browser_heldout_v5_empirical_exposure_only",
        "ngs_browser_heldout_v6", "ngs_browser_heldout_v7",
    )
    for path, key in zip((v3_selection_path, v5_selection_path, v6_selection_path, v7_selection_path), evidence_keys):
        if base.sha256_file(path) != contract["frozen_upstream_evidence"][key]["target_selection_sha256"]:
            raise ValueError(f"{key} selection mismatch")

    targets, diagnostics = select_targets(rows, contract, *selections)
    selection_receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v8-target-selection",
        "contract_id": contract["contract_id"],
        "selection_diagnostics": diagnostics,
        "targets": targets,
    }
    (output_dir / "target_selection.json").write_text(json.dumps(selection_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    browser_cfg = contract["browser_transport"]
    page_loaded = False
    query_input_count = 0
    browser_error: str | None = None
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=browser_cfg["context_user_agent"], locale=browser_cfg["context_locale"])
        page = context.new_page()
        locator = None
        try:
            page.goto(browser_cfg["page_url"], wait_until=browser_cfg["page_load_wait_until"], timeout=browser_cfg["page_load_timeout_ms"])
            page.wait_for_timeout(browser_cfg["post_load_settle_ms"])
            page_loaded = True
            locator = page.get_by_placeholder(browser_cfg["query_input_placeholder_exact"], exact=True)
            query_input_count = locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"

        for target_index, target in enumerate(targets, 1):
            planned: list[dict[str, Any]] = []
            attempts: list[dict[str, Any]] = []
            chosen_payload: dict[str, Any] | None = None
            action_error = browser_error
            may_execute_next = browser_error is None and locator is not None and query_input_count == 1
            for query_kind, query in query_plan(target):
                valid = grammar_valid(query)
                plan_item = {"query_kind": query_kind, "query": query, "grammar_valid": valid, "disposition": None}
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
                        lambda response, expected=query: base.matches_player_search_response(response.url, expected),
                        timeout=browser_cfg["response_timeout_ms"],
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
                (output_dir / relpath).write_bytes(body)
                parsed, parseable, semantic_error = base.parse_players_body(status, body)
                player_count = len(parsed.get("players", [])) if parseable and isinstance(parsed, dict) else 0
                attempts.append({
                    "attempt_index": attempt_index, "query_kind": query_kind, "query": query,
                    "response_url": response_url, "http_status": status, "content_type": content_type,
                    "parseable_players_array": parseable, "player_count": player_count,
                    "semantic_error": semantic_error, "browser_action_error": attempt_error,
                    "response_relpath": relpath, "response_bytes": len(body),
                    "response_sha256": base.sha256_bytes(body),
                })
                if attempt_error or not parseable:
                    may_execute_next = False
                elif player_count > 0:
                    chosen_payload = parsed
                    may_execute_next = False
                else:
                    may_execute_next = True

            resolution = v7.resolve_target(target, chosen_payload)
            results.append({
                "target_index": target_index,
                "target_row_identity": list(base.row_identity(target)),
                "target_visible_name": base.clean(target["visible_name"]),
                "target_canonical_data_name": base.clean(target.get("canonical_data_name")),
                "target_source_canonical_query_name": v7.canonical_query_name(target.get("canonical_data_name")),
                "target_team": base.clean(target["team"]),
                "target_position": base.clean(target["position"]),
                "target_jersey_number": base.clean(target.get("jersey_number")),
                "target_profile_path": base.clean(target.get("profile_path")),
                "target_strata": target["_strata"],
                "selection_key_sha256": target["_selection_key_sha256"],
                "browser_action_error": action_error,
                "planned_query_representations": planned,
                "query_attempts": attempts,
                "fallback_used": len(attempts) > 1,
                **resolution,
            })
        browser.close()

    with (output_dir / "target_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

    metrics, gates, passed, conditional = evaluate_gates(targets, results, contract, page_loaded, query_input_count)
    authority = dict(contract["authority_if_and_only_if_all_v8_gates_pass"] if passed else contract["authority_if_any_v8_gate_fails"])
    if passed:
        mapping = {
            "ari_az_team_alias_qualified_for_frozen_v8_population": "ari_az_team_alias_qualified",
            "source_canonical_name_representation_qualified_for_frozen_v8_population": "source_canonical_name_representation_qualified",
            "query_fallback_semantics_qualified_for_frozen_v8_population": "query_fallback_semantics_qualified",
            "multiple_candidate_tiebreak_qualified_for_frozen_v8_population": "multiple_candidate_tiebreak_qualified",
            "query_grammar_guard_qualified_for_frozen_v8_population": "query_grammar_guard_qualified",
        }
        for target_key, conditional_key in mapping.items():
            authority[target_key] = conditional[conditional_key]

    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v8-receipt",
        "contract_id": contract["contract_id"],
        "captured_at_utc": base.utc_now(),
        "status": "PASS" if passed else "FAIL",
        "target_selection": diagnostics,
        "browser_transport": {
            "page_url": browser_cfg["page_url"], "page_loaded": page_loaded,
            "query_input_count": query_input_count, "browser_error": browser_error,
            "context_locale": browser_cfg["context_locale"],
            "context_user_agent": browser_cfg["context_user_agent"],
            "manual_headers_or_credentials_used": False,
            "browser_storage_state_persisted": False,
            "direct_http_fallback_used": False, "explicit_retry_used": False,
        },
        "metrics": metrics, "gates": gates,
        "conditional_capability_evidence": conditional, "authority": authority,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "future_information_used_to_repair_point_in_time_state": False,
        "f_st_01_frozen_2026_unchanged": True,
        "research_only": True, "production_paths_changed": False,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--roster-metadata", required=True, type=Path)
    parser.add_argument("--v3-target-selection", required=True, type=Path)
    parser.add_argument("--v5-target-selection", required=True, type=Path)
    parser.add_argument("--v6-target-selection", required=True, type=Path)
    parser.add_argument("--v7-target-selection", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_probe(
        args.contract, args.roster_metadata, args.v3_target_selection,
        args.v5_target_selection, args.v6_target_selection,
        args.v7_target_selection, args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

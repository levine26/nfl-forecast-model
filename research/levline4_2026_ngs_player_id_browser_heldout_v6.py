#!/usr/bin/env python3
"""LevLine 4 NGS browser-context held-out resolver V6 (research only).

V6 deliberately delegates all query, normalization, semantic resolution, and
frozen gate logic to the byte-identical V5 implementation snapshot. V6-specific
code changes only the preregistered held-out exclusion set and versioned
provenance/artifact schema.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as frozen


def select_targets(
    rows: Iterable[dict[str, Any]],
    contract: dict[str, Any],
    v3_selection: dict[str, Any],
    v5_selection: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reuse frozen V5 selector with V3+V5 rows combined only as exclusions."""
    v3_targets = list(v3_selection.get("targets", []))
    v5_targets = list(v5_selection.get("targets", []))
    v3_ids = {frozen.row_identity(x) for x in v3_targets}
    v5_ids = {frozen.row_identity(x) for x in v5_targets}
    assert len(v3_targets) == 70
    assert len(v5_targets) == 74
    assert not (v3_ids & v5_ids)
    combined = {"targets": v3_targets + v5_targets}
    targets, diagnostics = frozen.select_targets(rows, contract, combined)
    selected = {frozen.row_identity(x) for x in targets}
    assert not (selected & v3_ids)
    assert not (selected & v5_ids)
    return targets, diagnostics


def run_probe(
    contract_path: Path,
    roster_path: Path,
    v3_selection_path: Path,
    v5_selection_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    response_dir = output_dir / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["schema_version"] != "levline4-2026-ngs-player-id-browser-heldout-v6-contract":
        raise ValueError("unexpected V6 contract schema")

    rows = frozen.load_jsonl(roster_path)
    v3_selection = json.loads(v3_selection_path.read_text(encoding="utf-8"))
    v5_selection = json.loads(v5_selection_path.read_text(encoding="utf-8"))

    roster_cfg = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    if frozen.sha256_file(roster_path) != roster_cfg["roster_metadata_sha256"] or len(rows) != roster_cfg["row_count"]:
        raise ValueError("roster source mismatch")
    v3_cfg = contract["frozen_upstream_evidence"]["ngs_browser_heldout_v3"]
    if frozen.sha256_file(v3_selection_path) != v3_cfg["target_selection_sha256"]:
        raise ValueError("V3 selection mismatch")
    v5_cfg = contract["frozen_upstream_evidence"]["ngs_browser_heldout_v5_empirical_exposure_only"]
    if frozen.sha256_file(v5_selection_path) != v5_cfg["target_selection_sha256"]:
        raise ValueError("V5 selection mismatch")

    targets, diagnostics = select_targets(rows, contract, v3_selection, v5_selection)
    (output_dir / "target_selection.json").write_text(
        json.dumps(
            {
                "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v6-target-selection",
                "contract_id": contract["contract_id"],
                "source_roster_metadata_sha256": frozen.sha256_file(roster_path),
                "v3_target_selection_sha256": frozen.sha256_file(v3_selection_path),
                "v5_target_selection_sha256": frozen.sha256_file(v5_selection_path),
                "selection_diagnostics": diagnostics,
                "targets": targets,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (output_dir / "contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    browser_cfg = contract["browser_transport"]
    page_loaded = False
    query_input_count = 0
    browser_error: str | None = None
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=browser_cfg["context_user_agent"],
            locale=browser_cfg["context_locale"],
        )
        page = context.new_page()
        locator = None
        try:
            page.goto(
                browser_cfg["page_url"],
                wait_until=browser_cfg["page_load_wait_until"],
                timeout=browser_cfg["page_load_timeout_ms"],
            )
            page.wait_for_timeout(browser_cfg["post_load_settle_ms"])
            page_loaded = True
            locator = page.get_by_placeholder(browser_cfg["query_input_placeholder_exact"], exact=True)
            query_input_count = locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"

        for target_index, target in enumerate(targets, 1):
            attempts: list[dict[str, Any]] = []
            chosen_payload: dict[str, Any] | None = None
            action_error = browser_error
            if browser_error is None and locator is not None and query_input_count == 1:
                for attempt_index, (query_kind, query) in enumerate(frozen.query_plan(frozen.clean(target["visible_name"])), 1):
                    if attempt_index > 1:
                        previous = attempts[-1]
                        if not (
                            previous["http_status"] == 200
                            and previous["parseable_players_array"]
                            and previous["player_count"] == 0
                        ):
                            break
                    body = b""
                    status = None
                    response_url = None
                    content_type = None
                    attempt_error = None
                    try:
                        with page.expect_response(
                            lambda response, expected=query: frozen.matches_player_search_response(response.url, expected),
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

                    relpath = f"responses/target_{target_index:03d}_attempt_{attempt_index}.json"
                    (output_dir / relpath).write_bytes(body)
                    parsed, parseable, semantic_error = frozen.parse_players_body(status, body)
                    player_count = len(parsed.get("players", [])) if parseable and isinstance(parsed, dict) else 0
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
                            "response_sha256": frozen.sha256_bytes(body),
                        }
                    )
                    if attempt_error or not parseable:
                        break
                    if player_count > 0:
                        chosen_payload = parsed
                        break

            resolution = frozen.resolve_target(target, chosen_payload)
            results.append(
                {
                    "target_index": target_index,
                    "target_row_identity": list(frozen.row_identity(target)),
                    "target_visible_name": frozen.clean(target["visible_name"]),
                    "target_team": frozen.clean(target["team"]),
                    "target_position": frozen.clean(target["position"]),
                    "target_jersey_number": frozen.clean(target.get("jersey_number")),
                    "target_profile_path": frozen.clean(target.get("profile_path")),
                    "target_strata": target["_strata"],
                    "selection_key_sha256": target["_selection_key_sha256"],
                    "browser_action_error": action_error,
                    "query_attempts": attempts,
                    "fallback_used": len(attempts) > 1,
                    **resolution,
                }
            )
        browser.close()

    with (output_dir / "target_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

    metrics, gates, passed, conditional = frozen.evaluate_gates(
        targets, results, contract, page_loaded, query_input_count
    )
    if passed:
        authority = dict(contract["authority_if_and_only_if_all_v6_gates_pass"])
        authority["ari_az_team_alias_qualified_for_frozen_v6_population"] = conditional["ari_az_team_alias_qualified"]
        authority["query_fallback_semantics_qualified_for_frozen_v6_population"] = conditional["query_fallback_semantics_qualified"]
        authority["multiple_candidate_tiebreak_qualified_for_frozen_v6_population"] = conditional["multiple_candidate_tiebreak_qualified"]
    else:
        authority = dict(contract["authority_if_any_v6_gate_fails"])

    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v6-receipt",
        "contract_id": contract["contract_id"],
        "captured_at_utc": frozen.utc_now(),
        "status": "PASS" if passed else "FAIL",
        "target_selection": diagnostics,
        "browser_transport": {
            "page_url": browser_cfg["page_url"],
            "page_loaded": page_loaded,
            "query_input_count": query_input_count,
            "browser_error": browser_error,
            "context_locale": browser_cfg["context_locale"],
            "context_user_agent": browser_cfg["context_user_agent"],
            "post_load_settle_ms": browser_cfg["post_load_settle_ms"],
            "manual_headers_or_credentials_used": False,
            "browser_storage_state_persisted": False,
            "direct_http_fallback_used": False,
            "explicit_retry_used": False,
        },
        "metrics": metrics,
        "gates": gates,
        "conditional_capability_evidence": conditional,
        "authority": authority,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "f_st_01_frozen_2026_unchanged": True,
        "research_only": True,
        "production_paths_changed": False,
        "v5_outcome_metrics_used_for_rule_or_threshold_design": False,
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--roster-metadata", required=True, type=Path)
    parser.add_argument("--v3-target-selection", required=True, type=Path)
    parser.add_argument("--v5-target-selection", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_probe(
        args.contract,
        args.roster_metadata,
        args.v3_target_selection,
        args.v5_target_selection,
        args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pre-execution corrected wrapper for LevLine 4 NGS browser held-out V4.

This wrapper changes no target selection, transport, query cascade, matching,
tiebreak, pass/fail gate, or downstream authority ceiling. It only implements
the separately preregistered addendum requiring actual observation of an
ARI-official -> AZ-NGS selected candidate before the conditional ARI<->AZ alias
capability can be marked qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from research import levline4_2026_ngs_player_id_browser_heldout_v4 as base

_ORIGINAL_EVALUATE_GATES = base.evaluate_gates


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_evaluate_gates(
    targets: list[dict[str, Any]],
    results: list[dict[str, Any]],
    contract: dict[str, Any],
    page_loaded: bool,
    query_input_count: int,
):
    metrics, gates, passed, conditional = _ORIGINAL_EVALUATE_GATES(
        targets, results, contract, page_loaded, query_input_count
    )
    byid = {tuple(r["target_row_identity"]): r for r in results}
    alias_results = [
        byid[base.row_identity(t)]
        for t in targets
        if "team_alias_ari" in t["_strata"]
    ]
    exercised = [
        r
        for r in alias_results
        if r.get("resolved")
        and str(r.get("target_team") or "").strip().upper() == "ARI"
        and str((r.get("selected_candidate") or {}).get("teamAbbr") or "").strip().upper() == "AZ"
    ]
    metrics["ari_az_alias_exercised_count"] = len(exercised)
    metrics["ari_az_alias_exercised_target_row_identities"] = [
        r["target_row_identity"] for r in exercised
    ]
    conditional["ari_az_team_alias_qualified"] = bool(
        passed
        and gates["team_alias_ari_unique_resolution_required"]
        and len(exercised) >= 1
    )
    return metrics, gates, passed, conditional


def load_and_validate_addendum(path: Path) -> dict[str, Any]:
    addendum = json.loads(path.read_text())
    assert addendum["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V4"
    assert addendum["status"] == "PREEXECUTION_PREREGISTRATION_CORRECTION"
    assert addendum["empirical_boundary"]["v4_ngs_requests_observed_before_this_addendum"] == 0
    assert addendum["empirical_boundary"]["v4_workflow_runs_before_this_addendum"] == 0
    assert addendum["empirical_boundary"]["v4_first_result_exists"] is False
    assert addendum["required_implementation_behavior"]["conditional_alias_flag_requires_exercised_count_minimum"] == 1
    return addendum


def run_probe(
    contract_path: Path,
    addendum_path: Path,
    roster_path: Path,
    v3_selection_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    addendum = load_and_validate_addendum(addendum_path)
    base.evaluate_gates = strict_evaluate_gates
    try:
        receipt = base.run_probe(contract_path, roster_path, v3_selection_path, output_dir)
    finally:
        base.evaluate_gates = _ORIGINAL_EVALUATE_GATES

    receipt["preexecution_addendum"] = {
        "schema_version": addendum["schema_version"],
        "sha256": sha256_file(addendum_path),
        "alias_exercise_requirement_applied": True,
        "minimum_exercised_count": 1,
    }
    (output_dir / "preexecution_addendum.json").write_text(
        json.dumps(addendum, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--addendum", required=True, type=Path)
    ap.add_argument("--roster-metadata", required=True, type=Path)
    ap.add_argument("--v3-target-selection", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    a = ap.parse_args()
    receipt = run_probe(
        a.contract,
        a.addendum,
        a.roster_metadata,
        a.v3_target_selection,
        a.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

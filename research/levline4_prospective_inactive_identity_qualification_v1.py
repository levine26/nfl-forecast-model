from __future__ import annotations

"""Evaluate first Week 2 Sunday inactive identity mechanics under frozen gates.

Research-only: this module evaluates immutable evidence already captured by the frozen
prospective executor. The weekly and global identity artifacts are both nflverse-derived,
so cross-artifact agreement is a consistency audit, not source-independent identity truth.
It cannot repair resolver misses, substitute a later execution, attach player value, or
affect forecasts.
"""

from collections import Counter
import argparse
import json
import math
from pathlib import Path
from typing import Any

CONTRACT_ID = "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-IDENTITY-QUALIFICATION-V1"
EXECUTION_CONTRACT_ID = "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-EXECUTION-V1"
WEEKLY_SHA256 = "fc993e0543950222cd20e0c29e457980da572d100bebff6a5d4bf5f7b72b051f"
GLOBAL_SHA256 = "023d7e5b652f56c1b41c432f394d81da60e2ab4df287daeb3baa1be76d6f2603"
MIN_EXACT_UNIQUE_RATE = 0.995
MAX_AMBIGUITIES = 0
MAX_CONTRADICTIONS = 0
MIN_AUDITABLE_FRACTION = 0.80
MIN_AUDITABLE_ROWS = 73
REQUIRED_AUDIT_AGREEMENT = 1.0
MIN_WILSON95_LOWER = 0.95


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    return rows


def wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1.0 + (z * z / total)
    center = (p + (z * z / (2.0 * total))) / denominator
    half = z * math.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total))) / denominator
    return max(0.0, center - half)


def _first_identity_execution(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        row
        for row in attempts
        if row.get("contract_id") == EXECUTION_CONTRACT_ID and row.get("execution_id")
    ]
    if not candidates:
        raise RuntimeError("no identity-executed Week 2 attempt exists yet")
    return sorted(
        candidates,
        key=lambda row: (str(row.get("captured_at_utc") or ""), str(row.get("attempt_id") or "")),
    )[0]


def evaluate(*, execution_output_dir: Path) -> dict[str, Any]:
    attempts = _read_jsonl(execution_output_dir / "attempts.jsonl")
    first = _first_identity_execution(attempts)
    execution_id = str(first["execution_id"])
    run_dir = execution_output_dir / "executions" / execution_id
    stored_receipt = json.loads((run_dir / "receipt.json").read_text(encoding="utf-8"))
    if stored_receipt != first:
        raise RuntimeError("attempt ledger and immutable execution receipt disagree")

    parsed_rows = _read_jsonl(run_dir / "parsed_due_cohort.jsonl")
    resolver_inputs = _read_jsonl(run_dir / "resolver_inputs.jsonl")
    resolver_rows = _read_jsonl(run_dir / "resolver_rows.jsonl")
    audit_rows = _read_jsonl(run_dir / "cross_source_audit_rows.jsonl")

    total = len(resolver_rows)
    state_counts = Counter(str(row.get("resolution_state") or "") for row in resolver_rows)
    exact_unique = state_counts.get("RESOLVED_EXACT_UNIQUE", 0)
    ambiguities = state_counts.get("AMBIGUOUS", 0)
    exact_unique_rate = exact_unique / total if total else 0.0

    audit_counts = Counter(str(row.get("audit_state") or "") for row in audit_rows)
    corroborated = audit_counts.get("CROSS_SOURCE_CORROBORATED", 0)
    contradictions = audit_counts.get("CROSS_SOURCE_CONTRADICTION", 0)
    auditable = corroborated + contradictions
    auditable_fraction = auditable / exact_unique if exact_unique else 0.0
    audit_agreement = corroborated / auditable if auditable else 0.0
    audit_wilson_lower = wilson_lower(corroborated, auditable)

    due_teams = {str(team) for team in first.get("due_teams") or []}
    parsed_teams = {str(row.get("team") or "") for row in parsed_rows}
    exact_due_team_coverage = bool(due_teams) and parsed_teams == due_teams

    lengths_consistent = (
        len(parsed_rows)
        == len(resolver_inputs)
        == len(resolver_rows)
        == len(audit_rows)
        == int(first.get("due_cohort_inactive_entries", -1))
    )
    observation_ids_consistent = (
        {str(row.get("observation_id")) for row in resolver_inputs}
        == {str(row.get("observation_id")) for row in resolver_rows}
        == {str(row.get("observation_id")) for row in audit_rows}
    )
    no_global_fallback = bool(first.get("global_source_used_as_fallback") is False) and all(
        row.get("global_source_used_as_fallback") is False for row in audit_rows
    )
    dependency_shas_match = (
        first.get("weekly_identity_projection_sha256") == WEEKLY_SHA256
        and first.get("global_identity_projection_sha256") == GLOBAL_SHA256
    )
    authority_firewall_intact = all(
        first.get(key) is False
        for key in (
            "availability_probability_feature_authorized",
            "player_value_join_authorized",
            "forecast_probability_effect_authorized",
            "model_fit_authorized",
            "production_authorized",
        )
    ) and int(first.get("completed_2026_outcomes_used", -1)) == 0

    gates = {
        "first_execution_status_pass": first.get("status") == "PASS_EVIDENCE_CAPTURED",
        "week_is_2": first.get("week") == 2,
        "one_distinct_matching_article_body": int(first.get("matching_distinct_article_bodies", -1)) == 1,
        "exact_due_team_coverage": exact_due_team_coverage,
        "row_and_observation_integrity": lengths_consistent and observation_ids_consistent and total > 0,
        "dependency_shas_match": dependency_shas_match,
        "exact_unique_resolution_rate_gte_0_995": exact_unique_rate >= MIN_EXACT_UNIQUE_RATE,
        "ambiguities_zero": ambiguities <= MAX_AMBIGUITIES,
        "cross_artifact_contradictions_zero": contradictions <= MAX_CONTRADICTIONS,
        "cross_artifact_auditable_fraction_gte_0_80": auditable_fraction >= MIN_AUDITABLE_FRACTION,
        "cross_artifact_auditable_rows_gte_73": auditable >= MIN_AUDITABLE_ROWS,
        "cross_artifact_agreement_eq_1": math.isclose(
            audit_agreement, REQUIRED_AUDIT_AGREEMENT, rel_tol=0.0, abs_tol=0.0
        ),
        "cross_artifact_agreement_wilson95_lower_gte_0_95": audit_wilson_lower >= MIN_WILSON95_LOWER,
        "global_source_never_used_as_fallback": no_global_fallback,
        "research_authority_firewall_intact": authority_firewall_intact,
    }
    mechanics_passed = all(gates.values())

    return {
        "schema_version": "levline4-2026-prospective-inactive-identity-qualification-v1",
        "contract_id": CONTRACT_ID,
        "status": (
            "PASS_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY_MECHANICS"
            if mechanics_passed
            else "FAIL_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY_MECHANICS"
        ),
        "evaluated_execution_id": execution_id,
        "evaluated_attempt_id": first.get("attempt_id"),
        "evaluated_captured_at_utc": first.get("captured_at_utc"),
        "first_identity_execution_only": True,
        "source_lineage": {
            "weekly_identity_provider": "nflverse",
            "global_identity_provider": "nflverse",
            "cross_artifact_audit_is_source_independent": False,
        },
        "metrics": {
            "total_resolver_rows": total,
            "exact_unique_resolutions": exact_unique,
            "exact_unique_resolution_rate": exact_unique_rate,
            "ambiguities": ambiguities,
            "cross_artifact_auditable_rows": auditable,
            "cross_artifact_auditable_fraction_of_exact_unique": auditable_fraction,
            "cross_artifact_corroborated": corroborated,
            "cross_artifact_contradictions": contradictions,
            "cross_artifact_agreement": audit_agreement,
            "cross_artifact_agreement_wilson95_lower_bound": audit_wilson_lower,
        },
        "gates": gates,
        "authority": {
            "week2_sunday_due_inactive_identity_mechanics_validated": mechanics_passed,
            "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
            "source_independent_identity_validation_still_required": True,
            "general_2026_player_identity_to_gsis_qualified": False,
            "game_day_membership_qualified": False,
            "active_or_healthy_inference_from_absence_authorized": False,
            "availability_probability_feature_authorized": False,
            "player_value_join_authorized": False,
            "forecast_probability_effect_authorized": False,
            "model_fit_authorized": False,
            "production_authorized": False,
        },
        "completed_2026_outcomes_used": 0,
        "f_st_01_frozen_2026_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execution-output-dir",
        type=Path,
        default=Path("research_outputs/levline4_prospective_inactive_execution_v1"),
    )
    parser.add_argument("--receipt-out", type=Path)
    args = parser.parse_args()
    receipt = evaluate(execution_output_dir=args.execution_output_dir)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt_out:
        args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if receipt["status"].startswith("FAIL_"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

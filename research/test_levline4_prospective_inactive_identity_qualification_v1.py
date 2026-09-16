from __future__ import annotations

import json
from pathlib import Path

from research.levline4_prospective_inactive_identity_qualification_v1 import (
    CONTRACT_ID,
    evaluate,
    wilson_lower,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _add_execution(
    root: Path,
    *,
    execution_id: str,
    captured_at: str,
    n: int = 73,
    contradiction_index: int | None = None,
    unresolved_index: int | None = None,
) -> dict:
    run_dir = root / "executions" / execution_id
    run_dir.mkdir(parents=True, exist_ok=True)
    parsed, inputs, resolver, audits = [], [], [], []
    state_counts: dict[str, int] = {}

    for i in range(n):
        team = "ARI" if i % 2 == 0 else "LAC"
        obs = f"obs-{execution_id}-{i:03d}"
        parsed.append({"team": team, "player_name_rendered": f"Player {i}"})
        inputs.append({"observation_id": obs, "team": team, "week": 2})
        state = "UNRESOLVED_NO_EXACT_MATCH" if unresolved_index == i else "RESOLVED_EXACT_UNIQUE"
        state_counts[state] = state_counts.get(state, 0) + 1
        resolved = None if unresolved_index == i else f"00-{i:04d}"
        resolver.append({
            "observation_id": obs,
            "team": team,
            "week": 2,
            "player_name_rendered": f"Player {i}",
            "resolution_state": state,
            "resolved_gsis_id": resolved,
        })
        if state != "RESOLVED_EXACT_UNIQUE":
            audit_state = "RESOLVER_NOT_RESOLVED"
        elif contradiction_index == i:
            audit_state = "CROSS_SOURCE_CONTRADICTION"
        else:
            audit_state = "CROSS_SOURCE_CORROBORATED"
        audits.append({
            "observation_id": obs,
            "team": team,
            "week": 2,
            "audit_state": audit_state,
            "global_source_used_as_fallback": False,
        })

    audit_counts: dict[str, int] = {}
    for row in audits:
        audit_counts[row["audit_state"]] = audit_counts.get(row["audit_state"], 0) + 1

    receipt = {
        "schema_version": "levline-2026-prospective-inactive-execution-v1",
        "contract_id": "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-EXECUTION-V1",
        "attempt_id": f"attempt-{execution_id}",
        "execution_id": execution_id,
        "status": "FAIL_CROSS_SOURCE_CONTRADICTION" if contradiction_index is not None else "PASS_EVIDENCE_CAPTURED",
        "captured_at_utc": captured_at,
        "week": 2,
        "due_game_ids": ["2026_02_ARI_LAC"],
        "due_teams": ["ARI", "LAC"],
        "matching_distinct_article_bodies": 1,
        "due_cohort_team_sections": 2,
        "due_cohort_inactive_entries": n,
        "weekly_identity_projection_sha256": "fc993e0543950222cd20e0c29e457980da572d100bebff6a5d4bf5f7b72b051f",
        "global_identity_projection_sha256": "023d7e5b652f56c1b41c432f394d81da60e2ab4df287daeb3baa1be76d6f2603",
        "resolver_receipt": {"resolution_counts": state_counts},
        "cross_source_audit_counts": audit_counts,
        "cross_source_contradictions": audit_counts.get("CROSS_SOURCE_CONTRADICTION", 0),
        "global_source_used_as_fallback": False,
        "availability_probability_feature_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_jsonl(run_dir / "parsed_due_cohort.jsonl", parsed)
    _write_jsonl(run_dir / "resolver_inputs.jsonl", inputs)
    _write_jsonl(run_dir / "resolver_rows.jsonl", resolver)
    _write_jsonl(run_dir / "cross_source_audit_rows.jsonl", audits)
    return receipt


def _write_attempts(root: Path, receipts: list[dict]) -> None:
    _write_jsonl(root / "attempts.jsonl", receipts)


def test_wilson_73_of_73_clears_frozen_point_95_gate() -> None:
    assert wilson_lower(73, 73) > 0.95
    assert wilson_lower(72, 72) < 0.95


def test_passes_only_narrow_week2_identity_authority(tmp_path: Path) -> None:
    root = tmp_path / "out"
    first = _add_execution(root, execution_id="first", captured_at="2026-09-20T16:00:00Z")
    _write_attempts(root, [first])
    result = evaluate(execution_output_dir=root)
    assert result["status"] == "PASS_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY"
    assert result["metrics"]["total_resolver_rows"] == 73
    assert result["metrics"]["exact_unique_resolution_rate"] == 1.0
    assert result["metrics"]["independent_audit_agreement"] == 1.0
    assert result["gates"]["independent_agreement_wilson95_lower_gte_0_95"] is True
    assert result["authority"]["week2_sunday_due_inactive_player_identity_to_gsis_qualified"] is True
    assert result["authority"]["general_2026_player_identity_to_gsis_qualified"] is False
    assert result["authority"]["availability_probability_feature_authorized"] is False
    assert result["authority"]["production_authorized"] is False
    assert result["completed_2026_outcomes_used"] == 0


def test_72_of_72_fails_minimum_independent_evidence_gate(tmp_path: Path) -> None:
    root = tmp_path / "out"
    first = _add_execution(root, execution_id="first", captured_at="2026-09-20T16:00:00Z", n=72)
    _write_attempts(root, [first])
    result = evaluate(execution_output_dir=root)
    assert result["status"] == "FAIL_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY"
    assert result["gates"]["independent_auditable_rows_gte_73"] is False
    assert result["gates"]["independent_agreement_wilson95_lower_gte_0_95"] is False


def test_cross_source_contradiction_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "out"
    first = _add_execution(root, execution_id="first", captured_at="2026-09-20T16:00:00Z", contradiction_index=0)
    _write_attempts(root, [first])
    result = evaluate(execution_output_dir=root)
    assert result["status"] == "FAIL_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY"
    assert result["gates"]["first_execution_status_pass"] is False
    assert result["gates"]["cross_source_contradictions_zero"] is False


def test_one_unresolved_in_73_fails_0_995_resolution_gate(tmp_path: Path) -> None:
    root = tmp_path / "out"
    first = _add_execution(root, execution_id="first", captured_at="2026-09-20T16:00:00Z", unresolved_index=0)
    _write_attempts(root, [first])
    result = evaluate(execution_output_dir=root)
    assert result["status"] == "FAIL_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY"
    assert result["metrics"]["exact_unique_resolution_rate"] < 0.995
    assert result["gates"]["exact_unique_resolution_rate_gte_0_995"] is False


def test_later_execution_cannot_rescue_first_identity_execution(tmp_path: Path) -> None:
    root = tmp_path / "out"
    first = _add_execution(root, execution_id="first", captured_at="2026-09-20T16:00:00Z", n=72)
    later = _add_execution(root, execution_id="later", captured_at="2026-09-20T16:10:00Z", n=73)
    _write_attempts(root, [later, first])
    result = evaluate(execution_output_dir=root)
    assert result["evaluated_execution_id"] == "first"
    assert result["status"] == "FAIL_WEEK2_SUNDAY_DUE_INACTIVE_IDENTITY"


def test_contract_identity_is_stable() -> None:
    assert CONTRACT_ID == "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-IDENTITY-QUALIFICATION-V1"

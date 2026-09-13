from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.v09b_execution_gate_v1 import evaluate_v09b_execution_gate


def test_validation_source_alone_cannot_authorize_v09b_fit():
    report = evaluate_v09b_execution_gate(
        validation_source_state_qualified=True,
        training_source_chronology_qualified=False,
        training_label_semantics_qualified=False,
        original_v09b_preregistration_unchanged=True,
    )
    assert report["v09b_execution_authorized"] is False
    assert set(report["blockers"]) == {
        "training_source_chronology_qualified",
        "training_label_semantics_qualified",
    }


def test_all_source_and_preregistration_gates_are_required():
    report = evaluate_v09b_execution_gate(
        validation_source_state_qualified=True,
        training_source_chronology_qualified=True,
        training_label_semantics_qualified=True,
        original_v09b_preregistration_unchanged=True,
    )
    assert report["blockers"] == []
    assert report["v09b_execution_authorized"] is True
    assert report["probability_model_built_by_gate"] is False
    assert report["production_dependency_authorized"] is False


def test_completed_2026_outcomes_fail_closed():
    with pytest.raises(ValueError, match="forbids completed 2026 outcomes"):
        evaluate_v09b_execution_gate(
            validation_source_state_qualified=True,
            training_source_chronology_qualified=True,
            training_label_semantics_qualified=True,
            original_v09b_preregistration_unchanged=True,
            completed_2026_outcomes_used=1,
        )


def test_effective_governance_recognizes_v3_validation_but_stays_closed():
    governance = json.loads(
        Path("research/availability/v09b_execution_governance_v1.json").read_text(
            encoding="utf-8"
        )
    )
    current = governance["current_evidence"]
    assert current["validation_source_state_qualified"] is True
    assert current["validation_source_contract_id"] == "V09B-AVAILABILITY-PRACTICE-STATE-CROSSCHECK-V3"
    assert current["training_source_chronology_qualified"] is False
    assert current["training_label_semantics_qualified"] is False
    assert current["original_preregistration_unchanged"] is True
    assert current["completed_2026_outcomes_used"] == 0

    report = evaluate_v09b_execution_gate(
        validation_source_state_qualified=current["validation_source_state_qualified"],
        training_source_chronology_qualified=current["training_source_chronology_qualified"],
        training_label_semantics_qualified=current["training_label_semantics_qualified"],
        original_v09b_preregistration_unchanged=current["original_preregistration_unchanged"],
        completed_2026_outcomes_used=current["completed_2026_outcomes_used"],
    )
    assert report["v09b_execution_authorized"] is False
    assert set(report["blockers"]) == {
        "training_source_chronology_qualified",
        "training_label_semantics_qualified",
    }
    assert current["v09b_execution_authorized"] is False

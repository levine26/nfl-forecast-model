from __future__ import annotations

"""Fail-closed execution governance for the frozen V09B availability experiment.

This module does not build availability features or fit a model. It only answers whether
all prerequisite source contracts are qualified before V09B may execute.
"""

from typing import Any


def evaluate_v09b_execution_gate(
    *,
    validation_source_state_qualified: bool,
    training_source_chronology_qualified: bool,
    training_label_semantics_qualified: bool,
    original_v09b_preregistration_unchanged: bool,
    completed_2026_outcomes_used: int = 0,
) -> dict[str, Any]:
    if int(completed_2026_outcomes_used) != 0:
        raise ValueError("V09B execution governance forbids completed 2026 outcomes")

    requirements = {
        "validation_source_state_qualified": bool(validation_source_state_qualified),
        "training_source_chronology_qualified": bool(training_source_chronology_qualified),
        "training_label_semantics_qualified": bool(training_label_semantics_qualified),
        "original_v09b_preregistration_unchanged": bool(
            original_v09b_preregistration_unchanged
        ),
    }
    blockers = [name for name, passed in requirements.items() if not passed]
    authorized = not blockers
    return {
        "gate_version": 1,
        "requirements": requirements,
        "blockers": blockers,
        "v09b_execution_authorized": authorized,
        "completed_2026_outcomes_used": 0,
        "probability_model_built_by_gate": False,
        "production_dependency_authorized": False,
    }


__all__ = ["evaluate_v09b_execution_gate"]

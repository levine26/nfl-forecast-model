from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path("research/source_qualification_registry_v2.json")
SLEEPER_QUALIFICATION_PATH = Path("research/sleeper_archive_qualification_v1.json")
INTEGRITY_POLICY_PATH = Path("research/source_integrity_qualification_policy_v1.json")

_RIGHTS_MARKERS = (
    "license",
    "licensing",
    "rights boundary",
    "redistribution",
    "commercial use",
    "commercial/public",
    "public product use",
    "public display",
    "declared license",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def effective_policy() -> dict[str, Any]:
    """Return the source-qualification policy enforced by research code.

    Rights/licensing fields remain governance metadata.  Only data-integrity failures
    can fail technical qualification; point-in-time failures remain explicitly
    fail-closed.
    """

    registry = _load(REGISTRY_PATH)
    overlay = _load(INTEGRITY_POLICY_PATH)
    policy = copy.deepcopy(registry["policy"])
    policy["qualification_basis"] = overlay["qualification_basis"]
    policy["rights_and_licensing"] = copy.deepcopy(overlay["rights_and_licensing"])
    policy["technical_blocker_categories"] = list(overlay["technical_blocker_categories"])
    policy["non_qualification_constraints"] = list(overlay["non_qualification_constraints"])
    policy["completed_2026_outcome_model_selection_allowed"] = overlay[
        "completed_2026_outcome_model_selection_allowed"
    ]
    policy["zero_cost_research_policy_preserved"] = overlay["zero_cost_research_policy_preserved"]
    policy["fail_closed_on_rights_failure"] = False
    policy["fail_closed_on_point_in_time_failure"] = True
    policy["fail_closed_on_data_integrity_failure"] = True
    return policy


def _rights_governance_note(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _RIGHTS_MARKERS)


def _apply_integrity_policy(row: dict[str, Any]) -> dict[str, Any]:
    effective = copy.deepcopy(row)
    known_failures = [str(item) for item in (effective.get("known_source_failures") or [])]
    rights_notes = [item for item in known_failures if _rights_governance_note(item)]
    technical_failures = [item for item in known_failures if not _rights_governance_note(item)]

    effective["qualification_basis"] = "DATA_INTEGRITY_ONLY"
    effective["rights_qualification_blocker"] = False
    effective["rights_metadata_retained"] = True
    effective["technical_known_source_failures"] = technical_failures
    effective["rights_governance_notes"] = rights_notes
    return effective


def effective_sources() -> list[dict[str, Any]]:
    registry = _load(REGISTRY_PATH)
    sources = [_apply_integrity_policy(item) for item in registry["sources"]]
    qualification = _load(SLEEPER_QUALIFICATION_PATH)
    if qualification.get("supplements_registry_scope_for_technical_research") is not True:
        return sources

    source_id = qualification["source_id"]
    row = next((item for item in sources if item.get("source_id") == source_id), None)
    if row is None:
        raise KeyError(f"qualification source not present in registry: {source_id}")

    scope = qualification["effective_scope"]
    row["classification"] = "QUALIFIED_RESEARCH"
    row["provider"] = "edgecdec/declan-fantasy-football verified public GitHub snapshot archive"
    row["historical_coverage"] = "2026-02-01+ point-in-time snapshots; no 2025 reconstruction"
    row["current_2026_support"] = True
    row["historical_research"] = True
    row["prospective_use"] = True
    row["public_display"] = False
    row["probability_features"] = (
        "2026 point-in-time and prospective shadow research after snapshot data-quality gates; "
        "completed-2026 outcome-based selection remains prohibited"
    )
    row["technical_status"] = qualification["technical_status"]
    row["supports_2025_reconstruction"] = scope["supports_2025_reconstruction"]
    row["supports_completed_2026_outcome_model_selection"] = scope[
        "supports_completed_2026_outcome_model_selection"
    ]
    row["supports_production_dependency"] = scope["supports_production_dependency"]
    row["qualification_record"] = str(SLEEPER_QUALIFICATION_PATH)
    row["qualification_basis"] = "DATA_INTEGRITY_ONLY"
    row["rights_qualification_blocker"] = False
    row["technical_known_source_failures"] = [
        "no 2025 historical coverage",
        "collector commit time is a conservative persistence bound rather than an official provider publication timestamp",
    ]
    row["technical_limitations"] = [
        "2025 reconstruction is unsupported",
        "snapshot commit time must be no later than the simulated decision timestamp",
        "completed-2026 outcomes may not be used for model, feature, architecture, hyperparameter or threshold selection",
    ]
    return sources


def effective_source(source_id: str) -> dict[str, Any]:
    for row in effective_sources():
        if row.get("source_id") == source_id:
            return row
    raise KeyError(source_id)

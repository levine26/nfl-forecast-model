from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path("research/source_qualification_registry_v2.json")
SLEEPER_OVERRIDE_PATH = Path("research/sleeper_archive_qualification_v1.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def effective_sources() -> list[dict[str, Any]]:
    registry = _load(REGISTRY_PATH)
    sources = copy.deepcopy(registry["sources"])
    override = _load(SLEEPER_OVERRIDE_PATH)
    if override.get("supersedes_registry_block_for_technical_research") is not True:
        return sources

    source_id = override["source_id"]
    row = next((item for item in sources if item.get("source_id") == source_id), None)
    if row is None:
        raise KeyError(f"override source not present in registry: {source_id}")

    scope = override["effective_scope"]
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
    row["technical_status"] = override["technical_status"]
    row["supports_2025_reconstruction"] = scope["supports_2025_reconstruction"]
    row["supports_completed_2026_outcome_model_selection"] = scope[
        "supports_completed_2026_outcome_model_selection"
    ]
    row["supports_production_dependency"] = scope["supports_production_dependency"]
    row["qualification_override"] = str(SLEEPER_OVERRIDE_PATH)
    return sources


def effective_source(source_id: str) -> dict[str, Any]:
    for row in effective_sources():
        if row.get("source_id") == source_id:
            return row
    raise KeyError(source_id)

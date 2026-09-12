from __future__ import annotations

"""Fail-closed governance for the V09B P(active) training target.

The gate deliberately separates a semantically correct target definition from source
coverage/provenance. A convenient roster-status field cannot authorize fitting unless
it is independently proven equivalent to the official game-specific inactive list.
"""

from dataclasses import dataclass
from typing import Any, Mapping


SEMANTIC_PROPERTIES = (
    "game_specific_active_inactive_semantics",
    "semantic_link_to_official_game_day_inactive_declaration",
    "target_does_not_depend_on_postgame_participation_or_snaps",
)
CHRONOLOGY_PROPERTIES = (
    "player_team_game_identity_reconstructable",
    "all_training_seasons_covered",
    "regular_season_coverage_measurable",
    "stable_identity_mapping_auditable",
    "source_provenance_reproducible",
)
PROHIBITED_PROXY_FLAGS = (
    "uses_current_game_snaps",
    "uses_postgame_participation_as_active_proxy",
    "weekly_roster_status_is_only_label_basis",
)


@dataclass(frozen=True)
class TrainingLabelGateResult:
    training_label_semantics_qualified: bool
    training_source_chronology_qualified: bool
    v09b_model_fit_authorized: bool
    blockers: tuple[str, ...]


def evaluate_training_label_source(
    evidence: Mapping[str, Any],
    *,
    completed_2026_outcomes_used: int = 0,
) -> TrainingLabelGateResult:
    if int(completed_2026_outcomes_used) != 0:
        raise ValueError("completed 2026 outcomes are prohibited in V09B source qualification")

    semantic_blockers = [key for key in SEMANTIC_PROPERTIES if evidence.get(key) is not True]
    chronology_blockers = [key for key in CHRONOLOGY_PROPERTIES if evidence.get(key) is not True]
    proxy_blockers = [key for key in PROHIBITED_PROXY_FLAGS if evidence.get(key) is True]
    blockers = semantic_blockers + chronology_blockers + proxy_blockers

    label_semantics = not semantic_blockers and not proxy_blockers
    chronology = not chronology_blockers and not proxy_blockers
    authorized = label_semantics and chronology

    return TrainingLabelGateResult(
        training_label_semantics_qualified=label_semantics,
        training_source_chronology_qualified=chronology,
        v09b_model_fit_authorized=authorized,
        blockers=tuple(blockers),
    )

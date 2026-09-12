from __future__ import annotations

"""Fail-closed governance for the V09B P(active) training target.

The gate deliberately separates a semantically correct target definition from source
coverage/provenance. A convenient roster-status field cannot authorize fitting unless
it is independently proven equivalent to the official game-specific inactive list.
"""

from dataclasses import dataclass
from typing import Mapping, Any


REQUIRED_PROPERTIES = (
    "game_specific_active_inactive_semantics",
    "semantic_link_to_official_game_day_inactive_declaration",
    "player_team_game_identity_reconstructable",
    "all_training_seasons_covered",
    "regular_season_coverage_measurable",
    "stable_identity_mapping_auditable",
    "target_does_not_depend_on_postgame_participation_or_snaps",
    "source_provenance_reproducible",
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

    blockers: list[str] = []
    for key in REQUIRED_PROPERTIES:
        if evidence.get(key) is not True:
            blockers.append(key)

    if evidence.get("uses_current_game_snaps") is True:
        blockers.append("uses_current_game_snaps")
    if evidence.get("uses_postgame_participation_as_active_proxy") is True:
        blockers.append("uses_postgame_participation_as_active_proxy")
    if evidence.get("weekly_roster_status_is_only_label_basis") is True:
        blockers.append("weekly_roster_status_is_only_label_basis")

    label_semantics = bool(
        evidence.get("game_specific_active_inactive_semantics") is True
        and evidence.get("semantic_link_to_official_game_day_inactive_declaration") is True
        and evidence.get("target_does_not_depend_on_postgame_participation_or_snaps") is True
        and not any(
            item in blockers
            for item in (
                "uses_current_game_snaps",
                "uses_postgame_participation_as_active_proxy",
                "weekly_roster_status_is_only_label_basis",
            )
        )
    )
    chronology = bool(
        evidence.get("all_training_seasons_covered") is True
        and evidence.get("regular_season_coverage_measurable") is True
        and evidence.get("source_provenance_reproducible") is True
        and evidence.get("player_team_game_identity_reconstructable") is True
        and evidence.get("stable_identity_mapping_auditable") is True
    )
    authorized = label_semantics and chronology and not blockers
    return TrainingLabelGateResult(
        training_label_semantics_qualified=label_semantics and not blockers,
        training_source_chronology_qualified=chronology and not blockers,
        v09b_model_fit_authorized=authorized,
        blockers=tuple(blockers),
    )

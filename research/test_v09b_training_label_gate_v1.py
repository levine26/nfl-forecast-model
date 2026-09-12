from __future__ import annotations

import pytest

from research.v09b_training_label_gate_v1 import evaluate_training_label_source


def _complete_evidence() -> dict[str, bool]:
    return {
        "game_specific_active_inactive_semantics": True,
        "semantic_link_to_official_game_day_inactive_declaration": True,
        "player_team_game_identity_reconstructable": True,
        "all_training_seasons_covered": True,
        "regular_season_coverage_measurable": True,
        "stable_identity_mapping_auditable": True,
        "target_does_not_depend_on_postgame_participation_or_snaps": True,
        "source_provenance_reproducible": True,
        "uses_current_game_snaps": False,
        "uses_postgame_participation_as_active_proxy": False,
        "weekly_roster_status_is_only_label_basis": False,
    }


def test_weekly_roster_status_alone_cannot_authorize_target() -> None:
    evidence = _complete_evidence()
    evidence["weekly_roster_status_is_only_label_basis"] = True
    result = evaluate_training_label_source(evidence)
    assert result.training_label_semantics_qualified is False
    assert result.v09b_model_fit_authorized is False
    assert "weekly_roster_status_is_only_label_basis" in result.blockers


def test_postgame_participation_proxy_cannot_authorize_target() -> None:
    evidence = _complete_evidence()
    evidence["uses_postgame_participation_as_active_proxy"] = True
    result = evaluate_training_label_source(evidence)
    assert result.training_label_semantics_qualified is False
    assert result.v09b_model_fit_authorized is False


def test_semantics_without_2012_2021_coverage_cannot_authorize_fit() -> None:
    evidence = _complete_evidence()
    evidence["all_training_seasons_covered"] = False
    result = evaluate_training_label_source(evidence)
    assert result.training_label_semantics_qualified is True
    assert result.training_source_chronology_qualified is False
    assert result.v09b_model_fit_authorized is False


def test_only_complete_clean_source_can_authorize() -> None:
    result = evaluate_training_label_source(_complete_evidence())
    assert result.training_label_semantics_qualified is True
    assert result.training_source_chronology_qualified is True
    assert result.v09b_model_fit_authorized is True
    assert result.blockers == ()


def test_completed_2026_outcome_use_raises() -> None:
    with pytest.raises(ValueError, match="completed 2026 outcomes"):
        evaluate_training_label_source(_complete_evidence(), completed_2026_outcomes_used=1)

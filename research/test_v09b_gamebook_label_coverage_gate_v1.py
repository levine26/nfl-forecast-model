from __future__ import annotations

import pytest

from research.v09b_gamebook_label_coverage_gate_v1 import (
    EXPECTED_GAMES_BY_SEASON,
    EXPECTED_TOTAL,
    evaluate_historical_label_coverage,
)


def _complete_receipt() -> dict[str, object]:
    return {
        "canonical_games_by_season": dict(EXPECTED_GAMES_BY_SEASON),
        "canonical_games_total": EXPECTED_TOTAL,
        "games_with_verified_source_bytes": EXPECTED_TOTAL,
        "duplicate_game_source_rows": 0,
        "canonical_game_coverage_rate": 1.0,
        "source_bytes_verified_rate": 1.0,
        "gamebook_parse_success_rate": 1.0,
        "not_active_section_present_rate": 1.0,
        "did_not_play_semantically_distinguished_rate": 1.0,
        "game_day_roster_universe_coverage_rate": 1.0,
        "player_team_game_identity_resolution_rate": 0.999,
        "duplicate_player_team_game_labels": 0,
        "contradictory_active_inactive_labels": 0,
        "positive_class_requires_game_day_roster_universe": True,
        "active_inferred_from_postgame_participation": False,
        "weekly_roster_ina_is_label_authority": False,
        "source_provenance_reproducible": True,
    }


def test_complete_clean_decade_can_authorize_source_gate() -> None:
    result = evaluate_historical_label_coverage(_complete_receipt())
    assert result.inactive_source_qualified is True
    assert result.game_day_roster_universe_qualified is True
    assert result.training_label_semantics_qualified is True
    assert result.training_source_chronology_qualified is True
    assert result.v09b_model_fit_authorized is True
    assert result.blockers == ()


def test_one_missing_game_fails_closed() -> None:
    receipt = _complete_receipt()
    receipt["games_with_verified_source_bytes"] = EXPECTED_TOTAL - 1
    receipt["canonical_game_coverage_rate"] = (EXPECTED_TOTAL - 1) / EXPECTED_TOTAL
    result = evaluate_historical_label_coverage(receipt)
    assert result.inactive_source_qualified is False
    assert result.v09b_model_fit_authorized is False
    assert "not all canonical games have verified source bytes" in result.blockers


def test_missing_season_game_cannot_be_hidden_by_total() -> None:
    receipt = _complete_receipt()
    counts = dict(EXPECTED_GAMES_BY_SEASON)
    counts[2016] -= 1
    counts[2021] += 1
    receipt["canonical_games_by_season"] = counts
    result = evaluate_historical_label_coverage(receipt)
    assert result.v09b_model_fit_authorized is False
    assert "canonical season game counts mismatch" in result.blockers


def test_inactive_list_without_positive_roster_denominator_is_insufficient() -> None:
    receipt = _complete_receipt()
    receipt["game_day_roster_universe_coverage_rate"] = 0.0
    receipt["positive_class_requires_game_day_roster_universe"] = False
    result = evaluate_historical_label_coverage(receipt)
    assert result.inactive_source_qualified is True
    assert result.game_day_roster_universe_qualified is False
    assert result.training_label_semantics_qualified is False
    assert result.v09b_model_fit_authorized is False


def test_postgame_participation_cannot_define_active_class() -> None:
    receipt = _complete_receipt()
    receipt["active_inferred_from_postgame_participation"] = True
    result = evaluate_historical_label_coverage(receipt)
    assert result.game_day_roster_universe_qualified is False
    assert result.v09b_model_fit_authorized is False


def test_weekly_roster_ina_cannot_be_label_authority() -> None:
    receipt = _complete_receipt()
    receipt["weekly_roster_ina_is_label_authority"] = True
    result = evaluate_historical_label_coverage(receipt)
    assert result.game_day_roster_universe_qualified is False
    assert result.v09b_model_fit_authorized is False


def test_completed_2026_outcomes_raise() -> None:
    with pytest.raises(ValueError, match="completed 2026 outcomes"):
        evaluate_historical_label_coverage(_complete_receipt(), completed_2026_outcomes_used=1)

from __future__ import annotations

from research.levline3_chronological_accuracy_audit_v1 import audit


def test_chronology_clean_fst_accuracy_audit_matches_frozen_historical_inputs() -> None:
    result = audit()
    assert result["games"] == 1087
    assert result["stack_correct"] == 741
    assert result["market_correct"] == 735
    assert abs(result["stack_accuracy"] - 0.6816927322907084) < 1e-12
    assert abs(result["market_accuracy"] - 0.6761729530818767) < 1e-12
    assert result["disagreement_games"] == 34
    assert result["stack_only_correct"] == 20
    assert result["market_only_correct"] == 14
    assert abs(result["switch_win_rate"] - (20 / 34)) < 1e-12
    assert result["2026_outcomes_used"] == 0
    assert result["production_changed"] is False
    assert result["promotion_authorized"] is False


def test_chronological_stack_is_trained_only_on_prior_seasons() -> None:
    result = audit()
    by_target = {int(row["season"]): row for row in result["coefficients"]}
    assert set(by_target) == {2022, 2023, 2024, 2025}
    assert by_target[2022]["training_last_season"] == 2021
    assert by_target[2023]["training_last_season"] == 2022
    assert by_target[2024]["training_last_season"] == 2023
    assert by_target[2025]["training_last_season"] == 2024

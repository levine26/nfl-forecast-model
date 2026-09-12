from __future__ import annotations

import pandas as pd

from research.levline4_accuracy_primary_v1 import (
    horizon_pair_comparison,
    paired_accuracy_comparison,
)


def _frame(correct, *, horizon="T-45m", brier=None, weeks=None):
    rows = []
    for i, value in enumerate(correct):
        rows.append(
            {
                "game_id": f"g{i}",
                "horizon": horizon,
                "winner_correct_eval": float(value),
                "brier_loss": float((brier or [0.2] * len(correct))[i]),
                "log_loss": 0.6,
                "season": 2026,
                "week": int((weeks or [1 + (i % 2) for i in range(len(correct))])[i]),
            }
        )
    return pd.DataFrame(rows)


def test_disagreement_set_identity() -> None:
    candidate = _frame([1, 1, 0, 1])
    benchmark = _frame([1, 0, 1, 1])
    result = paired_accuracy_comparison(candidate, benchmark, label="incumbent")
    assert result["games"] == 4
    assert result["candidate_accuracy"] == 0.75
    assert result["benchmark_accuracy"] == 0.75
    assert result["accuracy_delta"] == 0.0
    assert result["candidate_only_correct"] == 1
    assert result["benchmark_only_correct"] == 1
    assert result["discordant_games"] == 2
    assert result["switch_win_rate"] == 0.5
    assert result["mcnemar_exact_two_sided_p_diagnostic"] == 1.0
    assert result["promotion_authorized"] is False


def test_candidate_accuracy_gain_is_exactly_net_switches_over_all_games() -> None:
    candidate = _frame([1, 1, 1, 1, 0, 1])
    benchmark = _frame([1, 0, 0, 1, 1, 1])
    result = paired_accuracy_comparison(candidate, benchmark, label="incumbent")
    assert result["candidate_only_correct"] == 2
    assert result["benchmark_only_correct"] == 1
    assert result["discordant_games"] == 3
    assert result["switch_win_rate"] == 2 / 3
    assert result["accuracy_delta"] == 1 / 6


def test_no_disagreements_produces_no_switch_rate() -> None:
    candidate = _frame([1, 0, 1, 1])
    benchmark = _frame([1, 0, 1, 1])
    result = paired_accuracy_comparison(candidate, benchmark, label="incumbent")
    assert result["discordant_games"] == 0
    assert result["switch_win_rate"] is None
    assert result["accuracy_delta"] == 0.0
    assert result["mcnemar_exact_two_sided_p_diagnostic"] is None


def test_horizon_comparison_pairs_by_game_not_horizon_label() -> None:
    t45 = _frame([1, 1, 0, 1], horizon="T-45m")
    t120 = _frame([1, 0, 1, 1], horizon="T-120m")
    scored = pd.concat([t45, t120], ignore_index=True)
    result = horizon_pair_comparison(scored, "T-45m", "T-120m")
    assert result["games"] == 4
    assert result["candidate_only_correct"] == 1
    assert result["benchmark_only_correct"] == 1


def test_brier_is_secondary_guardrail_not_primary_selection() -> None:
    candidate = _frame([1, 1, 1, 1], brier=[0.21, 0.21, 0.21, 0.21])
    benchmark = _frame([1, 0, 1, 1], brier=[0.20, 0.20, 0.20, 0.20])
    result = paired_accuracy_comparison(candidate, benchmark, label="incumbent")
    assert result["accuracy_delta"] == 0.25
    assert result["brier_delta"] > 0
    assert "brier_secondary_guardrail_pass" in result
    assert result["promotion_authorized"] is False

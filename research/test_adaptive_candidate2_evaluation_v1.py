from __future__ import annotations

import pandas as pd

from research.adaptive_candidate2_evaluation_v1 import _coverage, _score


def _frame():
    return pd.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2025] * 4,
            "week": [1, 1, 2, 2],
            "home_win": [1, 0, 1, 0],
            "fst_prob": [0.60, 0.60, 0.40, 0.40],
            "candidate_prob": [0.60, 0.40, 0.60, 0.40],
            "strong_regime_shock": [False, True, True, False],
            "boundary_eligible": [False, True, True, False],
            "component_disagrees": [False, True, True, False],
            "candidate_switch": [False, True, True, False],
            "home_qb_practice_qualified": [False, True, False, False],
            "away_qb_practice_qualified": [False, False, True, False],
        }
    )


def test_score_counts_exact_winner_accuracy():
    frame = _frame()
    fst = _score(frame, "fst_prob")
    candidate = _score(frame, "candidate_prob")
    assert fst["correct"] == 2
    assert candidate["correct"] == 4
    assert fst["accuracy"] == 0.5
    assert candidate["accuracy"] == 1.0


def test_coverage_counts_only_same_sample_rows():
    coverage = _coverage(_frame())
    assert coverage["paired_games"] == 4
    assert coverage["weeks"] == 2
    assert coverage["strong_shock_games"] == 2
    assert coverage["candidate2_switches"] == 2
    assert coverage["qualified_qb_practice_join_games"] == 2

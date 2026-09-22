from __future__ import annotations

import pandas as pd

from research.adaptive_weekly_evaluation_v1 import exact_mcnemar_two_sided, switch_accounting


def test_switch_accounting_counts_only_disagreements():
    frame = pd.DataFrame({
        "home_win":[1,0,1,0],
        "reference":[0.6,0.4,0.6,0.6],
        "candidate":[0.6,0.6,0.4,0.4],
    })
    result = switch_accounting(frame, "candidate", "reference")
    assert result["disagreements"] == 3
    assert result["candidate_only_correct"] == 2
    assert result["reference_only_correct"] == 1
    assert result["net_correct_from_switches"] == 1


def test_exact_mcnemar_is_bounded():
    p = exact_mcnemar_two_sided(10, 2)
    assert 0.0 <= p <= 1.0

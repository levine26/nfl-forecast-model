from __future__ import annotations

import pandas as pd

from research.adaptive_candidate2_adversarial_v1 import _phase


def test_phase_partition_is_frozen():
    weeks = pd.Series([1, 6, 7, 12, 13, 22])
    assert _phase(weeks).tolist() == ["early", "early", "mid", "mid", "late", "late"]

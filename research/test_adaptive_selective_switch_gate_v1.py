from __future__ import annotations

import pandas as pd

from research.adaptive_selective_switch_gate_v1 import apply_selective_gate


def test_gate_switches_only_near_boundary_with_material_shift():
    frame = pd.DataFrame([
        {"fst_prob":0.53,"adaptive_prob":0.47},
        {"fst_prob":0.70,"adaptive_prob":0.30},
        {"fst_prob":0.52,"adaptive_prob":0.49},
        {"fst_prob":0.48,"adaptive_prob":0.60},
    ])
    out = apply_selective_gate(frame)
    assert bool(out.loc[0, "gate_eligible"]) is True
    assert bool(out.loc[1, "gate_eligible"]) is False
    assert bool(out.loc[2, "gate_eligible"]) is False
    assert bool(out.loc[3, "gate_eligible"]) is True
    assert out.loc[1, "gate_prob"] == out.loc[1, "fst_prob"]

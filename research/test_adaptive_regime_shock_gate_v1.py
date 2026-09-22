from __future__ import annotations

import numpy as np
import pandas as pd

from research.adaptive_regime_shock_gate_v1 import GateConfig, apply_gate


def _row(**overrides):
    row = {
        "game_id": "2025_02_AAA_BBB",
        "fst_prob": 0.53,
        "component_prob": 0.47,
        "home_qb1_changed": 0.0,
        "away_qb1_changed": 0.0,
        "home_ol_rank1_new_count": 0.0,
        "away_ol_rank1_new_count": 0.0,
        "home_qb_practice_status": None,
        "away_qb_practice_status": None,
    }
    row.update(overrides)
    return row


def test_gate_requires_all_three_conditions():
    frame = pd.DataFrame([_row(home_qb1_changed=1.0)])
    scored = apply_gate(frame)
    assert scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == 0.47


def test_gate_preserves_fst_without_shock():
    scored = apply_gate(pd.DataFrame([_row()]))
    assert not scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == 0.53


def test_gate_preserves_fst_without_component_disagreement():
    scored = apply_gate(
        pd.DataFrame([_row(component_prob=0.55, home_qb1_changed=1.0)])
    )
    assert not scored.loc[0, "candidate_switch"]


def test_gate_preserves_fst_outside_boundary():
    scored = apply_gate(
        pd.DataFrame([_row(fst_prob=0.60, home_qb1_changed=1.0)])
    )
    assert not scored.loc[0, "candidate_switch"]


def test_missing_state_fails_closed():
    scored = apply_gate(
        pd.DataFrame(
            [
                _row(
                    home_qb1_changed=np.nan,
                    away_qb1_changed=np.nan,
                    home_ol_rank1_new_count=np.nan,
                    away_ol_rank1_new_count=np.nan,
                )
            ]
        )
    )
    assert not scored.loc[0, "strong_regime_shock"]
    assert not scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == 0.53


def test_primary_ol_threshold_is_two():
    scored = apply_gate(
        pd.DataFrame(
            [
                _row(home_ol_rank1_new_count=1.0),
                _row(game_id="2025_02_CCC_DDD", home_ol_rank1_new_count=2.0),
            ]
        )
    )
    assert not scored.loc[0, "shock_ol_churn"]
    assert scored.loc[1, "shock_ol_churn"]
    assert scored.loc[1, "candidate_switch"]


def test_dnp_primary_and_limited_sensitivity_are_frozen():
    frame = pd.DataFrame(
        [
            _row(home_qb_practice_status="dnp"),
            _row(game_id="2025_02_CCC_DDD", home_qb_practice_status="limited"),
        ]
    )
    primary = apply_gate(frame)
    assert primary.loc[0, "shock_qb_practice"]
    assert not primary.loc[1, "shock_qb_practice"]

    sensitivity = apply_gate(
        frame,
        GateConfig(practice_definition="DNP_or_limited"),
    )
    assert sensitivity["shock_qb_practice"].tolist() == [True, True]


def test_gate_does_not_require_outcome_column():
    frame = pd.DataFrame([_row(home_qb1_changed=1.0)])
    assert "home_win" not in frame.columns
    scored = apply_gate(frame)
    assert scored.loc[0, "candidate_switch"]

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.adaptive_regime_shock_gate_v1 import (
    GateConfig,
    apply_gate,
    build_component_challenger,
    verify_registered_component_result,
)


def _row(**overrides):
    row = {
        "game_id": "2025_02_AAA_BBB",
        "fst_prob": 0.53,
        "component_prob": 0.47,
        "home_qb_change_shock": False,
        "away_qb_change_shock": False,
        "home_ol_new_count": 0.0,
        "away_ol_new_count": 0.0,
        "home_qb_practice_status": "",
        "away_qb_practice_status": "",
        "home_qb_practice_qualified": False,
        "away_qb_practice_qualified": False,
    }
    row.update(overrides)
    return row


def test_gate_switches_only_when_boundary_disagreement_and_shock_align():
    frame = pd.DataFrame([_row(home_qb_change_shock=True)])
    scored = apply_gate(frame)
    assert scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == pytest.approx(0.47)
    assert scored.loc[0, "shock_reason"] == "qb_change"


def test_gate_preserves_fst_without_shock():
    scored = apply_gate(pd.DataFrame([_row()]))
    assert not scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == pytest.approx(0.53)


def test_gate_preserves_fst_without_component_disagreement():
    scored = apply_gate(pd.DataFrame([_row(component_prob=0.55, home_qb_change_shock=True)]))
    assert not scored.loc[0, "candidate_switch"]


def test_gate_preserves_fst_outside_boundary():
    scored = apply_gate(pd.DataFrame([_row(fst_prob=0.60, home_qb_change_shock=True)]))
    assert not scored.loc[0, "candidate_switch"]


def test_missing_state_fails_closed():
    scored = apply_gate(
        pd.DataFrame(
            [
                _row(
                    home_qb_change_shock=np.nan,
                    away_qb_change_shock=np.nan,
                    home_ol_new_count=np.nan,
                    away_ol_new_count=np.nan,
                )
            ]
        )
    )
    assert not scored.loc[0, "strong_regime_shock"]
    assert not scored.loc[0, "candidate_switch"]
    assert scored.loc[0, "candidate_prob"] == pytest.approx(0.53)


def test_primary_ol_threshold_is_two():
    scored = apply_gate(
        pd.DataFrame(
            [
                _row(home_ol_new_count=1.0),
                _row(game_id="2025_02_CCC_DDD", home_ol_new_count=2.0),
            ]
        )
    )
    assert not scored.loc[0, "shock_ol_churn"]
    assert scored.loc[1, "shock_ol_churn"]
    assert scored.loc[1, "candidate_switch"]


def test_dnp_requires_qualified_practice_row():
    frame = pd.DataFrame(
        [
            _row(home_qb_practice_status="dnp", home_qb_practice_qualified=True),
            _row(
                game_id="2025_02_CCC_DDD",
                home_qb_practice_status="dnp",
                home_qb_practice_qualified=False,
            ),
        ]
    )
    scored = apply_gate(frame)
    assert scored.loc[0, "shock_qb_practice"]
    assert not scored.loc[1, "shock_qb_practice"]


def test_limited_status_is_robustness_only_not_primary():
    frame = pd.DataFrame(
        [
            _row(
                home_qb_practice_status="limited",
                home_qb_practice_qualified=True,
            )
        ]
    )
    primary = apply_gate(frame)
    assert not primary.loc[0, "shock_qb_practice"]

    sensitivity = apply_gate(frame, GateConfig(practice_mode="dnp_or_limited"))
    assert sensitivity.loc[0, "shock_qb_practice"]
    assert sensitivity.loc[0, "candidate_switch"]


def test_gate_refuses_target_outcome_column():
    frame = pd.DataFrame([_row(home_qb_change_shock=True)])
    frame["home_win"] = 1
    with pytest.raises(ValueError, match="before target outcomes"):
        apply_gate(frame)


def test_registered_component_stack_reproduces_before_candidate2():
    component = build_component_challenger()
    audit = verify_registered_component_result(component)
    assert audit["games"] == 1087
    assert audit["correct"] == 744
    assert audit["reproduced"] is True

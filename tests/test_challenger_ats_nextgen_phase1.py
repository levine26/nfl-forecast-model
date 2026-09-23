from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "research" / "ats-nextgen"


def _registry() -> dict:
    return json.loads((PROGRAM / "phase1_registry.json").read_text())


def test_phase1_registry_freezes_candidate_identities_and_firewalls():
    registry = _registry()
    assert registry["program"] == "LEVLINE_ATS_NEXTGEN"
    assert registry["phase"] == 1
    assert registry["production_model"] == "F-ST-01-FROZEN-2026"
    assert registry["production_changed"] is False
    assert registry["completed_2026_outcomes_authorized"] is False
    assert registry["phase2_started"] is False
    assert registry["chronology"]["random_kfold_allowed"] is False
    assert registry["chronology"]["outer_target_seasons"] == [2022, 2023, 2024, 2025]
    assert registry["q1"]["id"] == "ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1"
    assert registry["q2"]["id"] == "ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1"
    assert registry["q3"]["id"] == "ATS-Q3-DIRECT-CPL-HURDLE-V1"
    assert registry["q1"]["quantiles"] == [10 / 21, 0.5, 11 / 21]
    assert registry["q2"]["key_abs_margins"] == [3, 6, 7, 10, 14]
    assert registry["blend"]["q2_weight_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_phase1_canonical_sign_contract_and_required_files():
    registry = _registry()
    sign = registry["canonical_sign"]
    assert sign["ats_residual"] == "margin+home_spread"
    assert sign["cover"] == "ats_residual>0"
    assert sign["push"] == "ats_residual==0"
    assert sign["loss"] == "ats_residual<0"

    required = {
        "MASTER_PLAN.md",
        "PHASE_STATUS.md",
        "CURRENT_STATE_AND_NEXT_STEPS.md",
        "PHASE1_RESEARCH_CHARTER.md",
        "ATS_PROBLEM_REFORMULATION.md",
        "LITERATURE_REVIEW.md",
        "OPEN_SOURCE_MODEL_REVIEW.md",
        "MARKET_MICROSTRUCTURE_REVIEW.md",
        "DATA_AND_PIT_INVENTORY.md",
        "Q1_QUANTILE_PREREGISTRATION.md",
        "Q2_MARGIN_DISTRIBUTION_PREREGISTRATION.md",
        "Q3_DIRECT_ATS_PREREGISTRATION.md",
        "EVALUATION_PROTOCOL.md",
        "CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md",
        "ATS_ECONOMICS_AND_EV_CONTRACT.md",
        "RED_TEAM_AND_LEAKAGE_CHECKLIST.md",
        "PHASE2_HANDOFF.md",
        "FINAL_PHASE1_RECEIPT.md",
        "phase1_registry.json",
    }
    assert required <= {p.name for p in PROGRAM.iterdir() if p.is_file()}

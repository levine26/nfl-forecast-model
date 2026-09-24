from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "research" / "ats-frontier-v2"


def _registry() -> dict:
    return json.loads((PROGRAM / "phase1_registry.json").read_text())


def test_frontier_phase1_firewalls_and_shortlist():
    registry = _registry()
    assert registry["program"] == "LEVLINE_ATS_FRONTIER_V2"
    assert registry["phase"] == 1
    assert registry["production_model"] == "F-ST-01-FROZEN-2026"
    assert registry["production_changed"] is False
    assert registry["completed_2026_outcomes_authorized"] is False
    assert registry["completed_2026_outcomes_used_for_design"] == 0
    assert registry["new_frontier_candidate_performance_inspected"] is False
    assert registry["phase2_started"] is False
    assert registry["promotion_requires_explicit_user_green_light"] is True

    assert [c["id"] for c in registry["shortlist"]] == [
        "FRONTIER-M1-DYNAMIC-MARKET-STATE",
        "FRONTIER-M2-PLAYER-STATE-DELTA",
        "FRONTIER-M3-HIERARCHICAL-STATE",
        "FRONTIER-M4-DISCRETE-MARGIN-V2",
    ]


def test_frontier_phase1_sign_contract():
    sign = _registry()["canonical_sign"]
    assert sign["margin"] == "home_score-away_score"
    assert sign["ats_residual"] == "margin+home_spread"
    assert sign["cover"] == "ats_residual>0"
    assert sign["push"] == "ats_residual==0"
    assert sign["loss"] == "ats_residual<0"


def test_frontier_phase1_required_research_package():
    required = {
        "MASTER_PLAN.md",
        "PHASE_STATUS.md",
        "CURRENT_STATE_AND_NEXT_STEPS.md",
        "DECISION_LOG.md",
        "RESEARCH_INDEX.md",
        "SOURCE_LEDGER.md",
        "LEVLINE_FAILURE_ATLAS.md",
        "MARKET_EFFICIENCY_REVIEW.md",
        "MARKET_MICROSTRUCTURE_REVIEW.md",
        "MARKET_DATA_SOURCE_MATRIX.md",
        "NFL_DATA_SOURCE_MATRIX.md",
        "PLAYER_STATE_RESEARCH.md",
        "QB_VALUE_RESEARCH.md",
        "DYNAMIC_TEAM_STRENGTH_RESEARCH.md",
        "DISTRIBUTIONAL_FORECASTING_RESEARCH.md",
        "DISCRETE_MARGIN_V2_RESEARCH.md",
        "FORECAST_COMBINATION_RESEARCH.md",
        "OPEN_SOURCE_MODEL_REVIEW.md",
        "PROFESSIONAL_MODEL_REVIEW.md",
        "DAVID_SASSER_REVIEW.md",
        "CROSS_DOMAIN_METHOD_TRANSFER.md",
        "MARKET_DOMINANCE_FORENSICS.md",
        "CANDIDATE_RESEARCH_CARDS.md",
        "CANDIDATE_SHORTLIST.md",
        "DATA_FEASIBILITY_PREVIEW.md",
        "FUTURE_PHASE_ROADMAP.md",
        "PRODUCTION_FIREWALL.md",
        "EVIDENCE_BOUNDARY.md",
        "FUTURE_CHAT_PROTOCOL.md",
        "OPENING_RECEIPT.md",
        "phase1_registry.json",
    }
    actual = {p.name for p in PROGRAM.iterdir() if p.is_file()}
    assert required <= actual

    registry = _registry()
    if registry["status"] == "COMPLETE":
        assert "FINAL_PHASE1_RECEIPT.md" in actual
    else:
        assert registry["status"] == "SCIENTIFIC_WORK_COMPLETE_CLOSEOUT_PENDING"


def test_frontier_phase1_source_depth_and_rejected_hypotheses():
    registry = _registry()
    counts = registry["source_counts"]
    assert counts["serious_academic_or_technical"] >= 25
    assert counts["open_source_repositories_or_packages"] >= 15
    assert counts["professional_or_practitioner_systems"] >= 10
    assert counts["market_or_data_sources"] >= 10
    assert "simple_line_movement_rule" in registry["rejected_before_implementation"]
    assert "residual_stacking_or_ensemble_only_candidate" in registry["rejected_before_implementation"]

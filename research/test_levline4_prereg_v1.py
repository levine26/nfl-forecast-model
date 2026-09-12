from __future__ import annotations

import json
from pathlib import Path


SPEC = Path(__file__).with_name("levline4_prereg_v1.json")


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_levline4_is_research_only_and_preserves_frozen_production() -> None:
    spec = _spec()
    assert spec["status"] == "preregistered_research_only"
    assert spec["production_authorized"] is False
    assert spec["production_behavior_must_remain_unchanged"] is True
    assert spec["incumbent"]["candidate_id"] == "F-ST-01-FROZEN-2026"
    assert spec["incumbent"]["official_lock_horizon_minutes"] == 120
    assert spec["incumbent"]["mutation_allowed"] is False


def test_final_horizon_candidates_are_fixed_before_outcome_selection() -> None:
    spec = _spec()
    assert spec["research_clocks"]["final_candidate_horizons"] == [
        "T-60m",
        "T-45m",
        "T-30m",
    ]
    assert "No horizon is preferred based on 2026 outcomes" in spec["research_clocks"]["horizon_selection_rule"]


def test_prospective_gate_uses_proper_scoring_and_same_horizon_market() -> None:
    spec = _spec()
    evaluation = spec["evaluation"]
    gate = spec["prospective_evidence_gate"]
    assert evaluation["primary_metric"] == "brier"
    assert gate["minimum_eligible_graded_games"] >= 200
    assert gate["minimum_distinct_nfl_weeks"] >= 14
    assert "same-horizon" in gate["same_horizon_market_gate"]
    assert gate["automatic_promotion"] is False
    assert gate["explicit_authorization_required"] is True


def test_no_hindsight_or_2026_candidate_rescue() -> None:
    spec = _spec()
    integrity = spec["data_integrity"]
    assert integrity["point_in_time_required"] is True
    assert integrity["post_kickoff_information_allowed"] is False
    assert integrity["retrospective_horizon_reconstruction_allowed"] is False
    assert "never use completed 2026 outcomes to rescue" in integrity["2026_outcome_use"]

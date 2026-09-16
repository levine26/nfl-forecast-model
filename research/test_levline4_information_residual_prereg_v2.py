from __future__ import annotations

import json
from pathlib import Path


SPEC = Path(__file__).with_name("levline4_information_residual_prereg_v2.json")


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_program_is_research_only_and_preserves_frozen_incumbent() -> None:
    spec = _spec()
    assert spec["status"] == "preregistered_research_only"
    assert spec["production_authorized"] is False
    assert spec["incumbent"]["candidate_id"] == "F-ST-01-FROZEN-2026"
    assert spec["incumbent"]["official_lock_horizon_minutes"] == 120
    assert spec["incumbent"]["mutation_allowed"] is False


def test_all_ten_hypotheses_are_frozen_with_unique_ids() -> None:
    spec = _spec()
    families = spec["candidate_families"]
    assert len(families) == 10
    ids = [family["id"] for family in families]
    assert len(ids) == len(set(ids))
    assert ids == [
        "L4-H1-EXPECTED-LINEUP-RESIDUAL-V1",
        "L4-H2-QB-SCENARIO-REPLACEMENT-V1",
        "L4-H3-PERSONNEL-CONDITIONED-MATCHUPS-V1",
        "L4-H4-MARKET-PATH-MICROSTRUCTURE-V1",
        "L4-H5-BOOKMAKER-CONSENSUS-V1",
        "L4-H6-INACTIVE-INFORMATION-SURPRISE-V1",
        "L4-H7-STRUCTURAL-REGIME-CHANGE-V1",
        "L4-H8-STRUCTURED-BEAT-INTELLIGENCE-V1",
        "L4-H9-UNCERTAINTY-AWARE-SHRINKAGE-V1",
        "L4-H10-CONDITIONAL-SCENARIO-ENGINE-V1",
    ]


def test_chronology_firewall_forbids_2026_selection_and_hindsight() -> None:
    chronology = _spec()["chronology"]
    assert chronology["historical_selection_end"] == 2025
    assert chronology["completed_2026_outcomes_allowed_for_candidate_selection"] is False
    assert chronology["completed_2026_outcomes_allowed_for_rescue_tuning"] is False
    assert chronology["post_kickoff_inputs_allowed"] is False
    assert chronology["retrospective_tminus_reconstruction_allowed"] is False
    assert chronology["missing_historical_state_policy"] == "remain_missing"


def test_market_path_timing_and_same_horizon_market_are_explicit() -> None:
    families = {family["id"]: family for family in _spec()["candidate_families"]}
    h4 = families["L4-H4-MARKET-PATH-MICROSTRUCTURE-V1"]
    assert h4["required_horizons"] == ["T-120m", "T-60m", "T-45m", "T-30m"]
    assert h4["timing_gate_minutes_relative_to_target"] == [-7.5, 0.0]
    assert "same-horizon market" in h4["primary_gate"]


def test_dependency_blocked_candidates_cannot_skip_validation() -> None:
    families = {family["id"]: family for family in _spec()["candidate_families"]}
    assert families["L4-H3-PERSONNEL-CONDITIONED-MATCHUPS-V1"]["current_authorized_action"] == "blocked_by_dependency"
    assert families["L4-H10-CONDITIONAL-SCENARIO-ENGINE-V1"]["current_authorized_action"] == "blocked_by_dependency_issue_4"


def test_promotion_gate_remains_prospective_and_nonautomatic() -> None:
    gate = _spec()["promotion_firewall"]
    assert gate["minimum_eligible_graded_games"] >= 200
    assert gate["minimum_distinct_nfl_weeks"] >= 14
    assert gate["automatic_promotion"] is False

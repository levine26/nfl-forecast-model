from __future__ import annotations

import json
from pathlib import Path


PREREG = Path("research/ftn_process_prereg_v1.json")
EXPECTED_FIELDS = {
    "n_defense_box",
    "is_motion",
    "is_play_action",
    "is_screen_pass",
    "is_rpo",
    "is_qb_out_of_pocket",
    "is_interception_worthy",
    "n_blitzers",
    "n_pass_rushers",
    "is_qb_fault_sack",
}


def _prereg() -> dict:
    return json.loads(PREREG.read_text(encoding="utf-8"))


def test_ftn_experiment_is_frozen_before_results() -> None:
    prereg = _prereg()
    assert prereg["experiment_id"] == "FTN-PROCESS-01"
    assert prereg["status"] == "PREREGISTERED_NOT_RUN"
    assert prereg["production_effect"] == "none"
    assert set(prereg["candidate_raw_fields"]) == EXPECTED_FIELDS
    assert prereg["model_family"]["hyperparameter_search"] == "none"
    assert prereg["model_family"]["regularization"] == "C=1.0 fixed before results"


def test_ftn_availability_and_outcome_firewalls_are_explicit() -> None:
    prereg = _prereg()
    assert prereg["source"]["availability_field"] == "date_pulled"
    assert "date_pulled" in prereg["source"]["availability_rule"]
    firewall = prereg["outcome_firewall"]
    assert firewall["latest_outcome_season_allowed_for_model_selection"] == 2025
    assert firewall["completed_2026_outcomes_allowed"] is False
    assert firewall["same_game_ftn_rows_allowed"] is False
    assert firewall["realized_same_game_participation_allowed"] is False


def test_ftn_decision_rule_is_not_rescue_tunable() -> None:
    prereg = _prereg()
    rule = prereg["decision_rule"]
    assert "95% block-bootstrap upper bound" in rule["qualify_for_shadow_candidate"]
    assert "do not rescue-tune" in rule["otherwise"]
    assert any("No production promotion" in item for item in prereg["prohibitions"])
    assert any("T-120" in item for item in prereg["prohibitions"])

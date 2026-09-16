from __future__ import annotations

import json
from pathlib import Path

from research.levline4_2026_ngs_player_id_browser_heldout_v4_corrected import (
    load_and_validate_addendum,
    strict_evaluate_gates,
)

CONTRACT = Path("research/levline4_2026_ngs_player_id_browser_heldout_v4_contract.json")
ADDENDUM = Path("research/levline4_2026_ngs_player_id_browser_heldout_v4_preexecution_addendum.json")


def _contract():
    return json.loads(CONTRACT.read_text())


def _synthetic(alias_team_abbr: str):
    targets = []
    results = []
    for i in range(64):
        strata = ["coverage"]
        if i < 2:
            strata.append("team_alias_ari")
        if i < 8:
            strata.append("source_name_variant")
        team = "ARI" if i < 2 else f"T{i:02d}"
        candidate_team = alias_team_abbr if i == 0 else ("ARI" if i == 1 else team)
        target = {"team": team, "visible_name": f"Player {i}", "profile_path": f"/{i}", "_strata": strata}
        targets.append(target)
        results.append({
            "target_row_identity": [team, f"Player {i}", f"/{i}"],
            "target_team": team,
            "resolved": True,
            "selected_gsis_id": f"00-{i:07d}",
            "selected_candidate": {"gsisId": f"00-{i:07d}", "teamAbbr": candidate_team},
            "selected_candidate_gsis_valid": True,
            "jersey_comparable": True,
            "jersey_agrees": True,
            "query_attempts": [{"http_status": 200, "parseable_players_array": True, "player_count": 1}],
            "tiebreak_applied": False,
            "tiebreak_succeeded": False,
        })
    for i in range(2, 4):
        target = {"team": "ARI", "visible_name": f"Alias {i}", "profile_path": f"/a{i}", "_strata": ["team_alias_ari"]}
        targets.append(target)
        results.append({
            "target_row_identity": ["ARI", f"Alias {i}", f"/a{i}"],
            "target_team": "ARI",
            "resolved": True,
            "selected_gsis_id": f"00-{100+i:07d}",
            "selected_candidate": {"gsisId": f"00-{100+i:07d}", "teamAbbr": "ARI"},
            "selected_candidate_gsis_valid": True,
            "jersey_comparable": False,
            "jersey_agrees": None,
            "query_attempts": [{"http_status": 200, "parseable_players_array": True, "player_count": 1}],
            "tiebreak_applied": False,
            "tiebreak_succeeded": False,
        })
    for i in range(8, 16):
        target = {"team": f"V{i}", "visible_name": f"Variant {i}", "profile_path": f"/v{i}", "_strata": ["source_name_variant"]}
        targets.append(target)
        results.append({
            "target_row_identity": [f"V{i}", f"Variant {i}", f"/v{i}"],
            "target_team": f"V{i}",
            "resolved": True,
            "selected_gsis_id": f"00-{200+i:07d}",
            "selected_candidate": {"gsisId": f"00-{200+i:07d}", "teamAbbr": f"V{i}"},
            "selected_candidate_gsis_valid": True,
            "jersey_comparable": False,
            "jersey_agrees": None,
            "query_attempts": [{"http_status": 200, "parseable_players_array": True, "player_count": 1}],
            "tiebreak_applied": False,
            "tiebreak_succeeded": False,
        })
    return targets, results


def test_addendum_is_preexecution_and_narrow():
    a = load_and_validate_addendum(ADDENDUM)
    assert a["supersedes_only"] == "conditional ARI<->AZ alias-capability qualification criterion"
    assert a["empirical_boundary"]["correction_uses_no_v4_empirical_response"] is True
    assert a["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert a["governance"]["postgame_participation_used"] is False
    assert a["governance"]["f_st_01_frozen_2026_unchanged"] is True


def test_alias_capability_stays_false_when_equivalence_is_not_exercised():
    targets, results = _synthetic("ARI")
    metrics, gates, passed, conditional = strict_evaluate_gates(targets, results, _contract(), True, 1)
    assert passed is True
    assert all(gates.values())
    assert metrics["team_alias_ari_unique_resolution_count"] == 4
    assert metrics["ari_az_alias_exercised_count"] == 0
    assert conditional["ari_az_team_alias_qualified"] is False


def test_alias_capability_can_turn_true_only_after_actual_az_selection():
    targets, results = _synthetic("AZ")
    metrics, gates, passed, conditional = strict_evaluate_gates(targets, results, _contract(), True, 1)
    assert passed is True
    assert all(gates.values())
    assert metrics["team_alias_ari_unique_resolution_count"] == 4
    assert metrics["ari_az_alias_exercised_count"] == 1
    assert conditional["ari_az_team_alias_qualified"] is True


def test_correction_does_not_expand_downstream_authority():
    a = _contract()["authority_if_and_only_if_all_v4_gates_pass"]
    for key in (
        "general_2026_player_identity_to_gsis_qualified",
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
        "game_day_membership_qualified",
        "availability_state_authorized",
        "player_value_join_authorized",
        "forecast_probability_effect_authorized",
        "model_fit_authorized",
        "production_authorized",
    ):
        assert a[key] is False

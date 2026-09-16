from __future__ import annotations

import json
from pathlib import Path

from research.levline4_2026_ngs_player_id_browser_heldout_v3 import (
    evaluate_gates,
    matches_player_search_response,
    normalize_name,
    parse_players_body,
    resolve_target,
)

V3_CONTRACT = Path("research/levline4_2026_ngs_player_id_browser_heldout_v3_contract.json")
V2_CONTRACT = Path("research/levline4_2026_ngs_player_id_heldout_v2_contract.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_freezes_transport_only_change_from_v2():
    v3 = load(V3_CONTRACT)
    v2 = load(V2_CONTRACT)
    assert v3["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V3"
    assert v3["preregistration_state"]["v2_transport_failure_may_inform_v3_transport_only"] is True
    assert v3["preregistration_state"]["v2_semantic_candidate_data_observed_for_v3_targets"] is False
    assert v3["target_selection"]["reuse_exact_v2_70_target_population"] is True

    for key in (
        "v1_sentinel_visible_name_exclusions",
        "eligibility",
        "name_normalization",
        "selection_key",
        "coverage_stratum",
        "source_name_ambiguity_stratum",
        "union_rule",
        "expected_overlap_count",
        "expected_total_target_count",
    ):
        assert v3["target_selection"][key] == v2["target_selection"][key]

    for key in (
        "coverage_stratum_unique_resolution_minimum_count",
        "coverage_stratum_unique_resolution_minimum_fraction",
        "source_name_ambiguity_stratum_unique_resolution_required_count",
        "source_name_ambiguity_stratum_unique_resolution_required_fraction",
        "invalid_selected_gsis_count_allowed",
        "duplicate_selected_gsis_across_distinct_target_rows_allowed",
        "same_target_multiple_name_plus_team_candidate_count_allowed",
        "resolved_coverage_jersey_comparable_minimum_fraction",
        "resolved_coverage_jersey_agreement_minimum_fraction",
        "threshold_relaxation_after_first_result_allowed",
        "manual_unresolved_repair_before_gate_allowed",
    ):
        assert v3["frozen_pass_gates"][key] == v2["frozen_pass_gates"][key]

    assert v3["browser_transport"]["manual_headers_or_credentials_allowed"] is False
    assert v3["browser_transport"]["direct_http_fallback_allowed"] is False
    assert v3["browser_transport"]["explicit_retry_allowed"] is False
    assert v3["browser_transport"]["browser_storage_state_must_not_be_persisted"] is True
    assert v3["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert v3["governance"]["postgame_participation_used"] is False
    assert v3["governance"]["week2_inactive_execution_evidence_used_for_design"] is False
    assert v3["governance"]["f_st_01_frozen_2026_unchanged"] is True


def test_name_normalization_preserves_frozen_v2_order():
    assert normalize_name("  De'Vonta—Smith Jr. ") == "de vontasmith jr"
    assert normalize_name("A.J. Brown") == "a j brown"


def test_response_match_requires_exact_public_ngs_search_response():
    assert matches_player_search_response(
        "https://api.ngs.nfl.com/league/player/search?term=Patrick+Mahomes",
        "Patrick Mahomes",
    )
    assert matches_player_search_response(
        "https://api.ngs.nfl.com/league/player/search?term=Patrick%20Mahomes",
        "Patrick Mahomes",
    )
    assert not matches_player_search_response(
        "https://api.ngs.nfl.com/league/player/search?term=Patrick+Mahomes",
        "Patrick Mahomes II",
    )
    assert not matches_player_search_response(
        "https://example.com/league/player/search?term=Patrick+Mahomes",
        "Patrick Mahomes",
    )


def test_parse_players_body_fail_closed():
    parsed, ok, error = parse_players_body(200, b'{"players":[{"displayName":"X"}]}')
    assert ok is True and error is None and parsed["players"][0]["displayName"] == "X"

    _, ok, error = parse_players_body(401, b'{"message":"Unauthorized"}')
    assert ok is False and error == "http_status_401"

    _, ok, error = parse_players_body(200, b'{"players":"not-a-list"}')
    assert ok is False and error == "http_200_without_object_players_array"


def test_resolver_uses_only_exact_normalized_name_plus_exact_team_and_valid_gsis():
    target = {
        "visible_name": "Josh Allen",
        "team": "BUF",
        "jersey_number": "17",
    }
    payload = {
        "players": [
            {"displayName": "Josh Allen", "teamAbbr": "JAX", "gsisId": "00-0034857", "uniformNumber": 41},
            {"displayName": "Josh Allen", "teamAbbr": "BUF", "gsisId": "00-0034857", "uniformNumber": 17},
        ]
    }
    result = resolve_target(target, payload)
    assert result["resolved"] is True
    assert result["name_plus_team_match_count"] == 1
    assert result["selected_gsis_id"] == "00-0034857"
    assert result["jersey_comparable"] is True
    assert result["jersey_agrees"] is True

    bad = resolve_target(
        target,
        {"players": [{"displayName": "Josh Allen", "teamAbbr": "BUF", "gsisId": "bad"}]},
    )
    assert bad["resolved"] is False
    assert bad["selected_candidate_gsis_valid"] is False


def _synthetic_targets_and_results():
    targets = []
    results = []
    for idx in range(64):
        target = {
            "team": f"T{idx:02d}",
            "visible_name": f"Coverage Player {idx}",
            "profile_path": f"/coverage/{idx}",
            "_strata": ["coverage"],
        }
        targets.append(target)
        results.append(
            {
                "target_row_identity": [target["team"], target["visible_name"], target["profile_path"]],
                "http_status": 200,
                "parseable_players_array": True,
                "resolved": True,
                "unique_name_plus_team_candidate": True,
                "selected_candidate_gsis_valid": True,
                "name_plus_team_match_count": 1,
                "selected_gsis_id": f"00-{idx:07d}",
                "jersey_comparable": True,
                "jersey_agrees": True,
            }
        )
    for idx in range(6):
        target = {
            "team": f"A{idx:02d}",
            "visible_name": f"Ambiguous Player {idx // 2}",
            "profile_path": f"/ambiguity/{idx}",
            "_strata": ["source_name_ambiguity"],
        }
        targets.append(target)
        results.append(
            {
                "target_row_identity": [target["team"], target["visible_name"], target["profile_path"]],
                "http_status": 200,
                "parseable_players_array": True,
                "resolved": True,
                "unique_name_plus_team_candidate": True,
                "selected_candidate_gsis_valid": True,
                "name_plus_team_match_count": 1,
                "selected_gsis_id": f"00-{100+idx:07d}",
                "jersey_comparable": False,
                "jersey_agrees": None,
            }
        )
    return targets, results


def test_gate_logic_is_v2_thresholds_plus_browser_transport_gate():
    contract = load(V3_CONTRACT)
    targets, results = _synthetic_targets_and_results()
    metrics, gates, passed = evaluate_gates(
        targets, results, contract, page_loaded=True, query_input_count=1
    )
    assert passed is True
    assert all(gates.values())
    assert metrics["coverage_unique_resolution_count"] == 64
    assert metrics["source_name_ambiguity_unique_resolution_count"] == 6

    _, gates, passed = evaluate_gates(
        targets, results, contract, page_loaded=False, query_input_count=0
    )
    assert passed is False
    assert gates["page_loaded_and_unique_query_input"] is False


def test_authority_ceiling_remains_research_only_even_on_pass():
    contract = load(V3_CONTRACT)
    passed = contract["authority_if_and_only_if_all_v3_gates_pass"]
    assert passed["ngs_public_page_browser_context_transport_qualified_for_frozen_official_roster_v2_population"] is True
    assert passed["ngs_exact_display_name_plus_team_resolver_qualified_for_frozen_official_roster_v2_population"] is True
    assert passed["official_roster_to_ngs_gsis_candidate_bridge_qualified_for_separately_preregistered_heldout_application"] is True
    for key in (
        "ngs_endpoint_as_independent_or_stable_production_api_qualified",
        "ngs_is_independent_player_identity_ground_truth",
        "general_2026_player_identity_to_gsis_qualified",
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
        "game_day_membership_qualified",
        "availability_state_authorized",
        "player_value_join_authorized",
        "forecast_probability_effect_authorized",
        "model_fit_authorized",
        "production_authorized",
    ):
        assert passed[key] is False, key

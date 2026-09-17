from __future__ import annotations

import json
from pathlib import Path

from research import levline4_2026_ngs_player_id_browser_heldout_v7 as v7
from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as frozen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research/levline4_2026_ngs_player_id_browser_heldout_v7_contract.json"


def load_contract():
    return json.loads(CONTRACT.read_text())


def test_contract_freezes_v7_governance_and_fresh_population():
    c = load_contract()
    assert c["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V7"
    assert c["schema_version"] == "levline4-2026-ngs-player-id-browser-heldout-v7-contract"
    g = c["governance"]
    assert g["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert g["postgame_participation_used"] is False
    assert g["week2_inactive_execution_evidence_used_for_design"] is False
    assert g["f_st_01_frozen_2026_unchanged"] is True
    assert g["production_paths_may_change"] is False
    assert g["first_result_is_canonical_whether_pass_or_fail"] is True
    assert g["same_version_rule_adaptation_after_first_result"] is False
    p = c["preregistration_state"]
    assert p["contract_must_precede_v7_implementation_tests_and_workflow"] is True
    assert p["no_v7_target_ngs_responses_observed_before_contract_freeze"] is True
    assert p["v3_v5_v6_target_rows_may_not_be_used_for_v7_validation"] is True
    assert p["v6_may_inform_v7_rule_design_only"] is True
    assert p["v7_new_rule_is_limited_to_source_native_canonical_data_name"] is True
    assert p["fuzzy_or_phonetic_matching_allowed"] is False
    assert p["manual_alias_dictionary_allowed"] is False


def test_v7_population_and_thresholds_are_hash_locked():
    c = load_contract()
    t = c["target_selection"]
    assert t["expected_eligible_row_count"] == 2237
    assert t["expected_total_target_count"] == 103
    assert t["coverage_stratum"]["expected_target_count"] == 64
    assert t["team_alias_ari_stratum"]["expected_target_count"] == 4
    assert t["source_name_variant_stratum"]["expected_target_count"] == 16
    assert t["canonical_name_variant_stratum"]["expected_target_count"] == 32
    assert t["canonical_name_variant_stratum"]["expected_eligible_count"] == 317
    assert t["expected_sorted_row_identity_sha256"] == "8a6b4bd7f6f84f292a20f20ce378f69de74ea98ae34deeb09ad192bc64911d7c"
    assert t["expected_target_projection_sha256"] == "08170a782af614e79da43eaa201fc6898889b2001907adec72b6f259c2b7ef85"
    assert t["selection_salt"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V7"
    gates = c["frozen_pass_gates"]
    assert gates["coverage_stratum_unique_resolution_minimum_count"] == 61
    assert gates["coverage_stratum_unique_resolution_minimum_fraction"] == 0.953125
    assert gates["canonical_name_variant_stratum_unique_resolution_minimum_count"] == 30
    assert gates["canonical_name_variant_stratum_unique_resolution_minimum_fraction"] == 0.9375
    assert gates["source_name_variant_stratum_unique_resolution_minimum_count"] == 15
    assert gates["team_alias_ari_stratum_unique_resolution_required_count"] == 4
    assert gates["independent_resolved_coverage_jersey_agreement_minimum_fraction"] == 0.95
    assert gates["independent_resolved_coverage_jersey_comparable_minimum_fraction"] == 0.8
    assert gates["threshold_relaxation_after_first_result_allowed"] is False


def test_source_canonical_parser_is_deterministic_and_source_only():
    assert v7.canonical_query_name("uche,joshua") == "joshua uche"
    assert v7.canonical_query_name("Brown, Marquise") == "Marquise Brown"
    assert v7.canonical_query_name("murray,,kenneth jr.") == "kenneth murray jr."
    assert v7.canonical_query_name("Smith, John III") == "John Smith III"
    assert v7.canonical_query_name("singlecomponent") is None
    assert v7.canonical_query_name("a,b,c") is None
    assert v7.canonical_query_name("") is None


def test_v7_query_order_is_exact_suffix_canonical_then_surname():
    target = {
        "visible_name": "Josh Uche",
        "canonical_data_name": "uche,joshua",
    }
    assert v7.query_plan(target) == [
        ("exact_visible_name", "Josh Uche"),
        ("source_canonical_name", "joshua uche"),
        ("surname_only", "Uche"),
    ]
    suffix_target = {
        "visible_name": "John Smith Jr.",
        "canonical_data_name": "smith,john jr.",
    }
    assert v7.query_plan(suffix_target) == [
        ("exact_visible_name", "John Smith Jr."),
        ("terminal_suffix_stripped", "John Smith"),
        ("surname_only", "Smith"),
    ]


def test_v7_resolves_source_canonical_name_without_fuzzy_matching():
    target = {
        "visible_name": "Josh Uche",
        "canonical_data_name": "uche,joshua",
        "team": "MIA",
        "position": "LB",
        "jersey_number": "53",
    }
    payload = {"players": [
        {
            "displayName": "Joshua Uche",
            "teamAbbr": "MIA",
            "position": "LB",
            "uniformNumber": "53",
            "gsisId": "00-0000001",
        }
    ]}
    out = v7.resolve_target(target, payload)
    assert out["resolved"] is True
    assert out["selected_gsis_id"] == "00-0000001"
    assert out["selected_name_representation"] == "source_canonical"
    assert out["jersey_agrees"] is True

    wrong_name = {"players": [
        {
            "displayName": "Josh Uchee",
            "teamAbbr": "MIA",
            "position": "LB",
            "uniformNumber": "53",
            "gsisId": "00-0000002",
        }
    ]}
    miss = v7.resolve_target(target, wrong_name)
    assert miss["resolved"] is False
    assert miss["primary_candidate_count"] == 0


def test_v7_preserves_frozen_team_alias_and_multiple_candidate_tiebreak():
    assert frozen.team_matches("ARI", "AZ") is True
    target = {
        "visible_name": "John Smith",
        "canonical_data_name": "smith,john",
        "team": "ARI",
        "position": "WR",
        "jersey_number": "11",
    }
    payload = {"players": [
        {
            "displayName": "John Smith",
            "teamAbbr": "AZ",
            "position": "WR",
            "uniformNumber": "12",
            "gsisId": "00-0000001",
        },
        {
            "displayName": "John Smith",
            "teamAbbr": "AZ",
            "position": "WR",
            "uniformNumber": "11",
            "gsisId": "00-0000002",
        },
    ]}
    out = v7.resolve_target(target, payload)
    assert out["primary_candidate_count"] == 2
    assert out["tiebreak_applied"] is True
    assert out["tiebreak_succeeded"] is True
    assert out["selected_gsis_id"] == "00-0000002"


def test_v7_authority_ceiling_remains_research_only_even_on_pass():
    passed = load_contract()["authority_if_and_only_if_all_v7_gates_pass"]
    for key in (
        "availability_state_authorized",
        "forecast_probability_effect_authorized",
        "game_day_membership_qualified",
        "general_2026_player_identity_to_gsis_qualified",
        "model_fit_authorized",
        "ngs_endpoint_as_independent_or_stable_production_api_qualified",
        "ngs_is_independent_player_identity_ground_truth",
        "player_value_join_authorized",
        "production_authorized",
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
    ):
        assert passed[key] is False

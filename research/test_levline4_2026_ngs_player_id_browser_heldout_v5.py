from __future__ import annotations

import json
from pathlib import Path

from research.levline4_2026_ngs_player_id_browser_heldout_v5 import (
    evaluate_gates,
    name_key,
    query_plan,
    resolve_target,
    team_matches,
)

CONTRACT = Path("research/levline4_2026_ngs_player_id_browser_heldout_v5_contract.json")


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text())


def test_contract_freezes_preexecution_v4_withdrawal_and_governance():
    c = load_contract()
    assert c["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V5"
    assert c["preregistration_state"]["v4_was_withdrawn_before_empirical_execution"] is True
    assert c["preregistration_state"]["v5_reuses_exact_unobserved_v4_source_only_target_population"] is True
    assert c["frozen_upstream_evidence"]["abandoned_v4_preexecution"]["empirical_ngs_requests_observed"] == 0
    assert c["target_selection"]["expected_total_target_count"] == 74
    assert c["target_selection"]["expected_sorted_row_identity_sha256"] == "de8fefedbbd30d954836e8e33c46a2d4358d5efdb558be1e1fc08939ee36c3ad"
    assert c["target_selection"]["expected_target_projection_sha256"] == "df236d681b89fee79e1138b27334ff78792f46a1a90ff8280b27f8028fb2ad2a"
    assert c["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert c["governance"]["postgame_participation_used"] is False
    assert c["governance"]["week2_inactive_execution_evidence_used_for_design"] is False
    assert c["governance"]["f_st_01_frozen_2026_unchanged"] is True


def test_browser_context_is_explicitly_identical_to_successful_v3_context():
    b = load_contract()["browser_transport"]
    assert b["engine"] == "playwright chromium headless"
    assert b["context_locale"] == "en-US"
    assert b["context_user_agent"] == "LevLine-Research/1.0 (+https://github.com/levine26/nfl-forecast-model)"
    assert b["page_load_wait_until"] == "domcontentloaded"
    assert b["page_load_timeout_ms"] == 60000
    assert b["post_load_settle_ms"] == 1500
    assert b["response_timeout_ms"] == 15000
    assert b["manual_headers_or_credentials_allowed"] is False
    assert b["direct_http_fallback_allowed"] is False
    assert b["explicit_retry_allowed"] is False


def test_name_key_query_cascade_and_team_equivalence_are_narrow():
    assert name_key("J.J. Jansen") == name_key("JJ Jansen") == "jj jansen"
    assert name_key("John Ridgeway III") == name_key("John Ridgeway") == "john ridgeway"
    assert name_key("A.J. Brown") == "aj brown"
    assert query_plan("John Ridgeway III") == [
        ("exact_visible_name", "John Ridgeway III"),
        ("terminal_suffix_stripped", "John Ridgeway"),
        ("surname_only", "Ridgeway"),
    ]
    assert query_plan("T.J. Edwards") == [
        ("exact_visible_name", "T.J. Edwards"),
        ("surname_only", "Edwards"),
    ]
    assert team_matches("ARI", "ARI")
    assert team_matches("ARI", "AZ")
    assert not team_matches("ARI", "SF")
    assert team_matches("JAX", "JAX")
    assert not team_matches("JAX", "JAC")


def test_position_jersey_tiebreak_resolves_unique_joint_match_and_fails_closed():
    target = {"visible_name": "Tre Watson", "team": "MIA", "position": "TE", "jersey_number": "87"}
    payload = {"players": [
        {"displayName": "Tre Watson", "teamAbbr": "MIA", "position": "LB", "positionGroup": "LB", "jerseyNumber": 44, "gsisId": "00-0035349", "status": "CUT"},
        {"displayName": "Tre Watson", "teamAbbr": "MIA", "position": "TE", "positionGroup": "TE", "uniformNumber": "87", "gsisId": "00-0040094", "status": "DEV"},
    ]}
    result = resolve_target(target, payload)
    assert result["primary_candidate_count"] == 2
    assert result["tiebreak_applied"] is True
    assert result["tiebreak_succeeded"] is True
    assert result["selected_gsis_id"] == "00-0040094"

    mismatch = {"visible_name": "Brandon Johnson", "team": "PIT", "position": "WR", "jersey_number": "89"}
    payload = {"players": [
        {"displayName": "Brandon Johnson", "teamAbbr": "PIT", "position": "WR", "positionGroup": "WR", "uniformNumber": "82", "gsisId": "00-0037382"},
        {"displayName": "Brandon Johnson", "teamAbbr": "PIT", "position": "LB", "positionGroup": "LB", "jerseyNumber": 91, "gsisId": "00-0024356"},
    ]}
    result = resolve_target(mismatch, payload)
    assert result["tiebreak_applied"] is True
    assert result["tiebreak_succeeded"] is False
    assert result["resolved"] is False
    assert result["selected_gsis_id"] is None


def _synthetic_success():
    targets = []
    results = []
    for i in range(64):
        strata = ["coverage"]
        if i < 2:
            strata.append("team_alias_ari")
        if i < 8:
            strata.append("source_name_variant")
        team = "ARI" if i < 2 else f"T{i:02d}"
        target = {"team": team, "visible_name": f"Player {i}", "profile_path": f"/{i}", "_strata": strata}
        targets.append(target)
        selected_team = "AZ" if i == 0 else team
        results.append({
            "target_row_identity": [team, f"Player {i}", f"/{i}"],
            "resolved": True,
            "selected_gsis_id": f"00-{i:07d}",
            "selected_candidate": {"gsisId": f"00-{i:07d}", "teamAbbr": selected_team},
            "selected_candidate_gsis_valid": True,
            "jersey_comparable": True,
            "jersey_agrees": True,
            "query_attempts": [{"http_status": 200, "parseable_players_array": True, "player_count": 1}],
            "tiebreak_applied": i == 10,
            "tiebreak_succeeded": i == 10,
        })
    for i in range(2, 4):
        target = {"team": "ARI", "visible_name": f"Alias {i}", "profile_path": f"/a{i}", "_strata": ["team_alias_ari"]}
        targets.append(target)
        results.append({
            "target_row_identity": ["ARI", f"Alias {i}", f"/a{i}"],
            "resolved": True,
            "selected_gsis_id": f"00-{100+i:07d}",
            "selected_candidate": {"gsisId": f"00-{100+i:07d}", "teamAbbr": "AZ"},
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
        attempts = (
            [{"http_status": 200, "parseable_players_array": True, "player_count": 0},
             {"http_status": 200, "parseable_players_array": True, "player_count": 1}]
            if i == 8 else
            [{"http_status": 200, "parseable_players_array": True, "player_count": 1}]
        )
        results.append({
            "target_row_identity": [f"V{i}", f"Variant {i}", f"/v{i}"],
            "resolved": True,
            "selected_gsis_id": f"00-{200+i:07d}",
            "selected_candidate": {"gsisId": f"00-{200+i:07d}", "teamAbbr": f"V{i}"},
            "selected_candidate_gsis_valid": True,
            "jersey_comparable": False,
            "jersey_agrees": None,
            "query_attempts": attempts,
            "tiebreak_applied": False,
            "tiebreak_succeeded": False,
        })
    return targets, results


def test_gate_logic_excludes_tiebreak_rows_from_jersey_corroboration():
    targets, results = _synthetic_success()
    metrics, gates, passed, conditional = evaluate_gates(targets, results, load_contract(), True, 1)
    assert passed is True
    assert all(gates.values())
    assert metrics["coverage_unique_resolution_count"] == 64
    assert metrics["team_alias_ari_unique_resolution_count"] == 4
    assert metrics["source_name_variant_unique_resolution_count"] == 16
    assert metrics["independent_resolved_coverage_count"] == 63
    assert metrics["independent_resolved_coverage_jersey_comparable_count"] == 63
    assert metrics["team_alias_ari_selected_ngs_az_count"] >= 1
    assert conditional["ari_az_team_alias_qualified"] is True
    assert conditional["query_fallback_semantics_qualified"] is True
    assert conditional["multiple_candidate_tiebreak_qualified"] is True


def test_authority_ceiling_remains_research_only_even_on_pass():
    authority = load_contract()["authority_if_and_only_if_all_v5_gates_pass"]
    assert authority["ngs_repaired_name_team_resolver_qualified_for_frozen_v5_population"] is True
    assert authority["official_roster_to_ngs_gsis_candidate_bridge_qualified_for_separately_preregistered_heldout_application"] is True
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
        assert authority[key] is False

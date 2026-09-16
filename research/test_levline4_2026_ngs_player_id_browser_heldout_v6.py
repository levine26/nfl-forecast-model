from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from research import levline4_2026_ngs_player_id_browser_heldout_v6 as v6
from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as frozen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "research/levline4_2026_ngs_player_id_browser_heldout_v6_contract.json"
BASE = ROOT / "research/levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base.py"
V5_GIT_BLOB = "e21938b45180b5ed1db0ebb48aa3f8dc784bec33"


def load_contract():
    return json.loads(CONTRACT.read_text())


def test_frozen_base_is_byte_identical_v5_implementation_blob():
    observed = subprocess.check_output(["git", "hash-object", str(BASE)], text=True).strip()
    assert observed == V5_GIT_BLOB


def test_contract_freezes_governance_and_no_post_v5_adaptation():
    c = load_contract()
    assert c["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V6"
    assert c["schema_version"] == "levline4-2026-ngs-player-id-browser-heldout-v6-contract"
    g = c["governance"]
    assert g["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert g["postgame_participation_used"] is False
    assert g["week2_inactive_execution_evidence_used_for_design"] is False
    assert g["f_st_01_frozen_2026_unchanged"] is True
    assert g["production_paths_may_change"] is False
    p = c["preregistration_state"]
    assert p["v5_outcome_metrics_used_for_rule_or_threshold_design"] is False
    assert p["v5_target_rows_used_only_for_empirical_exposure_exclusion"] is True
    assert p["v5_target_rows_may_not_be_used_for_v6_validation"] is True
    assert p["v6_uses_frozen_v5_resolver_semantics_and_pass_gates_without_adaptation"] is True


def test_fresh_population_is_hash_locked_before_execution():
    t = load_contract()["target_selection"]
    assert t["expected_eligible_row_count"] == 2315
    assert t["expected_total_target_count"] == 78
    assert t["coverage_stratum"]["expected_target_count"] == 64
    assert t["team_alias_ari_stratum"]["expected_target_count"] == 4
    assert t["source_name_variant_stratum"]["expected_target_count"] == 16
    assert t["source_name_variant_stratum"]["expected_eligible_count"] == 199
    assert t["expected_overlap_counts"] == {
        "all_three": 0,
        "coverage_and_source_name_variant": 4,
        "coverage_and_team_alias_ari": 2,
        "team_alias_ari_and_source_name_variant": 0,
    }
    assert t["expected_sorted_row_identity_sha256"] == "ca06c3eadf135223bfe9695b255906f3b42f42263aacc7262119ec84b041df35"
    assert t["expected_target_projection_sha256"] == "fac150229b3426fee077ab82a1ef3dcf3ce010dbb1b39ddfac23bbf00a421b2e"
    assert t["selection_salt"] == "LEVLINE-4-2026-NGS-PLAYER-ID-BROWSER-HELDOUT-V6"


def test_frozen_rules_and_gates_are_not_relaxed():
    c = load_contract()
    gates = c["frozen_pass_gates"]
    assert gates["coverage_stratum_unique_resolution_minimum_count"] == 61
    assert gates["coverage_stratum_unique_resolution_minimum_fraction"] == 0.953125
    assert gates["source_name_variant_stratum_unique_resolution_minimum_count"] == 15
    assert gates["source_name_variant_stratum_unique_resolution_minimum_fraction"] == 0.9375
    assert gates["team_alias_ari_stratum_unique_resolution_required_count"] == 4
    assert gates["team_alias_ari_stratum_unique_resolution_required_fraction"] == 1.0
    assert gates["independent_resolved_coverage_jersey_agreement_minimum_fraction"] == 0.95
    assert gates["independent_resolved_coverage_jersey_comparable_minimum_fraction"] == 0.8
    assert gates["invalid_selected_gsis_count_allowed"] == 0
    assert gates["duplicate_selected_gsis_across_distinct_target_rows_allowed"] == 0
    assert gates["threshold_relaxation_after_first_result_allowed"] is False
    rule = c["fixed_resolution_rule"]
    assert rule["team_equivalence"] == {"ARI": ["ARI", "AZ"], "all_other_official_teams": "exact uppercase equality only"}
    assert rule["manual_resolution_allowed"] is False
    assert rule["fallback_matching_allowed_beyond_frozen_rules"] is False
    assert "status" in rule["fields_forbidden_from_selection"]


def test_frozen_semantics_cover_alias_initialism_fallback_and_tiebreak():
    assert frozen.name_key("A. J. Brown Jr.") == "aj brown"
    assert frozen.query_plan("John Smith Jr.") == [
        ("exact_visible_name", "John Smith Jr."),
        ("terminal_suffix_stripped", "John Smith"),
        ("surname_only", "Smith"),
    ]
    assert frozen.team_matches("ARI", "AZ") is True
    assert frozen.team_matches("ARI", "ARI") is True
    assert frozen.team_matches("ATL", "AZ") is False
    target = {"visible_name": "John Smith", "team": "ARI", "position": "WR", "jersey_number": "11"}
    payload = {"players": [
        {"displayName": "John Smith", "teamAbbr": "AZ", "position": "WR", "uniformNumber": "12", "gsisId": "00-0000001"},
        {"displayName": "John Smith", "teamAbbr": "AZ", "position": "WR", "uniformNumber": "11", "gsisId": "00-0000002"},
    ]}
    out = frozen.resolve_target(target, payload)
    assert out["primary_candidate_count"] == 2
    assert out["tiebreak_applied"] is True
    assert out["tiebreak_succeeded"] is True
    assert out["selected_gsis_id"] == "00-0000002"


def test_v6_combines_v3_and_v5_only_as_exclusions(monkeypatch):
    v3 = {"targets": [{"team": "A", "visible_name": "One", "profile_path": "/1"}] * 70}
    v5 = {"targets": [{"team": "B", "visible_name": "Two", "profile_path": "/2"}] * 74}
    # Use unique identities while keeping the frozen count assertions.
    v3["targets"] = [{"team": "A", "visible_name": f"One{i}", "profile_path": f"/1/{i}"} for i in range(70)]
    v5["targets"] = [{"team": "B", "visible_name": f"Two{i}", "profile_path": f"/2/{i}"} for i in range(74)]
    captured = {}

    def fake_select(rows, contract, combined):
        captured["combined"] = combined
        return [], {"ok": True}

    monkeypatch.setattr(frozen, "select_targets", fake_select)
    targets, diag = v6.select_targets([], {}, v3, v5)
    assert targets == []
    assert diag == {"ok": True}
    assert len(captured["combined"]["targets"]) == 144


def test_v6_authority_ceiling_remains_research_only():
    c = load_contract()
    passed = c["authority_if_and_only_if_all_v6_gates_pass"]
    for key in (
        "availability_state_authorized",
        "forecast_probability_effect_authorized",
        "general_2026_player_identity_to_gsis_qualified",
        "model_fit_authorized",
        "player_value_join_authorized",
        "production_authorized",
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
    ):
        assert passed[key] is False

import io
import json
import socket
import urllib.error
from pathlib import Path

from research.levline4_2026_ngs_player_id_heldout_v2 import (
    GSIS_RE,
    normalize_name,
    request_json,
    resolve_target,
    selection_key,
)


CONTRACT = Path("research/levline4_2026_ngs_player_id_heldout_v2_contract.json")


def test_name_normalization_is_frozen_ascii_nfkd_and_token_preserving():
    assert normalize_name("  De'Vonta—Smith Jr. ") == "de vonta smith jr"
    assert normalize_name("José Núñez") == "jose nunez"
    assert normalize_name("A.J. Brown") == "a j brown"


def test_selection_key_is_deterministic_and_sensitive_to_frozen_fields():
    row = {
        "team": "PHI",
        "visible_name": "Example Player",
        "position": "WR",
        "jersey_number": "6",
        "profile_path": "/team/players-roster/example-player/",
    }
    first = selection_key(row)
    second = selection_key(dict(row))
    changed = selection_key({**row, "jersey_number": "7"})
    assert first == second
    assert first != changed
    assert len(first) == 64


def test_resolver_uses_only_exact_normalized_name_plus_exact_team():
    target = {"visible_name": "Josh Allen", "team": "BUF", "jersey_number": "17"}
    response = {
        "players": [
            {"displayName": "Josh Allen", "teamAbbr": "ARI", "position": "C", "gsisId": "00-0030833", "uniformNumber": None, "status": "CUT"},
            {"displayName": "Josh Allen", "teamAbbr": "BUF", "position": "QB", "gsisId": "00-0034857", "uniformNumber": "17", "status": "ACT"},
        ]
    }
    out = resolve_target(target, response)
    assert out["name_plus_team_match_count"] == 1
    assert out["resolved"] is True
    assert out["selected_gsis_id"] == "00-0034857"
    assert out["jersey_comparable"] is True
    assert out["jersey_agrees"] is True


def test_resolver_fails_closed_on_multiple_matching_candidates():
    target = {"visible_name": "Same Name", "team": "KC", "jersey_number": "1"}
    response = {
        "players": [
            {"displayName": "Same Name", "teamAbbr": "KC", "gsisId": "00-0000001"},
            {"displayName": "Same Name", "teamAbbr": "KC", "gsisId": "00-0000002"},
        ]
    }
    out = resolve_target(target, response)
    assert out["name_plus_team_match_count"] == 2
    assert out["unique_name_plus_team_candidate"] is False
    assert out["resolved"] is False
    assert out["selected_gsis_id"] is None


def test_resolver_fails_closed_on_invalid_gsis():
    target = {"visible_name": "Example Player", "team": "LAR", "jersey_number": "9"}
    response = {"players": [{"displayName": "Example Player", "teamAbbr": "LAR", "gsisId": "", "uniformNumber": "9"}]}
    out = resolve_target(target, response)
    assert out["unique_name_plus_team_candidate"] is True
    assert out["selected_candidate_gsis_valid"] is False
    assert out["resolved"] is False
    assert out["selected_gsis_id"] is None


def test_non_timeout_urlerror_is_not_retried():
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        raise urllib.error.URLError("dns failure")

    out = request_json("https://example.test", urlopen=opener, sleep=lambda _: None)
    assert len(calls) == 1
    assert len(out["attempts"]) == 1
    assert out["semantic_error"] == "transport_nonretryable"


def test_timeout_is_retried_at_most_two_additional_times():
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        raise socket.timeout("timed out")

    out = request_json("https://example.test", urlopen=opener, sleep=lambda _: None)
    assert len(calls) == 3
    assert len(out["attempts"]) == 3
    assert out["semantic_error"] == "transport_timeout_exhausted"


def test_http_404_is_not_retried():
    calls = []

    def opener(request, timeout=None):
        calls.append(1)
        raise urllib.error.HTTPError(
            request.full_url,
            404,
            "not found",
            hdrs={},
            fp=io.BytesIO(b'{"players":[]}'),
        )

    out = request_json("https://example.test", urlopen=opener, sleep=lambda _: None)
    assert len(calls) == 1
    assert out["http_status"] == 404
    assert len(out["attempts"]) == 1


def test_gsis_pattern_is_exact():
    assert GSIS_RE.fullmatch("00-0034857")
    assert not GSIS_RE.fullmatch("00-034857")
    assert not GSIS_RE.fullmatch("10-0034857")
    assert not GSIS_RE.fullmatch("00-00348570")


def test_contract_freezes_targets_gates_and_scoped_authority_only():
    contract = json.loads(CONTRACT.read_text())
    assert contract["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-HELDOUT-V2"
    assert contract["target_selection"]["coverage_stratum"]["expected_target_count"] == 64
    assert contract["target_selection"]["source_name_ambiguity_stratum"]["expected_duplicate_name_group_count"] == 3
    assert contract["target_selection"]["source_name_ambiguity_stratum"]["expected_target_count"] == 6
    assert contract["target_selection"]["expected_total_target_count"] == 70
    assert contract["frozen_pass_gates"]["coverage_stratum_unique_resolution_minimum_count"] == 61
    assert contract["frozen_pass_gates"]["coverage_stratum_unique_resolution_minimum_fraction"] == 0.953125
    assert contract["frozen_pass_gates"]["source_name_ambiguity_stratum_unique_resolution_required_count"] == 6
    assert contract["fixed_query_and_resolution_rule"]["fallback_matching_allowed"] is False
    assert contract["fixed_query_and_resolution_rule"]["manual_resolution_allowed"] is False
    assert "network timeout" in contract["fixed_query_and_resolution_rule"]["request"]["transport_retry_policy"]
    authority = contract["authority_if_and_only_if_all_v2_gates_pass"]
    assert authority["ngs_exact_display_name_plus_team_resolver_qualified_for_frozen_official_roster_v2_population"] is True
    assert authority["official_roster_to_ngs_gsis_candidate_bridge_qualified_for_separately_preregistered_heldout_application"] is True
    for key in (
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
        assert authority[key] is False, key
    assert contract["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert contract["governance"]["postgame_participation_used"] is False
    assert contract["governance"]["week2_inactive_execution_evidence_used_for_design"] is False

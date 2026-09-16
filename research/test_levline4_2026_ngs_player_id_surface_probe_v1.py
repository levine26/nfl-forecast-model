from research.levline4_2026_ngs_player_id_surface_probe_v1 import (
    extract_gsis_values,
    is_nfl_https_url,
    json_key_paths,
    load_contract,
)


def test_nfl_network_allowlist_is_https_and_suffix_bounded():
    assert is_nfl_https_url("https://ngs.nfl.com/player-id-lookup")
    assert is_nfl_https_url("https://api.ngs.nfl.com/v1/player")
    assert is_nfl_https_url("https://nfl.com/foo")
    assert not is_nfl_https_url("http://ngs.nfl.com/player-id-lookup")
    assert not is_nfl_https_url("https://nfl.com.evil.example/foo")
    assert not is_nfl_https_url("https://example.com/foo")


def test_gsis_pattern_is_exact_and_deduplicated():
    text = "x 00-0033873 y 00-0033873 z 00-0012345 bad 00-12345678 10-0033873"
    assert extract_gsis_values(text) == ["00-0012345", "00-0033873"]


def test_json_key_paths_records_structure_without_value_selection():
    obj = {"data": [{"player": {"gsisId": "00-0033873", "name": "Example"}}], "meta": {"ok": True}}
    paths = json_key_paths(obj)
    assert "data" in paths
    assert "data[]" in paths
    assert "data[].player" in paths
    assert "data[].player.gsisId" in paths
    assert "data[].player.name" in paths
    assert "meta.ok" in paths
    assert "00-0033873" not in paths


def test_contract_freezes_three_non_target_discovery_queries_and_zero_authority():
    contract = load_contract()
    assert contract["frozen_discovery_queries"] == ["Patrick Mahomes", "Josh Allen", "Justin Jefferson"]
    assert contract["source"]["backend_endpoint_known_before_v1"] is False
    assert contract["browser_capture"]["no_week2_inactive_names_may_be_added_to_v1"] is True
    assert contract["frozen_diagnostics"]["diagnostics_may_not_select_or_qualify_a_backend_endpoint"] is True
    assert contract["v1_disposition"]["same_version_rule_adaptation_after_live_probe"] is False
    for key, value in contract["authority"].items():
        if key == "ngs_surface_capture_may_qualify":
            assert value is True
        else:
            assert value is False, key
    assert contract["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert contract["governance"]["postgame_participation_used"] is False
    assert contract["governance"]["week2_inactive_execution_evidence_used_for_design"] is False

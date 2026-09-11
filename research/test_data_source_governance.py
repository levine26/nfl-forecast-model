from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("research/data_source_governance.json")
ADVANCED_REGISTRY = Path("research/advanced_player_source_governance.json")
AVAILABILITY_CONTRACT = Path("research/availability_source_audit_contract.json")
AVAILABILITY_2025_QUALIFICATION = Path("research/availability/2025_reconstruction_qualification_v1.json")
V09B_RESOLUTION = Path("research/availability/V09B_source_blocker_resolution_v1.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload() -> dict:
    return _load(REGISTRY)


def _advanced_payload() -> dict:
    return _load(ADVANCED_REGISTRY)


def test_every_source_has_explicit_family_rights_metadata_and_production_status() -> None:
    payload = _payload()
    assert payload["status"] == "research_governance"
    assert payload["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert payload["rights_qualification_blocker"] is False
    sources = payload["sources"]
    assert sources
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    for row in sources:
        assert row.get("family")
        assert row.get("provider")
        assert row.get("rights_status")
        assert row.get("rights_qualification_blocker") is False
        assert row.get("production_eligibility")


def test_no_new_feed_is_accidentally_production_authorized() -> None:
    payload = _payload()
    for row in payload["sources"]:
        if row["source_id"] == "nflverse_games":
            assert row["production_eligibility"] == "existing_use_only"
            continue
        assert row["production_eligibility"] != "authorized"
        assert not str(row["production_eligibility"]).startswith("production_authorized")
    decisions = payload["current_decisions"]
    assert decisions["production_market_source_change_authorized"] is False
    assert decisions["player_availability_probability_feature_authorized"] is False
    assert decisions["completed_2026_outcome_model_selection_allowed"] is False


def test_market_families_cannot_be_silently_conflated() -> None:
    payload = _payload()
    by_id = {row["source_id"]: row for row in payload["sources"]}
    assert by_id["the_odds_api_us_h2h"]["family"] == "sportsbook_aggregator"
    assert by_id["polymarket"]["family"] == "prediction_exchange"
    assert by_id["kalshi"]["family"] == "prediction_exchange"
    assert "Never mix" in payload["family_rules"]["prediction_exchanges"]
    assert "data_integrity_audit" in by_id["kalshi"]["production_eligibility"]
    assert "rights" not in by_id["kalshi"]["production_eligibility"]
    for source_id in ("sportsbook_fanduel", "sportsbook_draftkings", "sportsbook_betmgm"):
        assert by_id[source_id]["family"] == "sportsbook"
        assert "De-vig" in by_id[source_id]["combination_policy"]


def test_availability_and_advanced_player_sources_remain_firewalled_for_data_reasons() -> None:
    payload = _payload()
    sources = payload["sources"]
    availability = [row for row in sources if row["family"] == "availability"]
    advanced = [row for row in sources if row["family"] == "advanced_player_statistics"]
    assert availability
    assert advanced
    assert all(row["production_eligibility"] != "authorized" for row in availability + advanced)
    decisions = payload["current_decisions"]
    assert decisions["recommended_first_availability_audit"] == "cross_season_availability_harmonization_2022_2025"
    assert "2025 composite is technically qualified" in decisions["availability_scope_note"]
    assert "unified 2022-2025" in decisions["availability_scope_note"]
    assert decisions["availability_2025_source_qualified"] is True
    assert decisions["availability_2022_2025_unified_backtest_authorized"] is False
    assert decisions["v09b_execution_authorized"] is False
    assert decisions["pff_active_research_status"] == "excluded_by_zero_cost_policy"
    assert decisions["rights_qualification_blocker"] is False

    sleeper = next(row for row in availability if row["source_id"] == "sleeper_historical_player_archive_candidate")
    assert sleeper["technical_status"] == "verified_2026_only"
    assert sleeper["zero_cost_eligible"] is True
    assert "no 2025 reconstruction" in sleeper["coverage_note"]

    reconstructed = next(row for row in availability if row["source_id"] == "availability_2025_composite_reconstruction")
    assert reconstructed["technical_status"] == "verified_2025_only"
    assert reconstructed["zero_cost_eligible"] is True
    assert reconstructed["probability_feature_authorized"] is False
    assert reconstructed["supports_2022_2025_unified_backtest"] is False
    assert reconstructed["qualification_record"].endswith("2025_reconstruction_qualification_v1.json")


def test_advanced_source_registry_qualifies_on_integrity_and_never_authorizes_production() -> None:
    payload = _advanced_payload()
    assert payload["status"] == "research_governance"
    assert payload["production_authorized"] is False
    assert payload["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert payload["rights_qualification_blocker"] is False
    assert payload["zero_cost_active_research_only"] is True
    sources = payload["sources"]
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    assert all(row.get("provider") and row.get("family") for row in sources)
    assert all(row.get("rights_qualification_blocker") is False for row in sources)
    assert all(row.get("production_eligibility") == "not_authorized" for row in sources)
    assert all(row.get("documentation") for row in sources)
    by_id = {row["source_id"]: row for row in sources}
    assert "CC-BY-SA-4.0" in by_id["ftn_charting_via_nflverse"]["license_status"]
    assert by_id["ftn_charting_via_nflverse"]["technical_qualification_status"].startswith("qualified")
    assert by_id["sis_football_commercial"]["zero_cost_eligible"] is False
    assert by_id["sumersports_subscription_stats"]["technical_qualification_status"] == "blocked_by_missing_reproducible_data_interface"
    assert by_id["direct_nfl_ngs_tracking"]["technical_qualification_status"] == "unavailable_to_current_zero_cost_pipeline"
    assert "rights/licensing metadata never blocks" in payload["selection_policy"].lower()


def test_availability_source_contract_fails_closed_on_data_integrity_not_rights() -> None:
    payload = _load(AVAILABILITY_CONTRACT)
    assert payload["status"] == "research_governance"
    assert payload["contract_version"] == 3
    assert payload["target_horizon_minutes"] == 120
    assert payload["production_authorized"] is False
    assert payload["player_availability_probability_feature_authorized"] is False
    assert payload["completed_2026_outcome_model_selection_allowed"] is False
    assert payload["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert payload["rights_qualification_blocker"] is False
    assert payload["zero_cost_active_research_only"] is True
    tests = payload["qualification_tests"]
    assert "2025" in tests["target_season_coverage"]
    assert "2022-2025" in tests["cross_season_harmonization"]
    assert "fail closed" in tests["revision_semantics"].lower()
    assert "Actual snaps" in tests["no_realized_participation_proxy"]
    assert "rights_gate" not in tests
    outcomes = set(payload["fail_closed_outcomes"])
    assert any("multi-season historical availability model fitting" in outcome for outcome in outcomes)
    assert any("no availability probability feature" in outcome for outcome in outcomes)
    assert any("no retroactive execution" in outcome for outcome in outcomes)
    qualified = {row["source_id"]: row for row in payload["qualified_zero_cost_scopes"]}
    assert qualified["availability_2025_composite_reconstruction"]["supports_2022_2025_unified_backtest"] is False
    assert qualified["availability_2025_composite_reconstruction"]["probability_feature_authorized"] is False
    assert qualified["sleeper_historical_player_archive_candidate"]["supports_2025_reconstruction"] is False
    assert payload["active_zero_cost_candidate_priority"][0]["source_id"] == "cross_season_availability_harmonization_2022_2025"
    assert {row["source_id"] for row in payload["inactive_nonzero_cost_candidates"]} == {
        "sportradar_weekly_injuries_v7",
        "sportsdataio_injuries",
    }


def test_exact_2025_qualification_receipt_and_v09b_resolution_are_consistent() -> None:
    qualification = _load(AVAILABILITY_2025_QUALIFICATION)
    resolution = _load(V09B_RESOLUTION)
    assert qualification["research_source_qualified"] is True
    assert qualification["supports_2025_reconstruction"] is True
    assert qualification["supports_2022_2025_unified_backtest"] is False
    assert qualification["probability_feature_authorized"] is False
    assert qualification["production_dependency_authorized"] is False
    assert qualification["completed_2026_outcome_model_selection_allowed"] is False
    assert resolution["source_blocker_resolution"]["qualification_record"] == str(AVAILABILITY_2025_QUALIFICATION)
    assert resolution["experiment_retroactively_run"] is False
    assert resolution["historical_result_rewritten"] is False
    assert resolution["current_authorization"]["v09b_execution_authorized"] is False

from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("research/data_source_governance.json")
ADVANCED_REGISTRY = Path("research/advanced_player_source_governance.json")
AVAILABILITY_CONTRACT = Path("research/availability_source_audit_contract.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload() -> dict:
    return _load(REGISTRY)


def _advanced_payload() -> dict:
    return _load(ADVANCED_REGISTRY)


def test_every_source_has_explicit_family_rights_and_production_status() -> None:
    payload = _payload()
    assert payload["status"] == "research_governance"
    sources = payload["sources"]
    assert sources
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    for row in sources:
        assert row.get("family")
        assert row.get("provider")
        assert row.get("rights_status")
        assert row.get("production_eligibility")


def test_no_new_feed_is_accidentally_production_authorized() -> None:
    payload = _payload()
    for row in payload["sources"]:
        if row["source_id"] == "nflverse_games":
            assert row["production_eligibility"] == "existing_use_only"
            continue
        assert row["production_eligibility"] != "authorized"
        assert not str(row["production_eligibility"]).startswith("production_authorized")
    assert payload["current_decisions"]["production_market_source_change_authorized"] is False
    assert payload["current_decisions"]["player_availability_probability_feature_authorized"] is False


def test_market_families_cannot_be_silently_conflated() -> None:
    payload = _payload()
    by_id = {row["source_id"]: row for row in payload["sources"]}
    assert by_id["the_odds_api_us_h2h"]["family"] == "sportsbook_aggregator"
    assert by_id["polymarket"]["family"] == "prediction_exchange"
    assert by_id["kalshi"]["family"] == "prediction_exchange"
    assert "Never mix" in payload["family_rules"]["prediction_exchanges"]
    for source_id in ("sportsbook_fanduel", "sportsbook_draftkings", "sportsbook_betmgm"):
        assert by_id[source_id]["family"] == "sportsbook"
        assert "De-vig" in by_id[source_id]["combination_policy"]


def test_availability_and_advanced_player_sources_remain_firewalled() -> None:
    payload = _payload()
    sources = payload["sources"]
    availability = [row for row in sources if row["family"] == "availability"]
    advanced = [row for row in sources if row["family"] == "advanced_player_statistics"]
    assert availability
    assert advanced
    assert all(row["production_eligibility"] != "authorized" for row in availability + advanced)
    assert payload["current_decisions"]["recommended_first_availability_audit"] == "sportradar_weekly_injuries_v7"
    assert payload["current_decisions"]["pff_public_use"] == "not_authorized_under_consumer_api_terms"


def test_advanced_source_registry_prefers_clear_rights_and_never_authorizes_production() -> None:
    payload = _advanced_payload()
    assert payload["status"] == "research_governance"
    assert payload["production_authorized"] is False
    sources = payload["sources"]
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    assert all(row.get("provider") and row.get("family") for row in sources)
    assert all(row.get("production_eligibility") == "not_authorized" for row in sources)
    assert all(row.get("documentation") for row in sources)
    by_id = {row["source_id"]: row for row in sources}
    assert "CC-BY-SA-4.0" in by_id["ftn_charting_via_nflverse"]["license_status"]
    assert "commercial license" in by_id["sis_football_commercial"]["rights_status"].lower()
    assert "not a storage" in by_id["sumersports_subscription_stats"]["rights_status"]
    assert "proprietary" in by_id["direct_nfl_ngs_tracking"]["rights_status"].lower()


def test_availability_source_contract_fails_closed_on_missing_point_in_time_evidence() -> None:
    payload = _load(AVAILABILITY_CONTRACT)
    assert payload["status"] == "research_governance"
    assert payload["target_horizon_minutes"] == 120
    assert payload["production_authorized"] is False
    tests = payload["qualification_tests"]
    assert "2025" in tests["target_season_coverage"]
    assert "fail closed" in tests["revision_semantics"].lower()
    assert "Actual snaps" in tests["no_realized_participation_proxy"]
    outcomes = set(payload["fail_closed_outcomes"])
    assert "no historical availability model fitting" in outcomes
    assert "no availability probability feature" in outcomes
    assert payload["candidate_source_priority"][0]["source_id"] == "sportradar_weekly_injuries_v7"

from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("research/data_source_governance.json")


def _payload() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


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

from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("research/source_qualification_registry_v2.json")
VALID = {
    "QUALIFIED_RESEARCH",
    "PROSPECTIVE_ONLY",
    "CONTEXT_ONLY",
    "IDENTITY_ONLY",
    "BLOCKED",
    "REJECTED",
}
REQUIRED_FIELDS = {
    "source_id",
    "provider",
    "classification",
    "cost",
    "license_usage_rights",
    "redistribution_rights",
    "historical_coverage",
    "current_2026_support",
    "refresh_cadence",
    "stable_ids",
    "timestamp_semantics",
    "publication_lag",
    "revision_history",
    "missingness",
    "known_source_failures",
    "historical_research",
    "prospective_use",
    "public_display",
    "probability_features",
}


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _sources() -> list[dict]:
    return _registry()["sources"]


def test_registry_is_zero_cost_and_fail_closed() -> None:
    registry = _registry()
    assert registry["policy"]["cost_ceiling_usd"] == 0
    assert registry["policy"]["source_availability_does_not_authorize_features"] is True
    assert registry["policy"]["completed_2026_outcomes_for_selection"] is False
    assert registry["policy"]["fail_closed_on_rights_or_point_in_time_failure"] is True


def test_every_source_has_complete_qualification_record_and_unique_id() -> None:
    sources = _sources()
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    for row in sources:
        assert REQUIRED_FIELDS.issubset(row)
        assert row["classification"] in VALID
        assert str(row["cost"]).startswith("$0")


def test_sleeper_archive_remains_blocked_until_independently_verified() -> None:
    row = next(r for r in _sources() if r["source_id"] == "sleeper_historical_player_archive_candidate")
    assert row["classification"] == "BLOCKED"
    assert row["historical_research"] is False
    assert row["probability_features"] is False
    assert ">=99.5%" in row["reopen_condition"]


def test_sleeper_live_rights_boundary_prevents_probability_or_public_use() -> None:
    row = next(r for r in _sources() if r["source_id"] == "sleeper_live_players")
    assert row["classification"] == "CONTEXT_ONLY"
    assert "non-commercial" in row["license_usage_rights"].lower()
    assert row["public_display"] is False
    assert row["probability_features"] is False


def test_depth_chart_state_cannot_become_injury_state() -> None:
    row = next(r for r in _sources() if r["source_id"] == "nflverse_depth_charts_2025_plus")
    assert "never direct injury substitution" in row["probability_features"]
    assert any("not injury status" in item.lower() for item in row["known_source_failures"])


def test_market_history_cannot_sneak_in_through_paid_endpoint() -> None:
    row = next(r for r in _sources() if r["source_id"] == "the_odds_api_free_tier")
    assert row["classification"] == "PROSPECTIVE_ONLY"
    assert "paid historical" in row["historical_coverage"].lower()
    assert row["historical_research"] is False


def test_exchange_family_stays_separate_from_sportsbook_consensus() -> None:
    row = next(r for r in _sources() if r["source_id"] == "polymarket_public_market_data")
    assert "never blend" in row["probability_features"].lower()


def test_weather_reconstruction_encodes_publication_lag() -> None:
    row = next(r for r in _sources() if r["source_id"] == "open_meteo_archived_runs")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert "initialisation time is not publication time" in row["known_source_failures"]
    assert "4-6h" in row["publication_lag"]

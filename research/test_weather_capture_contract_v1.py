from __future__ import annotations

import json
from pathlib import Path


CONTRACT = Path("research/weather_capture_contract_v1.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_weather_capture_fails_closed_without_qualified_venue_resolution() -> None:
    contract = _contract()
    assert contract["status"] == "BLOCKED_ON_QUALIFIED_VENUE_RESOLUTION"
    venue = contract["venue_resolution"]
    assert venue["status"] == "BLOCKING_DEPENDENCY"
    assert venue["home_team_centroid_allowed"] is False
    assert venue["city_centroid_allowed"] is False
    assert "Fail closed" in venue["neutral_site_policy"]


def test_nws_capture_is_prospective_but_not_a_probability_feature() -> None:
    source = _contract()["prospective_source"]
    assert source["source_id"] == "nws_api"
    assert source["authorized_for_collection"] is True
    assert source["authorized_as_probability_feature"] is False
    assert source["required_horizons"] == ["T-72h", "T-24h", "T-6h", "T-120m"]
    assert source["research_only_horizons"] == ["T-60m", "T-30m"]
    assert "Never replace" in source["point_in_time_rule"]


def test_historical_weather_requires_publication_lag_not_run_initialization() -> None:
    historical = _contract()["historical_source"]
    assert historical["source_id"] == "open_meteo_archived_runs"
    assert historical["authorized_as_probability_feature"] is False
    assert "availability lag" in historical["availability_rule"]


def test_weather_contract_preserves_2026_and_production_firewalls() -> None:
    prohibitions = _contract()["prohibitions"]
    assert any("realized same-game weather" in item for item in prohibitions)
    assert any("completed 2026" in item.lower() for item in prohibitions)
    assert any("F-ST-01-FROZEN-2026" in item for item in prohibitions)
    assert any("T-120" in item for item in prohibitions)

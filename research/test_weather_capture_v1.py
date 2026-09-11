from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research.weather_capture_v1 import (
    WeatherCaptureError,
    due_horizons,
    normalize_nws_forecast,
    parse_wind_speed_mph,
    select_hourly_period,
    unavailable_weather_snapshot,
)


def _venue(status="resolved"):
    return {
        "status": status,
        "stadium_name": "Example Stadium",
        "wikidata_qid": "Q123",
        "latitude": 33.5,
        "longitude": -112.1,
        "schedule_roof": "outdoors",
        "wikidata_retrieved_at_utc": "2026-09-10T00:00:00Z",
    }


def _hourly():
    return {
        "properties": {
            "updated": "2026-09-13T14:50:00Z",
            "generatedAt": "2026-09-13T14:51:00Z",
            "periods": [
                {
                    "startTime": "2026-09-13T16:00:00Z",
                    "endTime": "2026-09-13T17:00:00Z",
                    "temperature": 29,
                    "temperatureUnit": "C",
                    "windSpeed": "10 to 15 mph",
                    "windDirection": "SW",
                    "probabilityOfPrecipitation": {"value": 35},
                    "shortForecast": "Chance Showers",
                },
                {
                    "startTime": "2026-09-13T17:00:00Z",
                    "endTime": "2026-09-13T18:00:00Z",
                    "temperature": 84,
                    "temperatureUnit": "F",
                    "windSpeed": "Calm",
                    "windDirection": "S",
                    "probabilityOfPrecipitation": {"value": 10},
                    "shortForecast": "Mostly Sunny",
                },
            ],
        }
    }


def test_due_horizons_preserve_official_and_research_only_roles() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    official = due_horizons(kickoff, datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc))
    assert official == [{
        "horizon": "T-120m",
        "target_timestamp_utc": datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc),
        "timing_error_minutes": 0.0,
        "research_only": False,
    }]
    research = due_horizons(kickoff, datetime(2026, 9, 13, 16, 30, tzinfo=timezone.utc))
    assert research[0]["horizon"] == "T-30m"
    assert research[0]["research_only"] is True


def test_wind_parser_handles_ranges_calm_and_metric_units() -> None:
    assert parse_wind_speed_mph("10 to 15 mph") == (10.0, 15.0)
    assert parse_wind_speed_mph("Calm") == (0.0, 0.0)
    low, high = parse_wind_speed_mph("10 to 20 km/h")
    assert round(low, 3) == 6.214
    assert round(high, 3) == 12.427


def test_hourly_period_must_uniquely_contain_kickoff() -> None:
    period = select_hourly_period(_hourly()["properties"]["periods"], datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc))
    assert period["shortForecast"] == "Mostly Sunny"
    with pytest.raises(WeatherCaptureError, match="exactly one"):
        select_hourly_period([], datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc))


def test_normalized_snapshot_preserves_provider_and_venue_provenance() -> None:
    row = normalize_nws_forecast(
        game_id="2026_01_CAR_CHI",
        kickoff_timestamp_utc="2026-09-13T17:00:00Z",
        horizon="T-120m",
        target_timestamp_utc="2026-09-13T15:00:00Z",
        retrieval_timestamp_utc="2026-09-13T15:02:00Z",
        venue_receipt=_venue(),
        points_url="https://api.weather.gov/points/33.5,-112.1",
        hourly_url="https://api.weather.gov/gridpoints/TEST/1,1/forecast/hourly",
        hourly_payload=_hourly(),
    )
    assert row["status"] == "captured"
    assert row["research_only"] is False
    assert row["production_authorized"] is False
    assert row["temperature_f"] == 84
    assert row["wind_speed_mph_low"] == 0
    assert row["provider_updated_timestamp_utc"] == "2026-09-13T14:50:00Z"
    assert row["venue"]["wikidata_qid"] == "Q123"


def test_weather_capture_fails_without_resolved_venue() -> None:
    with pytest.raises(WeatherCaptureError, match="resolved venue"):
        normalize_nws_forecast(
            game_id="g",
            kickoff_timestamp_utc="2026-09-13T17:00:00Z",
            horizon="T-120m",
            target_timestamp_utc="2026-09-13T15:00:00Z",
            retrieval_timestamp_utc="2026-09-13T15:00:00Z",
            venue_receipt=_venue("unresolved"),
            points_url="x",
            hourly_url="y",
            hourly_payload=_hourly(),
        )


def test_unavailable_snapshot_is_explicit_and_nonproduction() -> None:
    row = unavailable_weather_snapshot(
        game_id="g",
        kickoff_timestamp_utc="2026-09-13T17:00:00Z",
        horizon="T-120m",
        target_timestamp_utc="2026-09-13T15:00:00Z",
        retrieval_timestamp_utc="2026-09-13T15:00:00Z",
        reason="venue unresolved",
        venue_receipt=_venue("unresolved"),
    )
    assert row["status"] == "unavailable"
    assert row["production_authorized"] is False
    assert row["venue_status"] == "unresolved"

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


HORIZONS = {
    "T-72h": 72 * 60,
    "T-24h": 24 * 60,
    "T-6h": 6 * 60,
    "T-120m": 120,
    "T-60m": 60,
    "T-45m": 45,
    "T-30m": 30,
}
RESEARCH_ONLY_HORIZONS = {"T-60m", "T-45m", "T-30m"}
CAPTURE_TOLERANCE_MINUTES = 7.5
WIND_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class WeatherCaptureError(ValueError):
    pass


def parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise WeatherCaptureError(f"{field} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise WeatherCaptureError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def due_horizons(kickoff_utc: datetime, now_utc: datetime) -> list[dict[str, Any]]:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    now = now_utc.astimezone(timezone.utc)
    due = []
    for label, minutes in HORIZONS.items():
        target = kickoff - timedelta(minutes=minutes)
        error = (now - target).total_seconds() / 60.0
        if abs(error) <= CAPTURE_TOLERANCE_MINUTES:
            due.append({
                "horizon": label,
                "target_timestamp_utc": target,
                "timing_error_minutes": error,
                "research_only": label in RESEARCH_ONLY_HORIZONS,
            })
    return due


def parse_wind_speed_mph(value: Any) -> tuple[float | None, float | None]:
    text = str(value or "").strip().lower()
    if not text:
        return None, None
    numbers = [float(item) for item in WIND_NUMBER.findall(text)]
    if not numbers:
        if "calm" in text:
            return 0.0, 0.0
        return None, None
    if "km/h" in text or "kmh" in text:
        numbers = [item * 0.621371 for item in numbers]
    elif "m/s" in text:
        numbers = [item * 2.23694 for item in numbers]
    return min(numbers), max(numbers)


def _temperature_f(value: Any, unit: Any) -> float | None:
    try:
        temp = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(temp):
        return None
    normalized = str(unit or "F").strip().upper()
    if normalized in {"F", "FAHRENHEIT"}:
        return temp
    if normalized in {"C", "CELSIUS"}:
        return temp * 9.0 / 5.0 + 32.0
    raise WeatherCaptureError(f"unsupported temperature unit: {unit}")


def select_hourly_period(periods: Iterable[dict[str, Any]], kickoff_utc: datetime) -> dict[str, Any]:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    matches = []
    for period in periods:
        try:
            start = parse_utc(period.get("startTime"), "startTime")
            end = parse_utc(period.get("endTime"), "endTime")
        except WeatherCaptureError:
            continue
        if start <= kickoff < end:
            matches.append((start, end, period))
    if len(matches) != 1:
        raise WeatherCaptureError("forecast periods do not contain exactly one kickoff interval")
    return matches[0][2]


def normalize_nws_forecast(
    *,
    game_id: str,
    kickoff_timestamp_utc: str,
    horizon: str,
    target_timestamp_utc: str,
    retrieval_timestamp_utc: str,
    venue_receipt: dict[str, Any],
    points_url: str,
    hourly_url: str,
    hourly_payload: dict[str, Any],
) -> dict[str, Any]:
    if horizon not in HORIZONS:
        raise WeatherCaptureError(f"unsupported horizon: {horizon}")
    if venue_receipt.get("status") != "resolved":
        raise WeatherCaptureError("weather capture requires a resolved venue receipt")
    kickoff = parse_utc(kickoff_timestamp_utc, "kickoff_timestamp_utc")
    target = parse_utc(target_timestamp_utc, "target_timestamp_utc")
    retrieval = parse_utc(retrieval_timestamp_utc, "retrieval_timestamp_utc")
    expected = kickoff - timedelta(minutes=HORIZONS[horizon])
    if target != expected:
        raise WeatherCaptureError("target timestamp does not match kickoff/horizon")
    if retrieval >= kickoff:
        raise WeatherCaptureError("weather snapshot must be retrieved before kickoff")

    properties = hourly_payload.get("properties") or {}
    periods = properties.get("periods") or []
    period = select_hourly_period(periods, kickoff)
    period_start = parse_utc(period.get("startTime"), "period.startTime")
    period_end = parse_utc(period.get("endTime"), "period.endTime")
    wind_low, wind_high = parse_wind_speed_mph(period.get("windSpeed"))
    precip = ((period.get("probabilityOfPrecipitation") or {}).get("value"))
    try:
        precip_value = float(precip) if precip is not None else None
    except (TypeError, ValueError):
        precip_value = None

    latitude = float(venue_receipt["latitude"])
    longitude = float(venue_receipt["longitude"])
    return {
        "schema_version": "levline-weather-snapshot-v1",
        "status": "captured",
        "game_id": game_id,
        "kickoff_timestamp_utc": kickoff.isoformat(),
        "horizon": horizon,
        "research_only": horizon in RESEARCH_ONLY_HORIZONS,
        "production_authorized": False,
        "target_timestamp_utc": target.isoformat(),
        "retrieval_timestamp_utc": retrieval.isoformat(),
        "timing_error_minutes": (retrieval - target).total_seconds() / 60.0,
        "source_id": "nws_api",
        "points_url": points_url,
        "hourly_forecast_url": hourly_url,
        "provider_updated_timestamp_utc": properties.get("updated"),
        "provider_generated_timestamp_utc": properties.get("generatedAt"),
        "forecast_period_start_utc": period_start.isoformat(),
        "forecast_period_end_utc": period_end.isoformat(),
        "temperature_f": _temperature_f(period.get("temperature"), period.get("temperatureUnit")),
        "wind_speed_mph_low": wind_low,
        "wind_speed_mph_high": wind_high,
        "wind_direction": period.get("windDirection"),
        "precipitation_probability_pct": precip_value,
        "short_forecast": period.get("shortForecast"),
        "venue": {
            "stadium_name": venue_receipt.get("stadium_name"),
            "wikidata_qid": venue_receipt.get("wikidata_qid"),
            "latitude": latitude,
            "longitude": longitude,
            "schedule_roof": venue_receipt.get("schedule_roof"),
            "venue_receipt_generated_from": venue_receipt.get("wikidata_retrieved_at_utc"),
        },
    }


def unavailable_weather_snapshot(
    *,
    game_id: str,
    kickoff_timestamp_utc: str,
    horizon: str,
    target_timestamp_utc: str,
    retrieval_timestamp_utc: str,
    reason: str,
    venue_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "levline-weather-snapshot-v1",
        "status": "unavailable",
        "game_id": game_id,
        "kickoff_timestamp_utc": kickoff_timestamp_utc,
        "horizon": horizon,
        "research_only": horizon in RESEARCH_ONLY_HORIZONS,
        "production_authorized": False,
        "target_timestamp_utc": target_timestamp_utc,
        "retrieval_timestamp_utc": retrieval_timestamp_utc,
        "source_id": "nws_api",
        "reason": reason,
        "venue_status": (venue_receipt or {}).get("status"),
        "stadium_name": (venue_receipt or {}).get("stadium_name"),
    }

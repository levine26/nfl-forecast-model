from __future__ import annotations

"""Research-only schema helpers for eventual Sunday Signal player impact cards.

Observed source statistics and LevLine modeled impacts are intentionally separate types.
This module produces no fantasy-style player projections and is not imported by the site
or production forecast path.
"""

from datetime import datetime, timezone
from typing import Any, Iterable

ALLOWED_OBSERVED_METRICS = {
    "target_share",
    "route_share",
    "air_yard_share",
    "epa_per_target",
    "epa_per_dropback",
    "success_rate",
    "cpoe",
    "pressure_rate",
    "separation",
    "ryoe",
    "snap_share",
    "ol_continuity",
    "avg_time_to_throw",
    "avg_intended_air_yards",
}

ALLOWED_IMPACT_METRICS = {
    "levline_qb_state",
    "levline_skill_unit_state",
    "levline_ol_state",
    "levline_pass_rush_state",
    "levline_run_defense_state",
    "levline_secondary_state",
    "levline_expected_lineup_value_lost",
    "levline_player_impact",
}

PROHIBITED_PROJECTION_TERMS = (
    "projected yard",
    "yard projection",
    "projected reception",
    "reception projection",
    "projected touchdown",
    "touchdown probability",
    "fantasy point",
    "anytime touchdown",
)


def _require(mapping: dict[str, Any], fields: Iterable[str], label: str) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def _projection_guard(value: Any) -> None:
    text = str(value or "").lower()
    if any(term in text for term in PROHIBITED_PROJECTION_TERMS):
        raise ValueError(f"Fantasy-style player projection is prohibited: {value}")


def validate_observed_stat(stat: dict[str, Any]) -> None:
    _require(
        stat,
        (
            "kind",
            "metric",
            "value",
            "unit",
            "source_name",
            "source_url",
            "source_data_as_of",
            "sample_size",
            "redistribution_review_status",
        ),
        "observed statistic",
    )
    if stat["kind"] != "source_observed":
        raise ValueError("Observed statistics must use kind=source_observed")
    if stat["metric"] not in ALLOWED_OBSERVED_METRICS:
        raise ValueError(f"Unregistered observed metric: {stat['metric']}")
    _projection_guard(stat["metric"])
    if stat["redistribution_review_status"] not in {"pending", "approved", "restricted", "do_not_publish"}:
        raise ValueError("Invalid redistribution_review_status")
    if not str(stat["source_url"]).startswith(("http://", "https://")):
        raise ValueError("Observed statistic requires a source URL")


def validate_impact(impact: dict[str, Any]) -> None:
    _require(
        impact,
        (
            "kind",
            "metric",
            "estimate",
            "uncertainty",
            "model_version",
            "feature_data_horizon",
            "interpretation",
        ),
        "LevLine impact",
    )
    if impact["kind"] != "levline_modeled_impact":
        raise ValueError("Modeled impacts must use kind=levline_modeled_impact")
    if impact["metric"] not in ALLOWED_IMPACT_METRICS:
        raise ValueError(f"Unregistered LevLine impact metric: {impact['metric']}")
    _projection_guard(impact["metric"])
    if float(impact["uncertainty"]) < 0:
        raise ValueError("Impact uncertainty must be non-negative")
    if "nfl" in str(impact["interpretation"]).lower() and "official" in str(impact["interpretation"]).lower():
        raise ValueError("LevLine modeled impact must not be represented as an official NFL statistic")


def validate_card(card: dict[str, Any]) -> None:
    _require(
        card,
        (
            "schema_version",
            "research_only",
            "game_id",
            "team",
            "player_id",
            "player_name",
            "position",
            "observed_statistics",
            "levline_impacts",
            "data_quality",
        ),
        "player impact card",
    )
    if card["research_only"] is not True:
        raise ValueError("Player impact cards are research-only until explicit promotion")
    if not str(card["player_id"]).strip():
        raise ValueError("Stable player_id is required; ambiguous identity fails closed")
    for value in (card["player_name"], card["position"]):
        _projection_guard(value)
    if not isinstance(card["observed_statistics"], list) or not isinstance(card["levline_impacts"], list):
        raise ValueError("observed_statistics and levline_impacts must be lists")
    for stat in card["observed_statistics"]:
        validate_observed_stat(stat)
    for impact in card["levline_impacts"]:
        validate_impact(impact)
    quality = card["data_quality"]
    _require(quality, ("identity_confidence", "coverage_status", "missing_fields"), "data_quality")
    if quality["identity_confidence"] not in {"stable_id", "unknown"}:
        raise ValueError("Only stable-ID or unknown identity states are permitted")


def build_payload(cards: list[dict[str, Any]], *, generated_utc: str | None = None) -> dict[str, Any]:
    for card in cards:
        validate_card(card)
    return {
        "schema_version": 1,
        "mode": "research_only",
        "public_site_consumes_this_file": False,
        "fantasy_style_projections": False,
        "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "cards": cards,
        "licensing_note": "Redistribution status is tracked per observed statistic. Pending or restricted sources must not be published without a separate review.",
    }

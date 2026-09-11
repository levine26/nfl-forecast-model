from __future__ import annotations

"""Research-only compositor for a Sunday Signal player Impact Monitor.

The monitor is explanatory only. It never changes game probabilities, never creates
fantasy-style projections, and never republishes an observed statistic unless that row's
redistribution review is explicitly approved.
"""

from datetime import datetime, timezone
from typing import Any

from nfl_forecast.player_impact_cards import validate_card

MONITOR_SCHEMA_VERSION = 1
PROHIBITED_FIELDS = {
    "actual_snap_count",
    "actual_snap_share",
    "actual_participation",
    "postgame_participation",
    "actual_home_score",
    "actual_away_score",
    "home_win",
    "final_inactive_learned_post_kickoff",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_recursive_keys(item))
    return keys


def _validate_monitor_card(card: dict[str, Any]) -> None:
    validate_card(card)
    forbidden = PROHIBITED_FIELDS.intersection(_recursive_keys(card))
    if forbidden:
        raise ValueError(f"Impact Monitor refuses retrospective/outcome fields: {sorted(forbidden)}")
    if card.get("research_only") is not True:
        raise ValueError("Impact Monitor requires research_only=true")


def public_safe_card(card: dict[str, Any]) -> dict[str, Any]:
    """Return a public-safe explanatory card with restricted source statistics removed."""
    _validate_monitor_card(card)
    observed = list(card.get("observed_statistics") or [])
    approved = [row for row in observed if row.get("redistribution_review_status") == "approved"]
    suppressed = len(observed) - len(approved)
    impacts = []
    for impact in card.get("levline_impacts") or []:
        item = dict(impact)
        item["research_only"] = True
        item["probability_feature_authorized"] = False
        impacts.append(item)

    availability = card.get("availability")
    if availability is not None:
        if not isinstance(availability, dict):
            raise ValueError("availability must be an object when supplied")
        source_status = str(availability.get("source_status") or "unknown")
        if source_status not in {"qualified", "prospective_unqualified", "unknown"}:
            raise ValueError(f"Invalid availability source_status: {source_status}")
        availability = {
            "practice_status": availability.get("practice_status"),
            "game_status": availability.get("game_status"),
            "source_status": source_status,
            "source_name": availability.get("source_name"),
            "source_url": availability.get("source_url"),
            "source_data_as_of": availability.get("source_data_as_of"),
            "probability_feature_authorized": False,
        }

    return {
        "game_id": card["game_id"],
        "team": card["team"],
        "player_id": card["player_id"],
        "player_name": card["player_name"],
        "position": card["position"],
        "observed_statistics": approved,
        "suppressed_observed_statistics": suppressed,
        "levline_impacts": impacts,
        "availability": availability,
        "data_quality": card["data_quality"],
        "research_only": True,
        "probability_feature_authorized": False,
    }


def build_impact_monitor_payload(
    cards: list[dict[str, Any]],
    *,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    safe = [public_safe_card(card) for card in cards]
    safe.sort(key=lambda row: (str(row["game_id"]), str(row["team"]), str(row["position"]), str(row["player_name"])))
    games: list[dict[str, Any]] = []
    for game_id in sorted({str(row["game_id"]) for row in safe}):
        players = [row for row in safe if str(row["game_id"]) == game_id]
        games.append(
            {
                "game_id": game_id,
                "players": players,
                "approved_observed_statistics": sum(len(row["observed_statistics"]) for row in players),
                "suppressed_observed_statistics": sum(int(row["suppressed_observed_statistics"]) for row in players),
                "research_only": True,
                "probability_feature_authorized": False,
            }
        )
    return {
        "schema_version": MONITOR_SCHEMA_VERSION,
        "mode": "research_explainability_only",
        "generated_utc": generated_utc or _now(),
        "probability_feature_authorized": False,
        "fantasy_style_projections": False,
        "source_observed_and_levline_modeled_are_distinct": True,
        "games": games,
        "publication_policy": (
            "Only source-observed rows with redistribution_review_status=approved are emitted. "
            "Pending, restricted, and do_not_publish rows are suppressed. LevLine impacts remain "
            "explicitly modeled research and are never represented as official NFL statistics."
        ),
    }

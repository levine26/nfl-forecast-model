from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA_VERSION = "levline-game-venue-v1"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/{qid}"


class VenueResolutionError(ValueError):
    pass


@dataclass(frozen=True)
class ExactCandidate:
    qid: str
    label: str
    match_text: str
    match_type: str


def normalize_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def exact_search_candidates(stadium_name: str, search_rows: Iterable[dict[str, Any]]) -> list[ExactCandidate]:
    target = normalize_name(stadium_name)
    if not target:
        return []
    found: dict[str, ExactCandidate] = {}
    for row in search_rows:
        qid = str(row.get("id") or "").strip()
        label = str(row.get("label") or "").strip()
        match = row.get("match") or {}
        match_text = str(match.get("text") or "").strip()
        exact_label = normalize_name(label) == target
        exact_match = normalize_name(match_text) == target
        if not qid or not (exact_label or exact_match):
            continue
        match_type = "label" if exact_label else str(match.get("type") or "alias")
        found[qid] = ExactCandidate(qid=qid, label=label, match_text=match_text, match_type=match_type)
    return list(found.values())


def choose_exact_candidate(stadium_name: str, search_rows: Iterable[dict[str, Any]]) -> ExactCandidate:
    candidates = exact_search_candidates(stadium_name, search_rows)
    if not candidates:
        raise VenueResolutionError("no exact Wikidata stadium label/alias match")
    if len(candidates) != 1:
        qids = ",".join(sorted(candidate.qid for candidate in candidates))
        raise VenueResolutionError(f"ambiguous exact Wikidata matches: {qids}")
    return candidates[0]


def _coordinate_statements(entity: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        statement
        for statement in (entity.get("claims") or {}).get("P625", [])
        if statement.get("rank") != "deprecated"
        and ((statement.get("mainsnak") or {}).get("datavalue") or {}).get("value")
    ]


def extract_coordinate(entity: dict[str, Any]) -> tuple[float, float, str]:
    statements = _coordinate_statements(entity)
    preferred = [statement for statement in statements if statement.get("rank") == "preferred"]
    eligible = preferred or [statement for statement in statements if statement.get("rank") in {None, "normal"}]
    if len(eligible) != 1:
        raise VenueResolutionError("Wikidata coordinate is missing or ambiguous")
    statement = eligible[0]
    value = statement["mainsnak"]["datavalue"]["value"]
    latitude = float(value.get("latitude"))
    longitude = float(value.get("longitude"))
    globe = str(value.get("globe") or "")
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise VenueResolutionError("Wikidata coordinate is non-finite")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise VenueResolutionError("Wikidata coordinate is outside WGS84 bounds")
    if globe and not globe.endswith("Q2"):
        raise VenueResolutionError("Wikidata coordinate is not on Earth")
    return latitude, longitude, str(statement.get("rank") or "normal")


def resolve_game_venue(
    *,
    schedule_row: dict[str, Any],
    search_rows: Iterable[dict[str, Any]],
    entity: dict[str, Any],
    schedule_retrieved_at_utc: str,
    wikidata_retrieved_at_utc: str,
) -> dict[str, Any]:
    game_id = str(schedule_row.get("game_id") or "").strip()
    stadium = str(schedule_row.get("stadium") or "").strip()
    if not game_id:
        raise VenueResolutionError("game_id is required")
    if not stadium:
        raise VenueResolutionError("schedule stadium is required")
    candidate = choose_exact_candidate(stadium, search_rows)
    entity_id = str(entity.get("id") or "")
    if entity_id != candidate.qid:
        raise VenueResolutionError("entity payload does not match selected QID")
    latitude, longitude, rank = extract_coordinate(entity)
    label = str(((entity.get("labels") or {}).get("en") or {}).get("value") or candidate.label).strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "resolved",
        "game_id": game_id,
        "gameday": schedule_row.get("gameday"),
        "away_team": schedule_row.get("away_team"),
        "home_team": schedule_row.get("home_team"),
        "stadium_name": stadium,
        "schedule_location": schedule_row.get("location"),
        "schedule_roof": schedule_row.get("roof"),
        "schedule_retrieved_at_utc": schedule_retrieved_at_utc,
        "wikidata_qid": candidate.qid,
        "wikidata_label": label,
        "wikidata_url": WIKIDATA_ENTITY_URL.format(qid=candidate.qid),
        "latitude": latitude,
        "longitude": longitude,
        "wikidata_retrieved_at_utc": wikidata_retrieved_at_utc,
        "resolution_match_type": candidate.match_type,
        "coordinate_rank": rank,
        "research_only": True,
        "production_authorized": False,
    }


def unresolved_game_venue(
    *,
    schedule_row: dict[str, Any],
    reason: str,
    schedule_retrieved_at_utc: str,
    attempted_at_utc: str | None = None,
) -> dict[str, Any]:
    attempted = attempted_at_utc or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "unresolved",
        "game_id": schedule_row.get("game_id"),
        "gameday": schedule_row.get("gameday"),
        "away_team": schedule_row.get("away_team"),
        "home_team": schedule_row.get("home_team"),
        "stadium_name": schedule_row.get("stadium"),
        "schedule_location": schedule_row.get("location"),
        "schedule_roof": schedule_row.get("roof"),
        "schedule_retrieved_at_utc": schedule_retrieved_at_utc,
        "attempted_at_utc": attempted,
        "reason": reason,
        "research_only": True,
        "production_authorized": False,
    }

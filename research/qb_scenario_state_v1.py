from __future__ import annotations

"""Prospective QB starter/replacement state capture for LevLine 4 H2.

A complete starter-probability distribution may be preserved, but this module never
creates conditional win probabilities or changes the official forecast.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Iterable

SCHEMA_VERSION = "levline-qb-scenario-state-v1"
STARTER_STATES = {
    "confirmed_starter",
    "expected_starter",
    "possible_starter",
    "backup",
    "emergency",
    "ruled_out",
    "unknown",
}
CONTINUITY_STATES = {
    "same_starter_same_system",
    "new_starter_same_system",
    "new_team_or_material_system_change",
    "returning_after_absence",
    "unknown",
}
ALLOWED_PROBABILITY_METHODS = {
    "source_explicit_probability",
    "frozen_pregame_estimator",
    "deterministic_official_confirmation",
}
FORBIDDEN_FIELDS = {
    "qb_value_points",
    "replacement_probability_delta",
    "conditional_win_probability",
    "win_probability_if_starts",
    "official_forecast_probability",
    "edge",
    "pick",
    "recommendation",
}


def _utc(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing required timestamp: {field}")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp for {field}: {text}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must be timezone-aware: {field}")
    return dt.astimezone(timezone.utc)


def _sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("raw_evidence_sha256 must be a 64-character lowercase hex digest")
    return text


def _optional_probability(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("starter_probability must be numeric") from exc
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError("starter_probability must be between 0 and 1")
    return out


def validate_qb_candidate(row: dict[str, Any]) -> dict[str, Any]:
    forbidden = sorted(key for key in FORBIDDEN_FIELDS if key in row and str(row.get(key) or "").strip())
    if forbidden:
        raise ValueError(f"forecast/scenario-effect fields are prohibited: {forbidden}")

    required = [
        "candidate_id",
        "snapshot_id",
        "game_id",
        "team",
        "player_id",
        "starter_state",
        "continuity_state",
        "source",
        "source_url_or_id",
        "raw_evidence_ref",
        "extractor_or_parser_id",
        "extractor_or_parser_version",
    ]
    for field in required:
        if not str(row.get(field) or "").strip():
            raise ValueError(f"missing required field: {field}")

    starter_state = str(row["starter_state"]).strip()
    continuity_state = str(row["continuity_state"]).strip()
    if starter_state not in STARTER_STATES:
        raise ValueError(f"unsupported starter_state: {starter_state}")
    if continuity_state not in CONTINUITY_STATES:
        raise ValueError(f"unsupported continuity_state: {continuity_state}")

    published_at = _utc(row.get("published_at_utc"), "published_at_utc")
    captured_at = _utc(row.get("captured_at_utc"), "captured_at_utc")
    asof = _utc(row.get("forecast_asof_utc"), "forecast_asof_utc")
    kickoff = _utc(row.get("kickoff_timestamp_utc"), "kickoff_timestamp_utc")
    if published_at > captured_at:
        raise ValueError("published_at_utc cannot be after captured_at_utc")
    if captured_at > asof:
        raise ValueError("captured_at_utc cannot be after forecast_asof_utc")
    if asof >= kickoff:
        raise ValueError("forecast_asof_utc must precede kickoff_timestamp_utc")

    probability = _optional_probability(row.get("starter_probability"))
    method = str(row.get("starter_probability_method") or "").strip() or None
    if probability is None and method is not None:
        raise ValueError("starter_probability_method requires starter_probability")
    if probability is not None and method not in ALLOWED_PROBABILITY_METHODS:
        raise ValueError("starter_probability requires an allowed frozen/source method")
    if starter_state == "unknown" and probability is not None:
        raise ValueError("unknown starter state cannot carry starter_probability")
    if starter_state == "ruled_out" and probability not in {None, 0.0}:
        raise ValueError("ruled_out candidate may only carry starter_probability 0")
    if starter_state == "confirmed_starter" and method == "deterministic_official_confirmation" and probability != 1.0:
        raise ValueError("deterministically confirmed starter must have probability 1")

    depth_order_raw = row.get("pregame_depth_order")
    if depth_order_raw is None or str(depth_order_raw).strip() == "":
        depth_order = None
    else:
        try:
            depth_order = int(depth_order_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("pregame_depth_order must be an integer") from exc
        if depth_order < 1:
            raise ValueError("pregame_depth_order must be >= 1")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": str(row["candidate_id"]).strip(),
        "snapshot_id": str(row["snapshot_id"]).strip(),
        "game_id": str(row["game_id"]).strip(),
        "team": str(row["team"]).strip(),
        "opponent": str(row.get("opponent") or "").strip() or None,
        "player_id": str(row["player_id"]).strip(),
        "player_name": str(row.get("player_name") or "").strip() or None,
        "starter_state": starter_state,
        "continuity_state": continuity_state,
        "pregame_depth_order": depth_order,
        "starter_probability": probability,
        "starter_probability_method": method,
        "source": str(row["source"]).strip(),
        "source_url_or_id": str(row["source_url_or_id"]).strip(),
        "raw_evidence_ref": str(row["raw_evidence_ref"]).strip(),
        "raw_evidence_sha256": _sha(row.get("raw_evidence_sha256")),
        "published_at_utc": published_at.isoformat().replace("+00:00", "Z"),
        "captured_at_utc": captured_at.isoformat().replace("+00:00", "Z"),
        "forecast_asof_utc": asof.isoformat().replace("+00:00", "Z"),
        "kickoff_timestamp_utc": kickoff.isoformat().replace("+00:00", "Z"),
        "minutes_to_kickoff": (kickoff - asof).total_seconds() / 60.0,
        "extractor_or_parser_id": str(row["extractor_or_parser_id"]).strip(),
        "extractor_or_parser_version": str(row["extractor_or_parser_version"]).strip(),
        "research_only": True,
        "production_authorized": False,
        "scenario_mixture_authorized": False,
        "conditional_win_probability_authorized": False,
        "forecast_mutation_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    digest_basis = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    normalized["candidate_sha256"] = hashlib.sha256(digest_basis.encode("utf-8")).hexdigest()
    return normalized


def validate_qb_snapshot(rows: Iterable[dict[str, Any]], *, tolerance: float = 1e-9) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = [validate_qb_candidate(dict(row)) for row in rows]
    if not candidates:
        return [], {
            "schema_version": SCHEMA_VERSION,
            "rows": 0,
            "probability_complete": False,
            "scenario_mixture_authorized": False,
            "production_authorized": False,
        }

    snapshot_ids = {row["snapshot_id"] for row in candidates}
    game_ids = {row["game_id"] for row in candidates}
    teams = {row["team"] for row in candidates}
    asofs = {row["forecast_asof_utc"] for row in candidates}
    kickoffs = {row["kickoff_timestamp_utc"] for row in candidates}
    if len(snapshot_ids) != 1 or len(game_ids) != 1 or len(teams) != 1 or len(asofs) != 1 or len(kickoffs) != 1:
        raise ValueError("QB snapshot rows must share snapshot_id, game_id, team, asof and kickoff")

    candidate_ids = [row["candidate_id"] for row in candidates]
    player_ids = [row["player_id"] for row in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("duplicate candidate_id")
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("duplicate player_id in QB snapshot")

    probabilities = [row["starter_probability"] for row in candidates]
    any_probability = any(value is not None for value in probabilities)
    all_probability = all(value is not None for value in probabilities)
    if any_probability and not all_probability:
        raise ValueError("partial QB starter-probability distribution is not allowed")

    probability_complete = False
    if all_probability:
        assert all(value is not None for value in probabilities)
        total = sum(float(value) for value in probabilities)
        if abs(total - 1.0) > tolerance:
            raise ValueError(f"QB starter probabilities must sum to 1; observed {total}")
        if any(row["starter_state"] == "unknown" for row in candidates):
            raise ValueError("probability-complete QB snapshot cannot contain unknown starter state")
        probability_complete = True

    audit = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": next(iter(snapshot_ids)),
        "game_id": next(iter(game_ids)),
        "team": next(iter(teams)),
        "rows": len(candidates),
        "probability_complete": probability_complete,
        "probability_sum": sum(float(value) for value in probabilities) if all_probability else None,
        "scenario_mixture_authorized": False,
        "conditional_win_probability_authorized": False,
        "research_only": True,
        "production_authorized": False,
        "forecast_mutation_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return candidates, audit

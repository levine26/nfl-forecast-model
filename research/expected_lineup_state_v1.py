from __future__ import annotations

"""Prospective, outcome-blind expected-lineup state capture for LevLine 4.

This module validates what was knowable at a forecast timestamp. It does not convert
football state into a win-probability adjustment and does not mutate production output.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Iterable

SCHEMA_VERSION = "levline-expected-lineup-state-v1"

MEMBERSHIP_STATES = {
    "confirmed_team_roster",
    "expected_team_roster",
    "uncertain_membership",
    "not_expected_on_game_roster",
    "unknown",
}
AVAILABILITY_STATES = {
    "available_confirmed",
    "expected_available",
    "questionable",
    "doubtful",
    "out",
    "suspended_or_exempt",
    "reserve_or_ir",
    "not_listed_on_qualified_report",
    "unknown",
}
ROLE_TIERS = {
    "starter",
    "rotation",
    "package",
    "backup",
    "emergency",
    "special_teams_only",
    "unknown",
}
UNITS = {"QB", "OL", "RB_WR_TE", "DEFENSIVE_FRONT", "LB", "SECONDARY", "SPECIAL_TEAMS"}
ALLOWED_PROBABILITY_METHODS = {
    "source_explicit_probability",
    "frozen_pregame_estimator",
    "deterministic_official_confirmation",
}
ALLOWED_ROLE_SHARE_METHODS = {
    "source_explicit_share",
    "frozen_pregame_estimator",
    "deterministic_role_rule",
}
FORBIDDEN_EFFECT_FIELDS = {
    "edge",
    "win_probability",
    "win_probability_delta",
    "probability_delta",
    "forecast_adjustment",
    "pick",
    "recommendation",
    "player_probability_points",
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


def _sha(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{field} must be a 64-character lowercase hex digest")
    return text


def _optional_unit_interval(value: Any, field: str) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return out


def validate_expected_lineup_observation(row: dict[str, Any]) -> dict[str, Any]:
    forbidden = sorted(
        key for key in FORBIDDEN_EFFECT_FIELDS if key in row and str(row.get(key) or "").strip()
    )
    if forbidden:
        raise ValueError(f"forecast-effect fields are prohibited: {forbidden}")

    required_text = [
        "observation_id",
        "snapshot_id",
        "game_id",
        "team",
        "player_id",
        "position",
        "unit",
        "membership_state",
        "availability_state",
        "expected_role_tier",
        "source",
        "source_url_or_id",
        "raw_evidence_ref",
        "extractor_or_parser_id",
        "extractor_or_parser_version",
    ]
    for field in required_text:
        if not str(row.get(field) or "").strip():
            raise ValueError(f"missing required field: {field}")

    membership = str(row["membership_state"]).strip()
    availability = str(row["availability_state"]).strip()
    role = str(row["expected_role_tier"]).strip()
    unit = str(row["unit"]).strip()
    if membership not in MEMBERSHIP_STATES:
        raise ValueError(f"unsupported membership_state: {membership}")
    if availability not in AVAILABILITY_STATES:
        raise ValueError(f"unsupported availability_state: {availability}")
    if role not in ROLE_TIERS:
        raise ValueError(f"unsupported expected_role_tier: {role}")
    if unit not in UNITS:
        raise ValueError(f"unsupported unit: {unit}")

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

    raw_sha = _sha(row.get("raw_evidence_sha256"), "raw_evidence_sha256")
    availability_probability = _optional_unit_interval(
        row.get("availability_probability"), "availability_probability"
    )
    availability_method = str(row.get("availability_probability_method") or "").strip() or None
    role_share = _optional_unit_interval(row.get("expected_role_share"), "expected_role_share")
    role_share_method = str(row.get("expected_role_share_method") or "").strip() or None

    if availability_probability is None and availability_method is not None:
        raise ValueError("availability_probability_method requires availability_probability")
    if availability_probability is not None:
        if availability_method not in ALLOWED_PROBABILITY_METHODS:
            raise ValueError("availability_probability requires an allowed frozen/source method")
        if availability in {"unknown", "not_listed_on_qualified_report"}:
            raise ValueError("unknown/not-listed state cannot be assigned an availability probability")
        if availability == "out" and availability_probability != 0.0:
            raise ValueError("out state may only carry deterministic availability probability 0")
        if availability == "available_confirmed" and availability_probability != 1.0:
            raise ValueError("available_confirmed may only carry deterministic probability 1")

    if role_share is None and role_share_method is not None:
        raise ValueError("expected_role_share_method requires expected_role_share")
    if role_share is not None:
        if role_share_method not in ALLOWED_ROLE_SHARE_METHODS:
            raise ValueError("expected_role_share requires an allowed frozen/source method")
        if role == "unknown":
            raise ValueError("unknown role tier cannot be assigned expected_role_share")

    if membership == "unknown" and (availability_probability is not None or role_share is not None):
        raise ValueError("unknown membership cannot carry continuous lineup inputs")
    if membership == "not_expected_on_game_roster" and role in {"starter", "rotation", "package"}:
        raise ValueError("not-expected roster membership conflicts with active role tier")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": str(row["observation_id"]).strip(),
        "snapshot_id": str(row["snapshot_id"]).strip(),
        "game_id": str(row["game_id"]).strip(),
        "team": str(row["team"]).strip(),
        "opponent": str(row.get("opponent") or "").strip() or None,
        "player_id": str(row["player_id"]).strip(),
        "player_name": str(row.get("player_name") or "").strip() or None,
        "position": str(row["position"]).strip(),
        "unit": unit,
        "membership_state": membership,
        "availability_state": availability,
        "expected_role_tier": role,
        "availability_probability": availability_probability,
        "availability_probability_method": availability_method,
        "expected_role_share": role_share,
        "expected_role_share_method": role_share_method,
        "source": str(row["source"]).strip(),
        "source_url_or_id": str(row["source_url_or_id"]).strip(),
        "raw_evidence_ref": str(row["raw_evidence_ref"]).strip(),
        "raw_evidence_sha256": raw_sha,
        "published_at_utc": published_at.isoformat().replace("+00:00", "Z"),
        "captured_at_utc": captured_at.isoformat().replace("+00:00", "Z"),
        "forecast_asof_utc": asof.isoformat().replace("+00:00", "Z"),
        "kickoff_timestamp_utc": kickoff.isoformat().replace("+00:00", "Z"),
        "minutes_to_kickoff": (kickoff - asof).total_seconds() / 60.0,
        "extractor_or_parser_id": str(row["extractor_or_parser_id"]).strip(),
        "extractor_or_parser_version": str(row["extractor_or_parser_version"]).strip(),
        "identity_method": str(row.get("identity_method") or "").strip() or None,
        "research_only": True,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "forecast_mutation_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    digest_basis = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    normalized["observation_sha256"] = hashlib.sha256(digest_basis.encode("utf-8")).hexdigest()
    return normalized


def validate_expected_lineup_snapshot(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized = [validate_expected_lineup_observation(dict(row)) for row in rows]
    if not normalized:
        return [], {
            "schema_version": SCHEMA_VERSION,
            "rows": 0,
            "research_only": True,
            "production_authorized": False,
            "probability_feature_authorized": False,
        }

    snapshot_ids = {row["snapshot_id"] for row in normalized}
    game_ids = {row["game_id"] for row in normalized}
    teams = {row["team"] for row in normalized}
    asofs = {row["forecast_asof_utc"] for row in normalized}
    kickoffs = {row["kickoff_timestamp_utc"] for row in normalized}
    if len(snapshot_ids) != 1 or len(game_ids) != 1 or len(teams) != 1 or len(asofs) != 1 or len(kickoffs) != 1:
        raise ValueError("snapshot rows must share snapshot_id, game_id, team, forecast_asof and kickoff")

    observation_ids = [row["observation_id"] for row in normalized]
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("duplicate observation_id")
    player_ids = [row["player_id"] for row in normalized]
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("duplicate player_id within expected-lineup snapshot")

    continuous_ready = sum(
        int(row["availability_probability"] is not None and row["expected_role_share"] is not None)
        for row in normalized
    )
    unknown_rows = sum(
        int(
            row["membership_state"] == "unknown"
            or row["availability_state"] == "unknown"
            or row["expected_role_tier"] == "unknown"
        )
        for row in normalized
    )
    audit = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": next(iter(snapshot_ids)),
        "game_id": next(iter(game_ids)),
        "team": next(iter(teams)),
        "rows": len(normalized),
        "continuous_input_ready_rows": continuous_ready,
        "unknown_state_rows": unknown_rows,
        "complete_expected_lineup_feature_authorized": False,
        "research_only": True,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "forecast_mutation_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return normalized, audit

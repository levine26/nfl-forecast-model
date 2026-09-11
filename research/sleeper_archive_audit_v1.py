from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA_VERSION = "levline-sleeper-archive-audit-v1"
IDENTITY_MIN_RATE = 0.995
SCHEMA_PRESENCE_MIN_RATE = 0.995
DEFAULT_STATE_FIELDS = (
    "injury_status",
    "practice_participation",
    "practice_description",
    "depth_chart_order",
    "status",
    "team",
    "position",
)


class SleeperArchiveAuditError(ValueError):
    pass


@dataclass(frozen=True)
class SnapshotEligibility:
    eligible: bool
    failures: tuple[str, ...]


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SleeperArchiveAuditError(f"{field} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise SleeperArchiveAuditError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def player_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = snapshot.get("players", snapshot)
    if not isinstance(raw, dict):
        raise SleeperArchiveAuditError("snapshot must be a player-id keyed object or contain a players object")
    out: dict[str, dict[str, Any]] = {}
    for player_id, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        key = str(player_id).strip()
        if not key:
            continue
        out[key] = payload
    if not out:
        raise SleeperArchiveAuditError("snapshot contains no usable player records")
    return out


def _research_population(players: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    # LevLine is an NFL game model, not a fantasy model. Preserve every individual
    # player currently attached to an NFL team so OL/DL/LB/DB/special-teams state can
    # be studied alongside offensive skill positions. Team-defense pseudo players and
    # clearly retired records are excluded from the player-level population.
    relevant = {
        player_id: payload
        for player_id, payload in players.items()
        if str(payload.get("team") or "").strip()
        and str(payload.get("position") or "").upper() != "DEF"
        and str(payload.get("status") or "").lower() != "retired"
    }
    return relevant or players


def audit_snapshot(
    snapshot: dict[str, Any],
    *,
    commit_timestamp_utc: str,
    decision_timestamp_utc: str,
    resolved_player_ids: Iterable[str] | None = None,
    state_fields: Iterable[str] = DEFAULT_STATE_FIELDS,
) -> dict[str, Any]:
    commit_time = _parse_utc(commit_timestamp_utc, "commit_timestamp_utc")
    decision_time = _parse_utc(decision_timestamp_utc, "decision_timestamp_utc")
    players = player_map(snapshot)
    population = _research_population(players)
    fields = tuple(dict.fromkeys(str(field) for field in state_fields if str(field)))
    if not fields:
        raise SleeperArchiveAuditError("state_fields cannot be empty")

    field_metrics: dict[str, dict[str, float | int]] = {}
    denominator = len(population)
    for field in fields:
        present = sum(1 for payload in population.values() if field in payload)
        non_null = sum(1 for payload in population.values() if payload.get(field) not in (None, ""))
        field_metrics[field] = {
            "key_present_count": present,
            "key_present_rate": present / denominator,
            "non_null_count": non_null,
            "non_null_rate": non_null / denominator,
        }

    resolved = None
    identity_rate = None
    if resolved_player_ids is not None:
        resolved = {str(player_id) for player_id in resolved_player_ids}
        identity_rate = sum(1 for player_id in population if player_id in resolved) / denominator

    return {
        "schema_version": SCHEMA_VERSION,
        "technical_source_status": "VERIFIED",
        "commit_timestamp_utc": commit_time.isoformat().replace("+00:00", "Z"),
        "decision_timestamp_utc": decision_time.isoformat().replace("+00:00", "Z"),
        "point_in_time_safe": commit_time <= decision_time,
        "total_player_records": len(players),
        "research_population_records": denominator,
        "state_fields": field_metrics,
        "identity_resolution_rate": identity_rate,
        "identity_resolution_count": None if resolved is None else sum(1 for player_id in population if player_id in resolved),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcome_selection_authorized": False,
    }


def eligibility(
    audit: dict[str, Any],
    *,
    required_fields: Iterable[str],
    require_identity_resolution: bool = True,
) -> SnapshotEligibility:
    failures: list[str] = []
    if audit.get("technical_source_status") != "VERIFIED":
        failures.append("source_not_verified")
    if audit.get("point_in_time_safe") is not True:
        failures.append("snapshot_persisted_after_decision_time")

    metrics = audit.get("state_fields") or {}
    for field in required_fields:
        row = metrics.get(field)
        if not isinstance(row, dict):
            failures.append(f"missing_field_metric:{field}")
            continue
        if float(row.get("key_present_rate") or 0.0) < SCHEMA_PRESENCE_MIN_RATE:
            failures.append(f"schema_presence_below_99.5pct:{field}")

    if require_identity_resolution:
        rate = audit.get("identity_resolution_rate")
        if rate is None:
            failures.append("identity_resolution_not_measured")
        elif float(rate) < IDENTITY_MIN_RATE:
            failures.append("identity_resolution_below_99.5pct")

    return SnapshotEligibility(eligible=not failures, failures=tuple(failures))

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "levline-point-in-time-v1"
HORIZON_MINUTES = {
    "T-7d": 7 * 24 * 60,
    "T-72h": 72 * 60,
    "T-24h": 24 * 60,
    "T-6h": 6 * 60,
    "T-120m": 120,
    "T-60m": 60,
    "T-30m": 30,
}
RESEARCH_ONLY_HORIZONS = {"T-60m", "T-30m"}
REQUIRED_INPUT_FAMILIES = {
    "schedule",
    "market",
    "personnel",
    "weather",
    "football",
    "context",
}


class SnapshotValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SnapshotReceipt:
    snapshot_id: str
    game_id: str
    horizon: str
    retrieval_timestamp_utc: str
    content_sha256: str


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SnapshotValidationError(f"{field} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise SnapshotValidationError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _content_hash(payload_without_receipt: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload_without_receipt)).hexdigest()


def target_timestamp(kickoff_timestamp_utc: str, horizon: str) -> str:
    if horizon not in HORIZON_MINUTES:
        raise SnapshotValidationError(f"unsupported horizon: {horizon}")
    kickoff = _parse_utc(kickoff_timestamp_utc, "kickoff_timestamp_utc")
    target = kickoff - timedelta(minutes=HORIZON_MINUTES[horizon])
    return target.isoformat().replace("+00:00", "Z")


def build_snapshot(
    *,
    game_id: str,
    kickoff_timestamp_utc: str,
    horizon: str,
    retrieval_timestamp_utc: str,
    schedule_state: str,
    inputs: dict[str, Any],
    source_state: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    if not game_id:
        raise SnapshotValidationError("game_id is required")
    if horizon not in HORIZON_MINUTES:
        raise SnapshotValidationError(f"unsupported horizon: {horizon}")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "kickoff_timestamp_utc": kickoff_timestamp_utc,
        "horizon": horizon,
        "research_only": horizon in RESEARCH_ONLY_HORIZONS,
        "target_timestamp_utc": target_timestamp(kickoff_timestamp_utc, horizon),
        "retrieval_timestamp_utc": retrieval_timestamp_utc,
        "schedule_state": schedule_state,
        "inputs": inputs,
        "source_state": list(source_state),
    }
    validate_snapshot(payload)
    digest = _content_hash(payload)
    payload["receipt"] = {
        "content_sha256": digest,
        "snapshot_id": f"{game_id}__{horizon}__{digest[:20]}",
    }
    return payload


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotValidationError("unknown schema_version")
    if snapshot.get("horizon") not in HORIZON_MINUTES:
        raise SnapshotValidationError("unsupported horizon")
    if not snapshot.get("game_id"):
        raise SnapshotValidationError("game_id is required")
    if not snapshot.get("schedule_state"):
        raise SnapshotValidationError("schedule_state is required")

    kickoff = _parse_utc(snapshot["kickoff_timestamp_utc"], "kickoff_timestamp_utc")
    retrieval = _parse_utc(snapshot["retrieval_timestamp_utc"], "retrieval_timestamp_utc")
    target = _parse_utc(snapshot["target_timestamp_utc"], "target_timestamp_utc")
    expected_target = kickoff - timedelta(minutes=HORIZON_MINUTES[snapshot["horizon"]])
    if target != expected_target:
        raise SnapshotValidationError("target timestamp does not match kickoff/horizon")
    if retrieval >= kickoff:
        raise SnapshotValidationError("pregame snapshot retrieval must precede kickoff")

    inputs = snapshot.get("inputs")
    if not isinstance(inputs, dict):
        raise SnapshotValidationError("inputs must be an object")
    missing = REQUIRED_INPUT_FAMILIES - set(inputs)
    if missing:
        raise SnapshotValidationError(f"missing input families: {sorted(missing)}")

    source_state = snapshot.get("source_state")
    if not isinstance(source_state, list) or not source_state:
        raise SnapshotValidationError("source_state must contain at least one source record")
    source_ids: set[str] = set()
    for row in source_state:
        source_id = row.get("source_id")
        if not source_id or source_id in source_ids:
            raise SnapshotValidationError("source_state source_id values must be unique and non-empty")
        source_ids.add(source_id)
        observed = _parse_utc(row.get("retrieved_at_utc"), f"{source_id}.retrieved_at_utc")
        if observed > retrieval:
            raise SnapshotValidationError(f"{source_id} was retrieved after snapshot retrieval time")
        available = row.get("available_at_utc")
        if available:
            available_at = _parse_utc(available, f"{source_id}.available_at_utc")
            if available_at > retrieval:
                raise SnapshotValidationError(f"future-information leakage from {source_id}")
        if "quality" not in row or "status" not in row:
            raise SnapshotValidationError(f"{source_id} must include status and quality")

    expected_research_only = snapshot["horizon"] in RESEARCH_ONLY_HORIZONS
    if snapshot.get("research_only") is not expected_research_only:
        raise SnapshotValidationError("research_only flag disagrees with horizon policy")

    receipt = snapshot.get("receipt")
    if receipt is not None:
        without_receipt = dict(snapshot)
        without_receipt.pop("receipt", None)
        digest = _content_hash(without_receipt)
        if receipt.get("content_sha256") != digest:
            raise SnapshotValidationError("snapshot content hash mismatch")
        expected_id = f"{snapshot['game_id']}__{snapshot['horizon']}__{digest[:20]}"
        if receipt.get("snapshot_id") != expected_id:
            raise SnapshotValidationError("snapshot_id mismatch")


def append_snapshot_jsonl(path: Path, snapshot: dict[str, Any]) -> SnapshotReceipt:
    validate_snapshot(snapshot)
    receipt = snapshot.get("receipt")
    if not receipt:
        raise SnapshotValidationError("snapshot must be built with build_snapshot before persistence")

    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    existing_slots: set[tuple[str, str, str]] = set()
    if path.exists():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                previous = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SnapshotValidationError(f"corrupt append-only store at line {line_number}") from exc
            validate_snapshot(previous)
            existing_ids.add(previous["receipt"]["snapshot_id"])
            existing_slots.add((previous["game_id"], previous["horizon"], previous["retrieval_timestamp_utc"]))

    snapshot_id = receipt["snapshot_id"]
    if snapshot_id in existing_ids:
        raise SnapshotValidationError("duplicate snapshot_id")
    slot = (snapshot["game_id"], snapshot["horizon"], snapshot["retrieval_timestamp_utc"])
    if slot in existing_slots:
        raise SnapshotValidationError("duplicate game/horizon/retrieval slot")

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        handle.write("\n")

    return SnapshotReceipt(
        snapshot_id=snapshot_id,
        game_id=snapshot["game_id"],
        horizon=snapshot["horizon"],
        retrieval_timestamp_utc=snapshot["retrieval_timestamp_utc"],
        content_sha256=receipt["content_sha256"],
    )

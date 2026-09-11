from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.sleeper_archive_audit_v1 import audit_snapshot, player_map


SCHEMA_VERSION = "levline-sleeper-player-state-v1"
SOURCE_REPOSITORY = "edgecdec/declan-fantasy-football"
SOURCE_PATH = "data/sleeper_players.json"
CORE_FIELDS = {
    "player_id",
    "full_name",
    "first_name",
    "last_name",
    "team",
    "position",
    "status",
    "active",
    "number",
    "age",
    "years_exp",
    "gsis_id",
    "espn_id",
    "yahoo_id",
    "rotowire_id",
    "fantasy_data_id",
    "sportradar_id",
    "pff_id",
}
STATE_PREFIXES = ("injury", "practice", "depth_chart")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def state_fields_for_record(record: dict[str, Any]) -> set[str]:
    return {
        str(key)
        for key in record
        if str(key) in CORE_FIELDS or str(key).startswith(STATE_PREFIXES)
    }


def slim_player_state(snapshot: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    players = player_map(snapshot)
    discovered: set[str] = set()
    out: dict[str, dict[str, Any]] = {}
    for player_id, record in players.items():
        team = str(record.get("team") or "").strip()
        status = str(record.get("status") or "").lower()
        position = str(record.get("position") or "").upper()
        if not team or status == "retired" or position == "DEF":
            continue
        fields = state_fields_for_record(record)
        discovered.update(fields)
        slim = {field: record.get(field) for field in sorted(fields)}
        slim["player_id"] = player_id
        out[player_id] = slim
    if not out:
        raise ValueError("no team-assigned player records remain after slimming")
    return out, sorted(discovered | {"player_id"})


def build_capture(
    snapshot: dict[str, Any],
    *,
    source_commit_sha: str,
    source_commit_timestamp_utc: str,
    retrieval_timestamp_utc: str,
) -> dict[str, Any]:
    commit_time = _parse_utc(source_commit_timestamp_utc)
    retrieval_time = _parse_utc(retrieval_timestamp_utc)
    if commit_time > retrieval_time:
        raise ValueError("source commit timestamp cannot be after retrieval time")

    players, fields = slim_player_state(snapshot)
    audit = audit_snapshot(
        {"players": players},
        commit_timestamp_utc=commit_time.isoformat(),
        decision_timestamp_utc=retrieval_time.isoformat(),
        resolved_player_ids=None,
        state_fields=[field for field in fields if field != "player_id"],
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_repository": SOURCE_REPOSITORY,
        "source_path": SOURCE_PATH,
        "source_commit_sha": source_commit_sha,
        "source_commit_timestamp_utc": commit_time.isoformat().replace("+00:00", "Z"),
        "retrieval_timestamp_utc": retrieval_time.isoformat().replace("+00:00", "Z"),
        "availability_bound": "source_git_commit_time",
        "fields": fields,
        "audit": audit,
        "players": players,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcome_selection_authorized": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def capture_filename(payload: dict[str, Any]) -> str:
    stamp = str(payload["source_commit_timestamp_utc"]).replace("-", "").replace(":", "")
    commit = str(payload["source_commit_sha"])[:12]
    return f"{stamp}__{commit}.json.gz"


def write_capture(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as handle:
            handle.write(encoded)


def read_capture(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))

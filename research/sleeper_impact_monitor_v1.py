from __future__ import annotations

"""Convert verified Sleeper archive captures into research-only Impact Monitor context.

This module consumes only point-in-time player-state snapshots already qualified by the
Sleeper archive pipeline. It creates no player-value estimate and cannot move LevLine
probabilities. Its purpose is to give research/UX layers stable all-position availability
state and auditable state-change events while a prospective 2026 history accumulates.
"""

import argparse
import csv
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from nfl_forecast.player_impact_monitor import build_impact_monitor_payload
from research.sleeper_archive_capture_v1 import SCHEMA_VERSION, SOURCE_REPOSITORY

SOURCE_NAME = "Verified Sleeper player-state archive"
SOURCE_URL = f"https://github.com/{SOURCE_REPOSITORY}"
CHANGE_FIELDS = (
    "team",
    "position",
    "status",
    "active",
    "injury_status",
    "practice_participation",
    "practice_description",
    "depth_chart_position",
    "depth_chart_order",
)
HEALTHY_INJURY_VALUES = {"", "none", "null", "healthy"}
FULL_PRACTICE_VALUES = {"", "full", "full participation"}
ACTIVE_STATUS_VALUES = {"", "active"}


def _parse_utc(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _canonical_capture_hash(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("content_sha256", None)
    raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_capture_for_decision(
    capture: dict[str, Any],
    *,
    decision_timestamp_utc: str,
) -> dict[str, Any]:
    if capture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected Sleeper archive capture schema")
    if capture.get("source_repository") != SOURCE_REPOSITORY:
        raise ValueError("unexpected Sleeper archive source repository")
    if capture.get("research_only") is not True or capture.get("production_authorized") is not False:
        raise ValueError("Sleeper archive capture must remain research-only")
    if not isinstance(capture.get("players"), dict) or not capture["players"]:
        raise ValueError("Sleeper archive capture has no player state")
    expected_hash = str(capture.get("content_sha256") or "")
    actual_hash = _canonical_capture_hash(capture)
    if not expected_hash or expected_hash != actual_hash:
        raise ValueError("Sleeper archive capture content hash mismatch")

    commit_time = _parse_utc(capture.get("source_commit_timestamp_utc"))
    decision_time = _parse_utc(decision_timestamp_utc)
    if commit_time > decision_time:
        raise ValueError("Sleeper archive capture was not available by the decision time")
    audit = capture.get("audit") or {}
    if audit.get("point_in_time_safe") is not True:
        raise ValueError("Sleeper archive capture did not pass point-in-time audit")
    return {
        "source_commit_timestamp_utc": commit_time.isoformat().replace("+00:00", "Z"),
        "decision_timestamp_utc": decision_time.isoformat().replace("+00:00", "Z"),
        "source_commit_sha": str(capture.get("source_commit_sha") or ""),
        "content_sha256": actual_hash,
        "player_count": len(capture["players"]),
    }


def _schedule_lookup(
    rows: Iterable[dict[str, Any]],
    *,
    season: int,
    week: int,
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in rows:
        try:
            row_season = int(float(str(row.get("season"))))
            row_week = int(float(str(row.get("week"))))
        except (TypeError, ValueError):
            continue
        if row_season != int(season) or row_week != int(week):
            continue
        game_id = str(row.get("game_id") or "").strip()
        if not game_id:
            continue
        for key in ("home_team", "away_team"):
            team = str(row.get(key) or "").strip()
            if not team:
                continue
            if team in lookup and lookup[team] != game_id:
                raise ValueError(f"multiple schedule games found for {team}")
            lookup[team] = game_id
    if not lookup:
        raise ValueError(f"no schedule games found for {season} week {week}")
    return lookup


def _clean(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _clean(value).lower()


def _requires_attention(record: dict[str, Any]) -> bool:
    if record.get("active") is False:
        return True
    if _lower(record.get("status")) not in ACTIVE_STATUS_VALUES:
        return True
    if _lower(record.get("injury_status")) not in HEALTHY_INJURY_VALUES:
        return True
    if _lower(record.get("practice_participation")) not in FULL_PRACTICE_VALUES:
        return True
    return False


def _practice_status(record: dict[str, Any]) -> str | None:
    value = _clean(record.get("practice_participation"))
    if value:
        return value
    description = _clean(record.get("practice_description"))
    return description or None


def _game_status(record: dict[str, Any]) -> str | None:
    injury = _clean(record.get("injury_status"))
    if injury and injury.lower() not in HEALTHY_INJURY_VALUES:
        return injury
    status = _clean(record.get("status"))
    if status and status.lower() not in ACTIVE_STATUS_VALUES:
        return status
    if record.get("active") is False:
        return "Inactive"
    return None


def build_qualified_availability_cards(
    capture: dict[str, Any],
    schedule_rows: Iterable[dict[str, Any]],
    *,
    season: int,
    week: int,
    decision_timestamp_utc: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    verification = validate_capture_for_decision(
        capture,
        decision_timestamp_utc=decision_timestamp_utc,
    )
    games = _schedule_lookup(schedule_rows, season=season, week=week)
    cards: list[dict[str, Any]] = []
    skipped_no_game = 0
    skipped_healthy = 0
    fallback_ids = 0
    positions: dict[str, int] = {}

    for archive_id, raw_record in capture["players"].items():
        if not isinstance(raw_record, dict):
            raise ValueError("Sleeper archive player state must be an object")
        team = _clean(raw_record.get("team"))
        if team not in games:
            skipped_no_game += 1
            continue
        if not _requires_attention(raw_record):
            skipped_healthy += 1
            continue
        player_name = _clean(raw_record.get("full_name")) or "Unknown player"
        position = _clean(raw_record.get("position")).upper() or "UNK"
        gsis_id = _clean(raw_record.get("gsis_id"))
        stable_id = gsis_id or f"sleeper:{archive_id}"
        if not gsis_id:
            fallback_ids += 1
        positions[position] = positions.get(position, 0) + 1
        missing_fields = []
        if not gsis_id:
            missing_fields.append("gsis_id")

        cards.append(
            {
                "schema_version": 1,
                "research_only": True,
                "game_id": games[team],
                "team": team,
                "player_id": stable_id,
                "player_name": player_name,
                "position": position,
                "observed_statistics": [],
                "levline_impacts": [],
                "availability": {
                    "practice_status": _practice_status(raw_record),
                    "game_status": _game_status(raw_record),
                    "source_status": "qualified",
                    "source_name": SOURCE_NAME,
                    "source_url": SOURCE_URL,
                    "source_data_as_of": verification["source_commit_timestamp_utc"],
                },
                "data_quality": {
                    "identity_confidence": "stable_id",
                    "coverage_status": "qualified_2026_point_in_time_player_state",
                    "missing_fields": missing_fields,
                    "identity_method": "gsis_id" if gsis_id else "sleeper_player_id",
                    "archive_player_id": str(archive_id),
                    "availability_bound": "source_git_commit_time",
                    "source_commit_sha": verification["source_commit_sha"],
                    "source_content_sha256": verification["content_sha256"],
                    "depth_chart_position": raw_record.get("depth_chart_position"),
                    "depth_chart_order": raw_record.get("depth_chart_order"),
                },
            }
        )

    audit = {
        **verification,
        "season": int(season),
        "week": int(week),
        "games_in_scope": len(set(games.values())),
        "qualified_cards": len(cards),
        "cards_by_position": dict(sorted(positions.items())),
        "fallback_sleeper_ids": fallback_ids,
        "skipped_players_without_schedule_game": skipped_no_game,
        "skipped_healthy_players": skipped_healthy,
        "probability_feature_authorized": False,
        "modeled_player_impacts_created": 0,
        "completed_2026_outcomes_used": 0,
    }
    return cards, audit


def build_state_change_events(
    previous_capture: dict[str, Any],
    current_capture: dict[str, Any],
    *,
    decision_timestamp_utc: str,
) -> list[dict[str, Any]]:
    previous = validate_capture_for_decision(
        previous_capture, decision_timestamp_utc=decision_timestamp_utc
    )
    current = validate_capture_for_decision(
        current_capture, decision_timestamp_utc=decision_timestamp_utc
    )
    if _parse_utc(previous["source_commit_timestamp_utc"]) > _parse_utc(current["source_commit_timestamp_utc"]):
        raise ValueError("previous Sleeper capture is newer than current capture")

    prior_players = previous_capture["players"]
    events: list[dict[str, Any]] = []
    for archive_id, current_record in current_capture["players"].items():
        prior_record = prior_players.get(archive_id)
        if not isinstance(prior_record, dict) or not isinstance(current_record, dict):
            continue
        changes: dict[str, dict[str, Any]] = {}
        for field in CHANGE_FIELDS:
            before = prior_record.get(field)
            after = current_record.get(field)
            if before != after:
                changes[field] = {"before": before, "after": after}
        if not changes:
            continue
        events.append(
            {
                "archive_player_id": str(archive_id),
                "player_id": _clean(current_record.get("gsis_id")) or f"sleeper:{archive_id}",
                "player_name": _clean(current_record.get("full_name")) or "Unknown player",
                "team": _clean(current_record.get("team")),
                "position": _clean(current_record.get("position")).upper(),
                "changed_fields": changes,
                "previous_source_commit_timestamp_utc": previous["source_commit_timestamp_utc"],
                "current_source_commit_timestamp_utc": current["source_commit_timestamp_utc"],
                "research_only": True,
                "probability_feature_authorized": False,
            }
        )
    events.sort(key=lambda row: (row["team"], row["position"], row["player_name"]))
    return events


def build_monitor_payload(
    capture: dict[str, Any],
    schedule_rows: list[dict[str, Any]],
    *,
    season: int,
    week: int,
    decision_timestamp_utc: str,
    previous_capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cards, audit = build_qualified_availability_cards(
        capture,
        schedule_rows,
        season=season,
        week=week,
        decision_timestamp_utc=decision_timestamp_utc,
    )
    payload = build_impact_monitor_payload(cards, generated_utc=decision_timestamp_utc)
    payload["capture_audit"] = audit
    payload["state_changes"] = (
        build_state_change_events(
            previous_capture,
            capture,
            decision_timestamp_utc=decision_timestamp_utc,
        )
        if previous_capture is not None
        else []
    )
    payload["source_scope"] = "verified_2026_sleeper_archive_all_positions"
    payload["live_site_consumes_this_file"] = False
    return payload


def _read_capture(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rb") as handle:
        payload = json.loads(handle.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("capture must be a JSON object")
    return payload


def _read_schedule(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _infer_scope(rows: list[dict[str, Any]]) -> tuple[int, int]:
    scopes: set[tuple[int, int]] = set()
    for row in rows:
        try:
            scopes.add((int(float(str(row["season"]))), int(float(str(row["week"])))))
        except (KeyError, TypeError, ValueError):
            continue
    if len(scopes) != 1:
        raise ValueError(f"schedule must contain exactly one season/week scope; found {sorted(scopes)}")
    return next(iter(scopes))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--previous-capture", type=Path)
    parser.add_argument("--schedule", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decision-time")
    args = parser.parse_args()

    schedule_rows = _read_schedule(args.schedule)
    season, week = _infer_scope(schedule_rows)
    decision = args.decision_time or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = build_monitor_payload(
        _read_capture(args.capture),
        schedule_rows,
        season=season,
        week=week,
        decision_timestamp_utc=decision,
        previous_capture=_read_capture(args.previous_capture) if args.previous_capture else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload["capture_audit"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

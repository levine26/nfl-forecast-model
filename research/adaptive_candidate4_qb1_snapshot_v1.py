from __future__ import annotations

"""Prospective T-120 QB1 identity capture for Adaptive Candidate 4.

This module freezes each Week 3+ Sunday team's QB1 from nflverse depth-chart state during
the one-sided T-120 capture window. Later Candidate 4 QB-shock construction consumes only
this immutable snapshot rather than re-querying depth charts after T-60.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from research.adaptive_candidate4_qb_shock_v1 import select_t120_qb1

SCHEMA_VERSION = "adaptive-candidate4-qb1-t120-snapshot-v1"
CANDIDATE_ID = "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1"
PREREGISTRATION_SHA = "74ecd303545c09f57593546472d27438e3d8a204"
CAPTURE_TOLERANCE_MINUTES = 7.5


EASTERN = ZoneInfo("America/New_York")


def _kickoff_from_feed(raw: dict[str, Any]) -> datetime | None:
    explicit = _utc(raw.get("kickoff_utc"))
    if explicit is not None:
        return explicit
    gameday = str(raw.get("gameday") or "")[:10]
    gametime = str(raw.get("gametime") or "")[:5]
    if not gameday or not gametime:
        return None
    try:
        local = datetime.strptime(f"{gameday} {gametime}", "%Y-%m-%d %H:%M").replace(
            tzinfo=EASTERN
        )
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


def _utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def due_t120_games(
    feed: pd.DataFrame,
    *,
    now_utc: datetime,
    existing_game_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    existing = existing_game_ids or set()
    now = now_utc.astimezone(timezone.utc)
    output: list[dict[str, Any]] = []
    for raw in feed.to_dict("records"):
        try:
            season = int(raw.get("season"))
            week = int(raw.get("week"))
            gameday = datetime.fromisoformat(str(raw.get("gameday"))[:10])
        except (TypeError, ValueError):
            continue
        if season != 2026 or week < 3 or gameday.weekday() != 6:
            continue
        game_id = str(raw.get("game_id") or "").strip()
        if not game_id or game_id in existing:
            continue
        kickoff = _kickoff_from_feed(raw)
        if kickoff is None:
            continue
        target = kickoff - timedelta(minutes=120)
        error = (now - target).total_seconds() / 60.0
        if not (-CAPTURE_TOLERANCE_MINUTES <= error <= 0.0):
            continue
        output.append(
            {
                "game_id": game_id,
                "season": season,
                "week": week,
                "gameday": str(raw.get("gameday")),
                "away_team": str(raw.get("away_team") or "").strip().upper(),
                "home_team": str(raw.get("home_team") or "").strip().upper(),
                "kickoff_utc": _iso(kickoff),
                "t120_target_utc": _iso(target),
                "capture_timing_error_minutes": error,
            }
        )
    return sorted(output, key=lambda row: row["game_id"])


def build_t120_qb1_snapshots(
    depth: pd.DataFrame,
    games: list[dict[str, Any]],
    *,
    captured_at_utc: datetime,
    nflreadpy_version: str,
) -> pd.DataFrame:
    captured = captured_at_utc.astimezone(timezone.utc)
    rows: list[dict[str, Any]] = []

    for game in games:
        kickoff = _utc(game.get("kickoff_utc"))
        target = _utc(game.get("t120_target_utc"))
        if kickoff is None or target is None:
            raise ValueError("game lacks valid kickoff/T-120 timestamps")
        if captured > target:
            raise ValueError("T-120 QB1 snapshot capture cannot occur after target")
        error = (captured - target).total_seconds() / 60.0
        if error < -CAPTURE_TOLERANCE_MINUTES or error > 0:
            raise ValueError("T-120 QB1 snapshot capture outside one-sided tolerance")

        home, home_reasons = select_t120_qb1(
            depth,
            team=str(game.get("home_team") or ""),
            kickoff_utc=kickoff,
        )
        away, away_reasons = select_t120_qb1(
            depth,
            team=str(game.get("away_team") or ""),
            kickoff_utc=kickoff,
        )
        reasons = [f"home_{x}" for x in home_reasons] + [f"away_{x}" for x in away_reasons]

        for side, qb in (("home", home), ("away", away)):
            if qb is None:
                continue
            source_time = _utc(qb.get("depth_timestamp_utc"))
            if source_time is None or source_time > captured:
                reasons.append(f"{side}_depth_state_not_observed_by_capture")

        complete = not reasons
        record = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": CANDIDATE_ID,
            "preregistration_sha": PREREGISTRATION_SHA,
            "game_id": str(game["game_id"]),
            "season": int(game["season"]),
            "week": int(game["week"]),
            "gameday": str(game["gameday"]),
            "home_team": str(game["home_team"]),
            "away_team": str(game["away_team"]),
            "kickoff_utc": _iso(kickoff),
            "t120_target_utc": _iso(target),
            "captured_at_utc": _iso(captured),
            "capture_timing_error_minutes": error,
            "home_t120_qb1_player_name": home["player_name"] if home else None,
            "home_t120_qb1_gsis_id": home["gsis_id"] if home else None,
            "home_t120_depth_timestamp_utc": home["depth_timestamp_utc"] if home else None,
            "away_t120_qb1_player_name": away["player_name"] if away else None,
            "away_t120_qb1_gsis_id": away["gsis_id"] if away else None,
            "away_t120_depth_timestamp_utc": away["depth_timestamp_utc"] if away else None,
            "qb1_snapshot_complete": bool(complete),
            "incomplete_reasons": "|".join(sorted(set(reasons))),
            "source": "nflverse_depth_charts_via_nflreadpy",
            "nflreadpy_version": str(nflreadpy_version),
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        basis = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        record["qb1_snapshot_sha256"] = hashlib.sha256(basis.encode("utf-8")).hexdigest()
        rows.append(record)
    return pd.DataFrame(rows)


def append_immutable_snapshots(
    existing: pd.DataFrame | None,
    new_rows: pd.DataFrame,
) -> pd.DataFrame:
    if existing is None or existing.empty:
        return new_rows.copy().reset_index(drop=True)
    required = {"game_id", "qb1_snapshot_sha256"}
    if not required.issubset(existing.columns):
        raise ValueError("existing QB1 snapshot ledger lacks immutable identity fields")
    if existing["game_id"].astype(str).duplicated().any():
        raise ValueError("existing QB1 snapshot ledger has duplicate game_id")

    out = existing.copy()
    known = {
        str(row["game_id"]): str(row["qb1_snapshot_sha256"])
        for row in out.to_dict("records")
    }
    additions: list[dict[str, Any]] = []
    for row in new_rows.to_dict("records"):
        game_id = str(row["game_id"])
        digest = str(row["qb1_snapshot_sha256"])
        if game_id in known:
            if known[game_id] != digest:
                raise ValueError(f"immutable Candidate 4 T-120 QB1 snapshot rewrite attempted for {game_id}")
            continue
        additions.append(row)
        known[game_id] = digest
    if additions:
        out = pd.concat([out, pd.DataFrame(additions)], ignore_index=True, sort=False)
    return out.reset_index(drop=True)

from __future__ import annotations

"""Outcome-blind health audit for preregistered LevLine 4 market horizons.

A missed exact-horizon capture remains missing. This module never backfills a missed
T-minus state with a later market price; it only records whether each scheduled
(game, horizon) observation is not yet open, currently open, captured under the
strict PIT contract, or irretrievably missed.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any

from research.market_capture_contract_v2 import MIN_CONSENSUS_BOOKS, QUALIFYING_CLOSE_ROW_TYPE
from research.market_capture_due_v2 import kickoff_utc
from research.market_capture_v2 import CAPTURE_TOLERANCE_MINUTES, HORIZONS

SCHEMA_VERSION = "levline4-market-capture-health-v1"


def _utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _slate_targets(slate_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    targets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in slate_rows:
        game_id = str(row.get("game_id") or "").strip()
        if not game_id:
            continue
        try:
            kickoff = kickoff_utc(str(row.get("gameday") or ""), str(row.get("gametime") or ""))
        except Exception:
            continue
        for horizon, minutes in HORIZONS.items():
            key = (game_id, horizon)
            if key in targets:
                raise ValueError(f"duplicate slate horizon identity: {key}")
            targets[key] = {
                "game_id": game_id,
                "home_team": str(row.get("home_team") or ""),
                "away_team": str(row.get("away_team") or ""),
                "kickoff_timestamp_utc": kickoff,
                "horizon": horizon,
                "target_timestamp_utc": kickoff - timedelta(minutes=minutes),
            }
    return targets


def _strict_capture_rows(
    ledger_rows: list[dict[str, Any]],
    targets: dict[tuple[str, str], dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    valid: dict[tuple[str, str], dict[str, Any]] = {}
    for row in ledger_rows:
        if str(row.get("row_type") or "") != QUALIFYING_CLOSE_ROW_TYPE:
            continue
        game_id = str(row.get("game_id") or "").strip()
        horizon = str(row.get("horizon") or "").strip()
        key = (game_id, horizon)
        expected = targets.get(key)
        if expected is None:
            continue
        source_count = _number(row.get("source_count"))
        probability = _number(row.get("h2h_home_no_vig"))
        request = _utc(row.get("request_timestamp_utc"))
        recorded_target = _utc(row.get("target_timestamp_utc"))
        if source_count is None or source_count < MIN_CONSENSUS_BOOKS:
            continue
        if probability is None or not 0.0 < probability < 1.0:
            continue
        if request is None or recorded_target is None:
            continue
        expected_target = expected["target_timestamp_utc"]
        if abs((recorded_target - expected_target).total_seconds()) > 1.0:
            continue
        computed_error = (request - expected_target).total_seconds() / 60.0
        if not (-CAPTURE_TOLERANCE_MINUTES <= computed_error <= 0.0):
            continue
        recorded_error = _number(row.get("timing_error_minutes"))
        if recorded_error is None or abs(recorded_error - computed_error) > (1.0 / 60.0):
            continue
        if request >= expected["kickoff_timestamp_utc"]:
            continue

        previous = valid.get(key)
        if previous is None or request < previous["request_timestamp_utc"]:
            valid[key] = {
                "request_timestamp_utc": request,
                "timing_error_minutes": computed_error,
                "source_count": int(source_count),
                "source_names": str(row.get("source_names") or ""),
            }
    return valid


def build_capture_health(
    slate_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
    *,
    now_utc: datetime | str | None = None,
) -> dict[str, Any]:
    now = _utc(now_utc) if now_utc is not None else datetime.now(timezone.utc)
    if now is None:
        raise ValueError("now_utc must be a valid timezone-aware timestamp")

    targets = _slate_targets(slate_rows)
    captured = _strict_capture_rows(ledger_rows, targets)
    rows: list[dict[str, Any]] = []
    counts = {
        "not_yet_open": 0,
        "window_open": 0,
        "captured_qualified": 0,
        "missed_window": 0,
    }

    for key in sorted(targets, key=lambda item: (targets[item]["target_timestamp_utc"], item[0], item[1])):
        target = targets[key]
        target_at = target["target_timestamp_utc"]
        window_opens = target_at - timedelta(minutes=CAPTURE_TOLERANCE_MINUTES)
        capture = captured.get(key)
        if capture is not None:
            status = "captured_qualified"
        elif now < window_opens:
            status = "not_yet_open"
        elif now <= target_at:
            status = "window_open"
        else:
            status = "missed_window"
        counts[status] += 1

        rows.append(
            {
                "game_id": target["game_id"],
                "home_team": target["home_team"],
                "away_team": target["away_team"],
                "horizon": target["horizon"],
                "kickoff_timestamp_utc": target["kickoff_timestamp_utc"].isoformat(),
                "target_timestamp_utc": target_at.isoformat(),
                "window_opens_utc": window_opens.isoformat(),
                "status": status,
                "captured_request_timestamp_utc": (
                    capture["request_timestamp_utc"].isoformat() if capture else None
                ),
                "captured_timing_error_minutes": (
                    capture["timing_error_minutes"] if capture else None
                ),
                "captured_source_count": capture["source_count"] if capture else None,
                "late_backfill_authorized": False,
            }
        )

    closed = counts["captured_qualified"] + counts["missed_window"]
    success_rate = counts["captured_qualified"] / closed if closed else None
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": now.isoformat(),
        "strict_window_minutes": [-CAPTURE_TOLERANCE_MINUTES, 0.0],
        "scheduled_game_horizons": len(rows),
        "counts": counts,
        "closed_window_capture_success_rate": success_rate,
        "rows": rows,
        "missed_horizon_ids": [
            f"{row['game_id']}:{row['horizon']}" for row in rows if row["status"] == "missed_window"
        ],
        "missingness_policy": "missed_horizon_remains_missing_no_late_backfill",
        "outcome_blind": True,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "research_only": True,
        "production_authorized": False,
        "promotion_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("research_outputs/market_capture_v2/market_snapshots.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research_outputs/market_capture_v2/capture_health.json"),
    )
    parser.add_argument("--now-utc", default=None)
    args = parser.parse_args()

    receipt = build_capture_health(
        _read_csv(args.slate),
        _read_csv(args.ledger),
        now_utc=args.now_utc,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

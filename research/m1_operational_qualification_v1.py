from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from research.m1_market_capture_due_v1 import kickoff_utc
from research.m1_market_contract_v1 import (
    ALL_FIXED_HORIZONS,
    CAPTURE_TOLERANCE_MINUTES,
    DIAGNOSTIC_HORIZONS,
    LATEST_PREKICK,
    LATEST_PREKICK_SAFETY_MINUTES,
    LATEST_PREKICK_WINDOW_MINUTES,
    MIN_COMPLETE_BOOKS,
    PREDICTOR_HORIZONS,
    PROGRAM_ID,
)

# Operational boundary only. This is the merge timestamp of the Phase-2 opening
# receipt and does not alter the frozen M1 feature, timing, or eligibility identity.
PHASE2_OPENED_AT_UTC = datetime(2026, 9, 25, 16, 35, 6, tzinfo=timezone.utc)

FIXED_HORIZON_STATES = {
    "pre_phase2_boundary",
    "future",
    "capture_window_open",
    "captured",
    "missed_no_valid_capture",
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _captured_pairs(ledger_path: Path) -> set[tuple[str, str]]:
    """Return only M1-qualified consensus captures; raw/partial rows do not close a horizon."""
    if not ledger_path.exists() or ledger_path.stat().st_size == 0:
        return set()
    result: set[tuple[str, str]] = set()
    try:
        with ledger_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("row_type") or "") != "consensus":
                    continue
                if str(row.get("m1_role") or "") not in {"predictor", "diagnostic_only"}:
                    continue
                count = _safe_float(row.get("source_count"))
                if count is None or count < MIN_COMPLETE_BOOKS:
                    continue
                game_id = str(row.get("game_id") or "").strip()
                horizon = str(row.get("horizon") or "").strip()
                if game_id and horizon:
                    result.add((game_id, horizon))
    except (OSError, csv.Error):
        return set()
    return result


def _fixed_state(
    *,
    target_utc: datetime,
    now_utc: datetime,
    phase2_opened_at_utc: datetime,
    captured: bool,
) -> str:
    if target_utc <= phase2_opened_at_utc:
        return "pre_phase2_boundary"
    if captured:
        return "captured"
    window_start = target_utc - timedelta(minutes=CAPTURE_TOLERANCE_MINUTES)
    if now_utc < window_start:
        return "future"
    if now_utc <= target_utc:
        return "capture_window_open"
    return "missed_no_valid_capture"


def _latest_state(
    *,
    kickoff_timestamp_utc: datetime,
    now_utc: datetime,
    phase2_opened_at_utc: datetime,
    captured: bool,
) -> str:
    if kickoff_timestamp_utc <= phase2_opened_at_utc:
        return "pre_phase2_boundary"
    if captured:
        return "captured"
    window_start = kickoff_timestamp_utc - timedelta(minutes=LATEST_PREKICK_WINDOW_MINUTES)
    window_end = kickoff_timestamp_utc - timedelta(minutes=LATEST_PREKICK_SAFETY_MINUTES)
    if now_utc < window_start:
        return "future"
    if now_utc <= window_end:
        return "capture_window_open"
    return "missed_no_valid_capture"


def qualification_rows(
    *,
    slate_path: Path,
    ledger_path: Path,
    now_utc: datetime,
    phase2_opened_at_utc: datetime = PHASE2_OPENED_AT_UTC,
) -> list[dict[str, Any]]:
    """Build an outcome-blind horizon-state table from schedule identity plus M1 capture evidence."""
    now = _as_utc(now_utc)
    opened = _as_utc(phase2_opened_at_utc)
    captured_pairs = _captured_pairs(ledger_path)
    if not slate_path.exists() or slate_path.stat().st_size == 0:
        return []

    rows: list[dict[str, Any]] = []
    with slate_path.open(newline="", encoding="utf-8") as handle:
        for source in csv.DictReader(handle):
            # Intentionally consume only schedule/identity fields. Outcome-bearing columns,
            # even if present on the source row, are never read into the qualification artifact.
            game_id = str(source.get("game_id") or "").strip()
            home_team = str(source.get("home_team") or "").strip()
            away_team = str(source.get("away_team") or "").strip()
            if not game_id:
                continue
            try:
                kickoff = kickoff_utc(source.get("gameday"), source.get("gametime"))
            except Exception:
                continue

            for horizon, minutes in ALL_FIXED_HORIZONS.items():
                target = kickoff - timedelta(minutes=minutes)
                state = _fixed_state(
                    target_utc=target,
                    now_utc=now,
                    phase2_opened_at_utc=opened,
                    captured=(game_id, horizon) in captured_pairs,
                )
                rows.append(
                    {
                        "game_id": game_id,
                        "away_team": away_team,
                        "home_team": home_team,
                        "kickoff_timestamp_utc": kickoff.isoformat(),
                        "horizon": horizon,
                        "role": "predictor" if horizon in PREDICTOR_HORIZONS else "diagnostic_only",
                        "target_timestamp_utc": target.isoformat(),
                        "phase2_eligible": target > opened,
                        "state": state,
                        "capture_tolerance_minutes": CAPTURE_TOLERANCE_MINUTES,
                        "minimum_complete_books": MIN_COMPLETE_BOOKS,
                        "completed_2026_outcomes_used": 0,
                    }
                )

            latest_state = _latest_state(
                kickoff_timestamp_utc=kickoff,
                now_utc=now,
                phase2_opened_at_utc=opened,
                captured=(game_id, LATEST_PREKICK) in captured_pairs,
            )
            rows.append(
                {
                    "game_id": game_id,
                    "away_team": away_team,
                    "home_team": home_team,
                    "kickoff_timestamp_utc": kickoff.isoformat(),
                    "horizon": LATEST_PREKICK,
                    "role": "diagnostic_only",
                    "target_timestamp_utc": kickoff.isoformat(),
                    "phase2_eligible": kickoff > opened,
                    "state": latest_state,
                    "capture_tolerance_minutes": None,
                    "minimum_complete_books": MIN_COMPLETE_BOOKS,
                    "completed_2026_outcomes_used": 0,
                }
            )

    return sorted(rows, key=lambda row: (row["target_timestamp_utc"], row["game_id"], row["horizon"]))


def qualification_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed = [row for row in rows if row["horizon"] in ALL_FIXED_HORIZONS]
    eligible_fixed = [row for row in fixed if bool(row["phase2_eligible"])]
    counts = Counter(str(row["state"]) for row in eligible_fixed)
    diagnostic_rows = [row for row in rows if row["role"] == "diagnostic_only"]
    predictor_rows = [row for row in rows if row["role"] == "predictor"]
    return {
        "program_id": PROGRAM_ID,
        "phase": "PROSPECTIVE PHASE 2 — LIVE ACCUMULATION AND OPERATIONAL QUALIFICATION",
        "status": "operational_attention_required" if counts.get("missed_no_valid_capture", 0) else "accumulating",
        "phase2_opened_at_utc": PHASE2_OPENED_AT_UTC.isoformat(),
        "frozen_capture_tolerance_minutes": CAPTURE_TOLERANCE_MINUTES,
        "minimum_complete_books": MIN_COMPLETE_BOOKS,
        "fixed_predictor_horizons": list(PREDICTOR_HORIZONS),
        "fixed_diagnostic_horizons": list(DIAGNOSTIC_HORIZONS),
        "latest_prekick_role": "diagnostic_only",
        "phase2_eligible_fixed_horizons": len(eligible_fixed),
        "qualification_state_counts": dict(sorted(counts.items())),
        "captured_fixed_horizons": counts.get("captured", 0),
        "missed_fixed_horizons": counts.get("missed_no_valid_capture", 0),
        "capture_windows_currently_open": counts.get("capture_window_open", 0),
        "predictor_rows_tracked": len(predictor_rows),
        "diagnostic_rows_tracked": len(diagnostic_rows),
        "diagnostic_horizons_physically_excluded_from_predictor_registry": True,
        "historical_or_completed_game_outcomes_read": False,
        "completed_2026_outcomes_used": 0,
        "research_only": True,
        "production_authorized": False,
        "production_changed": False,
    }


def write_qualification_artifacts(
    *,
    slate_path: Path,
    ledger_path: Path,
    output_dir: Path,
    now_utc: datetime,
    phase2_opened_at_utc: datetime = PHASE2_OPENED_AT_UTC,
) -> dict[str, Any]:
    rows = qualification_rows(
        slate_path=slate_path,
        ledger_path=ledger_path,
        now_utc=now_utc,
        phase2_opened_at_utc=phase2_opened_at_utc,
    )
    summary = qualification_summary(rows)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "horizon_qualification.csv"
    fields = [
        "game_id",
        "away_team",
        "home_team",
        "kickoff_timestamp_utc",
        "horizon",
        "role",
        "target_timestamp_utc",
        "phase2_eligible",
        "state",
        "capture_tolerance_minutes",
        "minimum_complete_books",
        "completed_2026_outcomes_used",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    (output_dir / "operational_qualification.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", default="outputs/this_week.csv")
    parser.add_argument("--ledger", default="research_outputs/m1_market_state_v1/market_snapshots.csv")
    parser.add_argument("--output-dir", default="research_outputs/m1_market_state_v1")
    parser.add_argument("--now-utc", default=None)
    args = parser.parse_args()
    now = datetime.now(timezone.utc) if args.now_utc is None else datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
    summary = write_qualification_artifacts(
        slate_path=Path(args.slate),
        ledger_path=Path(args.ledger),
        output_dir=Path(args.output_dir),
        now_utc=now,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

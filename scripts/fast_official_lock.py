from __future__ import annotations

"""Fast immutable T-120 snapshot from already-published canonical forecasts.

This path does NOT estimate, calibrate, refit or blend probabilities. It reuses
the existing official lock's ATS field function, records the actual UTC
execution timestamp, and appends new history records without reserializing
old locked records. GitHub commits the history and status files atomically.
"""

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import math
import os
from pathlib import Path
from typing import Any

from nfl_forecast.publish import (
    LOCK_META_COLUMNS,
    _ats_lock_fields,
    kickoff_utc,
)

OFFICIAL_FST = "F-ST-01-FROZEN-2026"
MAX_FORECAST_AGE_MINUTES = 90.0
LOCK_WINDOW_MINUTES = 120.0
LOCK_STATES = {"LOCKED", "RECOVERED_MISSED_LOCK"}


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must have a timezone")
    return parsed.astimezone(timezone.utc)


def _read_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate CSV headers")
    return headers, list(reader)


def _validate_prediction(row: dict[str, str], now: datetime) -> None:
    gid = str(row.get("game_id") or "")
    if row.get("final_probability_strategy") != OFFICIAL_FST or row.get("fst_artifact_id") != OFFICIAL_FST:
        raise ValueError(f"{gid}: canonical frozen production identity mismatch")
    if row.get("pick") not in {row.get("home_team"), row.get("away_team")}:
        raise ValueError(f"{gid}: canonical pick must be one of the playing teams")
    try:
        prob = float(row.get("final_home_prob") or "nan")
    except ValueError as exc:
        raise ValueError(f"{gid}: invalid official probability") from exc
    if not math.isfinite(prob) or not 0 < prob < 1:
        raise ValueError(f"{gid}: invalid official probability")
    stamped = _utc(row.get("prediction_timestamp_utc"))
    age_minutes = (now - stamped).total_seconds() / 60.0
    if not -3 <= age_minutes <= MAX_FORECAST_AGE_MINUTES:
        raise ValueError(f"{gid}: source forecast is stale/future-dated ({age_minutes:.1f} minutes)")
    for field in ("expected_margin", "spread_line", "margin_sigma", "expected_total"):
        value = float(row.get(field) or "nan")
        if not math.isfinite(value):
            raise ValueError(f"{gid}: missing canonical {field}")
    if float(row["margin_sigma"]) <= 0 or float(row["expected_total"]) <= 0:
        raise ValueError(f"{gid}: nonpositive canonical score-bridge inputs")


def build_new_receipts(
    feed_text: str,
    history_text: str,
    status: dict[str, Any],
    now_utc: datetime,
) -> tuple[str, dict[str, Any], list[str]]:
    """Preserve history_text as an exact prefix; return only validated additions."""
    now = now_utc.astimezone(timezone.utc)
    current_fields, current = _read_csv(feed_text)
    history_fields, official = _read_csv(history_text)
    required_history = set(current_fields) | set(LOCK_META_COLUMNS)
    if not required_history.issubset(history_fields):
        raise ValueError("official history missing canonical columns")
    if not current or not status or str(status.get("fst_artifact_id")) != OFFICIAL_FST:
        raise ValueError("missing current canonical forecast or F-ST status")
    if len({row.get("game_id") for row in current}) != len(current) or any(not row.get("game_id") for row in current):
        raise ValueError("current slate missing/duplicating game ids")

    # Existing immutable rows are never modified or removed, even if their
    # original lock was late. This includes recovered missed-lock receipts.
    known: set[str] = set()
    for row in official:
        gid = row.get("game_id") or ""
        if not gid or gid in known:
            raise ValueError(f"official history missing/duplicate game ID: {gid}")
        known.add(gid)
    new_rows: list[dict[str, Any]] = []
    for row in current:
        gid = str(row["game_id"])
        if gid in known:
            continue
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{gid}: malformed canonical kickoff") from exc
        minutes = (kickoff - now).total_seconds() / 60.0
        if not 0 < minutes <= LOCK_WINDOW_MINUTES:
            continue
        _validate_prediction(row, now)
        ats = _ats_lock_fields(row)
        new = dict(row)
        new.update({
            "kickoff_utc": kickoff.isoformat(),
            "lock_timestamp_utc": now.isoformat(),
            "minutes_to_kickoff_at_lock": repr(minutes),
            "lock_status": "LOCKED",
        })
        new.update({k: "" if str(v) in ("nan", "<NA>", "None") else v for k, v in ats.items()})
        for key in LOCK_META_COLUMNS:
            new.setdefault(key, "")
        new_rows.append(new)
        known.add(gid)

    if not new_rows:
        return history_text, status, []

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=history_fields, extrasaction="ignore", lineterminator="\n")
    for row in new_rows:
        writer.writerow(row)
    separator = "" if history_text.endswith(("\n", "\r\n")) else "\n"
    updated = history_text + separator + out.getvalue()
    new_status = dict(status)
    new_status["locked_official_predictions"] = sum(
        row.get("lock_status") in LOCK_STATES for row in official
    ) + len(new_rows)
    new_status["official_lock_update_utc"] = now.isoformat()
    return updated, new_status, [str(row["game_id"]) for row in new_rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    out = args.output_dir
    history_path = out / "prediction_history.csv"
    status_path = out / "status.json"
    original = history_path.read_text(encoding="utf-8")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    updated, new_status, games = build_new_receipts(
        (out / "this_week.csv").read_text(encoding="utf-8"),
        original, status, datetime.now(timezone.utc),
    )
    if not games:
        print("Fast official lock: no new eligible games")
        return
    # Staging files are replaced before Git commits; the GitHub push is the
    # atomic multi-artifact publication boundary. A failed push publishes none.
    hp = history_path.with_suffix(".csv.fastlock.tmp")
    sp = status_path.with_suffix(".json.fastlock.tmp")
    hp.write_text(updated, encoding="utf-8")
    sp.write_text(json.dumps(new_status, indent=2) + "\n", encoding="utf-8")
    os.replace(hp, history_path)
    os.replace(sp, status_path)
    print("Fast official lock appended:", ", ".join(games))


if __name__ == "__main__":
    main()

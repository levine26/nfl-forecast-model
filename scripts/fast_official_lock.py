from __future__ import annotations

"""Lightweight immutable T-120 lock from the *already published* frozen forecast.

This is a deadline-safety path, not a model run. No features, probabilities or
historical lock records are recomputed, retuned, backdated or rewritten.
The usual full pregame model refresh remains independently available.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from nfl_forecast.publish import (
    ATS_LOCK_COLUMNS, CURRENT_COLUMNS, LOCK_META_COLUMNS,
    OFFICIAL_SNAPSHOT_STATUSES, _ats_lock_fields, kickoff_utc,
)

IDENTITY = "F-ST-01-FROZEN-2026"
MAX_CANONICAL_AGE_MINUTES = 90.0
LOCK_WINDOW_MINUTES = 120.0
EXPECTED_HEADER = CURRENT_COLUMNS + LOCK_META_COLUMNS


class FastLockError(RuntimeError):
    """Never publish an invalid, stale, duplicate or unsupported lock."""


def _timestamp(value: object) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise FastLockError(f"Invalid or missing UTC timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise FastLockError("Timestamp is not timezone aware")
    return dt.astimezone(timezone.utc)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FastLockError(f"Missing canonical CSV: {path}")
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise FastLockError(f"Missing CSV header: {path}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise FastLockError(f"Malformed CSV columns: {path}")
    return list(reader.fieldnames), rows


def plan_fast_locks(
    current_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    now_utc: datetime,
    max_age_minutes: float = MAX_CANONICAL_AGE_MINUTES,
) -> list[dict[str, Any]]:
    """Validate the whole current slate and return only newly due lock rows."""
    if now_utc.tzinfo is None:
        raise FastLockError("Current time must be timezone aware")
    now_utc = now_utc.astimezone(timezone.utc)
    if not current_rows or not isinstance(status, dict):
        raise FastLockError("Incomplete current canonical slate or status")
    ids = [str(row.get("game_id") or "") for row in current_rows]
    if any(not x for x in ids) or len(set(ids)) != len(ids):
        raise FastLockError("Missing or duplicate canonical game IDs")
    if int(status.get("games") or 0) != len(ids):
        raise FastLockError("Status slate count differs from canonical rows")
    if status.get("final_probability_strategy") != IDENTITY or status.get("fst_artifact_id") != IDENTITY:
        raise FastLockError("Production forecast identity does not match frozen F-ST")
    season_week = {
        (str(row.get("season") or ""), str(row.get("week") or ""))
        for row in current_rows
    }
    if len(season_week) != 1:
        raise FastLockError("Mixed seasons/weeks in current canonical slate")

    history_ids: set[str] = set()
    for old in history_rows:
        gid = str(old.get("game_id") or "")
        if not gid or gid in history_ids:
            raise FastLockError("Missing or duplicate historical prediction lock ID")
        history_ids.add(gid)
        if old.get("lock_status") not in OFFICIAL_SNAPSHOT_STATUSES:
            raise FastLockError("Unrecognized official lock status")

    due: list[dict[str, Any]] = []
    for row in current_rows:
        gid = str(row["game_id"])
        if row.get("final_probability_strategy") != IDENTITY or row.get("fst_artifact_id") != IDENTITY:
            raise FastLockError(f"{gid}: unexpected production probability strategy/artifact")
        away, home, pick = (str(row.get(x) or "") for x in ("away_team", "home_team", "pick"))
        if not away or not home or pick not in {away, home}:
            raise FastLockError(f"{gid}: invalid matchup or canonical pick")
        try:
            prob = float(row.get("final_home_prob") or "nan")
        except ValueError as exc:
            raise FastLockError(f"{gid}: malformed final probability") from exc
        if not (0.0 < prob < 1.0):
            raise FastLockError(f"{gid}: invalid frozen final probability")
        if gid in history_ids:
            continue
        try:
            kickoff = kickoff_utc(row["gameday"], row["gametime"])
        except (KeyError, ValueError) as exc:
            raise FastLockError(f"{gid}: unparseable canonical kickoff") from exc
        minutes_to_kickoff = (kickoff - now_utc).total_seconds() / 60.0
        if not (0.0 < minutes_to_kickoff <= LOCK_WINDOW_MINUTES):
            continue

        generated = _timestamp(row.get("prediction_timestamp_utc"))
        age_minutes = (now_utc - generated).total_seconds() / 60.0
        if age_minutes < -0.1 or age_minutes > max_age_minutes:
            raise FastLockError(f"{gid}: cached canonical forecast is stale/future ({age_minutes:.1f}m)")
        # The input may be a recent MARKET refresh. It is still the published
        # official frozen F-ST probability, not a new or reconstructed model run.
        locked = {name: row.get(name, "") for name in CURRENT_COLUMNS}
        locked.update({name: "" for name in LOCK_META_COLUMNS})
        locked["kickoff_utc"] = kickoff.isoformat()
        locked["lock_timestamp_utc"] = now_utc.isoformat()
        locked["minutes_to_kickoff_at_lock"] = str(minutes_to_kickoff)
        locked["lock_status"] = "LOCKED"
        locked.update({k: "" if v is None or (isinstance(v, float) and math.isnan(v)) else v for k,v in _ats_lock_fields(row).items()})
        due.append(locked)
    return due


def _atomic_bytes(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix="."+path.name+".",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_fast_locks(output_dir: Path, now_utc: datetime) -> list[str]:
    current_path = output_dir / "this_week.csv"
    history_path = output_dir / "prediction_history.csv"
    header, current = _read_csv(current_path)
    historic_header, history = _read_csv(history_path)
    if header != CURRENT_COLUMNS or historic_header != EXPECTED_HEADER:
        raise FastLockError("Unexpected canonical/official schema; refusing append")
    status_path = output_dir / "status.json"
    if not status_path.is_file():
        raise FastLockError("Missing canonical status.json")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    additions = plan_fast_locks(current, history, status, now_utc=now_utc)
    if not additions:
        return []

    # Preserve every existing historical byte. Append-only means that a retry
    # cannot rewrite or accidentally reformat old grades or prediction locks.
    original = history_path.read_bytes()
    if not original.endswith(b"\n"):
        raise FastLockError("Official history missing terminal newline; cannot safely append")
    new_rows = io.StringIO(newline="")
    writer = csv.DictWriter(new_rows,fieldnames=historic_header,lineterminator="\n",extrasaction="raise")
    writer.writerows(additions)
    ids = [str(row["game_id"]) for row in additions]
    _atomic_bytes(history_path,original+new_rows.getvalue().encode("utf-8"))

    # Publish the real new lock count; keep the numerical generation timestamp
    # untouched since this job has NOT rerun the forecasting engine.
    status = dict(status)
    status["locked_official_predictions"] = len(history)+len(additions)
    status["last_immutable_lock_update_utc"] = now_utc.astimezone(timezone.utc).isoformat()
    _atomic_bytes(status_path,(json.dumps(status,indent=2,sort_keys=True)+"\n").encode("utf-8"))

    receipts = output_dir / "lock_fast_path_receipts"
    receipts.mkdir(parents=True,exist_ok=True)
    indexed = {str(row["game_id"]): row for row in current}
    for row in additions:
        gid = str(row["game_id"])
        receipt = {
            "game_id": gid,
            "forecast_path_identity": IDENTITY,
            "source": "latest_committed_canonical_fst_forecast",
            "source_prediction_timestamp_utc": indexed[gid].get("prediction_timestamp_utc"),
            "source_row_sha256": hashlib.sha256(
                json.dumps(indexed[gid],sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "actual_lock_timestamp_utc": row["lock_timestamp_utc"],
            "kickoff_utc": row["kickoff_utc"],
            "no_model_recomputation": True,
            "old_official_history_sha256": hashlib.sha256(original).hexdigest(),
        }
        _atomic_bytes(receipts / f"{gid}.json",(json.dumps(receipt,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    return ids


def main() -> int:
    parser=argparse.ArgumentParser(description="Lock only fresh canonical F-ST snapshots at the official T-120 boundary")
    parser.add_argument("--output-dir",type=Path,default=Path("outputs"))
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    try:
        locked=write_fast_locks(args.output_dir,now)
    except (FastLockError, OSError, ValueError, KeyError) as exc:
        parser.exit(1,f"FAIL CLOSED: official lock deadline safety path: {exc}\n")
    print(f"Fast immutable T-120 lock: {len(locked)} newly locked at {now.isoformat()}: {', '.join(locked)}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())

"""Fail-closed full-refresh publication guard, including already-locked games.

A completed game's immutable official receipt may predate market-provenance
instrumentation. That cannot make a new *unlocked* forecast unqualified, and
must not block publication of fresh forecasts for the remaining games.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

FROZEN_ID = "F-ST-01-FROZEN-2026"
FROZEN_TRAINING_SHA = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
FROZEN_IMPLEMENTATION_SHA = "59830d23e406d32c34e74919b31d0dd9f85b16ca"
LOCKED_FIELDS = (
    "game_id", "pick", "final_home_prob", "expected_margin", "spread_line",
    "prediction_timestamp_utc", "final_probability_strategy", "fst_artifact_id",
    "fst_artifact_training_data_sha256", "fst_artifact_freeze_implementation_sha",
    "market_snapshot_timestamp_utc", "market_snapshot_source", "market_freshness_status",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Missing/duplicate CSV headers: {path}")
        return list(reader)


def _utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return result.astimezone(timezone.utc)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(output_dir: Path, *, now_utc: datetime | None = None) -> dict[str, int]:
    current = _rows(output_dir / "this_week.csv")
    history = _rows(output_dir / "prediction_history.csv")
    status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    now = now_utc or datetime.now(timezone.utc)
    _require(now.tzinfo is not None, "Naive validation clock")
    now = now.astimezone(timezone.utc)
    generated = _utc(status["generated_utc"])
    _require(timedelta(0) <= now - generated <= timedelta(minutes=90), "Stale or future publication generation")

    ids = [r.get("game_id", "") for r in current]
    history_ids = [r.get("game_id", "") for r in history]
    _require(bool(ids) and all(ids) and len(ids) == len(set(ids)), "Missing/duplicate slate game IDs")
    _require(all(history_ids) and len(history_ids) == len(set(history_ids)), "Missing/duplicate official history IDs")
    _require(status.get("slate_completeness_verified") is True
             and status.get("expected_week_games") == len(ids)
             and status.get("games") == len(ids)
             and not status.get("missing_week_game_ids"), "Unverified or incomplete scheduled slate")
    _require(status.get("final_probability_strategy") == FROZEN_ID
             and status.get("fst_artifact_id") == FROZEN_ID
             and status.get("fst_artifact_training_data_sha256") == FROZEN_TRAINING_SHA,
             "Production status has non-frozen F-ST identity")
    _require(status.get("fst_fallback_count") == 0
             and status.get("market_available_games") == len(ids)
             and status.get("market_missing_or_invalid_games") == 0,
             "Fallback or missing market price in publication status")

    locked = {r["game_id"]: r for r in history if r.get("lock_status") == "LOCKED"}
    _require(status.get("locked_official_predictions") == len(locked), "Official receipt count mismatch")
    missing_provenance = 0
    locked_missing = 0
    unlocked = 0
    for row in current:
        gid = row["game_id"]
        _require(row.get("final_probability_strategy") == FROZEN_ID
                 and row.get("fst_artifact_id") == FROZEN_ID
                 and row.get("fst_artifact_training_data_sha256") == FROZEN_TRAINING_SHA
                 and row.get("fst_artifact_freeze_implementation_sha") == FROZEN_IMPLEMENTATION_SHA,
                 f"{gid}: changed frozen F-ST artifact")
        _require(row.get("fst_fallback", "").strip().lower() == "false", f"{gid}: F-ST fallback")
        _require(row.get("market_available", "").strip().lower() == "true", f"{gid}: missing market price")
        _require(row.get("pick") in {row.get("home_team"), row.get("away_team")}, f"{gid}: invalid pick")
        try:
            p = float(row["final_home_prob"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{gid}: invalid final probability") from exc
        _require(0.0 < p < 1.0, f"{gid}: out-of-range probability")
        provenance_ok = bool(row.get("market_snapshot_timestamp_utc")
                             and row.get("market_snapshot_source")
                             and row.get("market_freshness_status") == "refreshed_this_run")
        if not provenance_ok:
            missing_provenance += 1
        if gid in locked:
            receipt = locked[gid]
            _require(all(row.get(k, "") == receipt.get(k, "") for k in LOCKED_FIELDS),
                     f"{gid}: locked public forecast drifted from immutable receipt")
            if not provenance_ok:
                locked_missing += 1
            continue
        unlocked += 1
        _require(provenance_ok, f"{gid}: unlocked forecast lacks fresh observed market provenance")
        market_time = _utc(row["market_snapshot_timestamp_utc"])
        _require(timedelta(0) <= generated - market_time <= timedelta(minutes=90)
                 and market_time <= now, f"{gid}: stale/future market observation")
        kickoff = datetime.fromisoformat(f'{row["gameday"]}T{row["gametime"]}').replace(
            tzinfo=ZoneInfo("America/New_York")
        ).astimezone(timezone.utc)
        _require(kickoff > now, f"{gid}: past kickoff without genuine official receipt")

    _require(status.get("market_provenance_missing_games") == missing_provenance,
             "Market provenance summary does not match published rows")
    _require(missing_provenance == locked_missing,
             "Missing provenance is not isolated to immutable locked games")
    _require(status.get("status") == ("degraded" if missing_provenance else "healthy"),
             "Status label contradicts verified market provenance")
    return {"slate": len(ids), "locked": len(ids) - unlocked,
            "unlocked": unlocked, "historical_locked_without_provenance": locked_missing}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    result = validate(args.output_dir)
    print("Qualified full-model publication; locked legacy provenance remains disclosed:", result)


if __name__ == "__main__":
    main()

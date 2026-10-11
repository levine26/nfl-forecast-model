from __future__ import annotations

"""Read-only, versioned per-game official-lock deadline audit.

Never creates, moves, or backdates a lock. A missing lock after its target + 10 minutes is a
failure even if the separate scheduling mechanism has not fired. The official
history is authoritative; an earlier recorded late lock is reported truthfully
without mutating it or causing permanent new-run failures.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from scripts.pregame_due import kickoff_utc
from nfl_forecast.lock_policy import official_lock_target_minutes

TARGET_MINUTES = 120.0
GRACE_MINUTES = 10.0
WATCH_AFTER_KICKOFF_MINUTES = 180.0


def _timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid official lock timestamp: {value!r}") from exc


def audit_current_deadlines(
    games: list[dict[str, Any]],
    history: list[dict[str, Any]],
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    if not games or now_utc.tzinfo is None:
        raise ValueError("nonempty slate and timezone-aware clock required")
    now_utc = now_utc.astimezone(timezone.utc)
    game_ids = [str(row.get("game_id") or "").strip() for row in games]
    if any(not gid for gid in game_ids) or len(game_ids) != len(set(game_ids)):
        raise ValueError("canonical slate contains missing/duplicate game ID")

    lock_by_id: dict[str, dict[str, Any]] = {}
    for row in history:
        gid = str(row.get("game_id") or "").strip()
        if not gid or gid in lock_by_id:
            raise ValueError("official history missing/duplicate game ID")
        lock_by_id[gid] = row

    issues = {}
    games_out: dict[str, Any] = {}
    for row in games:
        gid = str(row["game_id"])
        kickoff = kickoff_utc(str(row.get("gameday") or ""), str(row.get("gametime") or ""))
        target_minutes = official_lock_target_minutes(row)
        target = kickoff - timedelta(minutes=target_minutes)
        grace_end = target + timedelta(minutes=GRACE_MINUTES)
        locked = lock_by_id.get(gid)
        minutes_to_kickoff = (kickoff - now_utc).total_seconds() / 60.0
        result: dict[str, Any] = {
            "kickoff_utc": kickoff.isoformat(),
            "target_lock_utc": target.isoformat(),
            "target_minutes_before_kickoff": target_minutes,
            "grace_end_utc": grace_end.isoformat(),
            "minutes_to_kickoff_now": round(minutes_to_kickoff, 3),
            "lock_status": locked.get("lock_status") if locked else "missing",
        }

        if locked and locked.get("lock_status") == "LOCKED":
            actual = _timestamp(locked.get("lock_timestamp_utc"))
            result["actual_lock_utc"] = actual.isoformat()
            delay = (actual - target).total_seconds() / 60.0
            result["minutes_late_vs_t120"] = round((actual - (kickoff - timedelta(minutes=TARGET_MINUTES))).total_seconds() / 60.0, 3)
            result["minutes_late_vs_target"] = round(delay, 3)
            result["state"] = (
                "premature_lock" if delay < -0.1 else
                "on_time_lock" if delay <= GRACE_MINUTES else "historically_late_lock"
            )
            if (result["state"] == "historically_late_lock"
                    and grace_end <= now_utc <= kickoff + timedelta(minutes=WATCH_AFTER_KICKOFF_MINUTES)):
                issues[gid] = [f"Official lock occurred {round(delay, 3)} minutes after the T-{int(target_minutes)} target; deadline exceeded 10-minute grace"]
        elif locked and locked.get("lock_status") == "RECOVERED_MISSED_LOCK":
            result["state"] = "recorded_missed_lock_recovery"
        elif grace_end <= now_utc <= kickoff + timedelta(minutes=WATCH_AFTER_KICKOFF_MINUTES):
            result["state"] = "overdue_missing_official_lock"
            issues[gid] = ["No immutable official lock found after its T-{int(target_minutes)} target plus 10 minutes"]
        elif now_utc < grace_end:
            result["state"] = "deadline_not_elapsed"
        else:
            result["state"] = "missing_lock_outside_active_watch_window"
        games_out[gid] = result

    target_values = sorted({x["target_minutes_before_kickoff"] for x in games_out.values()})
    counts = {state: sum(v["state"] == state for v in games_out.values())
              for state in sorted({v["state"] for v in games_out.values()})}
    return {
        "schema_version": 1,
        "kind": "read_only_current_slate_official_lock_deadline_audit",
        "generated_utc": now_utc.isoformat(),
        "games_expected": len(games),
        "games_audited": len(games_out),
        "target_minutes_before_kickoff": target_values[0] if len(target_values) == 1 else None,
        "observed_target_minutes": target_values,
        "target_policy": "2026_week_6_t60_prospective; earlier_t120",
        "grace_minutes": GRACE_MINUTES,
        "status": "active_lock_timing_violation" if issues else "no_active_lock_timing_violation",
        "issues": issues,
        "counts": counts,
        "games": games_out,
        "historical_lock_records_modified": False,
        "warning": "GitHub Actions scheduled workflows are best-effort and cannot guarantee exact versioned target execution.",
    }


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"{path}: CSV has no header")
        return list(reader)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--history", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now-utc", default=None, help="Test-only explicit offset-aware clock")
    args = parser.parse_args()
    now = _timestamp(args.now_utc) if args.now_utc else datetime.now(timezone.utc)
    report = audit_current_deadlines(_csv(args.current), _csv(args.history), now_utc=now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    for gid, state in sorted(report["games"].items()):
        if state["state"] in {"overdue_missing_official_lock", "historically_late_lock", "recorded_missed_lock_recovery"}:
            print(f"::warning title=Official lock deadline::{gid}: {state['state']}")
    if report["issues"]:
        raise SystemExit(f"FAIL CLOSED: {len(report['issues'])} current-slate games have overdue missing official lock: {sorted(report['issues'])}")
    print(f"Lock deadline audit: {report['games_audited']}/{report['games_expected']} canonical games checked; no missing overdue lock.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

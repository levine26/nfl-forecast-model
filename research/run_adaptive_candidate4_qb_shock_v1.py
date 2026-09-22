from __future__ import annotations

"""Run the prospective Candidate 4 QB-shock capture after the frozen T-60 cutoff.

The job waits for a short operational grace after T-60 so the independently scheduled
official inactive-source archive has time to persist its T-60-or-earlier observation.
Scientific evidence remains capped at T-60; the grace period never expands the source window.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research.adaptive_candidate4_qb_shock_v1 import (
    append_immutable_qb_state,
    build_qb_shock_rows_from_snapshots,
)

PROCESSING_GRACE_MINUTES = 10
MIN_WEEK = 3
EASTERN = ZoneInfo("America/New_York")


def _utc(value: object) -> datetime | None:
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


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
    return rows


def _week(game_id: str) -> int | None:
    parts = str(game_id or "").split("_")
    if len(parts) < 2 or parts[0] != "2026":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _cohort_key(games: list[dict]) -> tuple[str, tuple[str, ...]]:
    kickoff_values = {str(game.get("kickoff_utc") or "") for game in games}
    if len(kickoff_values) != 1:
        raise ValueError("cohort must share one kickoff")
    return next(iter(kickoff_values)), tuple(sorted(str(game.get("game_id") or "") for game in games))


def candidate_cohorts(
    archive_dir: Path,
    *,
    now_utc: datetime,
    existing_game_ids: set[str],
) -> list[list[dict]]:
    """Return unique Sunday cohorts whose T-60 evidence window has fully closed."""
    observations = _read_jsonl(archive_dir / "observations.jsonl")
    by_key: dict[tuple[str, tuple[str, ...]], list[dict]] = {}

    for observation in observations:
        due_games = list(observation.get("due_games") or [])
        if not due_games:
            continue

        groups: dict[str, list[dict]] = {}
        for game in due_games:
            gid = str(game.get("game_id") or "")
            week = _week(gid)
            kickoff = _utc(game.get("kickoff_utc"))
            if week is None or week < MIN_WEEK or kickoff is None:
                continue
            if kickoff.astimezone(EASTERN).weekday() != 6:
                continue
            groups.setdefault(kickoff.isoformat(), []).append(dict(game))

        for games in groups.values():
            if not games:
                continue
            kickoff = _utc(games[0].get("kickoff_utc"))
            if kickoff is None:
                continue
            t60 = kickoff - timedelta(minutes=60)
            ready = t60 + timedelta(minutes=PROCESSING_GRACE_MINUTES)
            if now_utc < ready or now_utc >= kickoff:
                continue
            if all(str(game.get("game_id") or "") in existing_game_ids for game in games):
                continue
            by_key[_cohort_key(games)] = games

    return [by_key[key] for key in sorted(by_key)]


def _verify_parser_authority(path: Path) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or receipt.get("qualification_passed") is not True:
        raise RuntimeError("inactive cohort parser V2 is not qualified")
    authority = receipt.get("authority") or {}
    if authority.get("player_level_parser_qualified_for_due_cohort_filtering") is not True:
        raise RuntimeError("inactive cohort parser receipt lacks due-cohort authority")
    if int(receipt.get("completed_2026_outcomes_used", -1)) != 0:
        raise RuntimeError("inactive parser qualification unexpectedly used 2026 outcomes")
    return receipt


def run(
    *,
    archive_dir: Path,
    output_csv: Path,
    parser_receipt_path: Path,
    qb1_snapshot_path: Path,
    now_utc: datetime | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    _verify_parser_authority(parser_receipt_path)

    existing = pd.read_csv(output_csv) if output_csv.exists() and output_csv.stat().st_size else pd.DataFrame()
    existing_ids = set(existing["game_id"].astype(str)) if "game_id" in existing.columns else set()
    cohorts = candidate_cohorts(
        archive_dir,
        now_utc=now,
        existing_game_ids=existing_ids,
    )
    if not cohorts:
        return {
            "status": "skipped",
            "reason": "no_candidate4_sunday_cohort_ready",
            "rows_added": 0,
            "processing_grace_minutes": PROCESSING_GRACE_MINUTES,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    qb1_snapshots = (
        pd.read_csv(qb1_snapshot_path)
        if qb1_snapshot_path.exists() and qb1_snapshot_path.stat().st_size
        else pd.DataFrame()
    )
    additions: list[pd.DataFrame] = []
    for games in cohorts:
        rows = build_qb_shock_rows_from_snapshots(
            qb1_snapshots,
            archive_dir=archive_dir,
            games=games,
        )
        if not rows.empty:
            additions.append(rows)

    new_rows = pd.concat(additions, ignore_index=True, sort=False) if additions else pd.DataFrame()
    combined = append_immutable_qb_state(existing, new_rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_csv, index=False)

    added = max(0, len(combined) - len(existing))
    return {
        "status": "captured" if added else "unchanged",
        "rows_added": int(added),
        "ledger_rows": int(len(combined)),
        "cohorts_processed": int(len(cohorts)),
        "qb1_snapshot_source": str(qb1_snapshot_path),
        "processing_grace_minutes": PROCESSING_GRACE_MINUTES,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=Path("research_outputs/inactive_article_source_archive_v1"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4/qb_state.csv"),
    )
    parser.add_argument(
        "--parser-receipt",
        type=Path,
        default=Path("research/inactive_article_cohort_parser_v2_receipt.json"),
    )
    parser.add_argument(
        "--qb1-snapshots",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4/qb1_t120_snapshots.csv"),
    )
    args = parser.parse_args()
    result = run(
        archive_dir=args.archive_dir,
        output_csv=args.output_csv,
        parser_receipt_path=args.parser_receipt,
        qb1_snapshot_path=args.qb1_snapshots,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

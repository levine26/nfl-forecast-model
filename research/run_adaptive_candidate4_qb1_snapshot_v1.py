from __future__ import annotations

"""Scheduled runner for the prospective Candidate 4 T-120 QB1 snapshot."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

import pandas as pd

from research.adaptive_candidate4_qb1_snapshot_v1 import (
    append_immutable_snapshots,
    build_t120_qb1_snapshots,
    due_t120_games,
)


def _load_depth_2026() -> tuple[pd.DataFrame, str]:
    import nflreadpy as nfl

    frame = nfl.load_depth_charts([2026])
    if hasattr(frame, "to_dicts"):
        depth = pd.DataFrame(frame.to_dicts())
    elif hasattr(frame, "to_pandas"):
        depth = frame.to_pandas()
    elif isinstance(frame, pd.DataFrame):
        depth = frame.copy()
    else:
        depth = pd.DataFrame(frame)
    return depth, importlib.metadata.version("nflreadpy")


def run(
    *,
    feed_path: Path,
    output_csv: Path,
    now_utc: datetime | None = None,
    depth_frame: pd.DataFrame | None = None,
    nflreadpy_version: str | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    feed = pd.read_csv(feed_path) if feed_path.exists() else pd.DataFrame()
    existing = (
        pd.read_csv(output_csv)
        if output_csv.exists() and output_csv.stat().st_size
        else pd.DataFrame()
    )
    existing_ids = set(existing["game_id"].astype(str)) if "game_id" in existing.columns else set()
    due = due_t120_games(feed, now_utc=now, existing_game_ids=existing_ids)
    if not due:
        return {
            "status": "skipped",
            "reason": "no_candidate4_t120_qb1_snapshot_due",
            "rows_added": 0,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    if depth_frame is None:
        depth, version = _load_depth_2026()
    else:
        depth = depth_frame.copy()
        version = str(nflreadpy_version or "test")

    new_rows = build_t120_qb1_snapshots(
        depth,
        due,
        captured_at_utc=now,
        nflreadpy_version=version,
    )
    combined = append_immutable_snapshots(existing, new_rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_csv, index=False)
    added = max(0, len(combined) - len(existing))
    return {
        "status": "captured" if added else "unchanged",
        "rows_added": int(added),
        "ledger_rows": int(len(combined)),
        "nflreadpy_version": version,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4/qb1_t120_snapshots.csv"),
    )
    args = parser.parse_args()
    print(json.dumps(run(feed_path=args.feed, output_csv=args.output_csv), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

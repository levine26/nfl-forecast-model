from __future__ import annotations

"""Materialize DEPTH-STATE-01 from nflverse 2025 depth-chart snapshots.

This is a source/personnel-state audit only.  Historical game outcomes are intentionally
not selected from the schedule and no model is fit or scored.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import nflreadpy as nfl
import pandas as pd

from research.depth_chart_state_v1 import build_depth_state

SAFE_SCHEDULE_COLUMNS = [
    "game_id",
    "season",
    "week",
    "game_type",
    "gameday",
    "gametime",
    "home_team",
    "away_team",
]


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def run(output_dir: str = "research_outputs/depth_chart_state_v1") -> dict:
    depth = _pandas(nfl.load_depth_charts([2025]))
    schedules = _pandas(nfl.load_schedules([2025]))
    keep = [column for column in SAFE_SCHEDULE_COLUMNS if column in schedules.columns]
    schedules = schedules[keep].copy()
    if "game_type" in schedules.columns:
        schedules = schedules[schedules["game_type"].astype(str).isin({"REG", "POST"})].copy()
    schedules = schedules[
        schedules["game_id"].notna()
        & schedules["home_team"].notna()
        & schedules["away_team"].notna()
    ].copy()

    built = build_depth_state(depth, schedules)
    audit = {
        **built.audit,
        "experiment_id": "DEPTH-STATE-01",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "research_only_source_foundation",
        "schedule_columns_loaded_into_builder": list(schedules.columns),
        "outcome_columns_loaded_into_builder": [],
        "model_fit": False,
        "model_scored": False,
        "automatic_promotion": False,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    built.team_game_state.to_csv(out / "team_game_depth_state.csv", index=False)
    built.game_features.to_csv(out / "game_depth_features.csv", index=False)
    (out / "audit.json").write_text(json.dumps(audit, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, default=str))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/depth_chart_state_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()

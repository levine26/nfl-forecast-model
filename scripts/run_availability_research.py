from __future__ import annotations

"""Audit whether historical sources can support leakage-safe v0.9B availability.

The job intentionally stops at source qualification. It never estimates P(active) when a
target season lacks timestamped injury/practice-report coverage.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess

import nflreadpy as nfl
import pandas as pd

from nfl_forecast.availability_research import (
    INJURY_SOURCE_LAST_VALID_SEASON,
    TARGET_SEASONS,
    qualify_v09b_sources,
)
from nfl_forecast.data import configure_cache


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _field_audit(frame: pd.DataFrame | None, fields: list[str]) -> dict:
    if frame is None or frame.empty:
        return {field: {"present": False, "non_null_rate": None} for field in fields}
    result = {}
    for field in fields:
        present = field in frame.columns
        result[field] = {
            "present": present,
            "non_null_rate": float(frame[field].notna().mean()) if present else None,
        }
    return result


def run(
    cache_dir: str = ".cache/nflreadpy",
    output_dir: str = "research_outputs/availability",
) -> dict:
    configure_cache(cache_dir)

    # Never request 2025 from the dead historical injury source. The absence is itself
    # recorded as a target-season blocker rather than masked by a retrospective proxy.
    injury_seasons = list(range(2009, INJURY_SOURCE_LAST_VALID_SEASON + 1))
    injuries = _pandas(nfl.load_injuries(injury_seasons))
    depth_2025 = _pandas(nfl.load_depth_charts([2025]))

    qualification = qualify_v09b_sources(injuries, depth_2025, target_seasons=TARGET_SEASONS)
    report = {
        **qualification,
        "mode": "research_only_source_audit",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "injury_loaded_seasons": injury_seasons,
        "injury_fields": _field_audit(
            injuries,
            [
                "season",
                "week",
                "team",
                "gsis_id",
                "report_primary_injury",
                "report_status",
                "practice_primary_injury",
                "practice_status",
                "date_modified",
            ],
        ),
        "depth_2025_fields": _field_audit(
            depth_2025,
            ["dt", "team", "gsis_id", "pos_grp", "pos_abb", "pos_slot", "pos_rank"],
        ),
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
        },
        "interpretation": (
            "A timestamped 2025 depth chart can support lineup-state reconstruction, but "
            "it does not supply 2025 official injury/practice-report probabilities. A full "
            "2022-2025 P(active) model remains blocked unless a separate timestamped 2025 "
            "availability source is validated."
        ),
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "v09b_source_qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if injuries is not None and not injuries.empty:
        summary = (
            injuries.groupby("season", as_index=False)
            .agg(
                rows=("season", "size"),
                players=("gsis_id", "nunique"),
                weeks=("week", "nunique"),
            )
        )
        summary.to_csv(out / "injury_coverage_by_season.csv", index=False)
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=".cache/nflreadpy")
    parser.add_argument("--output-dir", default="research_outputs/availability")
    args = parser.parse_args()
    run(args.cache_dir, args.output_dir)


if __name__ == "__main__":
    main()

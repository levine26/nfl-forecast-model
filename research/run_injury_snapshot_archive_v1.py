from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research.injury_snapshot_archive_v1 import SEASON, capture_week, verify_archive

DEFAULT_OUTPUT = Path("research_outputs/injury_snapshot_archive_v1")
DEFAULT_WEEK_SOURCE = Path("outputs/this_week.csv")


def resolve_current_week(path: str | Path = DEFAULT_WEEK_SOURCE) -> tuple[int, int]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"injury archive week source missing: {source}")
    frame = pd.read_csv(source, usecols=["season", "week"])
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce")
    frame["week"] = pd.to_numeric(frame["week"], errors="coerce")
    pairs = frame.dropna().drop_duplicates().astype(int)
    values = list(pairs.itertuples(index=False, name=None))
    if len(values) != 1:
        raise ValueError(f"injury archive requires exactly one current season/week; found {values}")
    season, week = values[0]
    if season != SEASON:
        raise ValueError(f"injury archive v1 is frozen to season {SEASON}; current output says {season}")
    if not 1 <= week <= 18:
        raise ValueError(f"injury archive current regular-season week invalid: {week}")
    return season, week


def run(*, output_dir: str | Path, season: int | None = None, week: int | None = None) -> dict:
    if (season is None) != (week is None):
        raise ValueError("season and week overrides must be supplied together")
    if season is None:
        season, week = resolve_current_week()
    assert week is not None
    result = capture_week(season=int(season), week=int(week), output_dir=output_dir)
    audit = verify_archive(output_dir)
    summary = {
        "observation": result.observation,
        "archive_audit": audit,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest_status.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not audit["integrity_ok"]:
        raise RuntimeError("injury snapshot archive integrity verification failed")
    if result.observation["status"] != "captured":
        raise RuntimeError(f"official injury snapshot capture failed: {result.observation.get('error')}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int)
    args = parser.parse_args()
    run(output_dir=args.output_dir, season=args.season, week=args.week)


if __name__ == "__main__":
    main()

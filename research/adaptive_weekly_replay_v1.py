from __future__ import annotations

"""Chronology-safe weekly replay utilities for adaptive LevLine research.

This module is research-only.  It materializes a deterministic week-by-week replay
from immutable historical provenance and guarantees that a forecast week can only
see rows from strictly earlier weeks.
"""

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
DEFAULT_START_SEASON = 2022
DEFAULT_END_SEASON = 2025


@dataclass(frozen=True)
class WeeklyReplaySlice:
    season: int
    week: int
    train: pd.DataFrame
    forecast: pd.DataFrame


def parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game_id format: {game_id!r}")
    season, week, away, home = parts
    return int(season), int(week), away, home


def load_replay_frame(path: str | Path = SOURCE) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"game_id", "season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"weekly replay source missing fields: {sorted(missing)}")
    if frame["game_id"].astype(str).duplicated().any():
        dupes = frame.loc[frame["game_id"].astype(str).duplicated(), "game_id"].astype(str).tolist()
        raise ValueError(f"weekly replay source contains duplicate game ids: {dupes[:5]}")

    parsed = frame["game_id"].map(parse_game_id)
    frame = frame.copy()
    frame["season_num"] = [x[0] for x in parsed]
    frame["week"] = [x[1] for x in parsed]
    frame["away_team"] = [x[2] for x in parsed]
    frame["home_team"] = [x[3] for x in parsed]

    season_source = pd.to_numeric(frame["season"], errors="coerce")
    if season_source.isna().any() or not np.array_equal(
        season_source.astype(int).to_numpy(), frame["season_num"].astype(int).to_numpy()
    ):
        raise ValueError("season column disagrees with immutable game_id season")

    for col in ("home_win", "market_prob", "pure_prob"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    usable = (
        frame["home_win"].isin([0, 1])
        & frame["market_prob"].gt(0.0)
        & frame["market_prob"].lt(1.0)
        & frame["pure_prob"].gt(0.0)
        & frame["pure_prob"].lt(1.0)
    )
    frame = frame.loc[usable].copy()
    if frame.empty:
        raise ValueError("weekly replay source has no usable rows")

    frame = frame.sort_values(["season_num", "week", "game_id"], kind="stable").reset_index(drop=True)
    frame["replay_order"] = np.arange(len(frame), dtype=int)
    return frame


def iter_weekly_replay(
    frame: pd.DataFrame,
    *,
    start_season: int = DEFAULT_START_SEASON,
    end_season: int = DEFAULT_END_SEASON,
) -> Iterator[WeeklyReplaySlice]:
    required = {"season_num", "week", "game_id", "home_win"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"replay frame missing normalized fields: {sorted(missing)}")

    targets = frame[
        frame["season_num"].between(int(start_season), int(end_season), inclusive="both")
    ].copy()
    if targets.empty:
        raise ValueError("no target weeks in requested replay window")

    for (season, week), forecast in targets.groupby(["season_num", "week"], sort=True):
        season = int(season)
        week = int(week)
        prior = (
            (frame["season_num"] < season)
            | ((frame["season_num"] == season) & (frame["week"] < week))
        )
        train = frame.loc[prior].copy()
        forecast = forecast.copy()

        if not train.empty:
            max_train_key = max(zip(train["season_num"].astype(int), train["week"].astype(int)))
            if max_train_key >= (season, week):
                raise RuntimeError(
                    f"chronology breach: replay {season} W{week} sees {max_train_key}"
                )
        if ((forecast["season_num"] != season) | (forecast["week"] != week)).any():
            raise RuntimeError("forecast slice contains a foreign week")

        yield WeeklyReplaySlice(season, week, train, forecast)


def replay_manifest(
    frame: pd.DataFrame,
    *,
    start_season: int = DEFAULT_START_SEASON,
    end_season: int = DEFAULT_END_SEASON,
) -> dict:
    weeks = []
    prior_target_games = 0
    for item in iter_weekly_replay(frame, start_season=start_season, end_season=end_season):
        weeks.append(
            {
                "season": item.season,
                "week": item.week,
                "training_games_available": int(len(item.train)),
                "forecast_games": int(len(item.forecast)),
                "same_week_outcomes_visible": False,
            }
        )
        prior_target_games += len(item.forecast)
    return {
        "artifact_id": "LEVLINE-ADAPTIVE-WEEKLY-REPLAY-V1",
        "source": str(SOURCE),
        "start_season": int(start_season),
        "end_season": int(end_season),
        "target_games": int(prior_target_games),
        "weeks": int(len(weeks)),
        "weekly_slices": weeks,
        "chronology_rule": "train rows must be strictly earlier than the forecast season/week",
        "2026_outcomes_used": 0,
        "production_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--start-season", type=int, default=DEFAULT_START_SEASON)
    parser.add_argument("--end-season", type=int, default=DEFAULT_END_SEASON)
    parser.add_argument("--output", default="research_outputs/adaptive_weekly_replay_v1/manifest.json")
    args = parser.parse_args()

    frame = load_replay_frame(args.source)
    manifest = replay_manifest(frame, start_season=args.start_season, end_season=args.end_season)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

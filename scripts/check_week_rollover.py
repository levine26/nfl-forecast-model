from __future__ import annotations

"""Detect when market-only refresh must yield to a complete new-week forecast."""

import argparse

import pandas as pd

SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"


def requires_rollover(current: pd.DataFrame, schedule: pd.DataFrame) -> bool:
    """Compare the published slate to the earliest unscored regular-season week.

    Scores, not the home-win label, distinguish completed games from upcoming
    games. This deliberately treats tied games as completed and does not guess
    a final result when an upstream score is absent.
    """
    required = {"season", "week"}
    if current.empty or not required.issubset(current.columns):
        raise ValueError("Current forecast is empty or missing season/week")
    identities = current[["season", "week"]].drop_duplicates()
    if len(identities) != 1:
        raise ValueError("Published current slate must contain exactly one season/week")
    season, published_week = (int(v) for v in identities.iloc[0].tolist())

    required_schedule = {"season", "week", "home_score", "away_score"}
    if not required_schedule.issubset(schedule.columns):
        raise ValueError("Schedule is missing season/week/final-score fields")
    target = schedule.loc[pd.to_numeric(schedule["season"], errors="coerce").eq(season)].copy()
    if "game_type" in target.columns:
        target = target.loc[target["game_type"].eq("REG")].copy()
    if target.empty:
        raise ValueError(f"No regular-season schedule found for {season}")
    unscored = target.loc[target["home_score"].isna() | target["away_score"].isna()].copy()
    if unscored.empty:
        return False
    next_week = int(pd.to_numeric(unscored["week"], errors="raise").min())
    return next_week > published_week


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", default="outputs/this_week.csv")
    parser.add_argument("--schedule-url", default=SCHEDULE_URL)
    args = parser.parse_args()
    current = pd.read_csv(args.current)
    schedule = pd.read_csv(args.schedule_url, low_memory=False)
    print(f"required={str(requires_rollover(current, schedule)).lower()}")


if __name__ == "__main__":
    main()

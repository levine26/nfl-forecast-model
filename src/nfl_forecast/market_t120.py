from __future__ import annotations

"""Research-only T-120 market snapshot selection.

This module never feeds LevLine probabilities. It reconstructs the latest observed
MARKET snapshot at or before kickoff minus 120 minutes from the append-only run
history so market research uses the same information horizon as the production
lock without lookahead.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.publish import kickoff_utc

T120_MINUTES = 120.0

RESEARCH_COLUMNS = [
    "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
    "kickoff_utc", "target_timestamp_utc", "snapshot_timestamp_utc",
    "minutes_to_kickoff_at_snapshot", "staleness_minutes_vs_t120", "no_lookahead",
    "market_home_prob", "pure_home_prob", "final_home_prob", "spread_line", "total_line",
    "snapshot_type", "prediction_id", "actual_home_score", "actual_away_score",
    "actual_home_win", "graded",
]


def _utc_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce")


def select_t120_market_snapshots(
    run_history: pd.DataFrame,
    prediction_history: pd.DataFrame | None = None,
    target_minutes: float = T120_MINUTES,
) -> pd.DataFrame:
    """Select the latest MARKET observation at or before each game's T-120 cutoff.

    A game with no eligible pre-cutoff observation is omitted rather than filled
    from a later market snapshot. ``staleness_minutes_vs_t120`` is always >= 0 for
    selected rows; this makes source cadence/coverage explicit for later research.
    """
    if run_history is None or run_history.empty:
        return pd.DataFrame(columns=RESEARCH_COLUMNS)

    required = {"game_id", "gameday", "gametime", "prediction_timestamp_utc", "snapshot_type"}
    missing = required - set(run_history.columns)
    if missing:
        raise ValueError(f"run history missing required T-120 fields: {sorted(missing)}")

    history = run_history.copy()
    history = history[history["snapshot_type"].astype(str).str.upper().eq("MARKET")].copy()
    history["_observed"] = _utc_series(history["prediction_timestamp_utc"])
    history = history[history["_observed"].notna()].copy()
    if history.empty:
        return pd.DataFrame(columns=RESEARCH_COLUMNS)

    rows: list[dict] = []
    for game_id, group in history.groupby("game_id", sort=True):
        first = group.iloc[0]
        try:
            kickoff = pd.Timestamp(kickoff_utc(first.get("gameday"), first.get("gametime")))
        except Exception:
            continue
        target = kickoff - pd.Timedelta(minutes=float(target_minutes))
        eligible = group[group["_observed"] <= target].sort_values("_observed")
        if eligible.empty:
            continue
        chosen = eligible.iloc[-1]
        observed = chosen["_observed"]
        minutes_to_kickoff = (kickoff - observed).total_seconds() / 60.0
        staleness = (target - observed).total_seconds() / 60.0
        row = {c: chosen.get(c, np.nan) for c in [
            "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
            "market_home_prob", "pure_home_prob", "final_home_prob", "spread_line", "total_line",
            "snapshot_type", "prediction_id",
        ]}
        row.update({
            "kickoff_utc": kickoff.isoformat(),
            "target_timestamp_utc": target.isoformat(),
            "snapshot_timestamp_utc": observed.isoformat(),
            "minutes_to_kickoff_at_snapshot": float(minutes_to_kickoff),
            "staleness_minutes_vs_t120": float(staleness),
            "no_lookahead": bool(observed <= target and staleness >= -1e-9),
            "actual_home_score": np.nan,
            "actual_away_score": np.nan,
            "actual_home_win": pd.NA,
            "graded": False,
        })
        rows.append(row)

    selected = pd.DataFrame(rows)
    if selected.empty:
        return pd.DataFrame(columns=RESEARCH_COLUMNS)

    if prediction_history is not None and not prediction_history.empty and "game_id" in prediction_history.columns:
        grade_cols = [c for c in ["game_id", "actual_home_score", "actual_away_score"] if c in prediction_history.columns]
        if len(grade_cols) == 3:
            grades = prediction_history[grade_cols].drop_duplicates("game_id", keep="last").copy()
            selected = selected.drop(columns=["actual_home_score", "actual_away_score"]).merge(grades, on="game_id", how="left")
            hs = pd.to_numeric(selected["actual_home_score"], errors="coerce")
            aw = pd.to_numeric(selected["actual_away_score"], errors="coerce")
            graded = hs.notna() & aw.notna()
            selected["graded"] = graded
            selected["actual_home_win"] = pd.array(np.where(graded, hs > aw, pd.NA), dtype="boolean")

    for col in RESEARCH_COLUMNS:
        if col not in selected.columns:
            selected[col] = pd.NA
    return selected[RESEARCH_COLUMNS].sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)


def write_t120_market_research(output_dir: str | Path = "outputs") -> pd.DataFrame:
    out = Path(output_dir)
    run_path = out / "run_history.csv"
    official_path = out / "prediction_history.csv"
    if not run_path.exists():
        frame = pd.DataFrame(columns=RESEARCH_COLUMNS)
    else:
        runs = pd.read_csv(run_path)
        official = pd.read_csv(official_path) if official_path.exists() else None
        frame = select_t120_market_snapshots(runs, official)
    frame.to_csv(out / "market_t120_research.csv", index=False)
    return frame

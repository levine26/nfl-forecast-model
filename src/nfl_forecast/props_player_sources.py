from __future__ import annotations

"""Source adapter for the LevLine Props offensive player-state research lane."""

from dataclasses import dataclass
from typing import Iterable

import nflreadpy as nfl
import pandas as pd

from .data import load_advanced_data, load_core_data


@dataclass(frozen=True)
class OffensivePropsSources:
    schedules: pd.DataFrame
    roster: pd.DataFrame
    pbp: pd.DataFrame
    snap_counts: pd.DataFrame | None
    routes: pd.DataFrame | None
    source_status: dict[str, str]


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame.copy()


def add_nflverse_kickoff_timestamp(schedules: pd.DataFrame) -> pd.DataFrame:
    """Add a UTC ``kickoff`` column to nflverse schedule rows.

    nflverse schedule ``gametime`` values are the published Eastern-time NFL game
    times. The conversion is explicit so downstream pregame guards never rely on a
    naive timestamp. Existing timezone-aware ``kickoff`` values are preserved.
    """
    out = schedules.copy()
    if "kickoff" in out.columns:
        parsed = pd.to_datetime(out["kickoff"], utc=True, errors="coerce")
        if parsed.notna().any():
            out["kickoff"] = parsed
            return out

    if not {"gameday", "gametime"}.issubset(out.columns):
        out["kickoff"] = pd.NaT
        return out

    naive = pd.to_datetime(
        out["gameday"].astype("string") + " " + out["gametime"].astype("string"),
        errors="coerce",
    )
    eastern = naive.dt.tz_localize(
        "America/New_York",
        ambiguous="NaT",
        nonexistent="NaT",
    )
    out["kickoff"] = eastern.dt.tz_convert("UTC")
    return out


def load_offensive_props_sources(
    *,
    seasons: Iterable[int],
    current_season: int,
    cache_dir: str = ".cache/nflreadpy",
) -> OffensivePropsSources:
    """Load the safe default source bundle for the offensive Props research beta.

    This deliberately reuses the repository's existing schedule/PBP/advanced loaders.
    Route participation is not loaded by default because a trustworthy live in-season
    route source is not guaranteed by this repository; callers may supply a separately
    timestamp-qualified route frame to the player-state contract when available.
    """
    season_list = sorted(set(int(value) for value in seasons))
    if current_season not in season_list:
        season_list.append(int(current_season))
        season_list.sort()

    bundle = load_core_data(season_list, cache_dir=cache_dir)
    bundle = load_advanced_data(bundle, season_list)
    schedules = add_nflverse_kickoff_timestamp(bundle.schedules)
    roster = _pandas(nfl.load_rosters(current_season))
    if roster is None or roster.empty:
        raise ValueError(f"No nflverse roster rows available for {current_season}")

    return OffensivePropsSources(
        schedules=schedules,
        roster=roster,
        pbp=bundle.pbp,
        snap_counts=bundle.snap_counts,
        routes=None,
        source_status={
            "schedules": "nflverse_via_existing_core_loader",
            "roster": "nflverse_load_rosters",
            "pbp": "nflverse_via_existing_core_loader",
            "snap_counts": (
                "nflverse_via_existing_advanced_loader"
                if bundle.snap_counts is not None
                else "missing"
            ),
            "routes": "not_loaded_fail_closed",
        },
    )

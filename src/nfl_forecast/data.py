from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import nflreadpy as nfl
import pandas as pd


@dataclass
class NFLDataBundle:
    schedules: pd.DataFrame
    pbp: pd.DataFrame
    team_stats: pd.DataFrame | None = None
    ngs_passing: pd.DataFrame | None = None
    ftn: pd.DataFrame | None = None
    pfr_pass: pd.DataFrame | None = None
    snap_counts: pd.DataFrame | None = None
    depth_charts: pd.DataFrame | None = None


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def configure_cache(cache_dir: str) -> None:
    os.environ.setdefault("NFLREADPY_CACHE", "filesystem")
    os.environ.setdefault("NFLREADPY_CACHE_DIR", cache_dir)
    os.environ.setdefault("NFLREADPY_CACHE_DURATION", "21600")
    os.environ.setdefault("NFLREADPY_VERBOSE", "False")


def load_core_data(seasons: Iterable[int], cache_dir: str = ".cache/nflreadpy") -> NFLDataBundle:
    seasons = list(seasons)
    configure_cache(cache_dir)
    # nflreadpy can lag the live season by a package release. The underlying
    # nflverse schedule is a public CSV and is the authoritative live scaffold.
    schedules = pd.read_csv("https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv", low_memory=False)
    schedules = schedules[schedules["season"].isin(seasons)].copy()

    # Prefer nflreadpy for PBP. If its package-level current-season guard lags,
    # retry only the seasons it currently supports; the schedule/results/Elo layer
    # still remains live and the next package/data refresh automatically restores PBP.
    try:
        pbp = _pandas(nfl.load_pbp(seasons))
    except ValueError as exc:
        msg = str(exc)
        import re
        m = re.search(r"between 1999 and (\d{4})", msg)
        if not m:
            raise
        supported_max = int(m.group(1))
        supported = [y for y in seasons if y <= supported_max]
        if not supported:
            raise
        pbp = _pandas(nfl.load_pbp(supported))
    try:
        team_stats = _pandas(nfl.load_team_stats(seasons))
    except Exception:
        team_stats = None
    return NFLDataBundle(schedules=schedules, pbp=pbp, team_stats=team_stats)


def load_advanced_data(bundle: NFLDataBundle, seasons: Iterable[int]) -> NFLDataBundle:
    """Best-effort advanced loaders. Failure never blocks the Core model."""
    seasons = list(seasons)
    loaders = {
        "ngs_passing": lambda: nfl.load_nextgen_stats(seasons, stat_type="passing"),
        "ftn": lambda: nfl.load_ftn_charting(seasons),
        "pfr_pass": lambda: nfl.load_pfr_advstats(seasons, stat_type="pass", summary_level="week"),
        "snap_counts": lambda: nfl.load_snap_counts(seasons),
        "depth_charts": lambda: nfl.load_depth_charts(seasons),
    }
    for attr, fn in loaders.items():
        try:
            setattr(bundle, attr, _pandas(fn()))
        except Exception:
            setattr(bundle, attr, None)
    return bundle

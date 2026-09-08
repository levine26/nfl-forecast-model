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
    schedules = _pandas(nfl.load_schedules(seasons))
    pbp = _pandas(nfl.load_pbp(seasons))
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

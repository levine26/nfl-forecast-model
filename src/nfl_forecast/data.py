from __future__ import annotations

import os
import re
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


def _load_pbp_with_live_fallback(seasons: list[int]):
    """Load PBP, tolerating only a not-yet-published newest-season asset.

    nflreadpy has used two behaviors when its data backend lags the live season:
    an up-front ValueError guard and, more recently, a 404 from the nflverse PBP
    release URL. Both mean the schedule/results layer can be live while EPA/form
    remains through the latest published PBP season. Other download failures and
    missing historical seasons remain fatal.
    """
    try:
        return _pandas(nfl.load_pbp(seasons))
    except ValueError as exc:
        match = re.search(r"between 1999 and (\d{4})", str(exc))
        if not match:
            raise
        supported_max = int(match.group(1))
        supported = [season for season in seasons if season <= supported_max]
        if not supported:
            raise
        return _pandas(nfl.load_pbp(supported))
    except ConnectionError as exc:
        message = str(exc)
        match = re.search(r"play_by_play_(\d{4})\.parquet", message)
        if not match or "404" not in message:
            raise
        missing_season = int(match.group(1))
        if not seasons or missing_season != max(seasons):
            raise
        supported = [season for season in seasons if season < missing_season]
        if not supported:
            raise
        return _pandas(nfl.load_pbp(supported))


def load_core_data(seasons: Iterable[int], cache_dir: str = ".cache/nflreadpy") -> NFLDataBundle:
    seasons = list(seasons)
    configure_cache(cache_dir)
    # nflreadpy can lag the live season by a package release. The underlying
    # nflverse schedule is a public CSV and is the authoritative live scaffold.
    schedules = pd.read_csv("https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv", low_memory=False)
    schedules = schedules[schedules["season"].isin(seasons)].copy()

    # Keep the live schedule even when the newest PBP asset has not been published.
    # The pipeline records the resulting EPA/form horizon in data_state.
    pbp = _load_pbp_with_live_fallback(seasons)
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

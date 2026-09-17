from __future__ import annotations

"""Source adapter for the LevLine Props offensive player-state research lane."""

from dataclasses import dataclass
from typing import Any, Iterable

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
    source_status: dict[str, Any]


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame.copy()


def _timezone_aware_utc(value):
    try:
        if value is None or pd.isna(value):
            return pd.NaT
    except (TypeError, ValueError):
        return pd.NaT
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError):
        return pd.NaT
    if ts.tzinfo is None:
        return pd.NaT
    return ts.tz_convert("UTC")


def normalize_snap_counts_player_ids(
    snap_counts: pd.DataFrame | None,
    players: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Normalize snap-count identity to stable GSIS IDs or fail closed.

    nflverse snap counts are sourced from PFR and commonly expose
    pfr_player_id rather than the GSIS IDs used by PBP/rosters. The nflverse
    players table is the canonical crosswalk. Ambiguous PFR IDs are discarded
    instead of guessed.
    """
    audit: dict[str, Any] = {
        "status": "missing",
        "rows_received": 0,
        "rows_mapped": 0,
        "rows_unmapped": 0,
        "ambiguous_pfr_ids": 0,
    }
    if snap_counts is None or snap_counts.empty:
        return None, audit

    work = snap_counts.copy()
    audit["rows_received"] = int(len(work))
    direct_col = next(
        (column for column in ("player_id", "gsis_id", "nflverse_id") if column in work.columns),
        None,
    )
    if direct_col:
        ids = work[direct_col].astype("string").fillna("").str.strip()
        valid = ids.ne("") & ids.ne("<NA>") & ids.str.lower().ne("nan")
        work["player_id"] = ids.where(valid, pd.NA)
        audit["rows_mapped"] = int(valid.sum())
        audit["rows_unmapped"] = int((~valid).sum())
        audit["status"] = "direct_stable_id" if valid.any() else "unusable_no_mapped_rows"
        return (work if valid.any() else None), audit

    if "pfr_player_id" not in work.columns:
        audit["status"] = "unusable_missing_identity"
        audit["rows_unmapped"] = int(len(work))
        return None, audit

    if players is None or players.empty or not {"pfr_id", "gsis_id"}.issubset(players.columns):
        audit["status"] = "unusable_missing_crosswalk"
        audit["rows_unmapped"] = int(len(work))
        return None, audit

    crosswalk = players[["pfr_id", "gsis_id"]].copy()
    crosswalk["pfr_id"] = crosswalk["pfr_id"].astype("string").fillna("").str.strip()
    crosswalk["gsis_id"] = crosswalk["gsis_id"].astype("string").fillna("").str.strip()
    valid_crosswalk = (
        crosswalk["pfr_id"].ne("")
        & crosswalk["gsis_id"].ne("")
        & crosswalk["pfr_id"].ne("<NA>")
        & crosswalk["gsis_id"].ne("<NA>")
        & crosswalk["pfr_id"].str.lower().ne("nan")
        & crosswalk["gsis_id"].str.lower().ne("nan")
    )
    crosswalk = crosswalk[valid_crosswalk].copy()

    unique_targets = crosswalk.groupby("pfr_id", sort=False)["gsis_id"].nunique()
    ambiguous = set(unique_targets[unique_targets.gt(1)].index.astype(str))
    audit["ambiguous_pfr_ids"] = len(ambiguous)
    safe_crosswalk = crosswalk[~crosswalk["pfr_id"].isin(ambiguous)].drop_duplicates(
        "pfr_id", keep="last"
    )
    mapping = safe_crosswalk.set_index("pfr_id")["gsis_id"].to_dict()

    pfr_ids = work["pfr_player_id"].astype("string").fillna("").str.strip()
    work["player_id"] = pfr_ids.map(mapping).astype("string")
    mapped = work["player_id"].fillna("").str.strip()
    valid = mapped.ne("") & mapped.ne("<NA>") & mapped.str.lower().ne("nan")
    work.loc[~valid, "player_id"] = pd.NA
    audit["rows_mapped"] = int(valid.sum())
    audit["rows_unmapped"] = int((~valid).sum())
    audit["status"] = "pfr_to_gsis_crosswalk" if valid.any() else "unusable_no_mapped_rows"
    return (work if valid.any() else None), audit


def add_nflverse_kickoff_timestamp(schedules: pd.DataFrame) -> pd.DataFrame:
    """Add a UTC ``kickoff`` column to nflverse schedule rows.

    nflverse schedule ``gametime`` values are the published Eastern-time NFL game
    times. The conversion is explicit so downstream pregame guards never rely on a
    naive timestamp. Existing timezone-aware ``kickoff`` values are preserved.
    """
    out = schedules.copy()
    existing = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    if "kickoff" in out.columns:
        existing = pd.to_datetime(
            out["kickoff"].map(_timezone_aware_utc),
            utc=True,
            errors="coerce",
        )

    if not {"gameday", "gametime"}.issubset(out.columns):
        out["kickoff"] = existing
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
    derived = eastern.dt.tz_convert("UTC")
    out["kickoff"] = existing.where(existing.notna(), derived)
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

    raw_snap_counts = bundle.snap_counts
    identity_crosswalk = roster if {"pfr_id", "gsis_id"}.issubset(roster.columns) else None
    crosswalk_error = None
    if (
        raw_snap_counts is not None
        and not raw_snap_counts.empty
        and not any(
            column in raw_snap_counts.columns
            for column in ("player_id", "gsis_id", "nflverse_id")
        )
        and "pfr_player_id" in raw_snap_counts.columns
        and identity_crosswalk is None
    ):
        try:
            identity_crosswalk = _pandas(nfl.load_players())
        except Exception as exc:
            crosswalk_error = str(exc)[:240]

    snap_counts, snap_status = normalize_snap_counts_player_ids(
        raw_snap_counts,
        identity_crosswalk,
    )
    if crosswalk_error:
        snap_status["crosswalk_error"] = crosswalk_error

    return OffensivePropsSources(
        schedules=schedules,
        roster=roster,
        pbp=bundle.pbp,
        snap_counts=snap_counts,
        routes=None,
        source_status={
            "schedules": {"status": "loaded", "provider": "nflverse_via_existing_core_loader"},
            "roster": {"status": "loaded", "provider": "nflverse_load_rosters"},
            "pbp": {
                "status": "loaded" if bundle.pbp is not None and not bundle.pbp.empty else "missing",
                "provider": "nflverse_via_existing_core_loader",
            },
            "snap_counts": snap_status,
            "routes": {"status": "not_loaded_fail_closed"},
        },
    )

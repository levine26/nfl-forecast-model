from __future__ import annotations

"""Source adapter for the LevLine Props offensive player-state research lane."""

from dataclasses import dataclass
from typing import Any, Iterable

import nflreadpy as nfl
import pandas as pd

from .data import load_advanced_data, load_core_data
from .props_player_state import normalize_team_code


@dataclass(frozen=True)
class OffensivePropsSources:
    schedules: pd.DataFrame
    roster: pd.DataFrame
    pbp: pd.DataFrame
    snap_counts: pd.DataFrame | None
    depth_charts: pd.DataFrame | None
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



def resolve_primary_qbs_from_depth_charts(
    depth_charts: pd.DataFrame | None,
    player_state: pd.DataFrame,
    *,
    game_id: str,
    forecast_timestamp: object,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Resolve point-in-time QB1 identities from timestamped 2025+ nflverse depth charts.

    Only timestamped rows at or before the forecast are eligible. Ambiguous rank-1 rows,
    missing stable GSIS IDs, future snapshots, and IDs not present as QBs in the canonical
    game player-state contract are rejected rather than guessed.
    """

    audit: dict[str, Any] = {
        "status": "missing",
        "rows_received": 0,
        "future_rows_discarded": 0,
        "invalid_timestamp_rows": 0,
        "teams_resolved": 0,
        "teams_ambiguous": [],
        "teams_missing": [],
    }
    if depth_charts is None or depth_charts.empty:
        return {}, audit
    required = {"dt", "team", "gsis_id", "pos_rank"}
    if not required.issubset(depth_charts.columns):
        audit["status"] = "unusable_missing_timestamped_2025_schema"
        return {}, audit

    forecast = pd.Timestamp(forecast_timestamp)
    if forecast.tzinfo is None:
        raise ValueError("depth-chart forecast_timestamp must be timezone-aware")
    forecast = forecast.tz_convert("UTC")

    work = depth_charts.copy()
    audit["rows_received"] = int(len(work))
    parsed: list[pd.Timestamp | pd.NaT] = []
    for value in work["dt"]:
        try:
            ts = pd.Timestamp(value)
        except Exception:
            ts = pd.NaT
        if pd.isna(ts) or ts.tzinfo is None:
            parsed.append(pd.NaT)
        else:
            parsed.append(ts.tz_convert("UTC"))
    work["_dt"] = pd.to_datetime(parsed, utc=True, errors="coerce")
    audit["invalid_timestamp_rows"] = int(work["_dt"].isna().sum())
    future = work["_dt"].gt(forecast)
    audit["future_rows_discarded"] = int(future.fillna(False).sum())
    work = work[work["_dt"].notna() & ~future].copy()
    if work.empty:
        audit["status"] = "unusable_no_pregame_rows"
        return {}, audit

    work["_team"] = work["team"].map(normalize_team_code)
    position_col = next(
        (
            column
            for column in ("pos_abb", "pos_grp", "pos_name", "position")
            if column in work.columns
        ),
        None,
    )
    if position_col is None:
        audit["status"] = "unusable_missing_position"
        return {}, audit
    position_text = work[position_col].astype("string").fillna("").str.upper().str.strip()
    work = work[position_text.eq("QB")].copy()
    if work.empty:
        audit["status"] = "unusable_no_qb_rows"
        return {}, audit

    state = player_state[player_state["game_id"].astype(str).eq(str(game_id))].copy()
    if state.empty:
        raise ValueError(f"player_state has no rows for game={game_id}")
    state["_team"] = state["team"].map(normalize_team_code)
    qb_state = state[
        state["position"].astype("string").fillna("").str.upper().eq("QB")
    ].copy()
    if "expected_active_state" in qb_state.columns:
        qb_state = qb_state[
            ~qb_state["expected_active_state"].astype("string").fillna("UNKNOWN").str.upper().eq("OUT")
        ].copy()
    if "roster_membership_state" in qb_state.columns:
        qb_state = qb_state[
            ~qb_state["roster_membership_state"].astype("string").fillna("UNKNOWN").isin(
                {"RESERVE_OR_UNAVAILABLE", "INACTIVE_ROSTER"}
            )
        ].copy()
    state_ids = {
        (str(row["_team"]), str(row["player_id"]))
        for _, row in qb_state.iterrows()
    }
    state_availability = {
        (str(row["_team"]), str(row["player_id"])): str(
            row.get("expected_active_state") or "UNKNOWN"
        ).upper()
        for _, row in qb_state.iterrows()
    }
    game_teams = sorted(set(state["_team"].astype(str)))
    resolved: dict[str, dict[str, str]] = {}

    for team in game_teams:
        rows = work[work["_team"].eq(team)].copy()
        if rows.empty:
            audit["teams_missing"].append(team)
            continue
        latest = rows["_dt"].max()
        rows = rows[rows["_dt"].eq(latest)].copy()
        rank = pd.to_numeric(rows["pos_rank"], errors="coerce")
        rows = rows[rank.notna()].copy()
        if rows.empty:
            audit["teams_missing"].append(team)
            continue
        rows["_rank"] = pd.to_numeric(rows["pos_rank"], errors="coerce")
        rows["_gsis_id"] = rows["gsis_id"].astype("string").fillna("").str.strip()
        rows = rows[
            rows.apply(lambda row: (team, str(row["_gsis_id"])) in state_ids, axis=1)
        ].copy()
        if rows.empty:
            audit["teams_missing"].append(team)
            continue
        rows["_active_state"] = rows["_gsis_id"].map(
            lambda value: state_availability.get((team, str(value)), "UNKNOWN")
        )
        non_doubtful = rows[~rows["_active_state"].eq("DOUBTFUL")].copy()
        if not non_doubtful.empty:
            rows = non_doubtful
        best_rank = float(rows["_rank"].min())
        candidates = rows[rows["_rank"].eq(best_rank)]["_gsis_id"]
        candidate_ids = sorted(
            {
                str(value)
                for value in candidates
                if value and value != "<NA>" and str(value).lower() != "nan"
            }
        )
        if len(candidate_ids) != 1:
            audit["teams_ambiguous"].append(
                {
                    "team": team,
                    "snapshot_utc": pd.Timestamp(latest).isoformat(),
                    "candidate_ids": candidate_ids,
                }
            )
            continue
        player_id = candidate_ids[0]
        resolved[team] = {
            "player_id": player_id,
            "provenance": (
                "nflverse_timestamped_depth_chart:"
                f"{pd.Timestamp(latest).isoformat()}:pos_rank={best_rank:g}"
            ),
        }

    audit["teams_resolved"] = len(resolved)
    audit["status"] = "qualified" if resolved else "unresolved"
    return resolved, audit


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
        depth_charts=bundle.depth_charts,
        routes=None,
        source_status={
            "schedules": {"status": "loaded", "provider": "nflverse_via_existing_core_loader"},
            "roster": {"status": "loaded", "provider": "nflverse_load_rosters"},
            "pbp": {
                "status": "loaded" if bundle.pbp is not None and not bundle.pbp.empty else "missing",
                "provider": "nflverse_via_existing_core_loader",
            },
            "snap_counts": snap_status,
            "depth_charts": {
                "status": "loaded"
                if bundle.depth_charts is not None and not bundle.depth_charts.empty
                else "missing",
                "provider": "nflverse_load_depth_charts",
            },
            "routes": {"status": "not_loaded_fail_closed"},
        },
    )

from __future__ import annotations

"""Canonical offensive player-state contract for the LevLine Props research beta.

This module is intentionally separate from the failed v0.9A player-value formulation.
It builds point-in-time-safe player usage state for downstream opportunity, efficiency,
and simulation lanes. Historical usage is restricted to games from weeks strictly
before the target week; current availability evidence must carry a capture timestamp.
"""

from dataclasses import dataclass
import math
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd

SCHEMA_VERSION = "levline_props_player_state.v1"
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
TEAM_NORMALIZATION = {"JAC": "JAX"}
NON_ROSTER_STATUSES = frozenset(
    {"CUT", "UFA", "RFA", "NWT", "RET", "TRC", "TRD", "TRL", "TRT", "RSR"}
)

CORE_COLUMNS = (
    "schema_version",
    "game_id",
    "player_id",
    "player_name",
    "position",
    "team",
    "opponent",
    "forecast_timestamp",
    "history_policy",
    "expected_active_state",
    "availability_source_status",
    "availability_prospective_only",
    "expected_role",
    "prior_games",
    "prior_dropbacks_pg_4",
    "prior_pass_attempts_pg_4",
    "prior_rush_attempts_pg_4",
    "prior_carries_pg_4",
    "prior_targets_pg_4",
    "prior_receptions_pg_4",
    "prior_carry_share_4",
    "prior_target_share_4",
    "prior_offense_snaps_pg_4",
    "prior_snap_share_4",
    "prior_routes_pg_4",
    "prior_route_participation_4",
    "prior_targets_per_route_4",
    "prior_qb_rushes_per_dropback_4",
    "prior_reception_rate_4",
    "prior_red_zone_carries_pg_4",
    "prior_goal_line_carries_pg_4",
    "prior_red_zone_targets_pg_4",
    "prior_end_zone_targets_pg_4",
    "missing_history",
    "missing_usage_history",
    "missing_snap_data",
    "missing_route_data",
    "missing_availability",
    "data_quality_state",
)


@dataclass(frozen=True)
class OffensivePlayerStateBuild:
    player_state: pd.DataFrame
    audit: dict[str, Any]


def _scalar_text(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def normalize_team_code(value: Any) -> str:
    code = _scalar_text(value).upper().strip()
    return TEAM_NORMALIZATION.get(code, code)


def normalize_player_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _scalar_text(value).lower())


def _first_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _number(frame: pd.DataFrame, column: str | None, default: float = 0.0) -> pd.Series:
    if not column or column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _text(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in frame.columns:
        return pd.Series("", index=frame.index, dtype="string")
    return frame[column].astype("string").fillna("")


def _valid_id(series: pd.Series) -> pd.Series:
    value = series.astype("string").fillna("").str.strip()
    return value.ne("") & value.ne("<NA>") & value.str.lower().ne("nan")


def _utc_timestamp(value: Any, *, label: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return ts.tz_convert("UTC")


def _optional_utc_timestamp(value: Any) -> pd.Timestamp:
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


def _normalize_roster(roster: pd.DataFrame) -> pd.DataFrame:
    if roster is None or roster.empty:
        raise ValueError("Current roster is required for stable offensive-player identity")

    id_col = _first_column(roster, ("player_id", "gsis_id", "nflverse_id"))
    name_col = _first_column(roster, ("player_name", "full_name", "display_name", "football_name"))
    pos_col = _first_column(roster, ("position", "position_group"))
    team_col = _first_column(roster, ("team", "recent_team", "club_code"))
    status_col = _first_column(
        roster,
        ("status", "roster_status", "status_description_abbr"),
    )
    missing = [
        label
        for label, col in (
            ("stable player ID", id_col),
            ("player name", name_col),
            ("position", pos_col),
            ("team", team_col),
        )
        if col is None
    ]
    if missing:
        raise ValueError(f"Roster missing required identity fields: {', '.join(missing)}")

    out = pd.DataFrame(
        {
            "player_id": _text(roster, id_col).str.strip(),
            "player_name": _text(roster, name_col).str.strip(),
            "position": _text(roster, pos_col).str.upper().str.strip(),
            "team": _text(roster, team_col).map(normalize_team_code),
            "roster_status_raw": _text(roster, status_col).str.upper().str.strip(),
        }
    )
    out = out[_valid_id(out["player_id"]) & out["position"].isin(SUPPORTED_POSITIONS)].copy()
    out = out[out["team"].ne("") & out["player_name"].ne("")].copy()
    out = out[~out["roster_status_raw"].isin(NON_ROSTER_STATUSES)].copy()

    status = out["roster_status_raw"]
    out["roster_membership_state"] = np.select(
        [
            status.eq("ACT"),
            status.eq("DEV"),
            status.eq("INA"),
            status.isin({"RES", "PUP", "SUS", "EXE", "E14", "RSN"}),
            status.eq(""),
        ],
        [
            "ACTIVE_ROSTER",
            "PRACTICE_SQUAD",
            "INACTIVE_ROSTER",
            "RESERVE_OR_UNAVAILABLE",
            "UNKNOWN",
        ],
        default="OTHER",
    )

    conflicts: list[str] = []
    for player_id, group in out.groupby("player_id", sort=False):
        if group[["player_name", "position", "team"]].drop_duplicates().shape[0] > 1:
            conflicts.append(str(player_id))
    if conflicts:
        sample = ", ".join(conflicts[:5])
        raise ValueError(f"Stable identity ambiguity for roster player_id(s): {sample}")

    return out.drop_duplicates("player_id", keep="last").reset_index(drop=True)


def _normalize_schedule(
    schedules: pd.DataFrame,
    *,
    season: int,
    week: int,
) -> pd.DataFrame:
    required = {"game_id", "home_team", "away_team"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"Schedules missing required columns: {sorted(missing)}")
    games = schedules.copy()
    if "season" in games.columns:
        games = games[pd.to_numeric(games["season"], errors="coerce").eq(season)]
    if "week" in games.columns:
        games = games[pd.to_numeric(games["week"], errors="coerce").eq(week)]
    if games.empty:
        raise ValueError(f"No schedule rows for season={season}, week={week}")

    games["home_team"] = games["home_team"].map(normalize_team_code)
    games["away_team"] = games["away_team"].map(normalize_team_code)
    if games["game_id"].astype("string").duplicated().any():
        raise ValueError("Duplicate game_id in target schedule")

    kickoff_col = _first_column(
        games,
        ("kickoff", "game_datetime", "start_time", "game_start", "datetime"),
    )
    if kickoff_col:
        games["kickoff_timestamp"] = pd.to_datetime(
            games[kickoff_col].map(_optional_utc_timestamp),
            utc=True,
            errors="coerce",
        )
    else:
        games["kickoff_timestamp"] = pd.NaT

    home = games[["game_id", "home_team", "away_team", "kickoff_timestamp"]].rename(
        columns={"home_team": "team", "away_team": "opponent"}
    )
    away = games[["game_id", "away_team", "home_team", "kickoff_timestamp"]].rename(
        columns={"away_team": "team", "home_team": "opponent"}
    )
    team_games = pd.concat([home, away], ignore_index=True)
    duplicate_team = team_games["team"].duplicated(keep=False)
    if duplicate_team.any():
        teams = sorted(team_games.loc[duplicate_team, "team"].unique())
        raise ValueError(f"Target schedule maps team to multiple games: {teams}")
    return team_games


def _historical_pbp_usage(
    pbp: pd.DataFrame | None,
    *,
    season: int,
    week: int,
) -> pd.DataFrame:
    metrics = [
        "dropbacks",
        "pass_attempts",
        "rush_attempts",
        "targets",
        "receptions",
        "red_zone_carries",
        "goal_line_carries",
        "red_zone_targets",
        "end_zone_targets",
    ]
    columns = ["game_id", "season", "week", "team", "player_id", "player_name", *metrics]
    if pbp is None or pbp.empty:
        return pd.DataFrame(columns=columns)

    required = {"game_id", "season", "week", "posteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing historical player-state keys: {sorted(missing)}")

    work = pbp.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    safe = work["season"].lt(season) | (work["season"].eq(season) & work["week"].lt(week))
    work = work[safe & work["season"].notna() & work["week"].notna()].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["season"] = work["season"].astype(int)
    work["week"] = work["week"].astype(int)
    work["team"] = work["posteam"].map(normalize_team_code)

    yardline = _number(work, "yardline_100", np.nan)
    red_zone = yardline.le(20)
    goal_line = yardline.le(5)
    air_yards = _number(work, "air_yards", np.nan)

    frames: list[pd.DataFrame] = []

    passer_id = _text(work, _first_column(work, ("passer_player_id", "passer_id")))
    passer_name = _text(work, _first_column(work, ("passer_player_name", "passer_name")))
    pass_attempt = _number(work, "pass_attempt").eq(1)
    sack = _number(work, "sack").eq(1)
    passer_mask = _valid_id(passer_id) & (pass_attempt | sack)
    if passer_mask.any():
        part = work.loc[passer_mask, ["game_id", "season", "week", "team"]].copy()
        part["player_id"] = passer_id.loc[passer_mask].astype(str).str.strip()
        part["player_name"] = passer_name.loc[passer_mask].astype(str).str.strip()
        part["dropbacks"] = 1.0
        part["pass_attempts"] = pass_attempt.loc[passer_mask].astype(float).to_numpy()
        for metric in metrics[2:]:
            part[metric] = 0.0
        frames.append(part)

    rusher_id = _text(work, _first_column(work, ("rusher_player_id", "rusher_id")))
    rusher_name = _text(work, _first_column(work, ("rusher_player_name", "rusher_name")))
    rush_attempt = _number(work, "rush_attempt").eq(1)
    rusher_mask = _valid_id(rusher_id) & rush_attempt
    if rusher_mask.any():
        part = work.loc[rusher_mask, ["game_id", "season", "week", "team"]].copy()
        part["player_id"] = rusher_id.loc[rusher_mask].astype(str).str.strip()
        part["player_name"] = rusher_name.loc[rusher_mask].astype(str).str.strip()
        part["dropbacks"] = 0.0
        part["pass_attempts"] = 0.0
        part["rush_attempts"] = 1.0
        part["targets"] = 0.0
        part["receptions"] = 0.0
        part["red_zone_carries"] = red_zone.loc[rusher_mask].fillna(False).astype(float).to_numpy()
        part["goal_line_carries"] = goal_line.loc[rusher_mask].fillna(False).astype(float).to_numpy()
        part["red_zone_targets"] = 0.0
        part["end_zone_targets"] = 0.0
        frames.append(part)

    receiver_id = _text(work, _first_column(work, ("receiver_player_id", "receiver_id")))
    receiver_name = _text(work, _first_column(work, ("receiver_player_name", "receiver_name")))
    receiver_mask = _valid_id(receiver_id)
    if receiver_mask.any():
        part = work.loc[receiver_mask, ["game_id", "season", "week", "team"]].copy()
        part["player_id"] = receiver_id.loc[receiver_mask].astype(str).str.strip()
        part["player_name"] = receiver_name.loc[receiver_mask].astype(str).str.strip()
        part["dropbacks"] = 0.0
        part["pass_attempts"] = 0.0
        part["rush_attempts"] = 0.0
        part["targets"] = 1.0
        part["receptions"] = (
            _number(work, "complete_pass").loc[receiver_mask].eq(1).astype(float).to_numpy()
        )
        part["red_zone_carries"] = 0.0
        part["goal_line_carries"] = 0.0
        part["red_zone_targets"] = red_zone.loc[receiver_mask].fillna(False).astype(float).to_numpy()
        end_zone = air_yards.ge(yardline) & yardline.notna() & air_yards.notna()
        part["end_zone_targets"] = (
            end_zone.loc[receiver_mask].fillna(False).astype(float).to_numpy()
        )
        frames.append(part)

    if not frames:
        return pd.DataFrame(columns=columns)

    events = pd.concat(frames, ignore_index=True)
    keys = ["game_id", "season", "week", "team", "player_id"]
    grouped = (
        events.groupby(keys, as_index=False, sort=False)
        .agg(
            player_name=("player_name", "last"),
            **{metric: (metric, "sum") for metric in metrics},
        )
    )
    return grouped


def _normalize_participation(
    frame: pd.DataFrame | None,
    *,
    season: int,
    week: int,
    kind: str,
) -> pd.DataFrame:
    empty_columns = [
        "game_id",
        "season",
        "week",
        "player_id",
        "offense_snaps",
        "snap_share",
        "routes",
        "route_participation",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=empty_columns)

    id_col = _first_column(frame, ("player_id", "gsis_id", "nflverse_id"))
    if id_col is None or "game_id" not in frame.columns:
        return pd.DataFrame(columns=empty_columns)
    work = frame.copy()
    if "season" not in work.columns or "week" not in work.columns:
        return pd.DataFrame(columns=empty_columns)
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    safe = work["season"].lt(season) | (work["season"].eq(season) & work["week"].lt(week))
    work = work[safe].copy()
    work["player_id"] = _text(work, id_col).str.strip()
    work = work[_valid_id(work["player_id"])].copy()
    if work.empty:
        return pd.DataFrame(columns=empty_columns)

    out = work[["game_id", "season", "week", "player_id"]].copy()
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    if kind == "snaps":
        snap_col = _first_column(work, ("offense_snaps", "offensive_snaps", "off_snaps"))
        share_col = _first_column(
            work,
            ("offense_pct", "offensive_snap_pct", "offense_snaps_pct", "snap_share"),
        )
        out["offense_snaps"] = _number(work, snap_col, np.nan)
        share = _number(work, share_col, np.nan)
        out["snap_share"] = np.where(share.gt(1.0), share / 100.0, share)
        out["routes"] = np.nan
        out["route_participation"] = np.nan
    elif kind == "routes":
        routes_col = _first_column(work, ("routes", "route_count", "pass_routes"))
        participation_col = _first_column(
            work,
            ("route_participation", "route_participation_rate", "route_pct"),
        )
        out["routes"] = _number(work, routes_col, np.nan)
        share = _number(work, participation_col, np.nan)
        out["route_participation"] = np.where(share.gt(1.0), share / 100.0, share)
        out["offense_snaps"] = np.nan
        out["snap_share"] = np.nan
    else:
        raise ValueError(f"Unknown participation kind: {kind}")
    return out


def _combine_history(
    pbp: pd.DataFrame | None,
    snap_counts: pd.DataFrame | None,
    routes: pd.DataFrame | None,
    *,
    season: int,
    week: int,
) -> pd.DataFrame:
    usage = _historical_pbp_usage(pbp, season=season, week=week)
    snaps = _normalize_participation(snap_counts, season=season, week=week, kind="snaps")
    route_rows = _normalize_participation(routes, season=season, week=week, kind="routes")

    keys = ["game_id", "season", "week", "player_id"]
    history = usage.copy()
    for piece in (snaps, route_rows):
        if piece.empty:
            continue
        keep = [column for column in piece.columns if column in keys or piece[column].notna().any()]
        piece = piece[keep].copy()
        if history.empty:
            history = piece
        else:
            history = history.merge(piece, on=keys, how="outer", validate="one_to_one")

    if history.empty:
        return history

    if "team" not in history.columns:
        history["team"] = ""
    if "player_name" not in history.columns:
        history["player_name"] = ""

    numeric = [
        "dropbacks",
        "pass_attempts",
        "rush_attempts",
        "targets",
        "receptions",
        "red_zone_carries",
        "goal_line_carries",
        "red_zone_targets",
        "end_zone_targets",
        "offense_snaps",
        "snap_share",
        "routes",
        "route_participation",
    ]
    for column in numeric:
        if column not in history.columns:
            history[column] = np.nan

    # Participation sources can publish when PBP does not. In that case, absence of a
    # PBP row is missing evidence, not zero usage. Fill PBP-derived opportunity metrics
    # with zero only for games whose PBP is actually present in the source horizon.
    pbp_game_ids: set[str] = set()
    if (
        pbp is not None
        and not pbp.empty
        and {"game_id", "season", "week"}.issubset(pbp.columns)
    ):
        period = pbp[["game_id", "season", "week"]].copy()
        period["season"] = pd.to_numeric(period["season"], errors="coerce")
        period["week"] = pd.to_numeric(period["week"], errors="coerce")
        safe_period = period["season"].lt(season) | (
            period["season"].eq(season) & period["week"].lt(week)
        )
        pbp_game_ids = set(
            period.loc[safe_period & period["game_id"].notna(), "game_id"].astype(str)
        )
    history["pbp_game_covered"] = history["game_id"].astype(str).isin(pbp_game_ids)

    pbp_metrics = (
        "dropbacks",
        "pass_attempts",
        "rush_attempts",
        "targets",
        "receptions",
        "red_zone_carries",
        "goal_line_carries",
        "red_zone_targets",
        "end_zone_targets",
    )
    for column in pbp_metrics:
        values = pd.to_numeric(history[column], errors="coerce")
        history[column] = values
        covered = history["pbp_game_covered"]
        history.loc[covered, column] = values.loc[covered].fillna(0.0)

    team_totals = (
        history.groupby(["game_id", "team"], as_index=False)
        .agg(
            team_rush_attempts=("rush_attempts", "sum"),
            team_targets=("targets", "sum"),
        )
    )
    history = history.merge(team_totals, on=["game_id", "team"], how="left")
    history["carry_share"] = np.where(
        history["team_rush_attempts"].gt(0),
        history["rush_attempts"] / history["team_rush_attempts"],
        np.nan,
    )
    history["target_share"] = np.where(
        history["team_targets"].gt(0),
        history["targets"] / history["team_targets"],
        np.nan,
    )
    return history.sort_values(["player_id", "season", "week", "game_id"]).reset_index(drop=True)


def _summary_for_player(group: pd.DataFrame) -> dict[str, Any]:
    group = group.sort_values(["season", "week", "game_id"])
    last4 = group.tail(4)
    observed = group[
        [
            "dropbacks",
            "pass_attempts",
            "rush_attempts",
            "targets",
            "receptions",
            "offense_snaps",
            "routes",
        ]
    ].fillna(0.0).sum(axis=1).gt(0)
    observed_games = group.loc[observed]
    last_game = observed_games.tail(1)

    def mean(column: str) -> float:
        values = pd.to_numeric(last4[column], errors="coerce")
        return float(values.mean()) if values.notna().any() else math.nan

    def ratio(num: str, den: str) -> float:
        numerator = pd.to_numeric(last4[num], errors="coerce").sum(min_count=1)
        denominator = pd.to_numeric(last4[den], errors="coerce").sum(min_count=1)
        if pd.isna(numerator) or pd.isna(denominator) or denominator <= 0:
            return math.nan
        return float(numerator / denominator)

    return {
        "prior_games": int(observed_games["game_id"].nunique()),
        "history_last_season": (
            int(last_game.iloc[-1]["season"]) if not last_game.empty else pd.NA
        ),
        "history_last_week": int(last_game.iloc[-1]["week"]) if not last_game.empty else pd.NA,
        "prior_dropbacks_pg_4": mean("dropbacks"),
        "prior_pass_attempts_pg_4": mean("pass_attempts"),
        "prior_rush_attempts_pg_4": mean("rush_attempts"),
        "prior_carries_pg_4": mean("rush_attempts"),
        "prior_targets_pg_4": mean("targets"),
        "prior_receptions_pg_4": mean("receptions"),
        "prior_carry_share_4": mean("carry_share"),
        "prior_target_share_4": mean("target_share"),
        "prior_offense_snaps_pg_4": mean("offense_snaps"),
        "prior_snap_share_4": mean("snap_share"),
        "prior_routes_pg_4": mean("routes"),
        "prior_route_participation_4": mean("route_participation"),
        "prior_targets_per_route_4": ratio("targets", "routes"),
        "prior_qb_rushes_per_dropback_4": ratio("rush_attempts", "dropbacks"),
        "prior_reception_rate_4": ratio("receptions", "targets"),
        "prior_red_zone_carries_pg_4": mean("red_zone_carries"),
        "prior_goal_line_carries_pg_4": mean("goal_line_carries"),
        "prior_red_zone_targets_pg_4": mean("red_zone_targets"),
        "prior_end_zone_targets_pg_4": mean("end_zone_targets"),
    }


def _summarize_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["player_id", "prior_games"])
    rows: list[dict[str, Any]] = []
    for player_id, group in history.groupby("player_id", sort=False):
        row = {"player_id": str(player_id)}
        row.update(_summary_for_player(group))
        rows.append(row)
    return pd.DataFrame(rows)


def _role_for_row(row: pd.Series) -> str:
    position = str(row.get("position") or "")
    games = int(row.get("prior_games") or 0)
    if games <= 0:
        return "UNKNOWN_NO_HISTORY"
    if position == "QB":
        dropbacks = float(row.get("prior_dropbacks_pg_4") or 0.0)
        return "QB_PRIMARY" if dropbacks >= 15.0 else "QB_RESERVE"
    if position == "RB":
        carry_share = row.get("prior_carry_share_4")
        target_share = row.get("prior_target_share_4")
        carry_share = 0.0 if pd.isna(carry_share) else float(carry_share)
        target_share = 0.0 if pd.isna(target_share) else float(target_share)
        if carry_share >= 0.45:
            return "RB_LEAD"
        if carry_share >= 0.20 or target_share >= 0.10:
            return "RB_ROTATION"
        return "RB_DEPTH"
    if position == "WR":
        target_share = row.get("prior_target_share_4")
        target_share = 0.0 if pd.isna(target_share) else float(target_share)
        if target_share >= 0.22:
            return "WR_PRIMARY"
        if target_share >= 0.12:
            return "WR_REGULAR"
        return "WR_ROTATION"
    if position == "TE":
        target_share = row.get("prior_target_share_4")
        target_share = 0.0 if pd.isna(target_share) else float(target_share)
        if target_share >= 0.16:
            return "TE_PRIMARY"
        if target_share >= 0.07:
            return "TE_ROTATION"
        return "TE_DEPTH"
    return "UNSUPPORTED"


def _availability_state(raw_status: str, game_status: str) -> str:
    combined = f"{raw_status} {game_status}".strip().lower()
    if any(token in combined for token in ("out", "inactive", "injured reserve", "ir")):
        return "OUT"
    if "doubtful" in combined:
        return "DOUBTFUL"
    if "questionable" in combined:
        return "QUESTIONABLE"
    if any(token in combined for token in ("active", "available", "no injury status")):
        return "AVAILABLE"
    return "UNKNOWN"


def flatten_current_injury_report(
    injuries: dict[str, list[dict[str, Any]]],
    source_meta: dict[str, Any],
) -> pd.DataFrame:
    """Flatten the existing NFL.com injury adapter without inventing stable IDs.

    The returned rows carry the source capture timestamp. Stable-ID resolution happens
    later against the current roster and therefore fails closed on duplicate names.
    """
    captured_at = source_meta.get("as_of")
    if not captured_at:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for team, players in injuries.items():
        for player in players:
            rows.append(
                {
                    "team": normalize_team_code(team),
                    "name": player.get("name", ""),
                    "position": player.get("position", ""),
                    "status": player.get("status", ""),
                    "game_status": player.get("game_status", ""),
                    "practice_status": player.get("practice_status", ""),
                    "source_name": player.get("source_name", source_meta.get("provider", "")),
                    "source_url": player.get("source_url", source_meta.get("source", "")),
                    "captured_at": captured_at,
                }
            )
    return pd.DataFrame(rows)


def _resolve_availability(
    availability: pd.DataFrame | None,
    roster: pd.DataFrame,
    *,
    forecast_timestamp: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    output_columns = [
        "player_id",
        "expected_active_state",
        "availability_status_raw",
        "practice_status_raw",
        "availability_capture_timestamp",
        "availability_source_name",
        "availability_source_status",
        "availability_prospective_only",
    ]
    audit = {
        "rows_received": 0,
        "rows_future_discarded": 0,
        "rows_missing_timestamp": 0,
        "rows_unresolved_identity": 0,
        "rows_ambiguous_identity": 0,
        "rows_resolved": 0,
        "conflicting_latest_rows": 0,
    }
    if availability is None or availability.empty:
        return pd.DataFrame(columns=output_columns), audit

    work = availability.copy()
    audit["rows_received"] = int(len(work))
    capture_col = _first_column(work, ("captured_at", "as_of", "timestamp"))
    if capture_col is None:
        audit["rows_missing_timestamp"] = int(len(work))
        return pd.DataFrame(columns=output_columns), audit

    captures = pd.to_datetime(work[capture_col], utc=True, errors="coerce")
    missing_time = captures.isna()
    audit["rows_missing_timestamp"] = int(missing_time.sum())
    future = captures.gt(forecast_timestamp)
    audit["rows_future_discarded"] = int(future.sum())
    work = work[~missing_time & ~future].copy()
    captures = captures[~missing_time & ~future]
    if work.empty:
        return pd.DataFrame(columns=output_columns), audit
    work["_captured_at"] = captures

    roster_lookup: dict[tuple[str, str], list[str]] = {}
    for _, row in roster.iterrows():
        key = (normalize_team_code(row["team"]), normalize_player_name(row["player_name"]))
        roster_lookup.setdefault(key, []).append(str(row["player_id"]))

    id_col = _first_column(work, ("player_id", "gsis_id", "nflverse_id"))
    name_col = _first_column(work, ("player_name", "name", "full_name", "display_name"))
    team_col = _first_column(work, ("team", "club", "recent_team"))
    resolved: list[str | None] = []
    for _, row in work.iterrows():
        candidate = _scalar_text(row.get(id_col, "")).strip() if id_col else ""
        team = normalize_team_code(row.get(team_col, "")) if team_col else ""
        if candidate:
            matched = roster[roster["player_id"].eq(candidate)]
            if len(matched) == 1 and (not team or str(matched.iloc[0]["team"]) == team):
                resolved.append(candidate)
                continue
            audit["rows_unresolved_identity"] += 1
            resolved.append(None)
            continue
        if not name_col or not team:
            audit["rows_unresolved_identity"] += 1
            resolved.append(None)
            continue
        key = (team, normalize_player_name(row.get(name_col)))
        candidates = roster_lookup.get(key, [])
        if len(candidates) == 1:
            resolved.append(candidates[0])
        elif len(candidates) > 1:
            audit["rows_ambiguous_identity"] += 1
            resolved.append(None)
        else:
            audit["rows_unresolved_identity"] += 1
            resolved.append(None)

    work["_player_id"] = resolved
    work = work[work["_player_id"].notna()].copy()
    if work.empty:
        return pd.DataFrame(columns=output_columns), audit

    status_col = _first_column(work, ("status", "designation", "availability_status"))
    game_status_col = _first_column(work, ("game_status",))
    practice_col = _first_column(work, ("practice_status",))
    source_col = _first_column(work, ("source_name", "provider", "source"))

    rows: list[dict[str, Any]] = []
    for player_id, group in work.groupby("_player_id", sort=False):
        latest_time = group["_captured_at"].max()
        latest = group[group["_captured_at"].eq(latest_time)]
        signatures = set(
            zip(
                _text(latest, status_col).astype(str),
                _text(latest, game_status_col).astype(str),
                _text(latest, practice_col).astype(str),
            )
        )
        if len(signatures) > 1:
            audit["conflicting_latest_rows"] += 1
            continue
        row = latest.iloc[-1]
        raw_status = _scalar_text(row.get(status_col, "")) if status_col else ""
        game_status = _scalar_text(row.get(game_status_col, "")) if game_status_col else ""
        practice_status = _scalar_text(row.get(practice_col, "")) if practice_col else ""
        rows.append(
            {
                "player_id": str(player_id),
                "expected_active_state": _availability_state(raw_status, game_status),
                "availability_status_raw": raw_status or game_status,
                "practice_status_raw": practice_status,
                "availability_capture_timestamp": latest_time.isoformat(),
                "availability_source_name": (
                    _scalar_text(row.get(source_col, "")) if source_col else ""
                ),
                "availability_source_status": "CURRENT_TIMESTAMPED",
                "availability_prospective_only": True,
            }
        )
    audit["rows_resolved"] = len(rows)
    return pd.DataFrame(rows, columns=output_columns), audit


def _quality_state(row: pd.Series) -> str:
    if bool(row.get("missing_history", True)) or bool(row.get("missing_usage_history", True)):
        return "LIMITED_NO_HISTORY"
    if not bool(row.get("missing_snap_data", True)) and not bool(
        row.get("missing_route_data", True)
    ):
        return "ENRICHED_HISTORY"
    return "CORE_HISTORY"


def build_offensive_player_state_contract(
    *,
    schedules: pd.DataFrame,
    roster: pd.DataFrame,
    pbp: pd.DataFrame | None,
    season: int,
    week: int,
    forecast_timestamp: Any,
    snap_counts: pd.DataFrame | None = None,
    routes: pd.DataFrame | None = None,
    availability: pd.DataFrame | None = None,
) -> OffensivePlayerStateBuild:
    """Build the canonical Sunday-sprint offensive player-state contract.

    Historical game usage is restricted to seasons/weeks strictly before the target
    week. This conservative rule intentionally forgoes same-week Thursday information
    so target-week PBP can never leak into Sunday features. Current availability is a
    separate prospective-only layer and is ignored unless its capture time is known and
    no later than ``forecast_timestamp``.
    """
    forecast_ts = _utc_timestamp(forecast_timestamp, label="forecast_timestamp")
    current_roster = _normalize_roster(roster)
    team_games = _normalize_schedule(schedules, season=season, week=week)

    current = current_roster.merge(team_games, on="team", how="inner", validate="many_to_one")
    if current.empty:
        raise ValueError("No supported offensive roster players map to the target slate")

    history = _combine_history(
        pbp,
        snap_counts,
        routes,
        season=season,
        week=week,
    )
    history_summary = _summarize_history(history)
    state = current.merge(history_summary, on="player_id", how="left", validate="one_to_one")

    numeric_history = [
        "prior_games",
        "prior_dropbacks_pg_4",
        "prior_pass_attempts_pg_4",
        "prior_rush_attempts_pg_4",
        "prior_carries_pg_4",
        "prior_targets_pg_4",
        "prior_receptions_pg_4",
        "prior_carry_share_4",
        "prior_target_share_4",
        "prior_offense_snaps_pg_4",
        "prior_snap_share_4",
        "prior_routes_pg_4",
        "prior_route_participation_4",
        "prior_targets_per_route_4",
        "prior_qb_rushes_per_dropback_4",
        "prior_reception_rate_4",
        "prior_red_zone_carries_pg_4",
        "prior_goal_line_carries_pg_4",
        "prior_red_zone_targets_pg_4",
        "prior_end_zone_targets_pg_4",
    ]
    for column in numeric_history:
        if column not in state.columns:
            state[column] = np.nan
    state["prior_games"] = pd.to_numeric(state["prior_games"], errors="coerce").fillna(0).astype(int)

    availability_state, availability_audit = _resolve_availability(
        availability,
        current_roster,
        forecast_timestamp=forecast_ts,
    )
    state = state.merge(availability_state, on="player_id", how="left", validate="one_to_one")
    state["expected_active_state"] = state["expected_active_state"].fillna("UNKNOWN")
    state["availability_source_status"] = state["availability_source_status"].fillna("MISSING")
    state["availability_prospective_only"] = (
        state["availability_prospective_only"].astype("boolean").fillna(False).astype(bool)
    )

    state["schema_version"] = SCHEMA_VERSION
    state["forecast_timestamp"] = forecast_ts.isoformat()
    state["history_policy"] = "STRICT_PRIOR_WEEK"
    state["expected_role"] = state.apply(_role_for_row, axis=1)

    state["missing_history"] = state["prior_games"].eq(0)
    state["missing_usage_history"] = state[
        [
            "prior_dropbacks_pg_4",
            "prior_rush_attempts_pg_4",
            "prior_targets_pg_4",
            "prior_receptions_pg_4",
        ]
    ].isna().all(axis=1)
    state["missing_snap_data"] = state["prior_offense_snaps_pg_4"].isna()
    state["missing_route_data"] = state["prior_routes_pg_4"].isna()
    state["missing_availability"] = state["availability_source_status"].eq("MISSING")
    state["missing_red_zone_history"] = (
        state["prior_red_zone_carries_pg_4"].isna()
        & state["prior_red_zone_targets_pg_4"].isna()
    )
    state["kickoff_known"] = state["kickoff_timestamp"].notna()
    state["forecast_is_pregame"] = (
        state["kickoff_timestamp"].isna() | state["kickoff_timestamp"].gt(forecast_ts)
    )
    state["data_quality_state"] = state.apply(_quality_state, axis=1)

    already_started = ~state["forecast_is_pregame"]
    games_started = sorted(state.loc[already_started, "game_id"].astype(str).unique())
    state = state[~already_started].copy()

    ordered = [column for column in CORE_COLUMNS if column in state.columns]
    extras = [column for column in state.columns if column not in ordered]
    state = state[ordered + extras].sort_values(
        ["game_id", "team", "position", "player_id"]
    ).reset_index(drop=True)

    validate_offensive_player_state(state)

    historical_max = None
    if not history.empty:
        latest = history.sort_values(["season", "week"]).tail(1).iloc[0]
        historical_max = {"season": int(latest["season"]), "week": int(latest["week"])}

    pbp_usable_rows = (
        int(history["pbp_game_covered"].fillna(False).astype(bool).sum())
        if not history.empty and "pbp_game_covered" in history.columns
        else 0
    )
    snap_usable_rows = (
        int(
            (
                history["offense_snaps"].notna()
                | history["snap_share"].notna()
            ).sum()
        )
        if not history.empty
        else 0
    )
    route_usable_rows = (
        int(
            (
                history["routes"].notna()
                | history["route_participation"].notna()
            ).sum()
        )
        if not history.empty
        else 0
    )

    audit = {
        "schema_version": SCHEMA_VERSION,
        "season": int(season),
        "week": int(week),
        "forecast_timestamp": forecast_ts.isoformat(),
        "history_policy": "STRICT_PRIOR_WEEK",
        "historical_max_period_used": historical_max,
        "supported_positions": sorted(SUPPORTED_POSITIONS),
        "eligible_players": int(len(state)),
        "games_started_and_dropped": games_started,
        "availability": availability_audit,
        "sources": {
            "pbp": "historical_lagged" if pbp_usable_rows > 0 else "missing_or_unusable",
            "snap_counts": (
                "historical_lagged" if snap_usable_rows > 0 else "missing_or_unusable"
            ),
            "routes": (
                "historical_lagged" if route_usable_rows > 0 else "missing_or_unusable"
            ),
            "availability": (
                "prospective_only_timestamped"
                if availability_audit["rows_resolved"] > 0
                else "missing_or_unusable"
            ),
        },
        "source_usable_rows": {
            "pbp": pbp_usable_rows,
            "snap_counts": snap_usable_rows,
            "routes": route_usable_rows,
        },
        "guardrails": [
            "No target-week PBP is used.",
            "Historical availability is never inferred from participation.",
            "Availability evidence after the forecast timestamp is discarded.",
            "Ambiguous player identity fails closed.",
            "Current availability is prospective-only unless separately reconstructed.",
            "Official LevLine winner probability code is not touched by this contract.",
        ],
    }
    return OffensivePlayerStateBuild(player_state=state, audit=audit)


def validate_offensive_player_state(frame: pd.DataFrame) -> None:
    missing = set(CORE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Player-state contract missing columns: {sorted(missing)}")
    if frame.empty:
        return

    ids = frame["player_id"].astype("string").fillna("").str.strip()
    if (~_valid_id(ids)).any():
        raise ValueError("Player-state contract contains missing stable player_id")
    if frame.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Player-state contract contains duplicate game_id/player_id rows")
    if (~frame["position"].isin(SUPPORTED_POSITIONS)).any():
        raise ValueError("Player-state contract contains unsupported position")
    if (~frame["forecast_is_pregame"].astype(bool)).any():
        raise ValueError("Player-state contract contains a row after known kickoff")

    timestamps = pd.to_datetime(frame["forecast_timestamp"], utc=True, errors="coerce")
    if timestamps.isna().any():
        raise ValueError("Player-state contract contains invalid forecast timestamp")
    valid_states = {"OUT", "DOUBTFUL", "QUESTIONABLE", "AVAILABLE", "UNKNOWN"}
    if (~frame["expected_active_state"].isin(valid_states)).any():
        raise ValueError("Player-state contract contains invalid expected_active_state")

from __future__ import annotations

"""Research-only qualification audit for historical pregame availability sources."""

from dataclasses import dataclass

import pandas as pd

TARGET_SEASONS = (2022, 2023, 2024, 2025)
T120_MINUTES = 120
PROHIBITED_FIELDS = {
    "actual_snap_count",
    "actual_snap_share",
    "actual_participation",
    "postgame_participation",
    "actual_home_score",
    "actual_away_score",
    "home_win",
    "final_inactive_learned_post_kickoff",
}


@dataclass(frozen=True)
class AvailabilityQualification:
    source_id: str
    historically_qualified: bool
    rows: int
    seasons_present: tuple[int, ...]
    target_seasons_complete: bool
    timestamp_parse_rate: float
    known_by_t120_rate: float
    source_id_missing_rate: float
    crosswalk_missing_rate: float
    ambiguous_crosswalk_ids: int
    point_in_time_history_proven: bool
    later_revision_reconstruction_proven: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "historically_qualified": self.historically_qualified,
            "rows": self.rows,
            "seasons_present": list(self.seasons_present),
            "target_seasons_complete": self.target_seasons_complete,
            "timestamp_parse_rate": self.timestamp_parse_rate,
            "known_by_t120_rate": self.known_by_t120_rate,
            "source_id_missing_rate": self.source_id_missing_rate,
            "crosswalk_missing_rate": self.crosswalk_missing_rate,
            "ambiguous_crosswalk_ids": self.ambiguous_crosswalk_ids,
            "point_in_time_history_proven": self.point_in_time_history_proven,
            "later_revision_reconstruction_proven": self.later_revision_reconstruction_proven,
            "reasons": list(self.reasons),
            "actual_snaps_used_for_availability": 0,
            "post_kickoff_outcomes_used": 0,
        }


def _team_schedule(schedules: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "season", "week", "home_team", "away_team", "kickoff_utc"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"Schedules missing availability audit fields: {sorted(missing)}")
    home = schedules[["game_id", "season", "week", "home_team", "kickoff_utc"]].rename(columns={"home_team": "team"})
    away = schedules[["game_id", "season", "week", "away_team", "kickoff_utc"]].rename(columns={"away_team": "team"})
    teams = pd.concat([home, away], ignore_index=True)
    if teams.duplicated(["season", "week", "team"]).any():
        raise ValueError("Schedule has duplicate team-week rows; availability alignment is ambiguous")
    teams["season"] = pd.to_numeric(teams.season, errors="coerce")
    teams["week"] = pd.to_numeric(teams.week, errors="coerce")
    teams["kickoff_utc"] = pd.to_datetime(teams.kickoff_utc, utc=True, errors="coerce")
    if teams[["season", "week", "kickoff_utc"]].isna().any().any():
        raise ValueError("Schedule availability keys/timestamps are incomplete")
    return teams


def _validate_crosswalk(crosswalk: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    required = {"source_player_id", "player_id"}
    missing = required - set(crosswalk.columns)
    if missing:
        raise ValueError(f"Crosswalk missing fields: {sorted(missing)}")
    work = crosswalk[list(required)].copy()
    work["source_player_id"] = work.source_player_id.astype("string").fillna("").str.strip()
    work["player_id"] = work.player_id.astype("string").fillna("").str.strip()
    work = work[work.source_player_id.ne("") & work.player_id.ne("")].copy()
    counts = work.groupby("source_player_id").player_id.nunique()
    ambiguous_ids = set(counts[counts.gt(1)].index.astype(str))
    safe = work[~work.source_player_id.isin(ambiguous_ids)].drop_duplicates("source_player_id", keep="first")
    return safe, len(ambiguous_ids)


def audit_availability_source(
    injuries: pd.DataFrame,
    schedules: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    source_id: str,
    point_in_time_history_proven: bool,
    later_revision_reconstruction_proven: bool,
    target_seasons: tuple[int, ...] = TARGET_SEASONS,
) -> tuple[AvailabilityQualification, pd.DataFrame]:
    """Audit whether a normalized source can support retrospective T-120 availability.

    A source cannot pass merely because its current historical payload has old dates.  It
    must separately prove point-in-time semantics and reconstruction of later revisions.
    This prevents a corrected post-kickoff row from being treated as if it were known at
    T-120.
    """
    required = {
        "season", "week", "team", "source_player_id", "status_date",
        "practice_status", "game_status",
    }
    missing = required - set(injuries.columns)
    if missing:
        raise ValueError(f"Availability source missing normalized fields: {sorted(missing)}")
    retrospective = PROHIBITED_FIELDS.intersection(injuries.columns)
    if retrospective:
        raise ValueError(f"Availability qualification refuses retrospective fields: {sorted(retrospective)}")

    frame = injuries.copy()
    frame["season"] = pd.to_numeric(frame.season, errors="coerce")
    frame["week"] = pd.to_numeric(frame.week, errors="coerce")
    frame = frame[frame.season.isin(target_seasons)].copy()
    if frame.empty:
        result = AvailabilityQualification(
            source_id=source_id,
            historically_qualified=False,
            rows=0,
            seasons_present=(),
            target_seasons_complete=False,
            timestamp_parse_rate=0.0,
            known_by_t120_rate=0.0,
            source_id_missing_rate=1.0,
            crosswalk_missing_rate=1.0,
            ambiguous_crosswalk_ids=0,
            point_in_time_history_proven=point_in_time_history_proven,
            later_revision_reconstruction_proven=later_revision_reconstruction_proven,
            reasons=("no_target_season_rows",),
        )
        return result, frame

    frame["source_player_id"] = frame.source_player_id.astype("string").fillna("").str.strip()
    source_missing = frame.source_player_id.eq("") | frame.source_player_id.str.lower().isin({"nan", "<na>"})
    source_id_missing_rate = float(source_missing.mean())
    frame["status_date_utc"] = pd.to_datetime(frame.status_date, utc=True, errors="coerce")
    timestamp_parse_rate = float(frame.status_date_utc.notna().mean())

    team_schedule = _team_schedule(schedules)
    frame = frame.merge(
        team_schedule,
        on=["season", "week", "team"],
        how="left",
        validate="many_to_one",
        indicator="_schedule_merge",
    )
    frame["t120_utc"] = frame.kickoff_utc - pd.to_timedelta(T120_MINUTES, unit="m")
    frame["known_by_t120"] = (
        frame.status_date_utc.notna()
        & frame.t120_utc.notna()
        & frame.status_date_utc.le(frame.t120_utc)
    )
    known_by_t120_rate = float(frame.known_by_t120.mean())

    safe_crosswalk, ambiguous = _validate_crosswalk(crosswalk)
    frame = frame.merge(safe_crosswalk, on="source_player_id", how="left", validate="many_to_one")
    crosswalk_missing_rate = float(frame.player_id.isna().mean())

    seasons_present = tuple(sorted(pd.to_numeric(frame.season, errors="coerce").dropna().astype(int).unique()))
    target_complete = set(target_seasons).issubset(seasons_present)
    reasons: list[str] = []
    if not target_complete:
        reasons.append("target_seasons_incomplete")
    if timestamp_parse_rate < 1.0:
        reasons.append("unparseable_status_timestamps")
    if known_by_t120_rate < 1.0:
        reasons.append("one_or_more_rows_not_proven_known_by_t120")
    if source_id_missing_rate > 0.0:
        reasons.append("missing_source_player_ids")
    if crosswalk_missing_rate > 0.0:
        reasons.append("incomplete_stable_id_crosswalk")
    if ambiguous > 0:
        reasons.append("ambiguous_source_player_ids")
    if frame._schedule_merge.ne("both").any():
        reasons.append("unmatched_team_week_schedule_rows")
    if not point_in_time_history_proven:
        reasons.append("point_in_time_history_not_proven")
    if not later_revision_reconstruction_proven:
        reasons.append("later_revision_reconstruction_not_proven")

    qualified = not reasons
    result = AvailabilityQualification(
        source_id=source_id,
        historically_qualified=qualified,
        rows=int(len(frame)),
        seasons_present=seasons_present,
        target_seasons_complete=target_complete,
        timestamp_parse_rate=timestamp_parse_rate,
        known_by_t120_rate=known_by_t120_rate,
        source_id_missing_rate=source_id_missing_rate,
        crosswalk_missing_rate=crosswalk_missing_rate,
        ambiguous_crosswalk_ids=ambiguous,
        point_in_time_history_proven=point_in_time_history_proven,
        later_revision_reconstruction_proven=later_revision_reconstruction_proven,
        reasons=tuple(reasons),
    )
    return result, frame

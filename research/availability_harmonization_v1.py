from __future__ import annotations

"""Pure helpers for the preregistered 2022-2025 availability harmonization audit.

This module qualifies source/state semantics only. It does not fit P(active), estimate
expected snaps, score games, inspect outcomes, or authorize any production feature.
"""

from dataclasses import dataclass
from datetime import timedelta
import hashlib
from zoneinfo import ZoneInfo

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import (
    GAME_STATUS_REPORT_DAYS_BEFORE,
    attach_stable_identity,
    normalize_game_status,
    normalize_practice_status,
    normalize_team,
)

TARGET_SEASONS = (2022, 2023, 2024, 2025)
LEGACY_SEASONS = (2022, 2023, 2024)
NFLVERSE_SOURCE_TIMEZONE = "America/Toronto"
CANONICAL_STATES = {"full", "limited", "dnp"}
REQUIRED_NFLVERSE_COLUMNS = {
    "season",
    "week",
    "team",
    "gsis_id",
    "position",
    "full_name",
    "first_name",
    "last_name",
    "practice_status",
    "report_status",
    "date_modified",
}


@dataclass(frozen=True)
class SeasonAuditSummary:
    season: int
    nflverse_rows: int
    official_crosscheck_rows: int
    official_pages_collected: int
    stable_gsis_missing_rate: float
    unique_identity_match_rate: float
    practice_status_agreement_rate: float
    diagnostic_game_status_agreement_rate: float
    known_by_t120_rate_among_matched_rows: float
    fully_qualified_practice_state_rate: float
    date_modified_parse_rate: float | None
    schedule_match_rate: float
    duplicate_identity_rows: int
    qualified: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "season": self.season,
            "nflverse_rows": self.nflverse_rows,
            "official_crosscheck_rows": self.official_crosscheck_rows,
            "official_pages_collected": self.official_pages_collected,
            "stable_gsis_missing_rate": self.stable_gsis_missing_rate,
            "unique_identity_match_rate": self.unique_identity_match_rate,
            "practice_status_agreement_rate": self.practice_status_agreement_rate,
            "diagnostic_game_status_agreement_rate": self.diagnostic_game_status_agreement_rate,
            "known_by_t120_rate_among_matched_rows": self.known_by_t120_rate_among_matched_rows,
            "fully_qualified_practice_state_rate": self.fully_qualified_practice_state_rate,
            "date_modified_parse_rate": self.date_modified_parse_rate,
            "schedule_match_rate": self.schedule_match_rate,
            "duplicate_identity_rows": self.duplicate_identity_rows,
            "qualified": self.qualified,
            "reasons": list(self.reasons),
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _parse_source_timestamp(value: object) -> pd.Timestamp:
    if value is None or pd.isna(value):
        return pd.NaT
    try:
        stamp = pd.Timestamp(value)
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize(
                NFLVERSE_SOURCE_TIMEZONE,
                ambiguous="raise",
                nonexistent="raise",
            )
        return stamp.tz_convert("UTC")
    except (TypeError, ValueError, OverflowError):
        return pd.NaT


def parse_date_modified_utc(values: pd.Series) -> pd.Series:
    """Parse nflverse row-update timestamps under nflverse's documented timezone.

    These timestamps are diagnostic source-integrity evidence only. They do not replace
    the uniform official filing-day chronology proof used by the harmonization contract.
    """

    return values.map(_parse_source_timestamp)


def validate_nflverse_frame(frame: pd.DataFrame, *, season: int) -> pd.DataFrame:
    missing = REQUIRED_NFLVERSE_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{season} nflverse injury asset missing fields: {sorted(missing)}")
    out = frame[pd.to_numeric(frame["season"], errors="coerce").eq(season)].copy()
    if out.empty:
        raise ValueError(f"{season} nflverse injury asset contains no target-season rows")
    out["week"] = pd.to_numeric(out["week"], errors="raise").astype(int)
    out["team"] = out["team"].map(normalize_team)
    return out


def kickoff_index(schedules: pd.DataFrame, *, season: int) -> pd.DataFrame:
    required = {"season", "week", "home_team", "away_team", "gameday", "gametime", "game_id"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule missing harmonization fields: {sorted(missing)}")

    games = schedules[pd.to_numeric(schedules["season"], errors="coerce").eq(season)].copy()
    if "game_type" in games.columns:
        games = games[games["game_type"].isin({"REG", "WC", "DIV", "CON", "SB"})].copy()
    if games.empty:
        raise ValueError(f"schedule has no supported games for {season}")

    stamp = pd.to_datetime(
        games["gameday"].astype(str) + " " + games["gametime"].fillna("00:00").astype(str),
        errors="coerce",
    )
    games["kickoff_utc"] = (
        stamp.dt.tz_localize("America/New_York", ambiguous="raise", nonexistent="raise")
        .dt.tz_convert("UTC")
    )
    if games["kickoff_utc"].isna().any():
        raise ValueError(f"one or more {season} kickoff timestamps are not parseable")

    eastern = ZoneInfo("America/New_York")
    deadlines: list[pd.Timestamp] = []
    for kickoff in games["kickoff_utc"]:
        local = kickoff.tz_convert(eastern)
        weekday = local.day_name()
        if weekday not in GAME_STATUS_REPORT_DAYS_BEFORE:
            raise ValueError(f"unsupported NFL game weekday for report chronology: {weekday}")
        report_day = local.date() - timedelta(days=GAME_STATUS_REPORT_DAYS_BEFORE[weekday])
        deadlines.append(
            pd.Timestamp(report_day, tz=eastern)
            + pd.Timedelta(days=1)
            - pd.Timedelta(seconds=1)
        )
    games["report_deadline_eod_utc"] = pd.DatetimeIndex(deadlines).tz_convert("UTC")

    home = games[
        ["game_id", "season", "week", "home_team", "kickoff_utc", "report_deadline_eod_utc"]
    ].rename(columns={"home_team": "team"})
    away = games[
        ["game_id", "season", "week", "away_team", "kickoff_utc", "report_deadline_eod_utc"]
    ].rename(columns={"away_team": "team"})
    out = pd.concat([home, away], ignore_index=True)
    out["team"] = out["team"].map(normalize_team)
    if out.duplicated(["season", "week", "team"]).any():
        duplicated = out[out.duplicated(["season", "week", "team"], keep=False)]
        raise ValueError(
            f"{season} schedule contains ambiguous team-week game identity: "
            f"{duplicated[['week', 'team']].drop_duplicates().to_dict('records')}"
        )
    return out


def build_season_reconstruction(
    nflverse: pd.DataFrame,
    official_reports: pd.DataFrame,
    schedules: pd.DataFrame,
    *,
    season: int,
) -> pd.DataFrame:
    """Build one season's canonical practice-state audit without model fitting."""

    base = validate_nflverse_frame(nflverse, season=season)
    ext = official_reports[pd.to_numeric(official_reports["season"], errors="coerce").eq(season)].copy()
    if ext.empty:
        raise ValueError(f"{season} official injury cross-check contains no rows")
    ext["team"] = ext["team"].map(normalize_team)

    matched = attach_stable_identity(ext, base)
    unique = matched[matched["identity_match_state"].eq("unique")].copy()
    duplicate_external = int(unique.duplicated(["season", "week", "team", "gsis_id"]).sum())
    if duplicate_external:
        raise ValueError(f"{season} official reports contain {duplicate_external} duplicate stable player-week rows")

    stable_cols = [
        "season",
        "week",
        "team",
        "gsis_id",
        "position",
        "full_name",
        "first_name",
        "last_name",
        "practice_status",
        "report_status",
        "date_modified",
    ]
    canonical = base[stable_cols].copy()
    canonical["team"] = canonical["team"].map(normalize_team)
    ext_cols = [
        "season",
        "week",
        "team",
        "gsis_id",
        "external_player",
        "external_position",
        "external_injury",
        "external_practice_status",
        "external_game_status",
        "external_source",
        "source_url",
        "identity_match_method",
    ]
    canonical = canonical.merge(
        unique[ext_cols],
        on=["season", "week", "team", "gsis_id"],
        how="left",
        validate="one_to_one",
    )
    canonical["identity_matched"] = canonical["external_player"].notna()
    canonical["nflverse_practice_normalized"] = canonical["practice_status"].map(normalize_practice_status)
    canonical["external_practice_normalized"] = canonical["external_practice_status"].map(normalize_practice_status)
    canonical["nflverse_game_normalized"] = canonical["report_status"].map(normalize_game_status)
    canonical["external_game_normalized"] = canonical["external_game_status"].map(normalize_game_status)
    canonical["recognized_practice_state"] = canonical["nflverse_practice_normalized"].isin(CANONICAL_STATES)
    canonical["practice_status_agrees"] = (
        canonical["identity_matched"]
        & canonical["nflverse_practice_normalized"].eq(canonical["external_practice_normalized"])
        & canonical["recognized_practice_state"]
    )
    canonical["game_status_agrees"] = (
        canonical["identity_matched"]
        & canonical["nflverse_game_normalized"].eq(canonical["external_game_normalized"])
    )
    canonical["date_modified_utc"] = parse_date_modified_utc(canonical["date_modified"])

    canonical = canonical.merge(
        kickoff_index(schedules, season=season),
        on=["season", "week", "team"],
        how="left",
        validate="many_to_one",
    )
    canonical["schedule_matched"] = canonical["kickoff_utc"].notna()
    canonical["t120_utc"] = canonical["kickoff_utc"] - pd.Timedelta(minutes=120)
    canonical["known_by_t120"] = (
        canonical["identity_matched"]
        & canonical["report_deadline_eod_utc"].notna()
        & canonical["t120_utc"].notna()
        & canonical["report_deadline_eod_utc"].le(canonical["t120_utc"])
    )
    canonical["fully_qualified_practice_state"] = (
        canonical["identity_matched"]
        & canonical["schedule_matched"]
        & canonical["known_by_t120"]
        & canonical["practice_status_agrees"]
        & canonical["recognized_practice_state"]
    )
    canonical["canonical_practice_state"] = canonical["nflverse_practice_normalized"].where(
        canonical["fully_qualified_practice_state"],
        "unknown",
    )
    canonical["availability_source"] = "nflverse+official_nfl_historical_report_crosscheck"
    canonical["chronology_policy"] = "official_game_status_report_day_eod_eastern_before_t120"
    canonical["historical_game_status_feature_authorized"] = False
    canonical["postgame_information_used"] = False

    def unresolved_reason(row: pd.Series) -> str:
        reasons: list[str] = []
        if not bool(row["identity_matched"]):
            reasons.append("identity_unresolved")
        if not bool(row["recognized_practice_state"]):
            reasons.append("practice_state_unrecognized")
        if bool(row["identity_matched"]) and not bool(row["practice_status_agrees"]):
            reasons.append("practice_state_crosscheck_mismatch")
        if not bool(row["schedule_matched"]):
            reasons.append("schedule_unmatched")
        elif bool(row["identity_matched"]) and not bool(row["known_by_t120"]):
            reasons.append("not_proven_known_by_t120")
        return ";".join(reasons)

    canonical["unresolved_reason"] = canonical.apply(unresolved_reason, axis=1)
    return canonical


def summarize_season(
    canonical: pd.DataFrame,
    *,
    season: int,
    official_crosscheck_rows: int,
    official_pages_collected: int,
    gates: dict,
) -> SeasonAuditSummary:
    frame = canonical[pd.to_numeric(canonical["season"], errors="coerce").eq(season)].copy()
    if frame.empty:
        raise ValueError(f"canonical harmonization frame is empty for {season}")

    total = len(frame)
    stable_missing = frame["gsis_id"].isna() | frame["gsis_id"].astype(str).str.strip().eq("")
    stable_missing_rate = float(stable_missing.mean())
    duplicate_identity_rows = int(frame.duplicated(["season", "week", "team", "gsis_id"]).sum())
    identity_rate = float(frame["identity_matched"].mean())
    matched = frame[frame["identity_matched"]].copy()
    practice_rate = float(matched["practice_status_agrees"].mean()) if len(matched) else 0.0
    game_rate = float(matched["game_status_agrees"].mean()) if len(matched) else 0.0
    known_rate = float(matched["known_by_t120"].mean()) if len(matched) else 0.0
    qualified_rate = float(frame["fully_qualified_practice_state"].mean())
    schedule_rate = float(frame["schedule_matched"].mean())
    date_rate = None
    if season in LEGACY_SEASONS:
        date_rate = float(frame["date_modified_utc"].notna().mean())

    reasons: list[str] = []
    if official_pages_collected != int(gates["official_nfl_pages_required_per_season"]):
        reasons.append("official_nfl_page_coverage_incomplete")
    if stable_missing_rate > float(gates["stable_gsis_missing_rate_max"]):
        reasons.append("stable_gsis_missing_rate_above_gate")
    if duplicate_identity_rows > int(gates["duplicate_identity_rows_allowed"]):
        reasons.append("duplicate_identity_rows_above_gate")
    if identity_rate < float(gates["unique_identity_match_rate_min"]):
        reasons.append("identity_match_rate_below_gate")
    if practice_rate < float(gates["practice_status_agreement_rate_min"]):
        reasons.append("practice_status_agreement_rate_below_gate")
    if game_rate < float(gates["diagnostic_game_status_agreement_rate_min"]):
        reasons.append("diagnostic_game_status_agreement_rate_below_gate")
    if known_rate < float(gates["known_by_t120_rate_required_among_matched_rows"]):
        reasons.append("known_by_t120_rate_below_gate")
    if qualified_rate < float(gates["fully_qualified_practice_state_rate_min"]):
        reasons.append("fully_qualified_practice_state_rate_below_gate")
    if schedule_rate < float(gates["schedule_match_rate_min"]):
        reasons.append("schedule_match_rate_below_gate")
    if date_rate is not None and date_rate < float(gates["legacy_date_modified_parse_rate_min"]):
        reasons.append("date_modified_parse_rate_below_gate")

    return SeasonAuditSummary(
        season=season,
        nflverse_rows=total,
        official_crosscheck_rows=int(official_crosscheck_rows),
        official_pages_collected=int(official_pages_collected),
        stable_gsis_missing_rate=stable_missing_rate,
        unique_identity_match_rate=identity_rate,
        practice_status_agreement_rate=practice_rate,
        diagnostic_game_status_agreement_rate=game_rate,
        known_by_t120_rate_among_matched_rows=known_rate,
        fully_qualified_practice_state_rate=qualified_rate,
        date_modified_parse_rate=date_rate,
        schedule_match_rate=schedule_rate,
        duplicate_identity_rows=duplicate_identity_rows,
        qualified=not reasons,
        reasons=tuple(reasons),
    )


def standardize_canonical(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "season",
        "week",
        "team",
        "gsis_id",
        "position",
        "full_name",
        "canonical_practice_state",
        "identity_matched",
        "practice_status_agrees",
        "game_status_agrees",
        "known_by_t120",
        "fully_qualified_practice_state",
        "kickoff_utc",
        "t120_utc",
        "report_deadline_eod_utc",
        "date_modified_utc",
        "availability_source",
        "chronology_policy",
        "historical_game_status_feature_authorized",
        "postgame_information_used",
        "unresolved_reason",
    ]
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"canonical frame missing standardized fields: {sorted(missing)}")
    out = frame[columns].copy()
    out = out.sort_values(["season", "week", "team", "gsis_id"], kind="stable").reset_index(drop=True)
    return out


def missingness_report(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"season", "week", "team", "position", "canonical_practice_state", "unresolved_reason"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missingness report frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["unknown"] = work["canonical_practice_state"].eq("unknown")
    report = (
        work.groupby(["season", "week", "team", "position"], dropna=False)
        .agg(
            rows=("gsis_id", "size"),
            unknown_rows=("unknown", "sum"),
            unknown_rate=("unknown", "mean"),
        )
        .reset_index()
    )
    return report

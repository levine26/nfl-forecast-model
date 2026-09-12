from __future__ import annotations

"""Research-only 2022-2025 availability-state harmonization.

This module proves source/schema/identity/chronology parity before V09B may be executed.
It does not estimate P(active), fit a forecast model, or touch production outputs.
"""

from dataclasses import dataclass
from datetime import timedelta
import hashlib
from io import StringIO
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import pandas as pd


TARGET_SEASONS = (2022, 2023, 2024, 2025)
TEAM_ABBR_ALIASES = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS"}
GAME_STATUS_REPORT_DAYS_BEFORE = {
    "Monday": 2,
    "Wednesday": 1,
    "Thursday": 1,
    "Friday": 1,
    "Saturday": 2,
    "Sunday": 2,
}
REQUIRED_INJURY_COLUMNS = {
    "season",
    "week",
    "team",
    "gsis_id",
    "position",
    "full_name",
    "practice_primary_injury",
    "practice_secondary_injury",
    "practice_status",
    "report_primary_injury",
    "report_secondary_injury",
    "report_status",
}
CANONICAL_COLUMNS = [
    "season",
    "week",
    "game_id",
    "team",
    "gsis_id",
    "position",
    "full_name",
    "practice_primary_injury",
    "practice_secondary_injury",
    "practice_status_normalized",
    "listed_on_injury_report",
    "report_deadline_eod_utc",
    "kickoff_utc",
    "t120_utc",
    "known_by_t120",
    "source_sha256",
]
DUPLICATE_KEY = ["season", "week", "team", "gsis_id"]
DUPLICATE_EQUIVALENCE_COLUMNS = [
    "position",
    "full_name",
    "practice_primary_injury",
    "practice_secondary_injury",
    "practice_status_normalized",
]

EXPECTED_V09B = {
    "candidate_version": "0.9B-player-value-availability",
    "feature_family": "player_value_availability",
    "training_seasons": list(range(2012, 2022)),
    "validation_seasons": [2022, 2023, 2024, 2025],
    "model_family": "expected player contribution = P(active) x expected snap share x latent value",
    "hyperparameter_search_policy": (
        "No fitting until every target season has validated timestamped pregame availability coverage."
    ),
    "primary_metric": "brier",
}


@dataclass(frozen=True)
class SeasonAudit:
    season: int
    source_sha256: str
    full_asset_rows: int
    regular_rows: int
    missing_id_rate: float
    raw_duplicate_excess_rows: int
    identical_duplicate_rows_collapsed: int
    conflicting_duplicate_groups: int
    schedule_join_missing_rate: float
    known_by_t120_rate: float
    unknown_practice_status_rate: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "source_sha256": self.source_sha256,
            "full_asset_rows": self.full_asset_rows,
            "regular_rows": self.regular_rows,
            "missing_id_rate": self.missing_id_rate,
            "raw_duplicate_excess_rows": self.raw_duplicate_excess_rows,
            "identical_duplicate_rows_collapsed": self.identical_duplicate_rows_collapsed,
            "conflicting_duplicate_groups": self.conflicting_duplicate_groups,
            "schedule_join_missing_rate": self.schedule_join_missing_rate,
            "known_by_t120_rate": self.known_by_t120_rate,
            "unknown_practice_status_rate": self.unknown_practice_status_rate,
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_team(value: object) -> str:
    text = str(value or "").strip().upper()
    return TEAM_ABBR_ALIASES.get(text, text)


def normalize_practice_status(value: object) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    text = str(value).strip().lower().replace("_", " ")
    if not text or text in {"nan", "none", "na", "n/a", "not reported", "not listed"}:
        return "unknown"
    if text in {"fp", "full", "full participation"} or "full participation" in text:
        return "full"
    if text in {"lp", "limited", "limited participation"} or "limited participation" in text:
        return "limited"
    if text == "dnp" or "did not participate" in text:
        return "dnp"
    return "unknown"


def _normalized_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def validate_injury_asset(
    payload: bytes,
    *,
    season: int,
    expected_rows: int | None = None,
    expected_sha256: str | None = None,
) -> tuple[pd.DataFrame, str]:
    digest = sha256_bytes(payload)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(
            f"{season} injury asset digest changed: expected {expected_sha256}, got {digest}"
        )
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = REQUIRED_INJURY_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{season} injury asset missing required fields: {sorted(missing)}")
    seasons = pd.to_numeric(frame["season"], errors="coerce")
    frame = frame[seasons.eq(season)].copy()
    if expected_rows is not None and len(frame) != int(expected_rows):
        raise ValueError(
            f"{season} injury row count changed: expected {expected_rows}, got {len(frame)}"
        )
    if frame.empty:
        raise ValueError(f"{season} injury asset contains no rows")
    return frame, digest


def build_schedule_index(schedules: pd.DataFrame, *, season: int) -> pd.DataFrame:
    required = {"season", "week", "home_team", "away_team", "gameday", "gametime", "game_id"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule missing harmonization fields: {sorted(missing)}")

    season_values = pd.to_numeric(schedules["season"], errors="coerce")
    week_values = pd.to_numeric(schedules["week"], errors="coerce")
    games = schedules[season_values.eq(season) & week_values.between(1, 18)].copy()
    if games.empty:
        raise ValueError(f"schedule contains no regular-season games for {season}")

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
        raise ValueError(f"{season} schedule contains ambiguous team-week identity")
    return out


def _collapse_equivalent_duplicates(frame: pd.DataFrame, *, season: int) -> tuple[pd.DataFrame, int, int]:
    """Collapse only duplicate player-week rows that are feature-equivalent.

    nflverse historical assets can contain repeated player/team/week rows. Because these
    files do not carry revision timestamps, a duplicate group is safe to collapse only
    when every field used by the practice-state feature is equivalent. Differences in
    report/game status are intentionally ignored because game status is not authorized as
    a historical feature in this lane. Any identity/practice-state disagreement fails closed.
    """
    duplicate_mask = frame.duplicated(DUPLICATE_KEY, keep=False)
    if not duplicate_mask.any():
        return frame, 0, 0

    duplicate_rows = frame.loc[duplicate_mask].copy()
    raw_excess = int(len(duplicate_rows) - duplicate_rows[DUPLICATE_KEY].drop_duplicates().shape[0])
    conflicting_groups = 0

    for _, group in duplicate_rows.groupby(DUPLICATE_KEY, dropna=False, sort=False):
        comparisons = pd.DataFrame(index=group.index)
        comparisons["position"] = group["position"].map(_normalized_text)
        comparisons["full_name"] = group["full_name"].map(_normalized_text)
        comparisons["practice_primary_injury"] = group["practice_primary_injury"].map(_normalized_text)
        comparisons["practice_secondary_injury"] = group["practice_secondary_injury"].map(_normalized_text)
        comparisons["practice_status_normalized"] = group["practice_status_normalized"]
        if any(comparisons[column].nunique(dropna=False) > 1 for column in DUPLICATE_EQUIVALENCE_COLUMNS):
            conflicting_groups += 1

    if conflicting_groups:
        raise ValueError(
            f"{season} contains {conflicting_groups} conflicting duplicate player-team-week groups"
        )

    collapsed = frame.drop_duplicates(DUPLICATE_KEY, keep="first").copy()
    collapsed_count = int(len(frame) - len(collapsed))
    return collapsed, raw_excess, collapsed_count


def harmonize_season(
    injury_frame: pd.DataFrame,
    schedules: pd.DataFrame,
    *,
    season: int,
    source_sha256: str,
) -> tuple[pd.DataFrame, SeasonAudit]:
    frame = injury_frame.copy()
    frame["season"] = pd.to_numeric(frame["season"], errors="raise").astype(int)
    frame["week"] = pd.to_numeric(frame["week"], errors="raise").astype(int)
    frame = frame[frame["season"].eq(season) & frame["week"].between(1, 18)].copy()
    if frame.empty:
        raise ValueError(f"{season} has no regular-season injury rows")

    frame["team"] = frame["team"].map(normalize_team)
    ids = frame["gsis_id"].astype("string").fillna("").str.strip()
    missing_ids = ids.eq("") | ids.str.lower().eq("nan") | ids.eq("<NA>")
    missing_id_rate = float(missing_ids.mean())
    if missing_id_rate:
        raise ValueError(f"{season} injury rows contain missing stable GSIS identity")

    frame["practice_status_normalized"] = frame["practice_status"].map(normalize_practice_status)
    frame, raw_duplicate_excess_rows, identical_duplicate_rows_collapsed = (
        _collapse_equivalent_duplicates(frame, season=season)
    )
    conflicting_duplicate_groups = 0

    frame["listed_on_injury_report"] = True
    frame["source_sha256"] = source_sha256

    schedule_index = build_schedule_index(schedules, season=season)
    out = frame.merge(
        schedule_index,
        on=["season", "week", "team"],
        how="left",
        validate="many_to_one",
    )
    out["t120_utc"] = out["kickoff_utc"] - pd.Timedelta(minutes=120)
    out["known_by_t120"] = (
        out["report_deadline_eod_utc"].notna()
        & out["t120_utc"].notna()
        & out["report_deadline_eod_utc"].le(out["t120_utc"])
    )

    schedule_missing = out["game_id"].isna()
    schedule_join_missing_rate = float(schedule_missing.mean())
    known_rate = float(out["known_by_t120"].mean())
    unknown_rate = float(out["practice_status_normalized"].eq("unknown").mean())

    canonical = out[CANONICAL_COLUMNS].copy()
    audit = SeasonAudit(
        season=season,
        source_sha256=source_sha256,
        full_asset_rows=int(len(injury_frame)),
        regular_rows=int(len(canonical)),
        missing_id_rate=missing_id_rate,
        raw_duplicate_excess_rows=raw_duplicate_excess_rows,
        identical_duplicate_rows_collapsed=identical_duplicate_rows_collapsed,
        conflicting_duplicate_groups=conflicting_duplicate_groups,
        schedule_join_missing_rate=schedule_join_missing_rate,
        known_by_t120_rate=known_rate,
        unknown_practice_status_rate=unknown_rate,
    )
    return canonical, audit


def validate_v09b_preregistry(registry: Mapping[str, Any]) -> tuple[bool, list[str]]:
    experiments = registry.get("experiments", []) if isinstance(registry, Mapping) else []
    target = next(
        (item for item in experiments if item.get("experiment_id") == "V09B-AVAILABILITY-001"),
        None,
    )
    if target is None:
        return False, ["V09B-AVAILABILITY-001 missing from experiment registry"]
    reasons: list[str] = []
    for key, expected in EXPECTED_V09B.items():
        if target.get(key) != expected:
            reasons.append(f"V09B preregistration drifted at {key}")
    prohibited = set(target.get("prohibited_inputs", []))
    for required in {
        "2026 outcomes",
        "actual current-game snaps",
        "retrospective inactive status",
        "later injury designation",
        "postgame participation",
    }:
        if required not in prohibited:
            reasons.append(f"V09B prohibited input missing: {required}")
    return not reasons, reasons


def evaluate_harmonization(
    audits: list[SeasonAudit],
    contract: Mapping[str, Any],
    *,
    v09b_prereg_ok: bool,
    qualified_2025_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    gates = contract["qualification_gates"]
    expected_hashes = contract["source"]["expected_sha256"]
    expected_rows = contract["source"]["expected_full_asset_rows"]
    by_season = {str(a.season): a for a in audits}
    reasons: list[str] = []

    for season in contract["target_seasons"]:
        key = str(season)
        audit = by_season.get(key)
        if audit is None:
            reasons.append(f"missing season audit: {season}")
            continue
        expected_hash = expected_hashes.get(key)
        if expected_hash is None:
            reasons.append(f"source hash not pinned: {season}")
        elif audit.source_sha256 != expected_hash:
            reasons.append(f"source hash mismatch: {season}")
        if audit.full_asset_rows != int(expected_rows[key]):
            reasons.append(f"source row count mismatch: {season}")
        if audit.missing_id_rate != float(gates["stable_identity_missing_rate"]):
            reasons.append(f"stable identity missingness failed: {season}")
        if audit.conflicting_duplicate_groups != int(gates["conflicting_duplicate_groups"]):
            reasons.append(f"conflicting duplicate practice-state groups failed: {season}")
        if audit.schedule_join_missing_rate != float(gates["schedule_join_missing_rate"]):
            reasons.append(f"schedule join missingness failed: {season}")
        if audit.known_by_t120_rate != float(gates["known_by_t120_rate"]):
            reasons.append(f"T-120 chronology failed: {season}")
        if audit.unknown_practice_status_rate > float(
            gates["practice_status_normalization_unknown_rate_max"]
        ):
            reasons.append(f"practice-status unknown rate too high: {season}")

    receipt_ok = bool(
        qualified_2025_receipt.get("research_source_qualified") is True
        and qualified_2025_receipt.get("supports_2025_reconstruction") is True
        and qualified_2025_receipt.get("probability_feature_authorized") is False
    )
    if not receipt_ok:
        reasons.append("qualified 2025 reconstruction receipt is missing or incompatible")
    if not v09b_prereg_ok:
        reasons.append("original V09B preregistration is not unchanged")

    unpinned_only = bool(reasons) and all(reason.startswith("source hash not pinned:") for reason in reasons)
    if not reasons:
        classification = "QUALIFIED_RESEARCH_2022_2025"
    elif unpinned_only:
        classification = "AUDIT_ONLY_UNPINNED_SOURCE_HASHES"
    else:
        classification = "BLOCKED"

    return {
        "record_version": 1,
        "technical_status": "VERIFIED" if classification != "BLOCKED" else "BLOCKED",
        "research_classification": classification,
        "target_seasons": list(contract["target_seasons"]),
        "season_audits": [audit.as_dict() for audit in audits],
        "blockers": reasons,
        "v09b_preregistration_unchanged": v09b_prereg_ok,
        "qualified_2025_receipt_ok": receipt_ok,
        "v09b_execution_authorized": classification == "QUALIFIED_RESEARCH_2022_2025",
        "probability_model_built": False,
        "probability_feature_authorized": False,
        "production_dependency_authorized": False,
        "completed_2026_outcomes_used": 0,
        "missing_row_semantics": (
            "absence means not injury-listed in this source; it is not an active/healthy imputation"
        ),
        "duplicate_policy": (
            "feature-equivalent duplicate player-team-week rows may collapse deterministically; "
            "any identity/practice-state disagreement fails closed"
        ),
        "historical_game_status_feature_authorized": False,
        "actual_snaps_used": 0,
        "postgame_participation_used": 0,
    }

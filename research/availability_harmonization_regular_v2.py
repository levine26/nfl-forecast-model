from __future__ import annotations

"""Strict regular-season availability source qualification for V09B.

This module is research-only. It proves identity/state/chronology/source integrity for
2022-2025 regular-season injury-report rows. It never fits P(active), expected snaps,
player value, game probabilities, or any production feature.
"""

from dataclasses import dataclass
import hashlib
from io import StringIO
from typing import Any, Mapping

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import (
    normalize_game_status,
    normalize_practice_status,
    normalize_team,
)
from research.availability_harmonization_v1 import (
    _collapse_equivalent_duplicates,
    build_schedule_index,
    normalize_practice_status as normalize_practice_status_v1,
    validate_v09b_preregistry,
)
from research.availability_identity_regular_v2 import attach_stable_identity_v2


TARGET_SEASONS = (2022, 2023, 2024, 2025)
LEGACY_DATE_MODIFIED_SEASONS = (2022, 2023, 2024)
CANONICAL_STATES = {"full", "limited", "dnp"}
OFFICIAL_SEMANTIC_COLUMNS = [
    "season",
    "week",
    "team",
    "external_player",
    "external_position",
    "external_injury",
    "external_practice_status",
    "external_game_status",
    "external_source",
    "source_url",
]
SCHEDULE_HASH_COLUMNS = [
    "season",
    "week",
    "game_id",
    "gameday",
    "gametime",
    "home_team",
    "away_team",
    "game_type",
]


@dataclass(frozen=True)
class StrictSeasonAudit:
    season: int
    injury_source_sha256: str
    full_asset_rows: int
    model_eligible_rows: int
    exception_rows_removed: int
    official_pages_collected: int
    official_rows: int
    official_semantic_sha256: str
    stable_gsis_missing_rate: float
    canonical_to_official_identity_rate: float
    official_to_canonical_identity_rate: float
    practice_status_agreement_rate: float
    diagnostic_game_status_agreement_rate: float
    known_by_t120_rate_among_identity_matched_rows: float
    fully_qualified_practice_state_rate: float
    date_modified_parse_rate: float | None
    schedule_match_rate: float
    non_exception_schedule_unmatched_rows: int
    duplicate_canonical_identity_rows: int
    identical_duplicate_rows_collapsed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "injury_source_sha256": self.injury_source_sha256,
            "full_asset_rows": self.full_asset_rows,
            "model_eligible_rows": self.model_eligible_rows,
            "exception_rows_removed": self.exception_rows_removed,
            "official_pages_collected": self.official_pages_collected,
            "official_rows": self.official_rows,
            "official_semantic_sha256": self.official_semantic_sha256,
            "stable_gsis_missing_rate": self.stable_gsis_missing_rate,
            "canonical_to_official_identity_rate": self.canonical_to_official_identity_rate,
            "official_to_canonical_identity_rate": self.official_to_canonical_identity_rate,
            "practice_status_agreement_rate": self.practice_status_agreement_rate,
            "diagnostic_game_status_agreement_rate": self.diagnostic_game_status_agreement_rate,
            "known_by_t120_rate_among_identity_matched_rows": self.known_by_t120_rate_among_identity_matched_rows,
            "fully_qualified_practice_state_rate": self.fully_qualified_practice_state_rate,
            "date_modified_parse_rate": self.date_modified_parse_rate,
            "schedule_match_rate": self.schedule_match_rate,
            "non_exception_schedule_unmatched_rows": self.non_exception_schedule_unmatched_rows,
            "duplicate_canonical_identity_rows": self.duplicate_canonical_identity_rows,
            "identical_duplicate_rows_collapsed": self.identical_duplicate_rows_collapsed,
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_csv_bytes(frame: pd.DataFrame, columns: list[str], sort_columns: list[str]) -> bytes:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"stable hash frame missing columns: {sorted(missing)}")
    out = frame[columns].copy()
    out = out.sort_values(sort_columns, kind="stable", na_position="last")
    for column in columns:
        out[column] = out[column].fillna("").astype(str)
    return out.to_csv(index=False, lineterminator="\n").encode("utf-8")


def official_semantic_sha256(frame: pd.DataFrame) -> str:
    return sha256_bytes(
        _stable_csv_bytes(frame, OFFICIAL_SEMANTIC_COLUMNS, OFFICIAL_SEMANTIC_COLUMNS)
    )


def schedule_subset_sha256(frame: pd.DataFrame) -> str:
    return sha256_bytes(
        _stable_csv_bytes(frame, SCHEDULE_HASH_COLUMNS, ["season", "week", "game_id"])
    )


def collapse_exact_official_duplicates(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    missing = set(OFFICIAL_SEMANTIC_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"official cross-check missing semantic fields: {sorted(missing)}")
    deduped = frame.drop_duplicates(OFFICIAL_SEMANTIC_COLUMNS, keep="first").reset_index(drop=True)
    return deduped, int(len(frame) - len(deduped))


def _exception_mask(frame: pd.DataFrame, exceptions: list[Mapping[str, Any]]) -> pd.Series:
    if frame.empty:
        return pd.Series(False, index=frame.index, dtype=bool)
    season_values = pd.to_numeric(frame["season"], errors="coerce")
    week_values = pd.to_numeric(frame["week"], errors="coerce")
    teams = frame["team"].map(normalize_team)
    mask = pd.Series(False, index=frame.index, dtype=bool)
    for item in exceptions:
        allowed_teams = {normalize_team(team) for team in item.get("teams", [])}
        mask |= (
            season_values.eq(int(item["season"]))
            & week_values.eq(int(item["week"]))
            & teams.isin(allowed_teams)
        )
    return mask


def remove_model_universe_exceptions(
    frame: pd.DataFrame,
    exceptions: list[Mapping[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame.empty:
        return frame.copy(), frame.copy()
    out = frame.copy()
    out["team"] = out["team"].map(normalize_team)
    mask = _exception_mask(out, exceptions)
    return out.loc[~mask].copy(), out.loc[mask].copy()


def filter_model_eligible_schedule(
    schedules: pd.DataFrame,
    exceptions: list[Mapping[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = set(SCHEDULE_HASH_COLUMNS) - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule missing strict audit fields: {sorted(missing)}")
    out = schedules[SCHEDULE_HASH_COLUMNS].copy()
    out["season"] = pd.to_numeric(out["season"], errors="raise").astype(int)
    out["week"] = pd.to_numeric(out["week"], errors="raise").astype(int)
    out = out[
        out["season"].isin(TARGET_SEASONS)
        & out["week"].between(1, 18)
        & out["game_type"].astype(str).eq("REG")
    ].copy()
    exception_mask = pd.Series(False, index=out.index, dtype=bool)
    for item in exceptions:
        expected = {normalize_team(team) for team in item.get("teams", [])}
        season_week = out["season"].eq(int(item["season"])) & out["week"].eq(int(item["week"]))
        matchup = out.apply(
            lambda row: {normalize_team(row["home_team"]), normalize_team(row["away_team"])} == expected,
            axis=1,
        )
        exception_mask |= season_week & matchup
    exceptions_out = out.loc[exception_mask].copy()
    out = out.loc[~exception_mask].copy()
    out["home_team"] = out["home_team"].map(normalize_team)
    out["away_team"] = out["away_team"].map(normalize_team)
    return out.reset_index(drop=True), exceptions_out.reset_index(drop=True)


def parse_date_modified_utc(values: pd.Series) -> pd.Series:
    def parse_one(value: object) -> pd.Timestamp:
        if value is None or pd.isna(value):
            return pd.NaT
        try:
            stamp = pd.Timestamp(value)
            if stamp.tzinfo is None:
                stamp = stamp.tz_localize(
                    "America/Toronto", ambiguous="raise", nonexistent="raise"
                )
            return stamp.tz_convert("UTC")
        except (TypeError, ValueError, OverflowError):
            return pd.NaT

    return values.map(parse_one)


def validate_strict_injury_frame(
    payload: bytes,
    *,
    season: int,
    expected_rows: int,
    expected_sha256: str,
) -> tuple[pd.DataFrame, str]:
    digest = sha256_bytes(payload)
    if digest != expected_sha256:
        raise ValueError(
            f"{season} injury asset digest changed: expected {expected_sha256}, got {digest}"
        )
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    required = {
        "season",
        "week",
        "team",
        "gsis_id",
        "position",
        "full_name",
        "first_name",
        "last_name",
        "practice_primary_injury",
        "practice_secondary_injury",
        "practice_status",
        "report_status",
    }
    if season in LEGACY_DATE_MODIFIED_SEASONS:
        required.add("date_modified")
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{season} injury asset missing strict fields: {sorted(missing)}")
    frame = frame[pd.to_numeric(frame["season"], errors="coerce").eq(season)].copy()
    if len(frame) != int(expected_rows):
        raise ValueError(f"{season} injury row count changed: expected {expected_rows}, got {len(frame)}")
    if frame.empty:
        raise ValueError(f"{season} injury asset contains no rows")
    return frame, digest


def build_strict_season(
    injury_frame: pd.DataFrame,
    official_reports: pd.DataFrame,
    schedules: pd.DataFrame,
    player_master: pd.DataFrame,
    *,
    season: int,
    injury_source_sha256: str,
    official_pages_collected: int,
    exceptions: list[Mapping[str, Any]],
) -> tuple[pd.DataFrame, StrictSeasonAudit, pd.DataFrame, pd.DataFrame]:
    base = injury_frame.copy()
    base["season"] = pd.to_numeric(base["season"], errors="raise").astype(int)
    base["week"] = pd.to_numeric(base["week"], errors="raise").astype(int)
    base = base[base["season"].eq(season) & base["week"].between(1, 18)].copy()
    base["team"] = base["team"].map(normalize_team)
    base, exception_rows = remove_model_universe_exceptions(base, exceptions)

    ids = base["gsis_id"].astype("string").fillna("").str.strip()
    missing_ids = ids.eq("") | ids.str.lower().eq("nan") | ids.eq("<NA>")
    missing_id_rate = float(missing_ids.mean()) if len(base) else 1.0
    if missing_id_rate:
        raise ValueError(f"{season} model-eligible injury rows contain missing GSIS identity")

    base["practice_status_normalized"] = base["practice_status"].map(normalize_practice_status_v1)
    before_collapse = len(base)
    base, _, collapsed = _collapse_equivalent_duplicates(base, season=season)
    if collapsed != before_collapse - len(base):
        raise RuntimeError("duplicate-collapse accounting drifted")
    duplicate_canonical = int(base.duplicated(["season", "week", "team", "gsis_id"]).sum())
    if duplicate_canonical:
        raise ValueError(f"{season} canonical stable identity remains duplicated")

    official = official_reports.copy()
    official["season"] = pd.to_numeric(official["season"], errors="raise").astype(int)
    official["week"] = pd.to_numeric(official["week"], errors="raise").astype(int)
    official["team"] = official["team"].map(normalize_team)
    official = official[official["season"].eq(season) & official["week"].between(1, 18)].copy()
    official, official_exception_rows = remove_model_universe_exceptions(official, exceptions)
    official, _ = collapse_exact_official_duplicates(official)
    semantic_digest = official_semantic_sha256(official)

    matched_official = attach_stable_identity_v2(official, base, player_master)
    unique_mask = matched_official["identity_match_state"].eq("unique")
    official_identity_rate = float(unique_mask.mean()) if len(matched_official) else 0.0
    unresolved_official = matched_official.loc[~unique_mask].copy()
    unique = matched_official.loc[unique_mask].copy()
    stable_key = ["season", "week", "team", "gsis_id"]
    if unique.duplicated(stable_key).any():
        duplicated = unique.loc[unique.duplicated(stable_key, keep=False), stable_key]
        raise ValueError(
            f"{season} official source has conflicting duplicate stable rows: "
            f"{duplicated.drop_duplicates().head(10).to_dict('records')}"
        )

    ext_cols = stable_key + [
        "external_player",
        "external_position",
        "external_injury",
        "external_practice_status",
        "external_game_status",
        "external_source",
        "source_url",
        "identity_match_method",
    ]
    canonical = base.merge(unique[ext_cols], on=stable_key, how="left", validate="one_to_one")
    canonical["identity_matched"] = canonical["external_player"].notna()
    canonical_identity_rate = float(canonical["identity_matched"].mean()) if len(canonical) else 0.0

    canonical["nflverse_practice_normalized"] = canonical["practice_status"].map(normalize_practice_status)
    canonical["external_practice_normalized"] = canonical["external_practice_status"].map(normalize_practice_status)
    canonical["nflverse_game_normalized"] = canonical["report_status"].map(normalize_game_status)
    canonical["external_game_normalized"] = canonical["external_game_status"].map(normalize_game_status)
    canonical["recognized_practice_state"] = canonical["nflverse_practice_normalized"].isin(CANONICAL_STATES)
    canonical["practice_status_agrees"] = (
        canonical["identity_matched"]
        & canonical["recognized_practice_state"]
        & canonical["nflverse_practice_normalized"].eq(canonical["external_practice_normalized"])
    )
    canonical["game_status_agrees"] = (
        canonical["identity_matched"]
        & canonical["nflverse_game_normalized"].eq(canonical["external_game_normalized"])
    )

    schedule_index = build_schedule_index(schedules, season=season)
    canonical = canonical.merge(
        schedule_index,
        on=["season", "week", "team"],
        how="left",
        validate="many_to_one",
    )
    canonical["schedule_matched"] = canonical["game_id"].notna()
    canonical["t120_utc"] = canonical["kickoff_utc"] - pd.Timedelta(minutes=120)
    canonical["known_by_t120"] = (
        canonical["identity_matched"]
        & canonical["schedule_matched"]
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
        canonical["fully_qualified_practice_state"], "unknown"
    )
    canonical["injury_source_sha256"] = injury_source_sha256
    canonical["availability_source"] = "nflverse+official_nfl_regular_historical_crosscheck"
    canonical["chronology_policy"] = "official_game_status_report_day_eod_eastern_before_t120"
    canonical["historical_game_status_feature_authorized"] = False
    canonical["postgame_information_used"] = False

    identity_matched = canonical[canonical["identity_matched"]].copy()
    practice_rate = float(identity_matched["practice_status_agrees"].mean()) if len(identity_matched) else 0.0
    game_rate = float(identity_matched["game_status_agrees"].mean()) if len(identity_matched) else 0.0
    known_rate = float(identity_matched["known_by_t120"].mean()) if len(identity_matched) else 0.0
    qualified_rate = float(canonical["fully_qualified_practice_state"].mean()) if len(canonical) else 0.0
    schedule_rate = float(canonical["schedule_matched"].mean()) if len(canonical) else 0.0
    schedule_unmatched = int((~canonical["schedule_matched"]).sum())

    date_rate: float | None = None
    if season in LEGACY_DATE_MODIFIED_SEASONS:
        parsed = parse_date_modified_utc(canonical["date_modified"])
        canonical["date_modified_utc"] = parsed
        date_rate = float(parsed.notna().mean())
    else:
        canonical["date_modified_utc"] = pd.NaT

    audit = StrictSeasonAudit(
        season=season,
        injury_source_sha256=injury_source_sha256,
        full_asset_rows=int(len(injury_frame)),
        model_eligible_rows=int(len(canonical)),
        exception_rows_removed=int(len(exception_rows)),
        official_pages_collected=int(official_pages_collected),
        official_rows=int(len(official)),
        official_semantic_sha256=semantic_digest,
        stable_gsis_missing_rate=missing_id_rate,
        canonical_to_official_identity_rate=canonical_identity_rate,
        official_to_canonical_identity_rate=official_identity_rate,
        practice_status_agreement_rate=practice_rate,
        diagnostic_game_status_agreement_rate=game_rate,
        known_by_t120_rate_among_identity_matched_rows=known_rate,
        fully_qualified_practice_state_rate=qualified_rate,
        date_modified_parse_rate=date_rate,
        schedule_match_rate=schedule_rate,
        non_exception_schedule_unmatched_rows=schedule_unmatched,
        duplicate_canonical_identity_rows=duplicate_canonical,
        identical_duplicate_rows_collapsed=int(collapsed),
    )
    exceptions_combined = pd.concat([exception_rows, official_exception_rows], ignore_index=True, sort=False)
    return canonical, audit, unresolved_official, exceptions_combined


def verify_2025_receipt(receipt: Mapping[str, Any]) -> bool:
    metrics = receipt.get("qualification_metrics", {}) if isinstance(receipt, Mapping) else {}
    return bool(
        receipt.get("research_source_qualified") is True
        and receipt.get("supports_2025_reconstruction") is True
        and receipt.get("probability_feature_authorized") is False
        and receipt.get("production_dependency_authorized") is False
        and metrics.get("actual_snaps_used") == 0
        and metrics.get("postgame_participation_used") == 0
        and metrics.get("completed_2026_outcomes_used") == 0
    )


def evaluate_strict_harmonization(
    audits: list[StrictSeasonAudit],
    contract: Mapping[str, Any],
    *,
    schedule_sha256: str,
    v09b_prereg_ok: bool,
    qualified_2025_receipt_ok: bool,
) -> dict[str, Any]:
    gates = contract["frozen_qualification_gates"]
    expected_injury_hashes = contract["primary_state_source"]["expected_sha256"]
    expected_rows = contract["primary_state_source"]["expected_full_asset_rows"]
    expected_official_hashes = contract["independent_crosscheck"]["expected_semantic_bundle_sha256"]
    expected_schedule_hash = contract["schedule_source"]["expected_derived_subset_sha256"]
    by_season = {int(a.season): a for a in audits}
    hard_blockers: list[str] = []
    pin_blockers: list[str] = []

    observed_seasons = sorted(by_season)
    required_seasons = [int(x) for x in gates["required_seasons_exact"]]
    if observed_seasons != required_seasons:
        hard_blockers.append("required seasons mismatch")

    for season in required_seasons:
        audit = by_season.get(season)
        if audit is None:
            hard_blockers.append(f"missing strict season audit: {season}")
            continue
        key = str(season)
        if audit.injury_source_sha256 != expected_injury_hashes[key]:
            hard_blockers.append(f"injury source hash mismatch: {season}")
        if audit.full_asset_rows != int(expected_rows[key]):
            hard_blockers.append(f"injury source row count mismatch: {season}")
        if audit.official_pages_collected != int(gates["official_nfl_pages_required_per_season"]):
            hard_blockers.append(f"official page coverage failed: {season}")
        expected_official = expected_official_hashes.get(key)
        if expected_official is None:
            pin_blockers.append(f"official semantic source hash not pinned: {season}")
        elif audit.official_semantic_sha256 != expected_official:
            hard_blockers.append(f"official semantic source hash mismatch: {season}")
        if audit.stable_gsis_missing_rate > float(gates["stable_gsis_missing_rate_max"]):
            hard_blockers.append(f"stable identity missingness failed: {season}")
        if audit.canonical_to_official_identity_rate < float(
            gates["canonical_to_official_unique_identity_match_rate_min"]
        ):
            hard_blockers.append(f"canonical-to-official identity gate failed: {season}")
        if audit.official_to_canonical_identity_rate < float(
            gates["official_to_canonical_identity_resolution_rate_min"]
        ):
            hard_blockers.append(f"official-to-canonical identity gate failed: {season}")
        if audit.practice_status_agreement_rate < float(gates["practice_status_agreement_rate_min"]):
            hard_blockers.append(f"practice-state agreement gate failed: {season}")
        if audit.diagnostic_game_status_agreement_rate < float(
            gates["diagnostic_game_status_agreement_rate_min"]
        ):
            hard_blockers.append(f"diagnostic game-status agreement gate failed: {season}")
        if audit.known_by_t120_rate_among_identity_matched_rows != float(
            gates["known_by_t120_rate_required_among_identity_matched_rows"]
        ):
            hard_blockers.append(f"T-120 chronology gate failed: {season}")
        if audit.fully_qualified_practice_state_rate < float(
            gates["fully_qualified_practice_state_rate_min"]
        ):
            hard_blockers.append(f"fully qualified practice-state gate failed: {season}")
        if season in LEGACY_DATE_MODIFIED_SEASONS:
            if audit.date_modified_parse_rate is None or audit.date_modified_parse_rate < float(
                gates["legacy_date_modified_parse_rate_min"]
            ):
                hard_blockers.append(f"date_modified integrity gate failed: {season}")
        if audit.schedule_match_rate != float(gates["schedule_match_rate_required_among_model_eligible_rows"]):
            hard_blockers.append(f"schedule match gate failed: {season}")
        if audit.non_exception_schedule_unmatched_rows > int(
            gates["non_exception_schedule_unmatched_rows_allowed"]
        ):
            hard_blockers.append(f"non-exception schedule unmatched rows failed: {season}")
        if audit.duplicate_canonical_identity_rows > int(
            gates["duplicate_canonical_identity_rows_allowed"]
        ):
            hard_blockers.append(f"duplicate canonical identity gate failed: {season}")

    if expected_schedule_hash is None:
        pin_blockers.append("derived schedule subset hash not pinned")
    elif schedule_sha256 != expected_schedule_hash:
        hard_blockers.append("derived schedule subset hash mismatch")
    if not v09b_prereg_ok:
        hard_blockers.append("original V09B preregistration drifted")
    if not qualified_2025_receipt_ok:
        hard_blockers.append("qualified 2025 reconstruction receipt incompatible")

    if hard_blockers:
        classification = "BLOCKED"
        technical_status = "BLOCKED"
    elif pin_blockers:
        classification = "AUDIT_ONLY_UNPINNED_STRICT_SOURCE_HASHES"
        technical_status = "VERIFIED"
    else:
        classification = "QUALIFIED_REGULAR_SEASON_SOURCE_2022_2025"
        technical_status = "VERIFIED"

    return {
        "record_version": 2,
        "technical_status": technical_status,
        "research_classification": classification,
        "target_seasons": required_seasons,
        "season_audits": [audit.as_dict() for audit in audits],
        "schedule_subset_sha256": schedule_sha256,
        "hard_blockers": hard_blockers,
        "pin_blockers": pin_blockers,
        "v09b_preregistration_unchanged": bool(v09b_prereg_ok),
        "qualified_2025_receipt_ok": bool(qualified_2025_receipt_ok),
        "v09b_execution_authorized": classification == "QUALIFIED_REGULAR_SEASON_SOURCE_2022_2025",
        "probability_model_built": False,
        "probability_feature_authorized": False,
        "production_dependency_authorized": False,
        "candidate_promotion_authorized": False,
        "completed_2026_outcomes_used": 0,
        "game_outcomes_used": 0,
        "historical_game_status_feature_authorized": False,
        "actual_snaps_used": 0,
        "postgame_participation_used": 0,
        "postseason_v4_reopened": False,
        "missing_row_semantics": "absence means not injury-listed in this source; never infer active or healthy",
    }


__all__ = [
    "OFFICIAL_SEMANTIC_COLUMNS",
    "SCHEDULE_HASH_COLUMNS",
    "StrictSeasonAudit",
    "build_strict_season",
    "collapse_exact_official_duplicates",
    "evaluate_strict_harmonization",
    "filter_model_eligible_schedule",
    "official_semantic_sha256",
    "parse_date_modified_utc",
    "remove_model_universe_exceptions",
    "schedule_subset_sha256",
    "sha256_bytes",
    "validate_strict_injury_frame",
    "validate_v09b_preregistry",
    "verify_2025_receipt",
]

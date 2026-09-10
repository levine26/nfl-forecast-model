from __future__ import annotations

"""Research-only availability coverage qualification for LevLine v0.9B.

This module does not estimate P(active). It determines whether the historical source stack
is complete enough to justify doing so without hindsight. A missing target season is a
hard blocker, not an invitation to backfill from final starters or postgame participation.
"""

from typing import Any, Iterable

import pandas as pd

TARGET_SEASONS = (2022, 2023, 2024, 2025)
INJURY_SOURCE_LAST_VALID_SEASON = 2024
PROHIBITED_AVAILABILITY_INPUTS = (
    "final_starter_identity",
    "postgame_snap_share",
    "post_kickoff_participation",
    "retrospective_inactive_status",
    "later_injury_designation",
)


def _coverage_by_season(frame: pd.DataFrame | None, seasons: Iterable[int]) -> dict[int, int]:
    requested = [int(x) for x in seasons]
    if frame is None or frame.empty or "season" not in frame.columns:
        return {season: 0 for season in requested}
    values = pd.to_numeric(frame["season"], errors="coerce")
    return {season: int(values.eq(season).sum()) for season in requested}


def _id_coverage(frame: pd.DataFrame | None, column: str = "gsis_id") -> dict[str, Any]:
    if frame is None or frame.empty or column not in frame.columns:
        return {"rows": 0, "known_ids": 0, "missing_ids": 0, "missing_id_rate": None}
    ids = frame[column].astype("string").fillna("").str.strip()
    known = ids.ne("") & ids.str.lower().ne("nan") & ids.ne("<NA>")
    rows = int(len(frame))
    known_n = int(known.sum())
    return {
        "rows": rows,
        "known_ids": known_n,
        "missing_ids": rows - known_n,
        "missing_id_rate": float((rows - known_n) / rows) if rows else None,
    }


def qualify_v09b_sources(
    injuries: pd.DataFrame | None,
    depth_2025: pd.DataFrame | None,
    *,
    target_seasons: Iterable[int] = TARGET_SEASONS,
) -> dict[str, Any]:
    targets = [int(x) for x in target_seasons]
    injury_coverage = _coverage_by_season(injuries, targets)
    missing_injury_seasons = [season for season in targets if injury_coverage.get(season, 0) == 0]

    depth_has_timestamp = bool(
        depth_2025 is not None
        and not depth_2025.empty
        and "dt" in depth_2025.columns
        and depth_2025["dt"].notna().any()
    )
    depth_timestamp_parse_rate = None
    if depth_has_timestamp:
        parsed = pd.to_datetime(depth_2025["dt"], errors="coerce", utc=True)
        depth_timestamp_parse_rate = float(parsed.notna().mean())

    blockers: list[str] = []
    if missing_injury_seasons:
        blockers.append(
            "missing timestamped injury/practice-status coverage for target seasons: "
            + ", ".join(str(x) for x in missing_injury_seasons)
        )
    if 2025 in targets and not depth_has_timestamp:
        blockers.append("2025 depth-chart snapshots are unavailable or lack a usable timestamp")

    return {
        "status": "blocked" if blockers else "qualified_for_model_research",
        "candidate": "v0.9B-player-value-plus-availability",
        "target_seasons": targets,
        "injury_source_last_valid_season": INJURY_SOURCE_LAST_VALID_SEASON,
        "injury_rows_by_season": injury_coverage,
        "injury_id_coverage": _id_coverage(injuries),
        "depth_2025": {
            "rows": int(len(depth_2025)) if depth_2025 is not None else 0,
            "stable_id_coverage": _id_coverage(depth_2025),
            "timestamp_field_present": depth_has_timestamp,
            "timestamp_parse_rate": depth_timestamp_parse_rate,
        },
        "blockers": blockers,
        "prohibited_hindsight_inputs": list(PROHIBITED_AVAILABILITY_INPUTS),
        "p_active_model_built": False,
        "2026_outcomes_used": 0,
        "promotion_authorized": False,
    }

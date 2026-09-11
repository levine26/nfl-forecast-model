from __future__ import annotations

"""Correct FTN-PROCESS-01 source-identity gating without changing the preregistered model.

The frozen preregistration defines identity as an unambiguous join on
``nflverse_game_id + nflverse_play_id`` to PBP ``game_id + play_id``. Team labels are
needed later to build offense/defense aggregates, but their nullability is a separate
semantic-eligibility question and must not redefine whether the source keys matched.

This module exists because the first real historical run exposed a pre-result
implementation bug: the original implementation treated non-null ``posteam`` and
``defteam`` as part of the identity gate. No historical model result was produced before
this correction.
"""

from typing import Any

import pandas as pd

from research.ftn_process_v1 import (
    EXPERIMENT_ID,
    MIN_IDENTITY_RATE,
    OFFENSE_METRICS,
    DEFENSE_METRICS,
    RAW_FIELDS,
    _bool_numeric,
    _utc_series,
)


class FTNIdentityGateError(RuntimeError):
    """Fail-closed source gate carrying a machine-readable preflight audit."""

    def __init__(self, message: str, audit: dict[str, Any]):
        super().__init__(message)
        self.audit = audit


def join_ftn_to_pbp(
    ftn: pd.DataFrame,
    pbp: pd.DataFrame,
    *,
    min_identity_rate: float = MIN_IDENTITY_RATE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required_ftn = {
        "nflverse_game_id",
        "nflverse_play_id",
        "season",
        "week",
        "date_pulled",
        *RAW_FIELDS,
    }
    missing_ftn = required_ftn - set(ftn.columns)
    if missing_ftn:
        raise ValueError(f"FTN-PROCESS-01 missing FTN fields: {sorted(missing_ftn)}")
    required_pbp = {"game_id", "play_id", "posteam", "defteam"}
    missing_pbp = required_pbp - set(pbp.columns)
    if missing_pbp:
        raise ValueError(f"FTN-PROCESS-01 missing PBP fields: {sorted(missing_pbp)}")

    chart = ftn.copy()
    season = pd.to_numeric(chart["season"], errors="coerce")
    if season.dropna().ge(2026).any():
        raise ValueError("FTN-PROCESS-01 may not load 2026-or-later FTN rows")
    chart["nflverse_game_id"] = chart["nflverse_game_id"].astype(str)
    chart["nflverse_play_id"] = pd.to_numeric(
        chart["nflverse_play_id"], errors="coerce"
    ).astype("Int64")
    chart["date_pulled_utc"] = _utc_series(chart["date_pulled"])

    chart_keys = chart[["nflverse_game_id", "nflverse_play_id"]]
    if chart_keys.isna().any(axis=None):
        raise ValueError("FTN-PROCESS-01 FTN rows contain missing game/play identity")
    if chart_keys.duplicated().any():
        raise ValueError("FTN-PROCESS-01 FTN game/play identity is not unique")

    keys = pbp[["game_id", "play_id", "posteam", "defteam"]].copy()
    keys["game_id"] = keys["game_id"].astype(str)
    keys["play_id"] = pd.to_numeric(keys["play_id"], errors="coerce").astype("Int64")
    keys = keys[keys["game_id"].notna() & keys["play_id"].notna()].copy()
    if keys[["game_id", "play_id"]].duplicated().any():
        raise ValueError("FTN-PROCESS-01 PBP game/play identity is not unique")

    joined = chart.merge(
        keys,
        how="left",
        left_on=["nflverse_game_id", "nflverse_play_id"],
        right_on=["game_id", "play_id"],
        validate="one_to_one",
        indicator="_pbp_key_merge",
    )

    key_matched = joined["_pbp_key_merge"].eq("both")
    team_semantic_eligible = (
        key_matched & joined["posteam"].notna() & joined["defteam"].notna()
    )
    date_valid = joined["date_pulled_utc"].notna()

    input_rows = int(len(joined))
    identity_matched_rows = int(key_matched.sum())
    semantic_eligible_rows = int(team_semantic_eligible.sum())
    identity_rate = float(key_matched.mean()) if input_rows else 0.0
    date_rate = float(date_valid.mean()) if input_rows else 0.0
    team_assignment_rate = (
        float(semantic_eligible_rows / identity_matched_rows)
        if identity_matched_rows
        else 0.0
    )

    audit = {
        "experiment_id": EXPERIMENT_ID,
        "identity_definition": "exact_game_id_plus_play_id_merge",
        "input_ftn_rows": input_rows,
        "identity_matched_rows": identity_matched_rows,
        "identity_unmatched_rows": input_rows - identity_matched_rows,
        "identity_join_rate": identity_rate,
        "semantic_team_eligible_rows": semantic_eligible_rows,
        "semantic_team_missing_rows": identity_matched_rows - semantic_eligible_rows,
        "semantic_team_assignment_rate_given_identity": team_assignment_rate,
        "date_pulled_valid_rows": int(date_valid.sum()),
        "date_pulled_valid_rate": date_rate,
        "minimum_required_rate": float(min_identity_rate),
        "latest_ftn_season": int(season.dropna().max()) if season.notna().any() else None,
        "completed_2026_outcomes_used": 0,
        "model_or_threshold_changed": False,
    }

    if identity_rate < float(min_identity_rate):
        raise FTNIdentityGateError(
            f"FTN-PROCESS-01 identity join rate {identity_rate:.6f} < {min_identity_rate:.6f}",
            audit,
        )
    if date_rate < float(min_identity_rate):
        raise FTNIdentityGateError(
            f"FTN-PROCESS-01 date_pulled validity {date_rate:.6f} < {min_identity_rate:.6f}",
            audit,
        )

    eligible = team_semantic_eligible & date_valid
    joined = joined.loc[eligible].drop(columns=["_pbp_key_merge"]).copy()
    for field in OFFENSE_METRICS.values():
        joined[field] = _bool_numeric(joined[field])
    for field in DEFENSE_METRICS.values():
        joined[field] = pd.to_numeric(joined[field], errors="coerce")

    audit["eligible_joined_rows"] = int(len(joined))
    return joined, audit

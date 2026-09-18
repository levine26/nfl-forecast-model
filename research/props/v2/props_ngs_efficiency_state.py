from __future__ import annotations

"""Point-in-time-safe Next Gen Stats state for LevLine Props 2.0 research.

This module is feature engineering only. It does not alter a Fair Line by itself.
It exposes strictly lagged weekly NGS signals that can support decomposed efficiency
challengers in a later rolling-origin fit.

NFL NGS weekly data have minimum-volume publication thresholds, so missing rows are
treated as missing evidence rather than zero performance.
"""

from dataclasses import dataclass, asdict
import math
from typing import Any

import numpy as np
import pandas as pd

ENGINE_VERSION = "levline-props-ngs-efficiency-state-v0.1.0"
RESEARCH_LABEL = "RESEARCH FEATURE STATE - NO PRODUCTION AUTHORIZATION"
HALF_LIFE_GAMES = 8.0

COMMON_REQUIRED = {
    "season",
    "week",
    "player_gsis_id",
}

PASSING_FEATURES = (
    "avg_time_to_throw",
    "avg_completed_air_yards",
    "avg_intended_air_yards",
    "avg_air_yards_differential",
    "aggressiveness",
    "avg_air_yards_to_sticks",
    "completion_percentage",
    "expected_completion_percentage",
    "completion_percentage_above_expectation",
)

RECEIVING_FEATURES = (
    "avg_air_distance",
    "avg_cushion",
    "avg_separation",
    "percent_share_of_intended_air_yards",
    "catch_percentage",
    "avg_yac",
    "avg_expected_yac",
    "avg_yac_above_expectation",
)

RUSHING_FEATURES = (
    "efficiency",
    "percent_attempts_gte_eight_defenders",
    "avg_time_to_los",
    "avg_rush_yards",
    "rush_yards_over_expected_per_att",
    "rush_pct_over_expected",
)


class NGSEfficiencyStateError(ValueError):
    pass


@dataclass(frozen=True)
class NGSPlayerState:
    player_id: str
    season: int
    week: int
    passing: dict[str, float | None]
    receiving: dict[str, float | None]
    rushing: dict[str, float | None]
    evidence: dict[str, float | int]
    engine_version: str = ENGINE_VERSION
    research_label: str = RESEARCH_LABEL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_id(value: Any) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return bool(text) and text.lower() not in {"nan", "<na>", "none", "null"}


def _normalize(frame: pd.DataFrame | None, *, season: int, week: int, label: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    missing = COMMON_REQUIRED - set(frame.columns)
    if missing:
        raise NGSEfficiencyStateError(f"{label} NGS frame missing fields: {sorted(missing)}")

    out = frame.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out["player_gsis_id"] = out["player_gsis_id"].astype("string").fillna("").str.strip()
    out = out[
        out["season"].notna()
        & out["week"].notna()
        & out["player_gsis_id"].map(_valid_id)
    ].copy()

    if "season_type" in out.columns:
        out = out[out["season_type"].astype(str).str.upper().eq("REG")].copy()

    # NGS week 0 is season summary, not a point-in-time weekly observation.
    out = out[out["week"].gt(0)].copy()
    unsafe = (out["season"] > int(season)) | (
        out["season"].eq(int(season)) & out["week"].ge(int(week))
    )
    out = out[~unsafe].copy()
    return out.sort_values(["season", "week", "player_gsis_id"]).reset_index(drop=True)


def _decay_weights(n: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return np.power(0.5, age / HALF_LIFE_GAMES)


def _weighted_feature(rows: pd.DataFrame, feature: str, opportunity_col: str) -> float | None:
    if feature not in rows.columns:
        return None
    values = pd.to_numeric(rows[feature], errors="coerce")
    if opportunity_col in rows.columns:
        opportunity = pd.to_numeric(rows[opportunity_col], errors="coerce").fillna(0.0)
    else:
        opportunity = pd.Series(1.0, index=rows.index)

    valid = values.notna() & opportunity.gt(0)
    if not valid.any():
        return None
    sub_values = values[valid].to_numpy(dtype=float)
    sub_opportunity = opportunity[valid].to_numpy(dtype=float)
    recency = _decay_weights(len(rows))[np.flatnonzero(valid.to_numpy())]
    weights = sub_opportunity * recency
    if weights.sum() <= 0:
        return None
    value = float(np.average(sub_values, weights=weights))
    return value if math.isfinite(value) else None


def _channel_state(
    frame: pd.DataFrame,
    player_id: str,
    features: tuple[str, ...],
    opportunity_col: str,
) -> tuple[dict[str, float | None], dict[str, float | int]]:
    if frame.empty:
        return {feature: None for feature in features}, {
            "rows": 0,
            "raw_opportunities": 0.0,
            "recency_weighted_opportunities": 0.0,
        }

    rows = frame[frame["player_gsis_id"].astype(str).eq(str(player_id))].copy()
    rows = rows.sort_values(["season", "week"])
    if rows.empty:
        return {feature: None for feature in features}, {
            "rows": 0,
            "raw_opportunities": 0.0,
            "recency_weighted_opportunities": 0.0,
        }

    if opportunity_col in rows.columns:
        opportunities = pd.to_numeric(rows[opportunity_col], errors="coerce").fillna(0.0).clip(lower=0)
    else:
        opportunities = pd.Series(1.0, index=rows.index)
    recency = _decay_weights(len(rows))
    return (
        {
            feature: _weighted_feature(rows, feature, opportunity_col)
            for feature in features
        },
        {
            "rows": int(len(rows)),
            "raw_opportunities": float(opportunities.sum()),
            "recency_weighted_opportunities": float(np.dot(opportunities.to_numpy(float), recency)),
        },
    )


def build_lagged_ngs_state(
    *,
    passing: pd.DataFrame | None,
    receiving: pd.DataFrame | None,
    rushing: pd.DataFrame | None,
    season: int,
    week: int,
    player_ids: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build strictly pre-target-week advanced efficiency state by GSIS player ID."""

    pass_hist = _normalize(passing, season=season, week=week, label="passing")
    rec_hist = _normalize(receiving, season=season, week=week, label="receiving")
    rush_hist = _normalize(rushing, season=season, week=week, label="rushing")

    discovered = set()
    for frame in (pass_hist, rec_hist, rush_hist):
        if not frame.empty:
            discovered.update(frame["player_gsis_id"].astype(str))
    ids = sorted(
        {str(value) for value in (player_ids if player_ids is not None else discovered) if _valid_id(value)}
    )

    records: list[dict[str, Any]] = []
    for player_id in ids:
        p_state, p_evidence = _channel_state(
            pass_hist, player_id, PASSING_FEATURES, "attempts"
        )
        r_state, r_evidence = _channel_state(
            rec_hist, player_id, RECEIVING_FEATURES, "targets"
        )
        u_state, u_evidence = _channel_state(
            rush_hist, player_id, RUSHING_FEATURES, "rush_attempts"
        )
        record = {
            "player_id": player_id,
            "target_season": int(season),
            "target_week": int(week),
            **{f"ngs_pass_{key}": value for key, value in p_state.items()},
            **{f"ngs_rec_{key}": value for key, value in r_state.items()},
            **{f"ngs_rush_{key}": value for key, value in u_state.items()},
            "ngs_pass_rows": p_evidence["rows"],
            "ngs_pass_attempts_raw": p_evidence["raw_opportunities"],
            "ngs_pass_attempts_weighted": p_evidence["recency_weighted_opportunities"],
            "ngs_rec_rows": r_evidence["rows"],
            "ngs_rec_targets_raw": r_evidence["raw_opportunities"],
            "ngs_rec_targets_weighted": r_evidence["recency_weighted_opportunities"],
            "ngs_rush_rows": u_evidence["rows"],
            "ngs_rush_attempts_raw": u_evidence["raw_opportunities"],
            "ngs_rush_attempts_weighted": u_evidence["recency_weighted_opportunities"],
        }
        records.append(record)

    frame = pd.DataFrame(records)
    latest = {}
    for label, hist in (
        ("passing", pass_hist),
        ("receiving", rec_hist),
        ("rushing", rush_hist),
    ):
        if hist.empty:
            latest[label] = None
        else:
            row = hist.sort_values(["season", "week"]).iloc[-1]
            latest[label] = {"season": int(row["season"]), "week": int(row["week"])}

    audit = {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "target_season": int(season),
        "target_week": int(week),
        "half_life_games": HALF_LIFE_GAMES,
        "players_requested": len(ids),
        "players_with_any_state": int(
            0 if frame.empty else (
                frame[["ngs_pass_rows", "ngs_rec_rows", "ngs_rush_rows"]].sum(axis=1).gt(0).sum()
            )
        ),
        "historical_max_period_used": latest,
        "target_week_rows_used": 0,
        "missing_rows_mean_missing_evidence_not_zero": True,
    }
    return frame, audit


def load_ngs_efficiency_history(seasons: list[int] | tuple[int, ...]):
    """Load all three NGS weekly channels through nflreadpy.

    Kept here, rather than the shared winner-model data bundle, so Props research
    cannot silently change official model inputs.
    """

    import nflreadpy as nfl

    def pandas(frame):
        return frame.to_pandas() if hasattr(frame, "to_pandas") else frame

    season_list = sorted({int(value) for value in seasons})
    return {
        "passing": pandas(nfl.load_nextgen_stats(season_list, stat_type="passing")),
        "receiving": pandas(nfl.load_nextgen_stats(season_list, stat_type="receiving")),
        "rushing": pandas(nfl.load_nextgen_stats(season_list, stat_type="rushing")),
    }

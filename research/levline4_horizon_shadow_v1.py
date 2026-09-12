from __future__ import annotations

"""Immutable exact-replay shadow ledger for LevLine 4 market horizons.

This module does not fit a model and does not touch production. It converts the first
qualified point-in-time sportsbook consensus captured at each preregistered horizon into
frozen research forecasts. The market candidate uses the consensus directly; the F-ST
candidate applies the already-frozen F-ST coefficients to that same market probability
and the nested PURE probability preserved in the official immutable lock, but only when
that lock existed no later than the horizon being evaluated.

Missing or late inputs fail closed. Forecast identities already present in the ledger are
never rewritten.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any

import numpy as np
import pandas as pd

from nfl_forecast.fst_production import (
    CANDIDATE_ID as FST_ARTIFACT_ID,
    frozen_fst_probability,
    load_fst_artifact,
)
from research.market_capture_contract_v2 import MIN_CONSENSUS_BOOKS, QUALIFYING_CLOSE_ROW_TYPE
from research.market_capture_v2 import CAPTURE_TOLERANCE_MINUTES, HORIZONS

LEDGER_VERSION = "LEVLINE4-HORIZON-SHADOW-V1"
MARKET_CANDIDATE_ID = "L4-MKT-H-V1"
FST_HORIZON_CANDIDATE_ID = "L4-FST-H-V1"
IDENTITY_COLUMNS = ("game_id", "horizon", "candidate_id")


def _as_utc(value: Any) -> pd.Timestamp:
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"invalid UTC timestamp: {value!r}")
    return parsed


def _finite_probability(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or not 0.0 < parsed < 1.0:
        return None
    return parsed


def _finite_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _int_or_none(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _input_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_existing(existing: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return existing.copy()
    missing = set(IDENTITY_COLUMNS) - set(existing.columns)
    if missing:
        raise ValueError(f"existing LevLine 4 shadow ledger missing identity fields: {sorted(missing)}")
    if existing.duplicated(list(IDENTITY_COLUMNS)).any():
        dupes = existing.loc[
            existing.duplicated(list(IDENTITY_COLUMNS), keep=False),
            list(IDENTITY_COLUMNS),
        ]
        raise ValueError(
            "existing LevLine 4 shadow ledger contains duplicate identities: "
            f"{dupes.to_dict('records')[:5]}"
        )
    return existing.copy()


def _qualified_consensus_rows(market: pd.DataFrame) -> pd.DataFrame:
    required = {
        "row_type",
        "game_id",
        "home_team",
        "away_team",
        "kickoff_timestamp_utc",
        "horizon",
        "target_timestamp_utc",
        "request_timestamp_utc",
        "timing_error_minutes",
        "h2h_home_no_vig",
        "source_count",
    }
    if market.empty or not required.issubset(market.columns):
        return pd.DataFrame()

    work = market.copy()
    work = work[work["row_type"].astype(str).eq(QUALIFYING_CLOSE_ROW_TYPE)].copy()
    work["source_count_num"] = pd.to_numeric(work["source_count"], errors="coerce")
    work["prob_num"] = pd.to_numeric(work["h2h_home_no_vig"], errors="coerce")
    work["timing_error_num"] = pd.to_numeric(work["timing_error_minutes"], errors="coerce")
    work["request_dt"] = pd.to_datetime(work["request_timestamp_utc"], utc=True, errors="coerce")
    work["target_dt"] = pd.to_datetime(work["target_timestamp_utc"], utc=True, errors="coerce")
    work["kickoff_dt"] = pd.to_datetime(work["kickoff_timestamp_utc"], utc=True, errors="coerce")

    valid_horizon = work["horizon"].astype(str).isin(HORIZONS)
    valid_prob = work["prob_num"].gt(0.0) & work["prob_num"].lt(1.0)
    valid_timing = work["timing_error_num"].abs().le(float(CAPTURE_TOLERANCE_MINUTES))
    valid_time = work[["request_dt", "target_dt", "kickoff_dt"]].notna().all(axis=1)
    pregame = work["request_dt"].lt(work["kickoff_dt"])
    enough_books = work["source_count_num"].ge(int(MIN_CONSENSUS_BOOKS))
    work = work[
        valid_horizon & valid_prob & valid_timing & valid_time & pregame & enough_books
    ].copy()
    if work.empty:
        return work

    expected_targets = work.apply(
        lambda row: row["kickoff_dt"]
        - pd.Timedelta(minutes=HORIZONS[str(row["horizon"])]),
        axis=1,
    )
    target_error_seconds = (work["target_dt"] - expected_targets).abs().dt.total_seconds()
    work = work[target_error_seconds.le(1.0)].copy()
    if work.empty:
        return work

    # The collector closes a horizon after its first qualified consensus. Reassert that
    # rule here so an accidental later retry can never rewrite the research forecast.
    work = work.sort_values(["game_id", "horizon", "request_dt"], kind="mergesort")
    return work.drop_duplicates(["game_id", "horizon"], keep="first").copy()


def _locked_rows(prediction_history: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if prediction_history.empty or "game_id" not in prediction_history.columns:
        return {}
    work = prediction_history.copy()
    if "lock_status" not in work.columns:
        return {}
    work = work[work["lock_status"].astype(str).eq("LOCKED")].copy()
    if work.empty:
        return {}
    if work["game_id"].astype(str).duplicated().any():
        dupes = work.loc[
            work["game_id"].astype(str).duplicated(keep=False), "game_id"
        ].astype(str).tolist()
        raise ValueError(
            f"official prediction history has duplicate LOCKED game ids: {dupes[:5]}"
        )
    return {str(row["game_id"]): row.to_dict() for _, row in work.iterrows()}


def _base_row(consensus: pd.Series, generated_at: pd.Timestamp) -> dict[str, Any]:
    horizon = str(consensus["horizon"])
    market_prob = float(consensus["prob_num"])
    home_team = str(consensus["home_team"])
    away_team = str(consensus["away_team"])
    kickoff = consensus["kickoff_dt"]
    target = consensus["target_dt"]
    request = consensus["request_dt"]
    return {
        "ledger_version": LEDGER_VERSION,
        "game_id": str(consensus["game_id"]),
        "season": _int_or_none(consensus.get("season")),
        "week": _int_or_none(consensus.get("week")),
        "home_team": home_team,
        "away_team": away_team,
        "kickoff_timestamp_utc": kickoff.isoformat(),
        "horizon": horizon,
        "horizon_minutes": int(HORIZONS[horizon]),
        "target_timestamp_utc": target.isoformat(),
        "market_snapshot_request_timestamp_utc": request.isoformat(),
        "market_timing_error_minutes": float(consensus["timing_error_num"]),
        "market_home_prob": market_prob,
        "market_source_count": int(consensus["source_count_num"]),
        "market_source_names": str(consensus.get("source_names") or ""),
        "market_probability_range": _finite_or_none(consensus.get("probability_range")),
        "market_max_freshness_minutes": _finite_or_none(
            consensus.get("max_freshness_minutes")
        ),
        "market_event_id": consensus.get("event_id"),
        "generated_at_utc": generated_at.isoformat(),
        "generation_mode": "prospective_exact_replay",
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }


def _market_candidate(consensus: pd.Series, generated_at: pd.Timestamp) -> dict[str, Any]:
    row = _base_row(consensus, generated_at)
    probability = float(row["market_home_prob"])
    row.update(
        {
            "candidate_id": MARKET_CANDIDATE_ID,
            "candidate_family": "same_horizon_market_consensus",
            "pure_home_prob": None,
            "pure_source_lock_timestamp_utc": None,
            "pure_source_model_version": None,
            "pure_source_fst_artifact_id": None,
            "fst_training_data_sha256": None,
            "fst_freeze_implementation_sha": None,
            "final_home_prob": probability,
            "pick": row["home_team"] if probability >= 0.5 else row["away_team"],
        }
    )
    row["input_digest_sha256"] = _input_digest(
        {
            "candidate_id": row["candidate_id"],
            "game_id": row["game_id"],
            "horizon": row["horizon"],
            "market_snapshot_request_timestamp_utc": row[
                "market_snapshot_request_timestamp_utc"
            ],
            "market_home_prob": row["market_home_prob"],
            "market_source_names": row["market_source_names"],
        }
    )
    return row


def _fst_candidate(
    consensus: pd.Series,
    official_lock: dict[str, Any],
    generated_at: pd.Timestamp,
) -> dict[str, Any] | None:
    pure = _finite_probability(official_lock.get("fst_pure_home_prob"))
    if pure is None:
        return None
    if str(official_lock.get("fst_artifact_id") or "") != FST_ARTIFACT_ID:
        return None
    try:
        lock_timestamp = _as_utc(official_lock.get("lock_timestamp_utc"))
    except ValueError:
        return None

    target = consensus["target_dt"]
    kickoff = consensus["kickoff_dt"]
    # The PURE state is usable only if it was already frozen by the candidate horizon.
    # This prevents a T-96 official lock, for example, from being replayed as a T-120
    # research forecast. It remains valid evidence for T-60/T-45/T-30 because those
    # targets occur later in time.
    if not (lock_timestamp <= target < kickoff):
        return None
    if lock_timestamp > generated_at:
        return None

    artifact = load_fst_artifact()
    market_prob = float(consensus["prob_num"])
    probability = float(
        frozen_fst_probability(
            np.asarray([market_prob], dtype=float),
            np.asarray([pure], dtype=float),
            artifact,
        )[0]
    )
    row = _base_row(consensus, generated_at)
    row.update(
        {
            "candidate_id": FST_HORIZON_CANDIDATE_ID,
            "candidate_family": "frozen_fst_same_horizon_market",
            "pure_home_prob": pure,
            "pure_source_lock_timestamp_utc": lock_timestamp.isoformat(),
            "pure_source_model_version": official_lock.get("model_version"),
            "pure_source_fst_artifact_id": official_lock.get("fst_artifact_id"),
            "fst_training_data_sha256": artifact.training_data_sha256,
            "fst_freeze_implementation_sha": artifact.freeze_implementation_sha,
            "final_home_prob": probability,
            "pick": row["home_team"] if probability >= 0.5 else row["away_team"],
        }
    )
    row["input_digest_sha256"] = _input_digest(
        {
            "candidate_id": row["candidate_id"],
            "game_id": row["game_id"],
            "horizon": row["horizon"],
            "market_snapshot_request_timestamp_utc": row[
                "market_snapshot_request_timestamp_utc"
            ],
            "market_home_prob": row["market_home_prob"],
            "pure_home_prob": row["pure_home_prob"],
            "pure_source_lock_timestamp_utc": row["pure_source_lock_timestamp_utc"],
            "fst_artifact_id": row["pure_source_fst_artifact_id"],
            "fst_training_data_sha256": row["fst_training_data_sha256"],
            "fst_freeze_implementation_sha": row["fst_freeze_implementation_sha"],
        }
    )
    return row


def build_shadow_ledger(
    market_snapshots: pd.DataFrame,
    prediction_history: pd.DataFrame,
    *,
    existing_ledger: pd.DataFrame | None = None,
    generated_at_utc: datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Return existing immutable rows plus any newly eligible pregame forecasts."""
    if generated_at_utc is None:
        generated_at = pd.Timestamp(datetime.now(timezone.utc))
    else:
        generated_at = _as_utc(generated_at_utc)

    existing = _validate_existing(
        existing_ledger if existing_ledger is not None else pd.DataFrame()
    )
    existing_keys = {
        tuple(str(row[column]) for column in IDENTITY_COLUMNS)
        for _, row in existing.iterrows()
    }
    consensus_rows = _qualified_consensus_rows(market_snapshots)
    if consensus_rows.empty:
        return existing.reset_index(drop=True)

    locks = _locked_rows(prediction_history)
    additions: list[dict[str, Any]] = []
    for _, consensus in consensus_rows.iterrows():
        # Never create a forecast after kickoff, even when all source inputs happened to
        # have been captured earlier. Missed prospective generation is intentionally lost.
        if generated_at >= consensus["kickoff_dt"]:
            continue

        market_row = _market_candidate(consensus, generated_at)
        market_key = tuple(str(market_row[column]) for column in IDENTITY_COLUMNS)
        if market_key not in existing_keys:
            additions.append(market_row)
            existing_keys.add(market_key)

        official_lock = locks.get(str(consensus["game_id"]))
        if official_lock is None:
            continue
        fst_row = _fst_candidate(consensus, official_lock, generated_at)
        if fst_row is None:
            continue
        fst_key = tuple(str(fst_row[column]) for column in IDENTITY_COLUMNS)
        if fst_key not in existing_keys:
            additions.append(fst_row)
            existing_keys.add(fst_key)

    if not additions:
        return existing.reset_index(drop=True)
    combined = pd.concat([existing, pd.DataFrame(additions)], ignore_index=True, sort=False)
    combined = _validate_existing(combined)
    order = [
        column
        for column in ("game_id", "horizon_minutes", "candidate_id")
        if column in combined.columns
    ]
    if order:
        combined = combined.sort_values(
            order,
            ascending=[True, False, True][: len(order)],
            kind="mergesort",
        )
    return combined.reset_index(drop=True)

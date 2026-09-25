from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

PROGRAM_ID = "FV2-PROS-M1-MARKETSTATE-01"
SCHEMA_VERSION = "levline-m1-market-state-v1"

PREDICTOR_HORIZONS = {
    "T-2160m": 2160,
    "T-720m": 720,
    "T-360m": 360,
    "T-120m": 120,
}
DIAGNOSTIC_HORIZONS = {
    "T-60m": 60,
    "T-30m": 30,
}
LATEST_PREKICK = "LATEST_PREKICK"
ALL_FIXED_HORIZONS = {**PREDICTOR_HORIZONS, **DIAGNOSTIC_HORIZONS}

CAPTURE_TOLERANCE_MINUTES = 7.5
LATEST_PREKICK_WINDOW_MINUTES = 10.0
LATEST_PREKICK_SAFETY_MINUTES = 1.0
MAX_EVENT_KICKOFF_DELTA_MINUTES = 30.0
MIN_COMPLETE_BOOKS = 2
STALE_QUOTE_MINUTES = 15.0
KEY_NUMBERS = (3.0, 7.0)

# The M1 V1 eligibility rule is deliberately strict and outcome-blind. A book is
# "complete" only when the four frozen contemporaneous market families and quote
# age are all available. Partial books remain raw evidence but do not close a horizon.
COMPLETE_BOOK_FIELDS = (
    "home_spread",
    "spread_home_cover_no_vig",
    "h2h_home_no_vig",
    "total_points",
    "freshness_minutes",
)

PREDICTOR_FEATURE_COLUMNS = (
    "consensus_spread_t120",
    "spread_favorite_no_vig_t120",
    "moneyline_favorite_no_vig_t120",
    "consensus_total_t120",
    "spread_dispersion_t120",
    "active_book_count_t120",
    "median_quote_age_minutes_t120",
    "stale_book_share_t120",
    "favorite_spread_strength_move_t360_to_t120",
    "spread_price_move_unchanged_number_t360_to_t120",
    "movement_breadth_t360_to_t120",
    "key_number_crossing_3_or_7_t360_to_t120",
    "spread_moneyline_logit_residual_t120",
)

# This is the mechanical information barrier used by tests and by model callers.
# Diagnostic fields are never part of the predictor feature registry.
DIAGNOSTIC_ONLY_PREFIXES = (
    "t60_",
    "t30_",
    "latest_prekick_",
)

FORBIDDEN_OUTCOME_FIELDS = {
    "home_score",
    "away_score",
    "result",
    "ats_result",
    "cover_result",
    "margin",
    "completed",
    "final_score",
}


def horizon_target(kickoff_utc: datetime, horizon: str) -> datetime:
    if horizon not in ALL_FIXED_HORIZONS:
        raise ValueError(f"unsupported fixed M1 horizon: {horizon}")
    kickoff = kickoff_utc.astimezone(timezone.utc)
    return kickoff - timedelta(minutes=ALL_FIXED_HORIZONS[horizon])


def due_fixed_horizons(kickoff_utc: datetime, now_utc: datetime) -> list[dict[str, Any]]:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    now = now_utc.astimezone(timezone.utc)
    rows: list[dict[str, Any]] = []
    for horizon, minutes in ALL_FIXED_HORIZONS.items():
        target = kickoff - timedelta(minutes=minutes)
        timing_error = (now - target).total_seconds() / 60.0
        if -CAPTURE_TOLERANCE_MINUTES <= timing_error <= 0.0:
            rows.append(
                {
                    "horizon": horizon,
                    "role": "predictor" if horizon in PREDICTOR_HORIZONS else "diagnostic_only",
                    "target_timestamp_utc": target,
                    "timing_error_minutes": timing_error,
                }
            )
    return rows


def latest_prekick_due(kickoff_utc: datetime, now_utc: datetime) -> bool:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    now = now_utc.astimezone(timezone.utc)
    minutes_to_kick = (kickoff - now).total_seconds() / 60.0
    return LATEST_PREKICK_SAFETY_MINUTES <= minutes_to_kick <= LATEST_PREKICK_WINDOW_MINUTES


def horizon_role(horizon: str) -> str:
    if horizon in PREDICTOR_HORIZONS:
        return "predictor"
    if horizon in DIAGNOSTIC_HORIZONS or horizon == LATEST_PREKICK:
        return "diagnostic_only"
    return "outside_m1"

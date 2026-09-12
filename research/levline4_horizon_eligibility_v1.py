from __future__ import annotations

"""Strict point-in-time eligibility for LevLine 4 horizon grading.

Raw audit/shadow rows remain immutable. This module only decides whether a preserved
row is eligible to claim a nominal T-minus forecast. In particular, a positive timing
error means the request happened after the nominal cutoff and is therefore excluded.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

MAX_EARLY_MINUTES = 7.5
PRIMARY_HORIZONS = ("T-120m", "T-60m", "T-45m", "T-30m")


@dataclass(frozen=True)
class HorizonEligibility:
    frame: pd.DataFrame
    audit: dict[str, Any]


def enforce_strict_cutoffs(shadows: pd.DataFrame) -> HorizonEligibility:
    if shadows.empty:
        return HorizonEligibility(
            shadows.copy(),
            {
                "input_rows": 0,
                "eligible_rows": 0,
                "excluded_missing_timing_rows": 0,
                "excluded_too_early_rows": 0,
                "excluded_post_cutoff_rows": 0,
                "strict_cutoff": True,
            },
        )

    if "market_timing_error_minutes" not in shadows.columns:
        # A forecast without timing provenance cannot support an exact T-minus claim.
        return HorizonEligibility(
            shadows.iloc[0:0].copy(),
            {
                "input_rows": int(len(shadows)),
                "eligible_rows": 0,
                "excluded_missing_timing_rows": int(len(shadows)),
                "excluded_too_early_rows": 0,
                "excluded_post_cutoff_rows": 0,
                "strict_cutoff": True,
                "reason": "missing_market_timing_error_minutes_fail_closed",
            },
        )

    work = shadows.copy()
    timing = pd.to_numeric(work["market_timing_error_minutes"], errors="coerce")
    missing = timing.isna()
    too_early = timing.lt(-MAX_EARLY_MINUTES)
    post_cutoff = timing.gt(0.0)
    eligible = ~(missing | too_early | post_cutoff)

    filtered = work.loc[eligible].copy()
    audit = {
        "input_rows": int(len(work)),
        "eligible_rows": int(len(filtered)),
        "excluded_missing_timing_rows": int(missing.sum()),
        "excluded_too_early_rows": int(too_early.sum()),
        "excluded_post_cutoff_rows": int(post_cutoff.sum()),
        "minimum_timing_error_minutes": -MAX_EARLY_MINUTES,
        "maximum_timing_error_minutes": 0.0,
        "strict_cutoff": True,
        "rule": "nominal T-minus forecasts may use only qualified observations no later than the cutoff",
    }
    return HorizonEligibility(filtered, audit)


def horizon_completeness_audit(shadows: pd.DataFrame) -> dict[str, Any]:
    """Describe capture completeness without imputing a missing horizon.

    This audit is deliberately descriptive. It helps detect selective complete-case
    samples; it never manufactures an earlier probability from later information.
    """
    if shadows.empty or not {"game_id", "horizon"}.issubset(shadows.columns):
        return {
            "games_with_any_eligible_horizon": 0,
            "games_with_all_four_eligible_horizons": 0,
            "horizon_presence_rate": {h: None for h in PRIMARY_HORIZONS},
            "presence_patterns": {},
        }

    # Candidate rows share the same market snapshot identity. Collapse to one row per
    # game/horizon so F-ST plus market does not double-count capture completeness.
    pairs = shadows[["game_id", "horizon"]].copy()
    pairs["game_id"] = pairs["game_id"].astype(str)
    pairs["horizon"] = pairs["horizon"].astype(str)
    pairs = pairs[pairs["horizon"].isin(PRIMARY_HORIZONS)].drop_duplicates()
    if pairs.empty:
        return {
            "games_with_any_eligible_horizon": 0,
            "games_with_all_four_eligible_horizons": 0,
            "horizon_presence_rate": {h: None for h in PRIMARY_HORIZONS},
            "presence_patterns": {},
        }

    by_game = pairs.groupby("game_id")["horizon"].agg(lambda s: set(s))
    denominator = int(len(by_game))
    pattern_counts: dict[str, int] = {}
    all_four = 0
    for horizons in by_game:
        pattern = "".join("1" if h in horizons else "0" for h in PRIMARY_HORIZONS)
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        if all(h in horizons for h in PRIMARY_HORIZONS):
            all_four += 1

    presence = {
        h: float(sum(h in values for values in by_game) / denominator)
        for h in PRIMARY_HORIZONS
    }
    return {
        "games_with_any_eligible_horizon": denominator,
        "games_with_all_four_eligible_horizons": int(all_four),
        "all_four_share_among_games_with_any": float(all_four / denominator),
        "horizon_presence_rate": presence,
        "presence_pattern_order": list(PRIMARY_HORIZONS),
        "presence_patterns": dict(sorted(pattern_counts.items())),
        "interpretation": (
            "Descriptive selection audit only. The canonical timing analysis still uses "
            "the all-four complete-case intersection and never imputes missing horizons."
        ),
    }

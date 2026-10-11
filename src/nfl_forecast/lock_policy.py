from __future__ import annotations

"""Versioned immutable official-lock policy.

The target change is PROSPECTIVE: season 2026 weeks 1–5 (and prior seasons)
remain T-120; season 2026 week 6 onward is T-60. Historical receipts,
their actual timestamps, and their original evaluation targets never change.
This module does not score, rewrite, or create predictions.
"""

import re
from typing import Mapping, Any

LEGACY_TARGET_MINUTES = 120.0
CURRENT_TARGET_MINUTES = 60.0
EFFECTIVE_SEASON = 2026
EFFECTIVE_WEEK = 6
GAME_ID_RE = re.compile(r"^(\d{4})_(\d{2})_[A-Z0-9]+_[A-Z0-9]+$")


def official_lock_target_minutes(row: Mapping[str, Any]) -> float:
    season, week = row.get("season"), row.get("week")
    if season is None or week is None or str(season).strip() == "" or str(week).strip() == "":
        match = GAME_ID_RE.fullmatch(str(row.get("game_id") or ""))
        if match:
            season, week = match.group(1), match.group(2)
        else:
            # Legacy analytical fixtures without season/week remain T-120.
            return LEGACY_TARGET_MINUTES
    try:
        identity = (int(float(season)), int(float(week)))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"invalid official lock season/week: {season!r}/{week!r}") from exc
    if not 1 <= identity[1] <= 22:
        raise ValueError(f"invalid official lock week: {identity[1]}")
    return CURRENT_TARGET_MINUTES if identity >= (EFFECTIVE_SEASON, EFFECTIVE_WEEK) else LEGACY_TARGET_MINUTES

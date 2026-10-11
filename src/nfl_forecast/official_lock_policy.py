from __future__ import annotations

"""Prospective official-lock policy; historical T-120 receipts remain untouched.

Week 6 of the 2026 NFL regular season is the first T-60 official cohort.
Research T-120 captures and frozen F-ST forecast coefficients are not changed.
This controls only how soon a new official lock is eligible and how that lock
is audited. Earlier rows must always be evaluated against their original T-120
target, even when the report is generated after the policy change.
"""

from typing import Any, Mapping
import re

ORIGINAL_LEAD_MINUTES = 120.0
NEW_LEAD_MINUTES = 60.0
EFFECTIVE_SEASON = 2026
EFFECTIVE_WEEK = 6
_ID = re.compile(r"^(\d{4})_(\d{2})_")


def official_lock_lead_minutes(game: Mapping[str, Any]) -> float:
    """Return immutable policy for a matchup, never inferred from lock timing."""
    raw_season = game.get("season")
    raw_week = game.get("week")
    try:
        season = int(str(raw_season).strip())
        week = int(str(raw_week).strip())
    except (ValueError, TypeError):
        match = _ID.match(str(game.get("game_id") or ""))
        if not match:
            raise ValueError("Missing season/week and invalid canonical game_id for official lock policy")
        season, week = int(match.group(1)), int(match.group(2))
    canonical = _ID.match(str(game.get("game_id") or ""))
    if canonical and (season, week) != (int(canonical.group(1)), int(canonical.group(2))):
        raise ValueError("Official lock season/week contradicts canonical game_id")
    if season < 2000 or not 1 <= week <= 22:
        raise ValueError(f"Invalid official lock season/week: {season}/{week}")
    return NEW_LEAD_MINUTES if (season, week) >= (EFFECTIVE_SEASON, EFFECTIVE_WEEK) else ORIGINAL_LEAD_MINUTES

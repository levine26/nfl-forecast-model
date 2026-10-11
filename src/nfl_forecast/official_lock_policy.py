from __future__ import annotations

"""Versioned production lock timing policy; never alters existing receipts.

2026 Weeks 1–5 retain their historic T−120 contract. Games scheduled on or
after 2026-10-15 (Week 6's first game) use T−60. The model, picks, grading,
and immutable receipt timestamps remain unchanged by this policy helper.
"""

from datetime import date

LEGACY_LOCK_LEAD_MINUTES = 120.0
NEW_LOCK_LEAD_MINUTES = 60.0
T60_EFFECTIVE_GAMEDAY = date(2026, 10, 15)


def official_lock_target_minutes(gameday: object) -> float:
    """Return the target for a game, rejecting malformed schedule dates."""
    try:
        scheduled_day = date.fromisoformat(str(gameday or "")[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid game date for official lock policy: {gameday!r}") from exc
    return (NEW_LOCK_LEAD_MINUTES if scheduled_day >= T60_EFFECTIVE_GAMEDAY
            else LEGACY_LOCK_LEAD_MINUTES)


def official_lock_policy_name(gameday: object) -> str:
    return "T-60-WEEK6-2026" if official_lock_target_minutes(gameday) == NEW_LOCK_LEAD_MINUTES else "T-120-LEGACY"

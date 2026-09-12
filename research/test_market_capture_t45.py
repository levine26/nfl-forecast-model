from __future__ import annotations

from datetime import datetime, timezone

from research.market_capture_due_v2 import HORIZONS as DUE_HORIZONS
from research.market_capture_v2 import HORIZONS, due_horizons, horizon_target


def test_t45_is_preregistered_in_both_capture_paths() -> None:
    assert HORIZONS["T-45m"] == 45
    assert DUE_HORIZONS["T-45m"] == 45


def test_t45_target_and_due_window() -> None:
    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    target = datetime(2026, 9, 13, 16, 15, tzinfo=timezone.utc)
    assert horizon_target(kickoff, "T-45m") == target
    due = due_horizons(kickoff, target)
    assert [row["horizon"] for row in due] == ["T-45m"]

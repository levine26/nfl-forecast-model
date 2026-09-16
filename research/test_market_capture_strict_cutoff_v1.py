from __future__ import annotations

from datetime import datetime, timedelta, timezone

from research.market_capture_v2 import CAPTURE_TOLERANCE_MINUTES, due_horizons


def test_capture_window_is_pre_cutoff_only() -> None:
    kickoff = datetime(2026, 9, 18, 0, 15, tzinfo=timezone.utc)
    target = kickoff - timedelta(minutes=120)

    assert [row["horizon"] for row in due_horizons(kickoff, target)] == ["T-120m"]
    assert [row["horizon"] for row in due_horizons(
        kickoff, target - timedelta(minutes=CAPTURE_TOLERANCE_MINUTES)
    )] == ["T-120m"]

    assert due_horizons(kickoff, target + timedelta(seconds=1)) == []
    assert due_horizons(
        kickoff, target - timedelta(minutes=CAPTURE_TOLERANCE_MINUTES, seconds=1)
    ) == []


def test_manual_dispatch_cannot_turn_later_information_into_nominal_horizon() -> None:
    kickoff = datetime(2026, 9, 18, 0, 15, tzinfo=timezone.utc)
    target = kickoff - timedelta(minutes=45)
    for seconds_late in (1, 60, 7 * 60 + 29):
        due = due_horizons(kickoff, target + timedelta(seconds=seconds_late))
        assert not any(row["horizon"] == "T-45m" for row in due)

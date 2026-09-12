from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from research.market_capture_due_v2 import HORIZONS as DUE_HORIZONS
from research.market_capture_due_v2 import due_rows
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


def test_schedule_gate_never_opens_after_nominal_t45_cutoff(tmp_path: Path) -> None:
    feed = tmp_path / "slate.csv"
    feed.write_text(
        "game_id,gameday,gametime\n"
        "2026_01_A_B,2026-09-13,13:00\n",
        encoding="utf-8",
    )
    before = datetime(2026, 9, 13, 16, 10, tzinfo=timezone.utc)
    exact = datetime(2026, 9, 13, 16, 15, tzinfo=timezone.utc)
    after = datetime(2026, 9, 13, 16, 15, 1, tzinfo=timezone.utc)

    assert ("2026_01_A_B", "T-45m", -5.0) in due_rows(feed, before)
    assert ("2026_01_A_B", "T-45m", 0.0) in due_rows(feed, exact)
    assert not any(horizon == "T-45m" for _, horizon, _ in due_rows(feed, after))

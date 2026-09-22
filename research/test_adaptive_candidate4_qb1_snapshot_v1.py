from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from research.adaptive_candidate4_qb1_snapshot_v1 import (
    append_immutable_snapshots,
    build_t120_qb1_snapshots,
    due_t120_games,
)


def _feed() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_LAC_BUF",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "gametime": "13:00",
            "away_team": "LAC",
            "home_team": "BUF",
        }
    ])


def _depth() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "dt": "2026-09-27T14:00:00Z",
            "team": "BUF",
            "player_name": "Josh Allen",
            "gsis_id": "00-0034857",
            "pos_abb": "QB",
            "pos_rank": 1,
        },
        {
            "dt": "2026-09-27T14:00:00Z",
            "team": "LAC",
            "player_name": "Justin Herbert",
            "gsis_id": "00-0036355",
            "pos_abb": "QB",
            "pos_rank": 1,
        },
    ])


def test_due_t120_resolves_kickoff_from_gameday_and_gametime() -> None:
    due = due_t120_games(
        _feed(),
        now_utc=datetime(2026, 9, 27, 14, 59, tzinfo=timezone.utc),
    )
    assert len(due) == 1
    row = due[0]
    assert row["kickoff_utc"] == "2026-09-27T17:00:00Z"
    assert row["t120_target_utc"] == "2026-09-27T15:00:00Z"
    assert row["capture_timing_error_minutes"] == pytest.approx(-1.0)


def test_due_t120_never_opens_after_cutoff() -> None:
    due = due_t120_games(
        _feed(),
        now_utc=datetime(2026, 9, 27, 15, 0, 1, tzinfo=timezone.utc),
    )
    assert due == []


def test_snapshot_freezes_bilateral_qb1_and_is_immutable() -> None:
    games = due_t120_games(
        _feed(),
        now_utc=datetime(2026, 9, 27, 14, 59, tzinfo=timezone.utc),
    )
    first = build_t120_qb1_snapshots(
        _depth(),
        games,
        captured_at_utc=datetime(2026, 9, 27, 14, 59, tzinfo=timezone.utc),
        nflreadpy_version="0.1.5",
    )
    row = first.iloc[0]
    assert bool(row["qb1_snapshot_complete"]) is True
    assert row["home_t120_qb1_player_name"] == "Josh Allen"
    assert row["away_t120_qb1_player_name"] == "Justin Herbert"
    assert row["captured_at_utc"] == "2026-09-27T14:59:00Z"
    assert row["completed_2026_outcomes_used"] == 0
    assert bool(row["production_authorized"]) is False

    combined = append_immutable_snapshots(first, first.copy())
    assert len(combined) == 1

    changed = first.copy()
    changed.loc[0, "home_t120_qb1_player_name"] = "Different QB"
    changed.loc[0, "qb1_snapshot_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="rewrite attempted"):
        append_immutable_snapshots(first, changed)


def test_snapshot_rejects_source_state_not_observed_by_capture() -> None:
    depth = _depth()
    depth.loc[depth["team"].eq("BUF"), "dt"] = "2026-09-27T14:59:30Z"
    games = due_t120_games(
        _feed(),
        now_utc=datetime(2026, 9, 27, 14, 59, tzinfo=timezone.utc),
    )
    out = build_t120_qb1_snapshots(
        depth,
        games,
        captured_at_utc=datetime(2026, 9, 27, 14, 59, tzinfo=timezone.utc),
        nflreadpy_version="0.1.5",
    )
    row = out.iloc[0]
    assert bool(row["qb1_snapshot_complete"]) is False
    assert "home_depth_state_not_observed_by_capture" in row["incomplete_reasons"]

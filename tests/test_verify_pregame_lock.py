from datetime import datetime, timezone

import pandas as pd
import pytest

from scripts.verify_pregame_lock import verify_pregame_locks


NOW = datetime(2026, 9, 9, 22, 25, tzinfo=timezone.utc)  # 115 min before 00:20 UTC kickoff


def current_feed():
    return pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "gameday": "2026-09-09",
        "gametime": "20:20",
        "final_home_prob": .61,
        "pick": "SEA",
    }])


def locked_history(lock_time="2026-09-09T22:25:00+00:00"):
    return pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "lock_status": "LOCKED",
        "lock_timestamp_utc": lock_time,
        "final_home_prob": .61,
        "pick": "SEA",
    }])


def test_requires_lock_inside_t120():
    with pytest.raises(RuntimeError, match="no official history"):
        verify_pregame_locks(current_feed(), pd.DataFrame(), NOW)


def test_accepts_one_coherent_lock_inside_t120():
    assert verify_pregame_locks(current_feed(), locked_history(), NOW) == ["2026_01_NE_SEA"]


def test_does_not_require_lock_before_t120():
    early = datetime(2026, 9, 9, 22, 19, tzinfo=timezone.utc)  # 121 min before kickoff
    assert verify_pregame_locks(current_feed(), pd.DataFrame(), early) == []


def test_rejects_duplicate_official_rows():
    duplicated = pd.concat([locked_history(), locked_history()], ignore_index=True)
    with pytest.raises(RuntimeError, match="duplicate official game ids"):
        verify_pregame_locks(current_feed(), duplicated, NOW)


def test_rejects_lock_timestamp_outside_window():
    with pytest.raises(RuntimeError, match="outside T-120"):
        verify_pregame_locks(current_feed(), locked_history("2026-09-09T22:19:00+00:00"), NOW)

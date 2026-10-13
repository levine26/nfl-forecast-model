from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.check_week_rollover import requires_rollover
from scripts.refresh_market import _set_market_snapshot_provenance


def _current(week=5):
    return pd.DataFrame({"season": [2026], "week": [week], "game_id": [f"2026_{week:02d}_A_B"]})


def _schedule(week5_home=37, week5_away=34):
    return pd.DataFrame([
        {"season": 2026, "week": 5, "game_type": "REG",
         "game_id": "2026_05_A_B", "home_score": week5_home, "away_score": week5_away},
        {"season": 2026, "week": 6, "game_type": "REG",
         "game_id": "2026_06_B_A", "home_score": np.nan, "away_score": np.nan},
    ])


def test_completed_week_5_dispatches_week_6_full_rebuild():
    assert requires_rollover(_current(5), _schedule())
    assert not requires_rollover(_current(6), _schedule())


def test_unreported_monday_final_must_not_be_invented():
    assert not requires_rollover(_current(5), _schedule(week5_home=np.nan, week5_away=np.nan))


def test_completed_tie_does_not_block_new_week():
    assert requires_rollover(_current(5), _schedule(week5_home=27, week5_away=27))


def test_race_or_invalid_mixed_slate_fails_closed():
    mixed = pd.concat([_current(5), _current(6)], ignore_index=True)
    with pytest.raises(ValueError, match="exactly one"):
        requires_rollover(mixed, _schedule())


def test_pandas_3_all_null_market_provenance_accepts_iso_timestamp():
    # CSV inferred columns are float64 when all rows are blank.
    frame = pd.DataFrame({
        "market_snapshot_timestamp_utc": [np.nan, np.nan],
        "market_snapshot_source": [np.nan, np.nan],
    })
    assert frame["market_snapshot_timestamp_utc"].dtype == "float64"
    observed = pd.Series([True, False], index=frame.index)
    timestamp = "2026-10-13T17:00:00+00:00"
    _set_market_snapshot_provenance(frame, observed, timestamp)
    assert frame.loc[0, "market_snapshot_timestamp_utc"] == timestamp
    assert frame.loc[0, "market_snapshot_source"] == "nflverse_games.csv_moneyline"
    assert pd.isna(frame.loc[1, "market_snapshot_timestamp_utc"])
    assert pd.isna(frame.loc[1, "market_snapshot_source"])


def test_market_refresh_preserves_prior_real_provenance_when_feed_is_missing():
    frame = pd.DataFrame({
        "market_snapshot_timestamp_utc": ["2026-10-12T14:00:00+00:00", np.nan],
        "market_snapshot_source": ["prior_feed", np.nan],
    })
    _set_market_snapshot_provenance(
        frame, pd.Series([False, True]), "2026-10-13T17:00:00+00:00"
    )
    assert frame.loc[0, "market_snapshot_source"] == "prior_feed"
    assert frame.loc[0, "market_snapshot_timestamp_utc"] == "2026-10-12T14:00:00+00:00"
    assert frame.loc[1, "market_snapshot_source"] == "nflverse_games.csv_moneyline"

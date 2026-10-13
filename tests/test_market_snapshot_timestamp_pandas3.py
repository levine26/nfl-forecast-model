"""Regression for pandas 3 rejection of text assignments to float64 CSV columns."""

from io import StringIO

import pandas as pd

from scripts.refresh_market import _stamp_market_observation


def test_blank_csv_market_metadata_can_be_timestamped():
    csv = "game_id,market_snapshot_timestamp_utc,market_snapshot_source\ng1,,\ng2,,\n"
    predictions = pd.read_csv(StringIO(csv))
    assert predictions["market_snapshot_timestamp_utc"].dtype.kind == "f"
    assert predictions["market_snapshot_source"].dtype.kind == "f"

    mask = pd.Series([True, False], index=predictions.index)
    timestamp = "2026-10-13T17:00:00+00:00"
    _stamp_market_observation(predictions, mask, timestamp)

    assert predictions.loc[0, "market_snapshot_timestamp_utc"] == timestamp
    assert predictions.loc[0, "market_snapshot_source"] == "nflverse_games.csv_moneyline"
    assert pd.isna(predictions.loc[1, "market_snapshot_timestamp_utc"])
    assert pd.isna(predictions.loc[1, "market_snapshot_source"])


def test_unobserved_previous_metadata_is_not_advanced():
    predictions = pd.DataFrame({
        "game_id": ["g1", "g2"],
        "market_snapshot_timestamp_utc": ["2026-10-12T23:00:00+00:00"] * 2,
        "market_snapshot_source": ["earlier_market_source"] * 2,
    })
    _stamp_market_observation(
        predictions,
        pd.Series([True, False], index=predictions.index),
        "2026-10-13T17:00:00+00:00",
    )
    assert predictions.loc[0, "market_snapshot_timestamp_utc"] == "2026-10-13T17:00:00+00:00"
    assert predictions.loc[1, "market_snapshot_timestamp_utc"] == "2026-10-12T23:00:00+00:00"
    assert predictions.loc[1, "market_snapshot_source"] == "earlier_market_source"


def test_missing_metadata_columns_are_added_as_strings():
    predictions = pd.DataFrame({"game_id": ["g1"]})
    _stamp_market_observation(
        predictions,
        pd.Series([True], index=predictions.index),
        "2026-10-13T17:00:00+00:00",
    )
    assert predictions.loc[0, "market_snapshot_timestamp_utc"] == "2026-10-13T17:00:00+00:00"
    assert predictions.loc[0, "market_snapshot_source"] == "nflverse_games.csv_moneyline"

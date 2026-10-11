"""Regression: persisted CSV Boolean strings must not inflate production health counters."""

from datetime import datetime, timezone
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.publish import _status_boolean_series, write_outputs


def test_mixed_csv_strings_and_native_boolean_values():
    frame = pd.DataFrame({
        "fst_fallback": ["False", False, " true ", True, "0", 0, None, np.nan],
        "market_available": ["True", True, "false", False, "1", 1, "", None],
    })
    assert _status_boolean_series(frame, "fst_fallback").tolist() == [
        False, False, True, True, False, False, False, False
    ]
    assert _status_boolean_series(frame, "market_available").tolist() == [
        True, True, False, False, True, True, False, False
    ]


def test_invalid_flag_is_rejected_instead_of_misreported():
    frame = pd.DataFrame({"fst_fallback": ["MAYBE"]})
    with pytest.raises(ValueError, match="fst_fallback"):
        _status_boolean_series(frame, "fst_fallback")


def test_publisher_status_does_not_count_false_string_as_fst_fallback(tmp_path):
    predictions = pd.DataFrame([{
        "game_id": "2026_06_CHI_GB", "season": 2026, "week": 6,
        "gameday": "2026-10-18", "gametime": "13:00",
        "home_team": "GB", "away_team": "CHI",
        "final_home_prob": 0.63, "pick": "GB",
        "market_home_prob": 0.61, "market_available": "True",
        "fst_fallback": "False",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "model_version": "0.9.0-fst",
        "snapshot_type": "EARLY",
        "prediction_timestamp_utc": "2026-10-18T15:00:00+00:00",
    }])
    games = pd.DataFrame([{"game_id": "2026_06_CHI_GB",
                           "home_team": "GB", "away_team": "CHI"}])
    write_outputs(
        SimpleNamespace(predictions=predictions, games=games),
        output_dir=tmp_path,
        now_utc=datetime(2026, 10, 18, 15, 30, tzinfo=timezone.utc),
    )
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["fst_fallback_count"] == 0
    assert status["market_available_games"] == 1
    assert status["market_missing_or_invalid_games"] == 0
    assert status["final_probability_strategy"] == "F-ST-01-FROZEN-2026"

from __future__ import annotations

import pandas as pd

from nfl_forecast.challenger_shadow import normalize_history


def test_normalize_history_preserves_boolean_grade_compatibility():
    history = pd.DataFrame(
        {
            "game_id": ["2026_01_AWAY_HOME"],
            "winner_correct": [float("nan")],
        }
    )

    normalized = normalize_history(history)

    assert normalized["winner_correct"].dtype == object
    assert pd.isna(normalized.at[0, "winner_correct"])
    normalized.at[0, "winner_correct"] = False
    assert normalized.at[0, "winner_correct"] is False

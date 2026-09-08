import pandas as pd
from nfl_forecast.features import add_pregame_rolling


def test_rolling_features_are_shifted():
    df = pd.DataFrame({
        "team": ["A","A","A"], "season": [2026]*3, "week": [1,2,3],
        "gameday": ["2026-09-01","2026-09-08","2026-09-15"],
        "off_epa": [1.0, 2.0, 100.0],
    })
    out = add_pregame_rolling(df, windows=(3,), alpha=0.5)
    assert out.loc[2, "off_epa_l3"] == 1.5
    assert out.loc[2, "off_epa_ewma"] < 10

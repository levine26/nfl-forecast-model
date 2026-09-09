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


def test_rolling_features_stay_with_the_correct_team_after_sorting():
    # Deliberately interleave teams and use non-monotonic index labels. The
    # calculation must be invariant to input order and must never attach one
    # team's rolling state to another team's row.
    df = pd.DataFrame({
        "team": ["B", "A", "B", "A", "B", "A"],
        "season": [2026] * 6,
        "week": [3, 1, 1, 3, 2, 2],
        "gameday": [
            "2026-09-15", "2026-09-01", "2026-09-01",
            "2026-09-15", "2026-09-08", "2026-09-08",
        ],
        "off_epa": [30.0, 1.0, 10.0, 3.0, 20.0, 2.0],
    }, index=[90, 11, 70, 13, 80, 12])

    out = add_pregame_rolling(df, windows=(3,), alpha=0.5)
    a3 = out[(out.team == "A") & (out.week == 3)].iloc[0]
    b3 = out[(out.team == "B") & (out.week == 3)].iloc[0]

    assert a3.off_epa_l3 == 1.5
    assert b3.off_epa_l3 == 15.0
    assert a3.off_epa_ewma == 1.5
    assert b3.off_epa_ewma == 15.0

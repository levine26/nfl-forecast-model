import pandas as pd

from nfl_forecast.publish import _current_week_publication_rows


def test_current_week_publication_retains_locked_completed_games():
    columns = [
        "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
        "final_home_prob", "pick", "model_version", "prediction_timestamp_utc",
    ]
    live = pd.DataFrame([{
        "game_id": "2026_04_ATL_NO", "season": 2026, "week": 4,
        "gameday": "2026-10-05", "gametime": "20:15", "away_team": "ATL", "home_team": "NO",
        "final_home_prob": 0.52, "pick": "NO", "model_version": "test",
        "prediction_timestamp_utc": "2026-10-05T22:47:00+00:00",
    }])
    official = pd.DataFrame([{
        "game_id": "2026_04_IND_WAS", "season": 2026, "week": 4,
        "gameday": "2026-10-04", "gametime": "13:00", "away_team": "IND", "home_team": "WAS",
        "final_home_prob": 0.61, "pick": "WAS", "model_version": "test",
        "prediction_timestamp_utc": "2026-10-04T14:55:00+00:00", "lock_status": "LOCKED",
    }])

    published = _current_week_publication_rows(live, official, columns)

    assert published["game_id"].tolist() == ["2026_04_IND_WAS", "2026_04_ATL_NO"]
    assert published.loc[published.game_id.eq("2026_04_IND_WAS"), "final_home_prob"].iloc[0] == 0.61


def test_current_week_publication_immutable_lock_overrides_newer_live_row():
    columns = ["game_id", "season", "week", "gameday", "gametime", "final_home_prob", "pick"]
    live = pd.DataFrame([{
        "game_id": "2026_04_ATL_NO", "season": 2026, "week": 4, "gameday": "2026-10-05",
        "gametime": "20:15", "final_home_prob": 0.70, "pick": "NO",
    }])
    official = pd.DataFrame([{
        "game_id": "2026_04_ATL_NO", "season": 2026, "week": 4, "gameday": "2026-10-05",
        "gametime": "20:15", "final_home_prob": 0.58, "pick": "NO", "lock_status": "LOCKED",
    }])

    published = _current_week_publication_rows(live, official, columns)

    assert len(published) == 1
    assert published.loc[0, "final_home_prob"] == 0.58

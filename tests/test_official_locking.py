from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pandas as pd

from nfl_forecast.publish import write_outputs


def _prediction(prob=0.70):
    return pd.DataFrame([{
        "game_id":"2026_01_A_B","season":2026,"week":1,"gameday":"2026-09-09","gametime":"20:20",
        "away_team":"A","home_team":"B","pure_home_prob":0.72,"market_home_prob":0.62,
        "final_home_prob":prob,"pick":"B","expected_margin":5.0,"expected_total":45.0,
        "spread_line":3.0,"total_line":44.0,"confidence":"High","model_disagreement":0.03,
        "snapshot_type":"FINAL","model_version":"test","prediction_timestamp_utc":"2026-09-09T22:55:00+00:00",
    }])


def test_official_prediction_waits_until_lock_window(tmp_path):
    # 20:20 ET in September = 00:20 UTC the next day. At T-121, no official
    # prediction may exist; the first valid refresh inside T-120 becomes official.
    games = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":None,"away_score":None}])
    too_early = datetime(2026, 9, 9, 22, 19, tzinfo=timezone.utc)
    write_outputs(SimpleNamespace(predictions=_prediction(0.68), games=games), tmp_path, now_utc=too_early, enforce_read_sync=False)
    before = pd.read_csv(tmp_path / "prediction_history.csv")
    assert before.empty

    inside = datetime(2026, 9, 9, 22, 21, tzinfo=timezone.utc)
    write_outputs(SimpleNamespace(predictions=_prediction(0.70), games=games), tmp_path, now_utc=inside, enforce_read_sync=False)
    locked = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(locked) == 1
    assert locked.loc[0, "lock_status"] == "LOCKED"
    assert locked.loc[0, "final_home_prob"] == 0.70
    assert 118.9 < locked.loc[0, "minutes_to_kickoff_at_lock"] < 119.1


def test_official_prediction_locks_once_and_is_immutable(tmp_path):
    # 20:20 ET = 00:20 UTC next day; this run is 80 minutes before kickoff.
    now = datetime(2026, 9, 9, 23, 0, tzinfo=timezone.utc)
    games = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":None,"away_score":None}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.70), games=games), tmp_path, now_utc=now, enforce_read_sync=False)
    first = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(first) == 1
    assert first.loc[0, "lock_status"] == "LOCKED"
    assert first.loc[0, "final_home_prob"] == 0.70

    # A later live refresh changes the model, but the official locked probability cannot change.
    later = datetime(2026, 9, 9, 23, 30, tzinfo=timezone.utc)
    write_outputs(SimpleNamespace(predictions=_prediction(0.82), games=games), tmp_path, now_utc=later, enforce_read_sync=False)
    second = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(second) == 1
    assert second.loc[0, "final_home_prob"] == 0.70


def test_locked_prediction_can_be_graded_without_mutating_forecast(tmp_path):
    now = datetime(2026, 9, 9, 23, 0, tzinfo=timezone.utc)
    games = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":None,"away_score":None}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.70), games=games), tmp_path, now_utc=now, enforce_read_sync=False)
    finished = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":27,"away_score":20}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.55), games=finished), tmp_path, now_utc=datetime(2026,9,10,2,0,tzinfo=timezone.utc), enforce_read_sync=False)
    hist = pd.read_csv(tmp_path / "prediction_history.csv")
    assert hist.loc[0, "final_home_prob"] == 0.70
    assert bool(hist.loc[0, "winner_correct"]) is True
    assert hist.loc[0, "actual_margin"] == 7.0

def test_week6_publisher_does_not_lock_before_t60(tmp_path):
    kickoff = datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc)
    predictions = _prediction()
    predictions.loc[0, "game_id"] = "2026_06_A_B"
    predictions.loc[0, "week"] = 6
    predictions.loc[0, "gameday"] = "2026-10-18"
    predictions.loc[0, "gametime"] = "13:00"
    games = pd.DataFrame([{"game_id": "2026_06_A_B",
                           "home_team": "B", "away_team": "A",
                           "home_score": None, "away_score": None}])
    write_outputs(SimpleNamespace(predictions=predictions, games=games), tmp_path,
                  now_utc=kickoff-timedelta(minutes=61), enforce_read_sync=False)
    assert pd.read_csv(tmp_path / "prediction_history.csv").empty
    write_outputs(SimpleNamespace(predictions=predictions, games=games), tmp_path,
                  now_utc=kickoff-timedelta(minutes=59), enforce_read_sync=False)
    locked = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(locked) == 1
    assert float(locked.loc[0, "minutes_to_kickoff_at_lock"]) == 59

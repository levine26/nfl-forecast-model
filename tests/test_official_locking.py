from datetime import datetime, timezone
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


def test_official_prediction_locks_once_and_is_immutable(tmp_path):
    # 20:20 ET = 00:20 UTC next day; this run is 80 minutes before kickoff.
    now = datetime(2026, 9, 9, 23, 0, tzinfo=timezone.utc)
    games = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":None,"away_score":None}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.70), games=games), tmp_path, now_utc=now)
    first = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(first) == 1
    assert first.loc[0, "lock_status"] == "LOCKED"
    assert first.loc[0, "final_home_prob"] == 0.70

    # A later live refresh changes the model, but the official locked probability cannot change.
    later = datetime(2026, 9, 9, 23, 30, tzinfo=timezone.utc)
    write_outputs(SimpleNamespace(predictions=_prediction(0.82), games=games), tmp_path, now_utc=later)
    second = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(second) == 1
    assert second.loc[0, "final_home_prob"] == 0.70


def test_locked_prediction_can_be_graded_without_mutating_forecast(tmp_path):
    now = datetime(2026, 9, 9, 23, 0, tzinfo=timezone.utc)
    games = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":None,"away_score":None}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.70), games=games), tmp_path, now_utc=now)
    finished = pd.DataFrame([{"game_id":"2026_01_A_B","home_team":"B","away_team":"A","home_score":27,"away_score":20}])
    write_outputs(SimpleNamespace(predictions=_prediction(0.55), games=finished), tmp_path, now_utc=datetime(2026,9,10,2,0,tzinfo=timezone.utc))
    hist = pd.read_csv(tmp_path / "prediction_history.csv")
    assert hist.loc[0, "final_home_prob"] == 0.70
    assert bool(hist.loc[0, "winner_correct"]) is True
    assert hist.loc[0, "actual_margin"] == 7.0

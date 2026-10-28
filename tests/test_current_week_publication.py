import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from nfl_forecast.publish import _current_week_publication_rows, _schedule_coverage_for_published_week, write_outputs


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


def test_schedule_coverage_detects_completed_game_without_official_receipt():
    published = pd.DataFrame([
        {"game_id": "2026_07_NE_CHI", "season": 2026, "week": 7},
        {"game_id": "2026_07_DAL_PHI", "season": 2026, "week": 7},
    ])
    schedule = pd.DataFrame([
        {"game_id": "2026_07_NE_CHI", "season": 2026, "week": 7},
        {"game_id": "2026_07_PIT_NO", "season": 2026, "week": 7},
        {"game_id": "2026_07_DAL_PHI", "season": 2026, "week": 7},
        {"game_id": "2026_08_CLE_BAL", "season": 2026, "week": 8},
    ])
    assert _schedule_coverage_for_published_week(published, schedule) == (
        3, ["2026_07_PIT_NO"]
    )
    assert _schedule_coverage_for_published_week(schedule[schedule["week"].eq(7)], schedule) == (3, [])


def test_missing_game_degrades_status_without_creating_official_receipt(tmp_path):
    predictions = pd.DataFrame([{
        "game_id": "2026_07_DAL_PHI", "season": 2026, "week": 7,
        "gameday": "2026-10-26", "gametime": "20:15",
        "home_team": "PHI", "away_team": "DAL",
        "final_home_prob": 0.4, "pick": "DAL",
        "market_home_prob": 0.42, "market_available": True,
        "fst_fallback": False,
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "model_version": "0.9.0-fst", "snapshot_type": "MARKET",
        "prediction_timestamp_utc": "2026-10-26T14:00:00+00:00",
    }])
    games = pd.DataFrame([
        {"game_id": "2026_07_DAL_PHI", "season": 2026, "week": 7,
         "home_team": "PHI", "away_team": "DAL"},
        {"game_id": "2026_07_PIT_NO", "season": 2026, "week": 7,
         "home_team": "NO", "away_team": "PIT"},
    ])
    write_outputs(
        SimpleNamespace(predictions=predictions, games=games),
        output_dir=tmp_path,
        now_utc=datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc),
    )
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["status"] == "degraded"
    assert status["games"] == 1
    assert status["expected_week_games"] == 2
    assert status["missing_week_game_ids"] == ["2026_07_PIT_NO"]
    assert status["slate_completeness_verified"] is True
    assert status["locked_official_predictions"] == 0
    assert "2026_07_PIT_NO" not in (tmp_path / "this_week.csv").read_text()



def test_complete_slate_requires_timestamped_market_provenance_for_healthy_status(tmp_path):
    predictions = pd.DataFrame([{
        "game_id": "2026_08_CAR_GB", "season": 2026, "week": 8,
        "gameday": "2026-10-29", "gametime": "20:15",
        "home_team": "GB", "away_team": "CAR",
        "final_home_prob": 0.61, "pick": "GB",
        "market_home_prob": 0.62, "market_available": True,
        "fst_fallback": False,
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "model_version": "0.9.0-fst", "snapshot_type": "MARKET",
        "prediction_timestamp_utc": "2026-10-27T15:30:00+00:00",
    }])
    games = predictions[["game_id", "season", "week", "home_team", "away_team"]].copy()
    now = datetime(2026, 10, 27, 15, 30, tzinfo=timezone.utc)
    write_outputs(
        SimpleNamespace(predictions=predictions, games=games),
        output_dir=tmp_path / "unknown", now_utc=now,
    )
    missing = json.loads((tmp_path / "unknown" / "status.json").read_text())
    assert missing["games"] == missing["expected_week_games"] == 1
    assert missing["slate_completeness_verified"] is True
    assert missing["market_available_games"] == 1
    assert missing["market_provenance_missing_games"] == 1
    assert missing["status"] == "degraded"

    predictions["market_snapshot_timestamp_utc"] = "2026-10-27T15:20:00+00:00"
    predictions["market_snapshot_source"] = "nflverse_games.csv_moneyline"
    predictions["market_freshness_status"] = "refreshed_this_run"
    write_outputs(
        SimpleNamespace(predictions=predictions, games=games),
        output_dir=tmp_path / "fresh", now_utc=now,
    )
    fresh = json.loads((tmp_path / "fresh" / "status.json").read_text())
    assert fresh["market_provenance_missing_games"] == 0
    assert fresh["status"] == "healthy"

    predictions["market_snapshot_timestamp_utc"] = "not-a-timestamp"
    write_outputs(
        SimpleNamespace(predictions=predictions, games=games),
        output_dir=tmp_path / "invalid", now_utc=now,
    )
    invalid = json.loads((tmp_path / "invalid" / "status.json").read_text())
    assert invalid["market_provenance_missing_games"] == 1
    assert invalid["status"] == "degraded"

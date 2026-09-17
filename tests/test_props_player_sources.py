import pandas as pd

from nfl_forecast.props_player_sources import add_nflverse_kickoff_timestamp


def test_nflverse_gameday_gametime_are_converted_from_eastern_to_utc():
    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_03_X_Y",
                "gameday": "2026-09-20",
                "gametime": "16:25",
            }
        ]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert converted.loc[0, "kickoff"] == pd.Timestamp("2026-09-20T20:25:00Z")


def test_existing_timezone_aware_kickoff_is_preserved_as_utc():
    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_03_X_Y",
                "kickoff": "2026-09-20T13:05:00-07:00",
            }
        ]
    )
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert converted.loc[0, "kickoff"] == pd.Timestamp("2026-09-20T20:05:00Z")


def test_missing_schedule_time_fields_remains_explicitly_unknown():
    schedules = pd.DataFrame([{"game_id": "2026_03_X_Y"}])
    converted = add_nflverse_kickoff_timestamp(schedules)
    assert pd.isna(converted.loc[0, "kickoff"])

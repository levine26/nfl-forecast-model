from __future__ import annotations

import pandas as pd
import pytest

from research.adaptive_weekly_replay_v1 import (
    iter_weekly_replay,
    load_replay_frame,
    parse_game_id,
)


def _frame() -> pd.DataFrame:
    rows = [
        {"game_id": "2021_18_A_B", "season": 2021, "home_win": 1, "market_prob": .6, "pure_prob": .55},
        {"game_id": "2022_01_C_D", "season": 2022, "home_win": 0, "market_prob": .4, "pure_prob": .45},
        {"game_id": "2022_01_E_F", "season": 2022, "home_win": 1, "market_prob": .7, "pure_prob": .65},
        {"game_id": "2022_02_G_H", "season": 2022, "home_win": 1, "market_prob": .52, "pure_prob": .51},
    ]
    frame = pd.DataFrame(rows)
    parsed = frame["game_id"].map(parse_game_id)
    frame["season_num"] = [x[0] for x in parsed]
    frame["week"] = [x[1] for x in parsed]
    frame["away_team"] = [x[2] for x in parsed]
    frame["home_team"] = [x[3] for x in parsed]
    frame["replay_order"] = range(len(frame))
    return frame


def test_parse_game_id():
    assert parse_game_id("2025_17_BUF_NE") == (2025, 17, "BUF", "NE")


def test_week_one_cannot_see_week_one_outcomes():
    replay = list(iter_weekly_replay(_frame(), start_season=2022, end_season=2022))
    week1 = replay[0]
    assert week1.week == 1
    assert set(week1.train.game_id) == {"2021_18_A_B"}
    assert set(week1.forecast.game_id) == {"2022_01_C_D", "2022_01_E_F"}


def test_week_two_can_see_prior_week_but_not_itself():
    replay = list(iter_weekly_replay(_frame(), start_season=2022, end_season=2022))
    week2 = replay[1]
    assert set(week2.train.game_id) == {
        "2021_18_A_B",
        "2022_01_C_D",
        "2022_01_E_F",
    }
    assert set(week2.forecast.game_id) == {"2022_02_G_H"}


def test_bad_game_id_rejected():
    with pytest.raises(ValueError):
        parse_game_id("bad_id")

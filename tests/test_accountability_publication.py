import pandas as pd

from nfl_forecast.accountability_publication import build_history_scoreboard, build_power_editorial


def test_power_editorial_explains_existing_ranking_without_new_score():
    power = pd.DataFrame([
        {"rank": 1, "team": "SEA", "elo_plus": 1634, "off_epa": .20, "def_epa_allowed": -.10, "pass_epa": .25, "recent_win_pct": .80, "movement": "▲2"},
        {"rank": 2, "team": "BUF", "elo_plus": 1610, "off_epa": .15, "def_epa_allowed": -.05, "pass_epa": .18, "recent_win_pct": .70, "movement": "→"},
        {"rank": 3, "team": "LV", "elo_plus": 1500, "off_epa": -.12, "def_epa_allowed": .14, "pass_epa": -.15, "recent_win_pct": .25, "movement": "▼1"},
    ])
    payload = build_power_editorial(power)

    assert len(payload["teams"]) == 3
    sea = payload["teams"][0]
    assert sea["team"] == "SEA"
    assert sea["rank"] == 1
    assert sea["movement_text"] == "up 2"
    assert "No. 1 Elo+ rating" in sea["why_here"]
    assert "guardrail" in sea
    assert "score" not in sea


def test_history_scoreboard_uses_only_locked_graded_forecasts():
    official = pd.DataFrame([
        {
            "game_id": "g1", "lock_status": "LOCKED", "final_home_prob": .70, "market_home_prob": .60,
            "actual_home_score": 27, "actual_away_score": 20, "winner_correct": True,
            "margin_abs_error": 2.0, "total_abs_error": 3.0,
        },
        {
            "game_id": "g2", "lock_status": "LOCKED", "final_home_prob": .40, "market_home_prob": .45,
            "actual_home_score": 24, "actual_away_score": 28, "winner_correct": True,
            "margin_abs_error": 1.0, "total_abs_error": 4.0,
        },
        {
            "game_id": "g3", "lock_status": "LOCKED", "final_home_prob": .80, "market_home_prob": .65,
            "actual_home_score": None, "actual_away_score": None, "winner_correct": None,
            "margin_abs_error": None, "total_abs_error": None,
        },
        {
            "game_id": "g4", "lock_status": "EARLY", "final_home_prob": .99, "market_home_prob": .50,
            "actual_home_score": 10, "actual_away_score": 30, "winner_correct": False,
            "margin_abs_error": 30.0, "total_abs_error": 20.0,
        },
    ])

    board = build_history_scoreboard(official)
    assert board["locked"] == 3
    assert board["graded"] == 2
    assert board["record"] == "2-0"
    assert board["winner_accuracy"] == 1.0
    assert round(board["margin_mae"], 3) == 1.5
    assert round(board["total_mae"], 3) == 3.5
    assert board["brier"] is not None
    assert board["market_brier"] is not None
    assert board["status"] == "live_forward_test"
    assert any("ROI" in note for note in board["notes"])


def test_history_scoreboard_waits_cleanly_before_first_lock():
    board = build_history_scoreboard(pd.DataFrame())
    assert board["locked"] == 0
    assert board["record"] == "0-0"
    assert board["status"] == "waiting_for_first_official_lock"

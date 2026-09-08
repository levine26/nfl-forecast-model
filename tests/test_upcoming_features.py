import pandas as pd

from nfl_forecast.features import build_matchup_features


def test_upcoming_game_receives_latest_completed_team_state():
    schedules = pd.DataFrame([
        {"game_id":"2026_01_A_B","season":2026,"week":1,"gameday":"2026-09-01","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":24,"away_score":17,"home_rest":7,"away_rest":7},
        {"game_id":"2026_02_A_B","season":2026,"week":2,"gameday":"2026-09-08","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":None,"away_score":None,"home_rest":7,"away_rest":7},
    ])
    team_games = pd.DataFrame([
        {"game_id":"2026_01_A_B","season":2026,"week":1,"team":"A","gameday":"2026-09-01","off_epa":0.20,"pass_epa":0.30,"rush_epa":0.05,"success_rate":0.52,"neutral_epa":0.18,"def_epa_allowed":-0.10,"def_pass_epa_allowed":-0.12,"def_rush_epa_allowed":-0.07,"def_success_allowed":0.40,"win":1.0},
        {"game_id":"2026_01_A_B","season":2026,"week":1,"team":"B","gameday":"2026-09-01","off_epa":-0.10,"pass_epa":-0.12,"rush_epa":-0.07,"success_rate":0.40,"neutral_epa":-0.08,"def_epa_allowed":0.20,"def_pass_epa_allowed":0.30,"def_rush_epa_allowed":0.05,"def_success_allowed":0.52,"win":0.0},
    ])
    elo = pd.DataFrame([
        {"game_id":"2026_01_A_B","home_elo":1500,"away_elo":1500,"elo_home_prob":0.56},
        {"game_id":"2026_02_A_B","home_elo":1515,"away_elo":1485,"elo_home_prob":0.60},
    ])
    games = build_matchup_features(team_games, schedules, elo)
    wk2 = games.loc[games["game_id"] == "2026_02_A_B"].iloc[0]
    assert wk2["home_off_epa_ewma"] == 0.20
    assert wk2["away_off_epa_ewma"] == -0.10
    assert abs(wk2["diff_off_epa_ewma"] - 0.30) < 1e-12

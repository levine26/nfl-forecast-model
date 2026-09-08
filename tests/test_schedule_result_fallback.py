import pandas as pd

from nfl_forecast.features import build_matchup_features


def test_schedule_results_fill_recent_win_when_pbp_missing():
    schedules = pd.DataFrame([
        {"game_id":"2025_18_A_B","season":2025,"week":18,"gameday":"2026-01-01","gametime":"13:00","game_type":"REG","home_team":"A","away_team":"B","home_score":20,"away_score":17,"home_rest":7,"away_rest":7},
        {"game_id":"2026_01_A_B","season":2026,"week":1,"gameday":"2026-09-01","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":30,"away_score":10,"home_rest":240,"away_rest":240},
        {"game_id":"2026_02_A_B","season":2026,"week":2,"gameday":"2026-09-08","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":None,"away_score":None,"home_rest":7,"away_rest":7},
    ])
    tg = pd.DataFrame([
        {"game_id":"2025_18_A_B","season":2025,"week":18,"team":"A","gameday":"2026-01-01","off_epa":0.2,"pass_epa":0.3,"rush_epa":0.05,"success_rate":0.52,"neutral_epa":0.18,"def_epa_allowed":-0.1,"def_pass_epa_allowed":-0.12,"def_rush_epa_allowed":-0.07,"def_success_allowed":0.4,"win":1.0},
        {"game_id":"2025_18_A_B","season":2025,"week":18,"team":"B","gameday":"2026-01-01","off_epa":-0.1,"pass_epa":-0.12,"rush_epa":-0.07,"success_rate":0.4,"neutral_epa":-0.08,"def_epa_allowed":0.2,"def_pass_epa_allowed":0.3,"def_rush_epa_allowed":0.05,"def_success_allowed":0.52,"win":0.0},
    ])
    elo = pd.DataFrame([
        {"game_id":"2025_18_A_B","home_elo":1500,"away_elo":1500,"elo_home_prob":.56},
        {"game_id":"2026_01_A_B","home_elo":1510,"away_elo":1490,"elo_home_prob":.58},
        {"game_id":"2026_02_A_B","home_elo":1520,"away_elo":1480,"elo_home_prob":.60},
    ])
    out = build_matchup_features(tg, schedules, elo)
    wk2 = out.loc[out.game_id.eq("2026_02_A_B")].iloc[0]
    assert wk2.home_win_ewma == 1.0
    assert wk2.away_win_ewma == 0.0

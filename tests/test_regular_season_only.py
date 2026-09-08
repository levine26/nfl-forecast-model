import pandas as pd

from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import build_matchup_features


def test_preseason_does_not_move_regular_season_elo():
    s = pd.DataFrame([
        {"game_id":"pre", "season":2026,"week":0,"gameday":"2026-08-20","gametime":"20:00","game_type":"PRE","home_team":"A","away_team":"B","home_score":50,"away_score":0},
        {"game_id":"reg", "season":2026,"week":1,"gameday":"2026-09-01","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":None,"away_score":None},
    ])
    e = build_pregame_elo(s)
    row = e.loc[e.game_id.eq("reg")].iloc[0]
    assert row.home_elo == 1500
    assert row.away_elo == 1500


def test_preseason_scaffold_not_in_rolling_window():
    schedules = pd.DataFrame([
        {"game_id":"2025_18_A_B","season":2025,"week":18,"gameday":"2026-01-01","gametime":"13:00","game_type":"REG","home_team":"A","away_team":"B","home_score":20,"away_score":17,"home_rest":7,"away_rest":7},
        {"game_id":"pre","season":2026,"week":0,"gameday":"2026-08-20","gametime":"20:00","game_type":"PRE","home_team":"A","away_team":"B","home_score":10,"away_score":7,"home_rest":7,"away_rest":7},
        {"game_id":"2026_01_A_B","season":2026,"week":1,"gameday":"2026-09-01","gametime":"20:00","game_type":"REG","home_team":"A","away_team":"B","home_score":None,"away_score":None,"home_rest":240,"away_rest":240},
    ])
    tg = pd.DataFrame([
        {"game_id":"2025_18_A_B","season":2025,"week":18,"team":"A","gameday":"2026-01-01","off_epa":0.2,"pass_epa":0.3,"rush_epa":0.05,"success_rate":0.52,"neutral_epa":0.18,"def_epa_allowed":-0.1,"def_pass_epa_allowed":-0.12,"def_rush_epa_allowed":-0.07,"def_success_allowed":0.4,"win":1.0},
        {"game_id":"2025_18_A_B","season":2025,"week":18,"team":"B","gameday":"2026-01-01","off_epa":-0.1,"pass_epa":-0.12,"rush_epa":-0.07,"success_rate":0.4,"neutral_epa":-0.08,"def_epa_allowed":0.2,"def_pass_epa_allowed":0.3,"def_rush_epa_allowed":0.05,"def_success_allowed":0.52,"win":0.0},
    ])
    elo = build_pregame_elo(schedules)
    g = build_matchup_features(tg, schedules, elo)
    wk1 = g.loc[g.game_id.eq("2026_01_A_B")].iloc[0]
    assert wk1.home_off_epa_ewma == 0.2
    assert wk1.away_off_epa_ewma == -0.1

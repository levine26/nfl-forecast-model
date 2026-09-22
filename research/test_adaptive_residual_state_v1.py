from __future__ import annotations

import pandas as pd

from research.adaptive_residual_state_v1 import run_state_filter


def test_same_week_games_use_preweek_state_only():
    frame = pd.DataFrame([
        {"game_id":"2022_01_A_B","season":2022,"week":1,"away_team":"A","home_team":"B","home_win":1,"fst_prob":0.50},
        {"game_id":"2022_01_C_D","season":2022,"week":1,"away_team":"C","home_team":"D","home_win":0,"fst_prob":0.50},
        {"game_id":"2022_02_A_B","season":2022,"week":2,"away_team":"A","home_team":"B","home_win":1,"fst_prob":0.50},
    ])
    out = run_state_filter(frame)
    week1 = out[out.week.eq(1)]
    assert (week1.home_state_preweek == 0.0).all()
    assert (week1.away_state_preweek == 0.0).all()
    week2 = out[out.week.eq(2)].iloc[0]
    assert week2.home_state_preweek != 0.0 or week2.away_state_preweek != 0.0
    assert ((out.adaptive_prob > 0.0) & (out.adaptive_prob < 1.0)).all()
    assert not out.state_updates_use_same_week_outcomes.any()

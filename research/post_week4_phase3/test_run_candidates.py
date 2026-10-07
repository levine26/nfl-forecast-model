"""Outcome-blind fixture tests for frozen Phase 3 implementation."""
import numpy as np
import pandas as pd
from research.post_week4_phase3.run_candidates import (
    CANDIDATES, early_state_features, fit_offset, predict_offset, season_forward,
)


def test_candidate_ids_and_small_fixed_penalty():
    assert CANDIDATES == ("MKT-COMP-RESIDUAL-V1", "MARGIN-RESIDUAL-WIN-V1", "EARLY-STATE-SHRINKAGE-V1")
    y = np.array([0, 1] * 150)
    m = np.full(len(y), 0.50)
    x = np.arange(len(y), dtype=float).reshape(-1, 1) / len(y)
    fit = fit_offset(y, m, x)
    result = predict_offset(m, x, fit)
    assert np.all(np.isfinite(result))
    assert ((result > 0) & (result < 1)).all()


def test_season_forward_excludes_target_and_future_outcomes():
    frame = pd.DataFrame([
        {"game_id": f"{y}_{i:02d}_A_B", "season": y, "home_win": (i % 2),
         "market_prob": .4 + .2 * (i % 4) / 3, "signal": (i % 7)/7}
        for y in range(2020, 2026) for i in range(140)
    ])
    original = season_forward(frame, ["signal"])
    altered = frame.copy()
    altered.loc[altered.season >= 2022, "home_win"] ^= 1
    next_run = season_forward(altered, ["signal"])
    ids = original.game_id.str.startswith("2022_")
    assert np.allclose(original.loc[ids,"candidate_prob"], next_run.loc[ids,"candidate_prob"])
    assert (original.fit_last_season < original.game_id.str[:4].astype(int)).all()


def test_early_state_excludes_current_game_and_keeps_offseason_prior():
    dates = ["2019-09-08", "2020-09-08", "2020-09-15"]
    schedules = pd.DataFrame([{"game_id":f"{year}_{week:02d}_A_B","season":year,
                               "week":week,"gameday":day,"home_team":"A","away_team":"B"}
                              for (year,week),day in zip([(2019,1),(2020,1),(2020,2)],dates)])
    values = [(1., -1.), (4., -4.), (8., -8.)]
    observed = pd.DataFrame([
        {"game_id":schedules.game_id.iloc[k],"team":team,
         "off_epa":val if team=="A" else -val,
         "def_epa_allowed":val/2 if team=="A" else -val/2}
        for k,(val,_) in enumerate(values) for team in ("A","B")
    ])
    before = early_state_features(observed,schedules)
    changed=observed.copy()
    changed.loc[changed.game_id.eq(schedules.game_id.iloc[1]),"off_epa"] = 999.0
    after=early_state_features(changed,schedules)
    # A current game's EPA cannot alter its pregame feature, but can alter next game's feature.
    assert np.isclose(before.off_state_diff.iloc[1], after.off_state_diff.iloc[1])
    assert not np.isclose(before.off_state_diff.iloc[2], after.off_state_diff.iloc[2])
    assert before.off_state_diff.notna().all()

from __future__ import annotations

import pandas as pd

from research.adaptive_error_audit_calibration_v1 import online_calibrate


def test_first_week_has_zero_intercept_and_no_training_rows():
    frame = pd.DataFrame([
        {"game_id":"2022_01_A_B","season":2022,"week":1,"home_win":1,"fst_prob":0.60},
        {"game_id":"2022_01_C_D","season":2022,"week":1,"home_win":0,"fst_prob":0.40},
        {"game_id":"2022_02_E_F","season":2022,"week":2,"home_win":1,"fst_prob":0.49},
    ])
    out = online_calibrate(frame)
    first = out[out.week.eq(1)]
    assert (first.calibration_intercept == 0.0).all()
    assert (first.calibration_training_games == 0).all()
    second = out[out.week.eq(2)].iloc[0]
    assert second.calibration_training_games == 2


def test_pick_preserving_variant_never_crosses_boundary():
    frame = pd.DataFrame([
        {"game_id":"2022_01_A_B","season":2022,"week":1,"home_win":1,"fst_prob":0.90},
        {"game_id":"2022_02_C_D","season":2022,"week":2,"home_win":1,"fst_prob":0.49},
        {"game_id":"2022_03_E_F","season":2022,"week":3,"home_win":0,"fst_prob":0.51},
    ])
    out = online_calibrate(frame)
    raw_side = out.fst_prob >= 0.5
    calibrated_side = out.pick_preserving_calibrated_prob >= 0.5
    assert raw_side.equals(calibrated_side)
    assert not out.same_week_outcomes_used_for_calibration.any()

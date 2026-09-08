import pandas as pd
import pytest

from nfl_forecast.diagnostics import (
    build_calibration_table,
    build_movement_attribution,
    build_postgame_autopsies,
    confidence_components,
)


def test_confidence_index_penalizes_disagreement_and_split():
    aligned = confidence_components(.72, .02, "ALIGNED")
    noisy = confidence_components(.72, .11, "WIN-MARGIN SPLIT")
    assert aligned["confidence_index"] > noisy["confidence_index"]
    assert 0 <= aligned["confidence_index"] <= 100


def test_movement_attribution_reconciles_final_delta():
    runs = pd.DataFrame([
        {"game_id":"g1","away_team":"A","home_team":"H","pick":"H","prediction_timestamp_utc":"2026-09-01T00:00:00Z","pure_home_prob":.60,"market_home_prob":.56,"final_home_prob":.59,"expected_margin":3.0,"expected_total":45.0},
        {"game_id":"g1","away_team":"A","home_team":"H","pick":"H","prediction_timestamp_utc":"2026-09-02T00:00:00Z","pure_home_prob":.64,"market_home_prob":.58,"final_home_prob":.625,"expected_margin":4.0,"expected_total":46.0},
    ])
    out = build_movement_attribution(runs)
    assert len(out) == 1
    row = out.iloc[0]
    total = row["model_component_pp"] + row["market_component_pp"] + row["residual_component_pp"]
    assert total == pytest.approx(row["final_home_delta_pp"])
    assert row["margin_delta"] == pytest.approx(1.0)


def test_calibration_uses_oof_rows_only():
    idx = [10, 11, 12, 13]
    hist = pd.DataFrame({"market_home_prob":[.6,.4,.7,.3]}, index=idx)
    base = pd.DataFrame({"home_win":[1,0,1,0],"stack":[.62,.42,.66,.35]}, index=idx)
    core = pd.DataFrame({"home_win":[1,0,1,0],"stack":[.65,.38,.72,.28]}, index=idx)
    out = build_calibration_table(hist, base, core, bins=5)
    assert set(out["model"]) == {"Sujar Baseline","Core Sujar+","Market","Final Ensemble"}
    assert out.groupby("model")["model_games"].max().eq(4).all()


def test_postgame_autopsy_never_invents_causal_story():
    official = pd.DataFrame([{
        "game_id":"g1","away_team":"A","home_team":"H","pick":"H","final_home_prob":.70,
        "projected_score":"H 27 – A 20","actual_home_score":24,"actual_away_score":21,
        "winner_correct":True,"margin_abs_error":4.0,"total_abs_error":2.0,
    }])
    out = build_postgame_autopsies(official)["g1"]
    assert out["winner_correct"] is True
    assert "Play-level causal analysis" in out["causal_analysis_status"]
    assert out["what_went_right"]

import pandas as pd

from nfl_forecast.diagnostics import build_movement_attribution, build_postgame_autopsies


def test_movement_attribution_respects_75_25_blend():
    rows = pd.DataFrame([
        {
            "game_id": "2026_01_NE_SEA",
            "prediction_timestamp_utc": "2026-09-09T00:00:00Z",
            "home_team": "SEA",
            "away_team": "NE",
            "pick": "SEA",
            "pure_home_prob": 0.70,
            "market_home_prob": 0.60,
            "final_home_prob": 0.675,
            "expected_margin": 6.0,
            "expected_total": 44.0,
        },
        {
            "game_id": "2026_01_NE_SEA",
            "prediction_timestamp_utc": "2026-09-09T01:00:00Z",
            "home_team": "SEA",
            "away_team": "NE",
            "pick": "SEA",
            "pure_home_prob": 0.72,
            "market_home_prob": 0.64,
            "final_home_prob": 0.70,
            "expected_margin": 7.0,
            "expected_total": 45.0,
        },
    ])
    out = build_movement_attribution(rows).iloc[0]
    assert round(out["model_component_pp"], 6) == 1.5
    assert round(out["market_component_pp"], 6) == 1.0
    assert abs(out["residual_component_pp"]) < 1e-9
    assert round(out["pick_delta_pp"], 6) == 2.5


def test_postgame_autopsy_emits_systematic_error_tags():
    official = pd.DataFrame([
        {
            "game_id": "2026_01_NE_SEA",
            "away_team": "NE",
            "home_team": "SEA",
            "pick": "SEA",
            "final_home_prob": 0.70,
            "projected_score": "SEA 27 – NE 19",
            "actual_home_score": 17,
            "actual_away_score": 31,
            "winner_correct": False,
            "margin_abs_error": 22.0,
            "total_abs_error": 2.0,
        }
    ])
    row = build_postgame_autopsies(official)["2026_01_NE_SEA"]
    assert row["winner_correct"] is False
    assert "winner_miss" in row["error_tags"]
    assert "margin_miss" in row["error_tags"]
    assert "total_miss" not in row["error_tags"]

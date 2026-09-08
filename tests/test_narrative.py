import pandas as pd

from nfl_forecast.narrative import build_game_previews


def test_preview_connects_history_and_structural_change_without_changing_forecast():
    predictions = pd.DataFrame([{
        "game_id":"g1","away_team":"LAC","home_team":"DEN","pick":"LAC",
        "final_home_prob":.36,"pure_home_prob":.34,"market_home_prob":.43,
        "expected_margin":-4.5,"expected_total":45.0,"spread_line":-1.5,
        "projected_score":"LAC 24.8 – DEN 20.3","model_disagreement":.04,"consistency_flag":"ALIGNED",
    }])
    evidence = {"g1":[
        {"category":"history","title":"Justin Herbert vs DEN coordinator","summary":"Across 4 prior games under the same defensive coordinator, Justin Herbert averaged +0.08 EPA/dropback over 130 dropbacks.","strength":"Moderate","sample_size":130,"source_name":"nflverse PBP","source_url":"https://example.com/history"},
        {"category":"coaching","title":"LAC offense changed","summary":"LAC enters the season under a new offensive staff with materially different decision-makers. Older matchup results are down-weighted.","strength":"Strong","source_name":"staff records","source_url":"https://example.com/staff"},
        {"category":"scheme","title":"LAC play action vs DEN","summary":"LAC used play action at an above-median rate and was efficient on those snaps. DEN was also strong against play action.","strength":"Strong","sample_size":100,"source_name":"FTN","source_url":"https://example.com/ftn"},
    ]}
    out = build_game_previews(predictions,evidence)["g1"]
    text = " ".join(out["paragraphs"])
    assert "historical matchup is relevant, but not automatically transferable" in text
    assert "What is different now" in text
    assert "LAC is the current model pick at 64.0%" in text
    assert "do not alter numerical probabilities" in out["guardrail"]


def test_preview_flags_uncertainty_when_models_disagree():
    predictions = pd.DataFrame([{
        "game_id":"g2","away_team":"A","home_team":"H","pick":"H",
        "final_home_prob":.55,"pure_home_prob":.56,"market_home_prob":.52,
        "expected_margin":.4,"expected_total":43.0,"spread_line":1.0,
        "projected_score":"H 21.7 – A 21.3","model_disagreement":.11,"consistency_flag":"NEUTRAL",
    }])
    out=build_game_previews(predictions,{"g2":[]})["g2"]
    assert "component-model disagreement is elevated" in out["what_could_make_us_wrong"]
    assert "close to a coin flip" in out["what_could_make_us_wrong"]

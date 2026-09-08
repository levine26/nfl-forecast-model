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
        {"category":"history","title":"Justin Herbert vs DEN coordinator","summary":"Justin Herbert has faced this defensive structure four times. He averaged +0.08 EPA/dropback over 130 dropbacks.","strength":"Moderate","sample_size":130,"source_name":"nflverse PBP","source_url":"https://example.com/history"},
        {"category":"coaching","title":"LAC offense changed","summary":"LAC enters the season under a new offensive staff with materially different decision-makers. Older matchup results are down-weighted.","strength":"Strong","source_name":"staff records","source_url":"https://example.com/staff"},
        {"category":"scheme","title":"LAC play action vs DEN","summary":"LAC used play action at an above-median rate and was efficient on those snaps. DEN was also strong against play action.","strength":"Strong","sample_size":100,"source_name":"FTN","source_url":"https://example.com/ftn"},
    ]}
    out = build_game_previews(predictions,evidence)["g1"]
    text = " ".join(out["paragraphs"])
    assert "But this is not a rerun" in text
    assert "LevLine has LAC at 64.0% to win" in text
    assert "football-only model" in text
    guardrail = out["guardrail"].lower()
    assert "numerical forecast" in guardrail
    assert "chronological out-of-sample validation" in guardrail


def test_preview_uses_dry_humor_for_a_true_coin_flip():
    predictions = pd.DataFrame([{
        "game_id":"g2","away_team":"A","home_team":"H","pick":"H",
        "final_home_prob":.505,"pure_home_prob":.51,"market_home_prob":.50,
        "expected_margin":.1,"expected_total":43.0,"spread_line":0.0,
        "projected_score":"H 21.6 – A 21.5","model_disagreement":.03,"consistency_flag":"ALIGNED",
    }])
    out=build_game_previews(predictions,{"g2":[]})["g2"]
    assert "coin flip wearing a decimal point" in out["paragraphs"][0]
    assert "by a whisker" in out["headline"]


def test_preview_flags_uncertainty_when_models_disagree():
    predictions = pd.DataFrame([{
        "game_id":"g3","away_team":"A","home_team":"H","pick":"H",
        "final_home_prob":.55,"pure_home_prob":.56,"market_home_prob":.52,
        "expected_margin":.4,"expected_total":43.0,"spread_line":1.0,
        "projected_score":"H 21.7 – A 21.3","model_disagreement":.11,"consistency_flag":"NEUTRAL",
    }])
    out=build_game_previews(predictions,{"g3":[]})["g3"]
    warning = out["what_could_make_us_wrong"].lower()
    assert "component models disagree more than usual" in warning
    assert "coin-flip territory" in warning

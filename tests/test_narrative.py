import pandas as pd

from nfl_forecast.narrative import build_game_previews


def _base_game(game_id="g1", away="LAC", home="DEN", pick="LAC", home_prob=.36):
    return {
        "game_id": game_id,
        "away_team": away,
        "home_team": home,
        "pick": pick,
        "final_home_prob": home_prob,
        "pure_home_prob": .34 if pick == away else .66,
        "market_home_prob": .43 if pick == away else .57,
        "expected_margin": -4.5 if pick == away else 4.5,
        "expected_total": 45.0,
        "spread_line": -1.5 if pick == away else 1.5,
        "projected_score": f"{pick} 24.8 – {home if pick == away else away} 20.3",
        "model_disagreement": .04,
        "consistency_flag": "ALIGNED",
    }


def test_read_synthesizes_history_without_reprinting_the_evidence():
    predictions = pd.DataFrame([_base_game()])
    history_summary = "Justin Herbert has faced DEN four times. He averaged +0.08 EPA/dropback over 130 dropbacks."
    evidence = {"g1":[
        {
            "category":"history","title":"Justin Herbert vs DEN: player history","summary":history_summary,
            "strength":"Strong","sample_size":130,"source_name":"nflverse PBP","source_url":"https://example.com/history",
            "metadata":{"family":"qb_opponent_history","advantage_team":"LAC"},
        },
        {
            "category":"coaching","title":"DEN defense changed","summary":"DEN enters the season with a different defensive decision-maker.",
            "strength":"Strong","source_name":"staff records","source_url":"https://example.com/staff",
            "metadata":{"family":"coaching"},
        },
        {
            "category":"scheme","title":"LAC protection vs DEN pass rush","summary":"LAC protected well last season; DEN generated pressure at an above-average rate.",
            "strength":"Strong","sample_size":220,"source_name":"FTN","source_url":"https://example.com/ftn",
            "metadata":{"family":"pressure","advantage_team":"LAC","editorial_score":.5},
        },
    ]}
    out = build_game_previews(predictions,evidence)["g1"]
    read = " ".join(out["paragraphs"])

    assert out["story_spine"]["primary_family"] == "qb_opponent_history"
    assert out["story_spine"]["primary_mode"] == "support"
    assert "actual memory" in read or "blank-slate" in read or "prior tape" in read
    assert "130 dropbacks" not in read
    assert history_summary not in read
    assert "LevLine has LAC" not in read
    assert "numerical forecast" in out["guardrail"].lower()


def test_different_matchup_families_produce_different_reads_and_headlines():
    predictions = pd.DataFrame([
        _base_game("pressure-game","A","H","H",.64),
        _base_game("explosive-game","X","Y","Y",.66),
    ])
    evidence = {
        "pressure-game":[{
            "category":"scheme","title":"H pass rush vs A protection",
            "summary":"H created sacks at a high rate while A allowed them too often. Exact supporting numbers live below the Read.",
            "strength":"Strong","sample_size":300,"metadata":{"family":"pressure","advantage_team":"H","editorial_score":1.2},
        }],
        "explosive-game":[{
            "category":"scheme","title":"Y explosives vs X prevention",
            "summary":"Y created chunk passes frequently while X struggled to prevent them. Exact supporting numbers live below the Read.",
            "strength":"Strong","sample_size":300,"metadata":{"family":"explosives","advantage_team":"Y","editorial_score":1.2},
        }],
    }
    out = build_game_previews(predictions,evidence)
    p = out["pressure-game"]
    e = out["explosive-game"]

    assert p["story_spine"]["primary_family"] == "pressure"
    assert e["story_spine"]["primary_family"] == "explosives"
    assert p["headline"] != e["headline"]
    assert p["paragraphs"][0] != e["paragraphs"][0]
    assert "Exact supporting numbers" not in p["paragraphs"][0]
    assert "Exact supporting numbers" not in e["paragraphs"][0]


def test_read_prefers_a_real_pick_supporting_signal_over_a_higher_counter_signal():
    predictions = pd.DataFrame([_base_game("vegas","MIA","LV","LV",.58)])
    evidence = {"vegas":[
        {
            "category":"scheme","title":"MIA early downs vs LV","summary":"MIA early-down evidence.",
            "strength":"Strong","sample_size":500,"metadata":{"family":"early_down","advantage_team":"MIA","editorial_score":2.0},
        },
        {
            "category":"scheme","title":"LV pressure vs MIA protection","summary":"LV pressure evidence.",
            "strength":"Moderate","sample_size":120,"metadata":{"family":"pressure","advantage_team":"LV","editorial_score":.2},
        },
    ]}
    out = build_game_previews(predictions,evidence)["vegas"]
    assert out["story_spine"]["primary_family"] == "pressure"
    assert out["story_spine"]["primary_advantage_team"] == "LV"
    assert out["story_spine"]["primary_mode"] == "support"
    assert "LV" in out["paragraphs"][0]


def test_team_level_availability_note_never_treats_team_code_as_a_person():
    predictions = pd.DataFrame([_base_game("ne-sea","NE","SEA","SEA",.69)])
    evidence = {"ne-sea":[
        {
            "category":"personnel","title":"NE — multiple players on the report","summary":"Official availability context.",
            "strength":"Strong","metadata":{"family":"availability"},"as_of":"2026-09-08T20:00:00+00:00",
        }
    ]}
    out = build_game_previews(predictions,evidence)["ne-sea"]
    read = out["paragraphs"][0]
    assert out["story_spine"]["primary_family"] == "availability"
    assert "NE is the name" not in read
    assert "personnel" in read.lower() or "active roster" in read.lower()


def test_matchup_meter_uses_live_evidence_not_only_scheme_rows():
    predictions = pd.DataFrame([_base_game()])
    evidence = {"g1":[
        {
            "category":"personnel","title":"DEN — starting tackle questionable","summary":"Official injury report note.",
            "strength":"Strong","metadata":{"family":"availability","advantage_team":"LAC"},"as_of":"2026-09-08T20:00:00+00:00",
        },
        {
            "category":"scheme","title":"LAC protection vs DEN pass rush","summary":"Pressure note.",
            "strength":"Strong","sample_size":300,"metadata":{"family":"pressure","advantage_team":"LAC","editorial_score":.8},"as_of":"2026-09-08T19:00:00+00:00",
        },
        {
            "category":"matchup","title":"DEN YAC vs LAC tackling","summary":"YAC note.",
            "strength":"Strong","sample_size":300,"metadata":{"family":"yac","advantage_team":"DEN","editorial_score":.7},"as_of":"2026-09-08T19:00:00+00:00",
        },
        {
            "category":"history","title":"Justin Herbert vs DEN: player history","summary":"History note.",
            "strength":"Moderate","sample_size":90,"metadata":{"family":"qb_opponent_history","advantage_team":"LAC"},"as_of":"2026-09-08T18:00:00+00:00",
        },
    ]}
    meter = build_game_previews(predictions,evidence)["g1"]["matchup_meter"]
    families = [row["family"] for row in meter]

    assert "availability" in families
    assert "pressure" in families
    assert len(families) == len(set(families))
    assert all("title" in row and "as_of" in row for row in meter)


def test_factor_cards_summarize_instead_of_copying_raw_evidence():
    predictions = pd.DataFrame([_base_game()])
    raw = "LAC gave up sacks on 8.7% of pass plays; DEN got home on 7.1%. This is the exact evidence sentence."
    evidence = {"g1":[{
        "category":"scheme","title":"LAC protection vs DEN pass rush","summary":raw,
        "strength":"Strong","sample_size":300,"metadata":{"family":"pressure","advantage_team":"LAC","editorial_score":1.0},
    }]}
    out = build_game_previews(predictions,evidence)["g1"]
    assert out["key_factors"][0]["summary"] != raw
    assert "8.7%" not in out["key_factors"][0]["summary"]


def test_uncertainty_stays_in_what_could_make_this_wrong_section():
    predictions = pd.DataFrame([{
        "game_id":"g3","away_team":"A","home_team":"H","pick":"H",
        "final_home_prob":.55,"pure_home_prob":.56,"market_home_prob":.52,
        "expected_margin":.4,"expected_total":43.0,"spread_line":1.0,
        "projected_score":"H 21.7 – A 21.3","model_disagreement":.11,"consistency_flag":"NEUTRAL",
    }])
    out=build_game_previews(predictions,{"g3":[]})["g3"]
    warning = out["what_could_make_us_wrong"].lower()
    read = " ".join(out["paragraphs"]).lower()
    assert "component models disagree more than usual" in warning
    assert "coin-flip territory" in warning
    assert "coin flip wearing a decimal point" not in read

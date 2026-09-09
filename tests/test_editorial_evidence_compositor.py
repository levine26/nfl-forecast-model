import pandas as pd

from nfl_forecast.editorial_voice import polish_preview_slate


def test_compositor_prefers_raw_pressure_fact_over_generic_card_summary():
    predictions = pd.DataFrame([{
        "game_id":"g","away_team":"AAA","home_team":"BBB","pick":"BBB"
    }])
    previews = {"g": {
        "headline":"old",
        "paragraphs":["old read"],
        "story_spine":{"primary_title":"AAA protection vs BBB pass rush","secondary_title":"BBB explosives vs AAA prevention"},
        "key_factors":[
            {"title":"AAA protection vs BBB pass rush","summary":"The pressure matchup tilts BBB; obvious passing downs are where it can become decisive.","metadata":{"family":"pressure","advantage_team":"BBB"}},
            {"title":"BBB explosives vs AAA prevention","summary":"The chunk-play path tilts BBB; the opponent's answer is forcing longer drives.","metadata":{"family":"explosives","advantage_team":"BBB"}},
        ],
        "matchup_meter":[],"notebook":[],
    }}
    evidence = {"g": [
        {"title":"AAA protection vs BBB pass rush","summary":"AAA gave up sacks on 8.1% of pass plays last season; BBB got home on 10.4%. If this turns into an obvious-passing-down game, that matchup gets loud fast.","metadata":{"family":"pressure","advantage_team":"BBB"}},
        {"title":"BBB explosives vs AAA prevention","summary":"BBB hit a 20+ yard pass on 12.3% of pass plays; AAA allowed one on 7.4%. The short version: BBB wants chunks, and AAA would rather make it earn twelve-play drives.","metadata":{"family":"explosives","advantage_team":"BBB"}},
    ]}
    out = polish_preview_slate(previews, predictions, evidence)["g"]
    public = " ".join([out["paragraphs"][0], out["case_for_pick"], out["case_for_opponent"], out["what_could_make_us_wrong"]])
    assert "8.1% sack rate" in public
    assert "10.4% sack rate" in public
    assert "12.3% of passes gained 20+ yards" in public
    assert "obvious passing downs are where it can become decisive" not in public
    assert "opponent's answer is forcing longer drives" not in public


def test_staff_impact_renderer_uses_coordinator_tendency_values():
    predictions = pd.DataFrame([{
        "game_id":"g","away_team":"AAA","home_team":"BBB","pick":"BBB"
    }])
    title = "What Jane Coach could change in BBB"
    previews = {"g": {
        "headline":"old","paragraphs":["old"],
        "story_spine":{"primary_title":title},
        "key_factors":[{"title":title,"summary":"Staff Impact is one of this matchup's clearest live signals.","metadata":{"family":"staff_impact"}}],
        "matchup_meter":[],"notebook":[],
    }}
    evidence = {"g": [{
        "title":title,
        "summary":"BBB's new coordinator, Jane Coach, arrives with a verifiable prior-team tendency profile.",
        "metadata":{
            "family":"staff_impact","advantage_team":"BBB","coordinator":"Jane Coach",
            "prior_profile":{"motion_rate":0.62,"play_action_rate":0.31,"plays":900},
            "team_baseline":{"motion_rate":0.41,"play_action_rate":0.20,"plays":850},
        },
    }]}
    out = polish_preview_slate(previews, predictions, evidence)["g"]
    public = " ".join([out["paragraphs"][0], out["case_for_pick"]])
    assert "Jane Coach tendency delta" in public
    assert "motion rate 62% vs 41%" in public
    assert "Staff Impact is one of" not in public

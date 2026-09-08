import pandas as pd

from nfl_forecast.context_plus import diversify_game_evidence, upgrade_contextual_evidence
from nfl_forecast.narrative import build_game_previews


def test_diversity_prefers_different_scheme_families():
    items=[
        {"category":"scheme","title":"A play action","strength":"Strong","side":"away","sample_size":150,"metadata":{"family":"play_action","editorial_score":2}},
        {"category":"scheme","title":"B play action","strength":"Strong","side":"home","sample_size":140,"metadata":{"family":"play_action","editorial_score":1}},
        {"category":"scheme","title":"Pressure","strength":"Moderate","side":"away","sample_size":120,"metadata":{"family":"pressure","editorial_score":2}},
        {"category":"matchup","title":"Explosives","strength":"Moderate","side":"home","sample_size":100,"metadata":{"family":"explosives","editorial_score":1}},
    ]
    out=diversify_game_evidence(items)
    families=[(x.get("metadata") or {}).get("family") for x in out if x.get("category") in {"scheme","matchup"}]
    assert len(families)==len(set(families))
    assert "pressure" in families and "explosives" in families


def test_preview_exposes_three_deciding_factors_and_levline_brand():
    preds=pd.DataFrame([{"game_id":"2026_01_ATL_PIT","away_team":"ATL","home_team":"PIT","pick":"PIT","final_home_prob":.67,"expected_margin":6.2,"expected_total":47.7,"projected_score":"PIT 27 - ATL 21","pure_home_prob":.70,"market_home_prob":.60,"spread_line":3.5,"model_disagreement":.04,"consistency_flag":"ALIGNED"}])
    evidence={"2026_01_ATL_PIT":[
        {"category":"scheme","title":"Pressure","summary":"PIT creates pressure at an above-average rate.","strength":"Strong","sample_size":180,"metadata":{"family":"pressure","advantage_team":"PIT"}},
        {"category":"matchup","title":"Explosives","summary":"ATL creates explosive passes at a high rate.","strength":"Moderate","sample_size":150,"metadata":{"family":"explosives","advantage_team":"ATL"}},
        {"category":"history","title":"QB history","summary":"The quarterback has struggled in prior meetings.","strength":"Moderate","sample_size":90,"metadata":{"family":"qb_opponent_history","advantage_team":"PIT"}},
    ]}
    p=build_game_previews(preds,evidence)["2026_01_ATL_PIT"]
    assert p["brand"]=="Sunday Signal"
    assert p["engine"]=="LevLine"
    assert len(p["key_factors"])==3
    assert "LevLine" in p["paragraphs"][0]


def test_upgrade_does_not_mutate_prediction_probabilities():
    preds=pd.DataFrame([{"game_id":"g1","away_team":"AAA","home_team":"BBB","gameday":"2026-09-10","gametime":"20:00"}])
    rows=[]
    for i in range(120):
        rows.append({"season":2025,"posteam":"AAA","defteam":"BBB" if i<60 else "CCC","play_type":"pass","pass":1,"rush":0,"epa":.18 if i%2==0 else -.04,"yards_gained":25 if i%5==0 else 7,"down":1 if i%2==0 else 2,"yardline_100":50,"sack":1 if i%18==0 else 0,"touchdown":0,"qb_scramble":0,"game_id":f"x{i//60}","passer_player_id":"q1"})
        rows.append({"season":2025,"posteam":"BBB","defteam":"AAA","play_type":"pass","pass":1,"rush":0,"epa":.02,"yards_gained":6,"down":1,"yardline_100":50,"sack":1 if i%8==0 else 0,"touchdown":0,"qb_scramble":0,"game_id":f"y{i//60}","passer_player_id":"q2"})
    pbp=pd.DataFrame(rows); ftn=pbp.assign(n_blitzers=0,n_defense_box=6,shotgun=1,is_motion=0,is_play_action=0,is_rpo=0,is_screen_pass=0)
    upgraded,status=upgrade_contextual_evidence(preds,{"g1":[]},pbp,ftn,None,{},2026)
    assert status["status"]=="healthy" and "g1" in upgraded
    assert "final_home_prob" not in preds.columns

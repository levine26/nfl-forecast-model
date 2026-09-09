import pandas as pd

from nfl_forecast.editorial_finalize import finalize_previews


def test_finalizer_replaces_generic_factor_copy_and_builds_notebook():
    predictions = pd.DataFrame([{"game_id":"g","away_team":"SF","home_team":"LA","pick":"LA"}])
    previews = {"g": {
        "headline":"LevLine sees LA differently than the market",
        "paragraphs":["Specific read."],
        "case_for_pick":"Specific Rams case.",
        "case_for_opponent":"Specific 49ers case.",
        "what_could_make_us_wrong":"Specific countercase.",
        "story_spine":{"primary_title":"LA explosives vs SF"},
        "key_factors":[{"title":"LA explosives vs SF","summary":"Explosives is a live signal."}],
        "matchup_meter":[{"title":"LA explosives vs SF","summary":"Generic."}],
        "notebook":[],
    }}
    evidence = {"g": [
        {"category":"scheme","title":"LA explosives vs SF","summary":"The Rams produced a 20+ yard pass on 7.1% of attempts in the comparison sample.","strength":"Strong","metadata":{"family":"explosives","advantage_team":"LA"}},
        {"category":"history","title":"Matthew Stafford vs SF: career game ledger","summary":"The full career ledger contains 14 meaningful passing games.","strength":"Strong","metadata":{"family":"career_qb_opponent_ledger"}},
        {"category":"personnel","title":"Matthew Stafford: Next Gen passing profile","summary":"Stafford averaged 2.75 seconds to throw.","strength":"Strong","metadata":{"family":"ngs_qb_profile"}},
    ]}
    status = finalize_previews(predictions, previews, evidence)
    assert status["status"] == "healthy"
    assert previews["g"]["key_factors"][0]["summary"].startswith("The Rams produced")
    assert previews["g"]["matchup_meter"][0]["summary"].startswith("The Rams produced")
    assert any("career game ledger" in item["title"] for item in previews["g"]["notebook"])
    assert previews["g"]["headline"] == "The Rams' shortcut is the big-play battle"
    assert previews["g"]["editorial_version"] == "story-desk-v3"

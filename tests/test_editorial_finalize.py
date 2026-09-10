import pandas as pd
import pytest

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


def _status_preview(headline: str, player: str, team: str, rate: str, team_copy: str) -> dict:
    return {
        "headline": headline,
        "paragraphs": [
            f"The official NFL injury report lists {player} (WR) as Limited Participation In Practice. "
            "No game-status designation is posted yet, so this is treated as availability context rather than an assumption the player will be inactive. "
            f"Later, {player} was limited in practice. That matters a little more against {team}'s specific plan. "
            f"Pressure reached {rate}% of opponent pass plays last season for {team}. "
            f"For the passing game backdrop, the relevant opponent-side profile was {team}'s coverage structure. "
            f"{player} usage is context for the role at {team}, not an injury point value. {team_copy}"
        ],
        "case_for_pick": f"{player} leverage.",
        "case_for_opponent": f"{headline} counter.",
        "what_could_make_us_wrong": f"{player} variance.",
        "editorial_voice": {"game_specific": True},
        "key_factors": [],
        "matchup_meter": [],
        "notebook": [],
    }


def test_finalizer_exempts_standardized_facts_without_weakening_substantive_uniqueness_gate():
    predictions = pd.DataFrame([
        {"game_id":"g1","away_team":"ATL","home_team":"PIT","pick":"PIT"},
        {"game_id":"g2","away_team":"BAL","home_team":"IND","pick":"BAL"},
    ])
    previews = {
        "g1": _status_preview(
            "Falcons-Steelers pressure test", "Drake London", "Pittsburgh", "4.5",
            "Pittsburgh must win the protection battle on passing downs.",
        ),
        "g2": _status_preview(
            "Ravens-Colts coverage test", "Zay Flowers", "Baltimore", "5.5",
            "Baltimore must create clean answers against disguised coverage.",
        ),
    }

    status = finalize_previews(predictions, previews, {"g1": [], "g2": []})
    assert status["status"] == "healthy"

    repeated_editorial = "This substantive football sentence must never repeat across separate matchup previews."
    previews["g1"]["case_for_pick"] = repeated_editorial
    previews["g2"]["case_for_pick"] = repeated_editorial
    with pytest.raises(ValueError, match="publication repeats game-file prose across matchups"):
        finalize_previews(predictions, previews, {"g1": [], "g2": []})

from pathlib import Path
import sys

import pandas as pd

# The executable story-desk pass lives under scripts/ so production can run it
# directly. Add the repository root explicitly because pytest's installed-package
# import mode does not guarantee that the checkout root is on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nfl_forecast.source_policy import provenance_grade
from nfl_forecast.story_context import build_story_context
from scripts.polish_publication import normalize_qb_history, rewrite_previews, require_publication_quality


def test_qb_recent_sample_excludes_two_dropback_cameo():
    evidence = {"g": [{
        "category": "history",
        "title": "Jacoby Brissett vs LAC: player history",
        "strength": "Weak",
        "metadata": {
            "family": "qb_opponent_history",
            "meetings": [
                {"season": 2024, "week": 17, "dropbacks": 2, "epa_per_dropback": -1.0, "success_rate": 0.0, "human_label": "2024 Week 17"},
                {"season": 2022, "week": 5, "dropbacks": 34, "epa_per_dropback": 0.2, "success_rate": 0.5, "human_label": "2022 Week 5"},
            ],
        },
    }]}
    audit = normalize_qb_history(evidence)
    item = evidence["g"][0]
    assert item["metadata"]["games"] == 1
    assert item["metadata"]["excluded_cameos"] == 1
    assert "recent analytical sample, not a career meeting count" in item["summary"]
    assert audit[0]["career_count_published"] is False


def test_melbourne_story_context_is_verified_and_specific():
    predictions = pd.DataFrame([{"game_id":"2026_01_SF_LA","season":2026,"week":1,"away_team":"SF","home_team":"LA"}])
    schedules = pd.DataFrame([
        {"season":2025,"week":10,"away_team":"SF","home_team":"LA","away_score":26,"home_score":42,"gameday":"2025-11-09"},
        {"season":2025,"week":5,"away_team":"LA","home_team":"SF","away_score":20,"home_score":17,"gameday":"2025-10-05"},
    ])
    story = build_story_context(predictions, schedules)["2026_01_SF_LA"]
    families = {(item.get("metadata") or {}).get("family") for item in story}
    assert "international_event" in families
    assert "international_travel" in families
    assert "rivalry" in families
    assert any("7,937" in item["summary"] for item in story)


def test_rewrite_removes_robotic_case_language_and_leads_with_event():
    predictions = pd.DataFrame([{
        "game_id":"2026_01_SF_LA","away_team":"SF","home_team":"LA","pick":"LA",
        "final_home_prob":.70,"pure_home_prob":.72,"market_home_prob":.64,"model_disagreement":.04,
    }])
    evidence = {"2026_01_SF_LA": [
        {"category":"travel","title":"Australia","summary":"First NFL regular-season game in Australia.","strength":"Strong","metadata":{"family":"international_event"}},
        {"category":"history","title":"Rivalry","summary":"San Francisco leads the all-time series 79-72-3.","strength":"Strong","sample_size":154,"metadata":{"family":"rivalry"}},
        {"category":"scheme","title":"LA explosives vs SF","summary":"LA created more explosive passes in the relevant sample.","strength":"Strong","sample_size":700,"metadata":{"family":"explosives","advantage_team":"LA"}},
        {"category":"matchup","title":"SF third downs vs LA","summary":"SF owns the stronger third-down profile in the relevant sample.","strength":"Strong","sample_size":700,"metadata":{"family":"third_down","advantage_team":"SF"}},
    ]}
    previews = {"2026_01_SF_LA": {
        "headline":"LevLine sees LA differently than the market",
        "paragraphs":["The answer on the other side is SF's edge."],
        "case_for_pick":"The case for LA has two distinct levers.",
        "case_for_opponent":"SF owns a real matchup counter-signal.",
    }}
    rewrite_previews(predictions, previews, evidence)
    require_publication_quality(previews)
    preview = previews["2026_01_SF_LA"]
    assert preview["headline"] == "Rams-49ers takes a 154-game rivalry to Melbourne"
    assert "Melbourne Cricket Ground" in preview["paragraphs"][0]
    assert "two distinct levers" not in str(preview).lower()
    assert "counter-signal" not in str(preview).lower()


def test_provenance_grades_conflict_fails_closed():
    assert provenance_grade(independent_sources=2) == "A"
    assert provenance_grade(official=True) == "B"
    assert provenance_grade(derived=True) == "C"
    assert provenance_grade(independent_sources=2, conflict=True) == "HOLD"


def test_story_desk_preserves_game_specific_voice_outside_special_story():
    predictions = pd.DataFrame([{
        "game_id":"g","away_team":"AAA","home_team":"BBB","pick":"BBB",
        "final_home_prob":.61,"pure_home_prob":.62,"market_home_prob":.58,"model_disagreement":.04,
    }])
    evidence = {"g": [
        {"category":"scheme","title":"AAA protection vs BBB pass rush","summary":"AAA gave up sacks on 8.0% of pass plays; BBB got home on 9.0%. If this turns into an obvious-passing-down game, that matchup gets loud fast.","strength":"Strong","sample_size":400,"metadata":{"family":"pressure","advantage_team":"BBB"}},
    ]}
    previews = {"g": {
        "headline":"AAA protection vs BBB pass rush",
        "paragraphs":["A deliberately game-specific Read.", "A market paragraph that must survive."],
        "case_for_pick":"BBB case already composed from canonical evidence.",
        "case_for_opponent":"AAA countercase already composed from canonical evidence.",
        "what_could_make_us_wrong":"A matchup-specific failure mode.",
        "editorial_voice":{"game_specific":True,"slate_aware":True},
    }}
    rewrite_previews(predictions, previews, evidence)
    preview = previews["g"]
    assert preview["paragraphs"] == ["A deliberately game-specific Read.", "A market paragraph that must survive."]
    assert preview["case_for_pick"] == "BBB case already composed from canonical evidence."
    assert preview["case_for_opponent"] == "AAA countercase already composed from canonical evidence."
    assert "obvious-passing-down" not in " ".join([preview["case_for_pick"], preview["case_for_opponent"]])


def test_story_desk_special_event_promotes_lead_without_overwriting_cases():
    predictions = pd.DataFrame([{
        "game_id":"2026_01_SF_LA","away_team":"SF","home_team":"LA","pick":"LA",
        "final_home_prob":.70,"pure_home_prob":.72,"market_home_prob":.64,"model_disagreement":.04,
    }])
    evidence = {"2026_01_SF_LA": [
        {"category":"travel","title":"Australia","summary":"First NFL regular-season game in Australia.","strength":"Strong","metadata":{"family":"international_event"}},
        {"category":"history","title":"Rivalry","summary":"San Francisco leads the all-time series 79-72-3.","strength":"Strong","sample_size":154,"metadata":{"family":"rivalry"}},
    ]}
    previews = {"2026_01_SF_LA": {
        "headline":"Matthew Stafford vs SF: player history",
        "paragraphs":["Original game-specific lead.", "Original market paragraph."],
        "case_for_pick":"Keep the LA case.",
        "case_for_opponent":"Keep the SF case.",
        "what_could_make_us_wrong":"Keep the failure mode.",
        "editorial_voice":{"game_specific":True,"slate_aware":True},
    }}
    rewrite_previews(predictions, previews, evidence)
    preview = previews["2026_01_SF_LA"]
    assert preview["headline"] == "Rams-49ers takes a 154-game rivalry to Melbourne"
    assert "Melbourne Cricket Ground" in preview["paragraphs"][0]
    assert preview["paragraphs"][1] == "Original market paragraph."
    assert preview["case_for_pick"] == "Keep the LA case."
    assert preview["case_for_opponent"] == "Keep the SF case."

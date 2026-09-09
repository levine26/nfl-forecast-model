from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compose_copilot_media_reads.py"
spec = importlib.util.spec_from_file_location("compose_copilot_media_reads", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

compose = module.compose
_canonical_url = module._canonical_url


def _ngrams(text: str, n: int = 7) -> set[str]:
    import re
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return {" ".join(words[i:i+n]) for i in range(max(0, len(words) - n + 1))}


def test_bing_redirect_resolves_to_direct_approved_publisher():
    url = (
        "http://www.bing.com/news/apiclick.aspx?ref=FexRss&"
        "url=https%3A%2F%2Fsports.yahoo.com%2Farticles%2Fbroncos-example.html"
    )
    assert _canonical_url(url, "Yahoo Sports") == "https://sports.yahoo.com/articles/broncos-example.html"


def test_composer_owns_exact_model_facts_and_sources():
    predictions = pd.DataFrame([
        {
            "game_id": "2026_01_DEN_KC",
            "away_team": "DEN",
            "home_team": "KC",
            "pick": "DEN",
            "final_home_prob": 0.38,
            "pure_home_prob": 0.32,
            "market_home_prob": 0.48,
            "expected_margin": -6.5,
            "spread_line": 3.5,
            "projected_score": "DEN 27.0 – KC 20.5",
        }
    ])
    payload = {
        "games": {
            "2026_01_DEN_KC": {
                "headline": "Broncos-Chiefs: Denver's rush challenges Kansas City protection",
                "paragraph1": (
                    "Denver wants its four-man rush to disrupt Kansas City's timing without sacrificing coverage bodies, while the Chiefs need clean early downs to keep their full passing menu available. Kansas City can punish overaggressive pressure with quick answers, but the Broncos can control the game if they create long-yardage downs and make the protection hold up repeatedly."
                ),
                "model_rationale": (
                    "Denver's pass rush and Kansas City's protection create the clearest football support for the Broncos, especially if early downs force longer developing passing situations."
                ),
                "sources": [
                    {"name": "ESPN", "title": "Chiefs prepare for Denver front", "url": "https://www.espn.com/nfl/story/_/id/example"},
                ],
            }
        }
    }
    previews = {
        "2026_01_DEN_KC": {
            "reported_sources": [
                {
                    "source_name": "Yahoo Sports",
                    "title": "Broncos pass rush enters opener healthy",
                    "source_url": "http://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fsports.yahoo.com%2Farticles%2Fdenver.html",
                }
            ],
            "key_factors": [{"title": "KC protection vs DEN pass rush"}],
        }
    }
    result = compose(payload, predictions, previews, {"2026_01_DEN_KC": []})
    entry = result["games"]["2026_01_DEN_KC"]
    p2 = entry["paragraph2"]
    assert "62.0% win probability" in p2
    assert "football-only PURE is 68.0%" in p2
    assert "market view is 52.0%" in p2
    assert "75% PURE / 25% MARKET" in p2
    assert "Denver Broncos -6.5" in p2
    assert "Kansas City Chiefs -3.5" in p2
    assert "DEN 27.0 – KC 20.5" in p2
    assert p2.endswith("The pick: Denver Broncos moneyline.")
    assert len(entry["sources"]) == 2
    assert {module._domain_family(x["url"]) for x in entry["sources"]} == {"espn.com", "yahoo.com"}


def test_numeric_llm_rationale_is_discarded_instead_of_published():
    predictions = pd.DataFrame([
        {
            "game_id": "2026_01_ATL_PIT",
            "away_team": "ATL",
            "home_team": "PIT",
            "pick": "PIT",
            "final_home_prob": 0.64,
            "pure_home_prob": 0.66,
            "market_home_prob": 0.58,
            "expected_margin": 5.2,
            "spread_line": 3.5,
            "projected_score": "PIT 26.0 – ATL 20.8",
        }
    ])
    payload = {
        "games": {
            "2026_01_ATL_PIT": {
                "headline": "Falcons-Steelers: Pittsburgh pressure tests Atlanta's new plan",
                "paragraph1": (
                    "Pittsburgh wants to make Atlanta play from behind the chains and expose its protection to obvious passing downs. The Falcons need a stable early-down run-pass mix and quick quarterback answers to keep the Steelers from dictating protections. If Atlanta avoids third-and-long, it can test Pittsburgh horizontally; if not, the Steelers can turn the game into a pass-rush problem."
                ),
                "model_rationale": "LevLine is 99% because the market spread is 12.5 and PURE is 100%.",
                "sources": [
                    {"name": "NFL.com", "title": "Steelers prepare for Falcons", "url": "https://www.nfl.com/news/example"},
                    {"name": "CBS Sports", "title": "Falcons opener update", "url": "https://www.cbssports.com/nfl/news/example"},
                ],
            }
        }
    }
    previews = {"2026_01_ATL_PIT": {"key_factors": [{"title": "ATL protection vs PIT pass rush"}]}}
    entry = compose(payload, predictions, previews, {"2026_01_ATL_PIT": []})["games"]["2026_01_ATL_PIT"]
    assert "99%" not in entry["paragraph2"]
    assert "12.5" not in entry["paragraph2"]
    assert "ATL protection vs PIT pass rush" in entry["paragraph2"]


def test_deterministic_model_paragraphs_do_not_share_seven_word_template_span():
    predictions = pd.DataFrame([
        {
            "game_id": "g1", "away_team": "DEN", "home_team": "KC", "pick": "DEN",
            "final_home_prob": 0.38, "pure_home_prob": 0.32, "market_home_prob": 0.48,
            "expected_margin": -6.5, "spread_line": 3.5, "projected_score": "DEN 27.0 – KC 20.5",
        },
        {
            "game_id": "g2", "away_team": "ATL", "home_team": "PIT", "pick": "PIT",
            "final_home_prob": 0.64, "pure_home_prob": 0.66, "market_home_prob": 0.58,
            "expected_margin": 5.2, "spread_line": 3.5, "projected_score": "PIT 26.0 – ATL 20.8",
        },
    ])
    payload = {"games": {
        "g1": {
            "headline": "Broncos-Chiefs: pressure matchup",
            "paragraph1": "Denver and Kansas City each have a clear protection problem to solve before the passing game can settle. The Broncos want pressure with four, while the Chiefs need early-down efficiency and quick answers to prevent obvious rush situations from deciding possessions throughout the game.",
            "model_rationale": "Denver's defensive front can support the Broncos if Kansas City is forced into predictable passing downs and longer protection assignments.",
            "sources": [
                {"name": "ESPN", "title": "One", "url": "https://www.espn.com/nfl/one"},
                {"name": "NFL.com", "title": "Two", "url": "https://www.nfl.com/news/two"},
            ],
        },
        "g2": {
            "headline": "Falcons-Steelers: protection matchup",
            "paragraph1": "Atlanta needs to keep Pittsburgh from owning obvious passing downs, while the Steelers want their front to make the Falcons play faster than planned. The Falcons can protect themselves with efficient early downs, but Pittsburgh gains control if Atlanta repeatedly asks its protection to survive long-developing dropbacks.",
            "model_rationale": "Pittsburgh's pressure plan supports the Steelers when Atlanta falls behind schedule and has to expose its protection to longer passing situations.",
            "sources": [
                {"name": "CBS Sports", "title": "Three", "url": "https://www.cbssports.com/nfl/three"},
                {"name": "Yahoo Sports", "title": "Four", "url": "https://sports.yahoo.com/nfl/four"},
            ],
        },
    }}
    previews = {"g1": {}, "g2": {}}
    result = compose(payload, predictions, previews, {"g1": [], "g2": []})["games"]
    assert not (_ngrams(result["g1"]["paragraph2"]) & _ngrams(result["g2"]["paragraph2"]))

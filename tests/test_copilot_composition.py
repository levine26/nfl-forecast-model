from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from nfl_forecast.copilot_source_backfill import backfill_direct_sources, canonical_direct_url


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


def test_official_team_domains_are_approved_publishers():
    assert _canonical_url(
        "https://www.packers.com/news/example", "Green Bay Packers"
    ) == "https://www.packers.com/news/example"
    assert _canonical_url(
        "https://www.vikings.com/news/example", "Minnesota Vikings"
    ) == "https://www.vikings.com/news/example"


def test_unresolved_or_homepage_substitution_is_not_fabricated():
    assert _canonical_url("https://news.google.com/rss/articles/opaque", "ESPN") == ""
    assert _canonical_url("", "NFL.com", "https://www.nfl.com/") == ""
    assert _canonical_url("https://www.nfl.com/teams/kansas-city-chiefs/", "NFL.com") == ""
    assert _canonical_url("https://www.chiefs.com/schedule/", "Chiefs") == ""


class _Response:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _OfficialSourceSession:
    def get(self, url, **kwargs):
        del kwargs
        if "baltimoreravens.com" in url:
            return _Response(
                """<?xml version='1.0'?><rss><channel>
                <item>
                  <title>Ravens prepare for Colts in Week 1</title>
                  <description>Baltimore Ravens prepare to face the Indianapolis Colts.</description>
                  <link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fwww.baltimoreravens.com%2Fnews%2Fravens-colts-week-1-preview</link>
                  <source url='https://www.baltimoreravens.com/'>Baltimore Ravens</source>
                </item>
                </channel></rss>"""
            )
        if "colts.com" in url:
            return _Response(
                """<?xml version='1.0'?><rss><channel>
                <item>
                  <title>Colts set for opener against Ravens</title>
                  <description>Indianapolis Colts host the Baltimore Ravens in Week 1.</description>
                  <link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fwww.colts.com%2Fnews%2Fcolts-ravens-week-1-preview</link>
                  <source url='https://www.colts.com/'>Indianapolis Colts</source>
                </item>
                </channel></rss>"""
            )
        raise AssertionError(f"unexpected backfill query: {url}")


def test_source_backfill_uses_two_independent_direct_official_articles():
    row = pd.Series({"away_team": "BAL", "home_team": "IND"})
    sources = backfill_direct_sources(row, [], session=_OfficialSourceSession())
    assert len(sources) == 2
    assert {module._domain_family(source["url"]) for source in sources} == {
        "baltimoreravens.com",
        "colts.com",
    }
    assert all("bing.com" not in source["url"] for source in sources)
    assert canonical_direct_url("https://www.baltimoreravens.com/") == ""


def test_source_backfill_discards_generic_existing_source_before_counting_families():
    row = pd.Series({"away_team": "BAL", "home_team": "IND"})
    generic = [{"name": "NFL", "title": "Game shell", "url": "https://www.nfl.com/games/ravens-at-colts-2026-reg-1"}]
    sources = backfill_direct_sources(row, generic, session=_OfficialSourceSession())
    assert len(sources) == 2
    assert all("/games/" not in source["url"] for source in sources)


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
    assert "LevLine's Broncos win probability is 62.0% against Chiefs" in p2
    assert "football-only PURE rates the Broncos at 68.0%" in p2
    assert "MARKET rates the Broncos at 52.0%" in p2
    assert "75% PURE for Broncos" in p2 and "25% MARKET" in p2
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


def test_deterministic_model_paragraphs_do_not_share_seven_word_template_span_when_all_probabilities_match():
    predictions = pd.DataFrame([
        {
            "game_id": "g1", "away_team": "DEN", "home_team": "KC", "pick": "DEN",
            "final_home_prob": 0.384, "pure_home_prob": 0.473, "market_home_prob": 0.407,
            "expected_margin": -6.5, "spread_line": 3.5, "projected_score": "DEN 27.0 – KC 20.5",
        },
        {
            "game_id": "g2", "away_team": "ATL", "home_team": "PIT", "pick": "PIT",
            "final_home_prob": 0.616, "pure_home_prob": 0.527, "market_home_prob": 0.593,
            "expected_margin": 5.2, "spread_line": 3.5, "projected_score": "PIT 26.0 – ATL 20.8",
        },
    ])
    payload = {"games": {
        "g1": {
            "headline": "Broncos-Chiefs: pressure matchup",
            "paragraph1": "Denver and Kansas City each have a clear protection problem to solve before the passing game can settle. The Broncos want pressure with four, while the Chiefs need early-down efficiency and quick answers to prevent obvious rush situations from deciding possessions throughout the game.",
            "model_rationale": "Denver's defensive front can support the Broncos if Kansas City is forced into predictable passing downs and longer protection assignments.",
            "sources": [
                {"name": "ESPN", "title": "One", "url": "https://www.espn.com/nfl/story/_/id/one"},
                {"name": "NFL.com", "title": "Two", "url": "https://www.nfl.com/news/two"},
            ],
        },
        "g2": {
            "headline": "Falcons-Steelers: protection matchup",
            "paragraph1": "Atlanta needs to keep Pittsburgh from owning obvious passing downs, while the Steelers want their front to make the Falcons play faster than planned. The Falcons can protect themselves with efficient early downs, but Pittsburgh gains control if Atlanta repeatedly asks its protection to survive long-developing dropbacks.",
            "model_rationale": "Pittsburgh's pressure plan supports the Steelers when Atlanta falls behind schedule and has to expose its protection to longer passing situations.",
            "sources": [
                {"name": "CBS Sports", "title": "Three", "url": "https://www.cbssports.com/nfl/news/three"},
                {"name": "Yahoo Sports", "title": "Four", "url": "https://sports.yahoo.com/articles/four.html"},
            ],
        },
    }}
    previews = {"g1": {}, "g2": {}}
    result = compose(payload, predictions, previews, {"g1": [], "g2": []})["games"]
    for gid in ("g1", "g2"):
        assert "61.6%" in result[gid]["paragraph2"]
        assert "52.7%" in result[gid]["paragraph2"]
        assert "59.3%" in result[gid]["paragraph2"]
    assert not (_ngrams(result["g1"]["paragraph2"]) & _ngrams(result["g2"]["paragraph2"]))

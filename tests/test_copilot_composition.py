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


def _den_kc_prediction() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_01_DEN_KC",
            "away_team": "DEN",
            "home_team": "KC",
            "pick": "DEN",
            "final_home_prob": 0.38,
            "fst_pure_home_prob": 0.32,
            "pure_home_prob": 0.49,
            "market_home_prob": 0.48,
            "margin_sigma": 13.5,
            "expected_total": 47.5,
            "expected_margin": 8.5,
            "spread_line": 3.5,
            "projected_score": "KC 35.0 – DEN 12.5",
        }
    ])


def _den_kc_payload(rationale: str) -> dict:
    return {
        "games": {
            "2026_01_DEN_KC": {
                "headline": "Broncos-Chiefs: Denver's rush challenges Kansas City protection",
                "paragraph1": (
                    "Denver wants its four-man rush to disrupt Kansas City's timing without sacrificing coverage bodies, while the Chiefs need clean early downs to keep their full passing menu available. Kansas City can punish overaggressive pressure with quick answers, but the Broncos can control the game if they create long-yardage downs and make the protection hold up repeatedly."
                ),
                "model_rationale": rationale,
                "sources": [
                    {"name": "ESPN", "title": "Chiefs prepare for Denver front", "url": "https://www.espn.com/nfl/story/_/id/example"},
                ],
            }
        }
    }


def _den_kc_previews() -> dict:
    return {
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


def test_composer_owns_canonical_3_0_model_facts_and_sources():
    rationale = (
        "Denver's pass rush and Kansas City's protection create the clearest football support for the Broncos, especially if early downs force longer developing passing situations."
    )
    result = compose(_den_kc_payload(rationale), _den_kc_prediction(), _den_kc_previews(), {"2026_01_DEN_KC": []})
    entry = result["games"]["2026_01_DEN_KC"]
    p2 = entry["paragraph2"]

    assert entry["model_rationale"].startswith("Denver's pass rush")
    assert "LevLine 3.0 gives the Broncos a 62.0%" in p2
    assert "68.0% football-only signal" in p2
    assert "52.0% vig-free market signal" in p2
    assert "not a fixed arithmetic blend" in p2
    assert "probability-implied presentation line of Denver Broncos -4.1" in p2
    assert "market line of Kansas City Chiefs -3.5" in p2
    assert "DEN 26 – KC 22" in p2
    assert "Kansas City Chiefs -8.5" not in p2
    assert "75% PURE" not in p2
    assert p2.endswith("The pick: Denver Broncos moneyline.")
    assert len(entry["sources"]) == 2
    assert {module._domain_family(x["url"]) for x in entry["sources"]} == {"espn.com", "yahoo.com"}


def test_numeric_provider_rationale_is_discarded_instead_of_published():
    entry = compose(
        _den_kc_payload("LevLine is 99% because the market spread is 12.5 and PURE is 100%."),
        _den_kc_prediction(),
        _den_kc_previews(),
        {"2026_01_DEN_KC": []},
    )["games"]["2026_01_DEN_KC"]

    assert "99%" not in entry["paragraph2"]
    assert "12.5" not in entry["paragraph2"]
    assert "Football context: KC protection vs DEN pass rush" in entry["paragraph2"]


def test_composer_preserves_human_rationale_for_final_renderer():
    rationale = (
        "Denver can support the forecast by forcing Kansas City into obvious passing downs where the Broncos can rush without sacrificing coverage numbers."
    )
    entry = compose(
        _den_kc_payload(rationale),
        _den_kc_prediction(),
        _den_kc_previews(),
        {"2026_01_DEN_KC": []},
    )["games"]["2026_01_DEN_KC"]

    assert entry["model_rationale"] == rationale
    assert rationale in entry["paragraph2"]

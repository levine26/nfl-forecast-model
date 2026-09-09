from __future__ import annotations

import pandas as pd

from nfl_forecast.media_context import fetch_media_context
from nfl_forecast.media_editorial import rewrite_reads_with_media


class _Response:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _Session:
    def get(self, url, **kwargs):
        if "news.google.com" in url:
            return _Response(
                """<?xml version='1.0'?><rss><channel>
                <item><title>Chiefs expect Patrick Mahomes to start Week 1 against Broncos - ESPN</title>
                <link>https://example.com/espn</link><pubDate>Tue, 08 Sep 2026 20:00:00 GMT</pubDate>
                <source url='https://espn.com'>ESPN</source></item>
                <item><title>Broncos-Chiefs same-game parlay picks - Betting Blog</title>
                <link>https://example.com/bet</link><pubDate>Tue, 08 Sep 2026 23:00:00 GMT</pubDate>
                <source url='https://example.com'>Betting Blog</source></item>
                </channel></rss>"""
            )
        if "bing.com" in url:
            return _Response(
                """<?xml version='1.0'?><rss><channel>
                <item><title>Chiefs left tackle trending toward missing opener</title>
                <link>https://example.com/cbs</link><description>Latest Kansas City injury update.</description>
                <pubDate>Tue, 08 Sep 2026 21:00:00 GMT</pubDate><source>CBS Sports</source></item>
                </channel></rss>"""
            )
        raise AssertionError(url)


def _predictions() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_01_DEN_KC",
            "season": 2026,
            "week": 1,
            "gameday": "2026-09-14",
            "gametime": "20:15",
            "away_team": "DEN",
            "home_team": "KC",
            "pick": "DEN",
            "final_home_prob": 0.40875,
            "pure_home_prob": 0.34,
            "market_home_prob": 0.615,
            "expected_margin": -6.5,
            "spread_line": -3.5,
            "projected_score": "DEN 27.0 – KC 20.5",
        }
    ])


def test_media_context_prioritizes_major_reporting_and_rejects_noise(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    media, status = fetch_media_context(_predictions(), session=_Session(), lookback_days=3650)
    items = media["2026_01_DEN_KC"]
    assert items[0]["source_name"] == "ESPN"
    assert all("Betting Blog" != item["source_name"] for item in items)
    assert all("CBS Sports" != item["source_name"] for item in items)
    assert items[0]["metadata"]["substantive"] is True
    assert items[0]["metadata"]["trusted_source"] is True
    assert status["games_with_reporting"] == 1
    assert status["games_with_substantive_reporting"] == 1
    assert status["games_with_trusted_reporting"] == 1
    assert status["providers"]["x_recent_search"]["status"] == "unavailable"


def test_media_led_read_is_matchup_preview_then_model_explanation():
    predictions = _predictions()
    previews = {
        "2026_01_DEN_KC": {
            "headline": "old template headline",
            "paragraphs": ["old paragraph one", "old paragraph two", "old paragraph three"],
            "editorial_voice": {"primary_variant": 0},
        }
    }
    media = {
        "2026_01_DEN_KC": [
            {
                "title": "Chiefs expect Patrick Mahomes to start Week 1 against Broncos",
                "source_name": "ESPN",
                "source_url": "https://example.com/espn",
                "as_of": "2026-09-08T20:00:00+00:00",
                "metadata": {
                    "editorial_score": 130,
                    "family": "reported_angle",
                    "substantive": True,
                    "trusted_source": True,
                },
            },
            {
                "title": "Chiefs left tackle trending toward missing opener",
                "source_name": "CBS Sports",
                "source_url": "https://example.com/cbs",
                "as_of": "2026-09-08T21:00:00+00:00",
                "metadata": {
                    "editorial_score": 120,
                    "family": "reported_angle",
                    "substantive": True,
                    "trusted_source": True,
                },
            },
        ]
    }
    evidence = {
        "2026_01_DEN_KC": [
            {
                "category": "matchup",
                "title": "KC protection vs DEN pass rush",
                "summary": "KC gave up sacks on 8.2% of pass plays last season; DEN got home on 9.7% of pass plays.",
                "metadata": {"family": "pressure"},
            }
        ]
    }
    result = rewrite_reads_with_media(previews, predictions, evidence, media)
    preview = result["2026_01_DEN_KC"]
    assert len(preview["paragraphs"]) == 2
    paragraph1, paragraph2 = preview["paragraphs"]

    assert "Broncos" in paragraph1 and "Chiefs" in paragraph1
    assert "8.2%" in paragraph1 and "9.7%" in paragraph1
    assert "according to" not in paragraph1.lower()
    assert "deserves the first paragraph" not in paragraph1.lower()
    assert "market gap:" not in paragraph1.lower()

    assert "LevLine" in paragraph2
    assert "59.1%" in paragraph2
    assert "66.0%" in paragraph2
    assert "38.5%" in paragraph2
    assert "75% PURE / 25% market" in paragraph2
    assert "Denver Broncos -6.5" in paragraph2
    assert "Denver Broncos -3.5" in paragraph2
    assert "DEN 27.0 – KC 20.5" in paragraph2
    assert paragraph2.endswith("The pick: Denver Broncos moneyline.")

    assert all("old paragraph" not in p.lower() for p in preview["paragraphs"])
    assert preview["editorial_voice"]["media_led"] is True
    assert preview["editorial_voice"]["two_paragraph_contract"] is True
    assert preview["reported_sources"][0]["source_name"] == "ESPN"

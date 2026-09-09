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
            "pure_home_prob": 0.34,
            "market_home_prob": 0.605,
        }
    ])


def test_media_context_prioritizes_major_reporting_over_betting_noise(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    media, status = fetch_media_context(_predictions(), session=_Session(), lookback_days=3650)
    items = media["2026_01_DEN_KC"]
    assert items[0]["source_name"] == "ESPN"
    assert any(item["source_name"] == "CBS Sports" for item in items)
    assert items[0]["metadata"]["substantive"] is True
    assert status["games_with_reporting"] == 1
    assert status["games_with_substantive_reporting"] == 1
    assert status["providers"]["x_recent_search"]["status"] == "unavailable"


def test_media_led_read_uses_reporting_then_quantitative_mechanism():
    predictions = _predictions()
    previews = {
        "2026_01_DEN_KC": {
            "headline": "old template headline",
            "paragraphs": ["KC protection vs DEN pass rush deserves the first paragraph because it can alter the menu."],
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
                "metadata": {"editorial_score": 130, "family": "reported_angle", "substantive": True},
            },
            {
                "title": "Chiefs left tackle trending toward missing opener",
                "source_name": "CBS Sports",
                "source_url": "https://example.com/cbs",
                "as_of": "2026-09-08T21:00:00+00:00",
                "metadata": {"editorial_score": 120, "family": "reported_angle", "substantive": True},
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
    read = result["2026_01_DEN_KC"]["paragraphs"][0]
    assert "ESPN reports Patrick Mahomes is expected to start Week 1 against Broncos" in read
    assert "CBS Sports has Chiefs left tackle trending toward missing opener" in read
    assert "Broncos–Chiefs pressure note" in read
    assert "Chiefs allowed an 8.2% sack rate" in read
    assert "Broncos generated 9.7%" in read
    assert "PURE has Denver 26.5 percentage points above consensus in Broncos–Chiefs" in read
    assert "deserves the first paragraph" not in read
    assert "KC protection vs DEN pass rush" not in read
    assert result["2026_01_DEN_KC"]["editorial_voice"]["media_led"] is True
    assert result["2026_01_DEN_KC"]["editorial_voice"]["game_specific"] is True
    assert result["2026_01_DEN_KC"]["reported_sources"][0]["source_name"] == "ESPN"

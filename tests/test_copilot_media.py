from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads


def _predictions():
    return pd.DataFrame([
        {"game_id": "2026_01_DEN_KC", "away_team": "DEN", "home_team": "KC", "pick": "DEN"}
    ])


def _generated(path: Path, generated_utc: str | None = None):
    stamp = generated_utc or pd.Timestamp.now(tz="UTC").isoformat()
    path.write_text(json.dumps({
        "games": {
            "2026_01_DEN_KC": {
                "headline": "Broncos-Chiefs: Denver's rush tests Kansas City's protection",
                "paragraph1": "Kansas City gets Patrick Mahomes back, but the matchup starts with whether the Chiefs can keep Denver's rush from turning long-yardage downs into the defining part of the night. The Broncos need their front to win without constant extra pressure so the secondary can stay disciplined. Kansas City, meanwhile, needs its protection to hold up well enough for Mahomes to attack Denver beyond the first read.",
                "paragraph2": "LevLine makes Denver the winner at 64.0%. Sunday Signal's football-only PURE component is 68.0% Broncos while the market view is 52.0%, so the production 75% PURE / 25% market blend still lands clearly on Denver. The model also makes the Broncos the stronger side on the projected margin, with the score expectation pointing the same direction. The pick: Denver Broncos moneyline.",
                "generated_utc": stamp,
                "sources": [
                    {"name": "ESPN", "title": "Mahomes expected to start", "url": "https://www.espn.com/nfl/story/example"},
                    {"name": "CBS Sports", "title": "Chiefs line update", "url": "https://www.cbssports.com/nfl/example"},
                ],
            }
        }
    }))


def test_copilot_read_replaces_entire_legacy_read(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    _generated(generated)
    previews = {
        "2026_01_DEN_KC": {
            "headline": "old",
            "paragraphs": ["old lead", "old second paragraph that must disappear", "old third"],
            "editorial_voice": {"media_led": True},
        }
    }
    result, status = apply_copilot_reads(previews, _predictions(), generated)
    assert status["status"] == "healthy"
    assert status["games_applied"] == 1
    preview = result["2026_01_DEN_KC"]
    assert preview["headline"].startswith("Broncos-Chiefs")
    assert len(preview["paragraphs"]) == 2
    assert preview["paragraphs"][0].startswith("Kansas City gets Patrick Mahomes")
    assert preview["paragraphs"][1].endswith("The pick: Denver Broncos moneyline.")
    assert "old second paragraph" not in " ".join(preview["paragraphs"])
    assert preview["editorial_voice"]["copilot_researched"] is True
    assert preview["editorial_voice"]["two_paragraph_contract"] is True
    assert preview["reported_sources"][0]["source_name"] == "ESPN"


def test_missing_copilot_artifact_leaves_fallback_untouched(tmp_path: Path):
    previews = {"2026_01_DEN_KC": {"headline": "fallback", "paragraphs": ["fallback one", "fallback two"]}}
    result, status = apply_copilot_reads(previews, _predictions(), tmp_path / "missing.json")
    assert status["status"] == "unavailable"
    assert status["games_applied"] == 0
    assert result["2026_01_DEN_KC"]["headline"] == "fallback"


def test_newer_reporting_blocks_older_copilot_overlay(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    now = pd.Timestamp.now(tz="UTC")
    _generated(generated, (now - pd.Timedelta(minutes=30)).isoformat())
    previews = {
        "2026_01_DEN_KC": {
            "headline": "fresh fallback headline",
            "paragraphs": ["Fresh matchup paragraph.", "Fresh LevLine paragraph. The pick: Denver Broncos moneyline."],
            "reported_sources": [
                {
                    "source_name": "ESPN",
                    "source_url": "https://www.espn.com/nfl/story/fresh",
                    "title": "New starter update",
                    "as_of": (now - pd.Timedelta(minutes=5)).isoformat(),
                }
            ],
        }
    }
    result, status = apply_copilot_reads(previews, _predictions(), generated)
    assert status["games_applied"] == 0
    assert status["skipped"]["2026_01_DEN_KC"] == "newer_reporting_available"
    assert result["2026_01_DEN_KC"]["headline"] == "fresh fallback headline"

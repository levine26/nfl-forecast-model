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
                "headline": "Mahomes returns, but Denver can test Kansas City's protection immediately",
                "read": "Patrick Mahomes is expected back for Kansas City, but the opener still starts with a protection question against Denver's front. The Broncos have enough pass-rush speed to make the Chiefs prove their line is settled before the rest of the offense can breathe. Kansas City still owns the higher-end quarterback answer, while Denver has a cleaner path to disruption than the public number suggests. That tension is the game, not a generic Week 1 power-rating argument.",
                "generated_utc": stamp,
                "sources": [
                    {"name": "ESPN", "title": "Mahomes expected to start", "url": "https://www.espn.com/nfl/story/example"},
                    {"name": "CBS Sports", "title": "Chiefs line update", "url": "https://www.cbssports.com/nfl/example"},
                ],
            }
        }
    }))


def test_copilot_read_applies_when_validated_output_exists(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    _generated(generated)
    previews = {
        "2026_01_DEN_KC": {
            "headline": "old",
            "paragraphs": ["old read"],
            "editorial_voice": {"media_led": True},
        }
    }
    result, status = apply_copilot_reads(previews, _predictions(), generated)
    assert status["status"] == "healthy"
    assert status["games_applied"] == 1
    preview = result["2026_01_DEN_KC"]
    assert preview["headline"].startswith("Mahomes returns")
    assert preview["editorial_voice"]["copilot_researched"] is True
    assert preview["editorial_voice"]["fallback_templates_used"] is False
    assert preview["reported_sources"][0]["source_name"] == "ESPN"


def test_missing_copilot_artifact_leaves_fallback_untouched(tmp_path: Path):
    previews = {"2026_01_DEN_KC": {"headline": "fallback", "paragraphs": ["fallback read"]}}
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
            "paragraphs": ["Fresh deterministic reporting says the starter situation changed."],
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

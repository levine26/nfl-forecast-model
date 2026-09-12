from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads


def _predictions():
    return pd.DataFrame([
        {
            "game_id": "2026_01_DEN_KC",
            "away_team": "DEN",
            "home_team": "KC",
            "pick": "DEN",
            "final_home_prob": 0.36,
            "fst_pure_home_prob": 0.32,
            "market_home_prob": 0.48,
            "margin_sigma": 12.9,
            "expected_total": 44.0,
            "spread_line": -2.5,
        }
    ])


def _generated(path: Path, generated_utc: str | None = None):
    stamp = generated_utc or pd.Timestamp.now(tz="UTC").isoformat()
    path.write_text(json.dumps({
        "games": {
            "2026_01_DEN_KC": {
                "headline": "Broncos-Chiefs: Denver's rush tests Kansas City's protection",
                "paragraph1": "Kansas City gets Patrick Mahomes back, but the matchup starts with whether the Chiefs can keep Denver's rush from turning long-yardage downs into the defining part of the night. The Broncos need their front to win without constant extra pressure so the secondary can stay disciplined. Kansas City, meanwhile, needs its protection to hold up well enough for Mahomes to attack Denver beyond the first read.",
                "model_rationale": "Denver's pressure plan can narrow Kansas City's passing menu if the Broncos create long-yardage downs without exposing their secondary to easy answers.",
                "paragraph2": "This deliberately stale provider paragraph must never be published verbatim after the canonical forecast changes. The pick: Denver Broncos moneyline.",
                "generated_utc": stamp,
                "sources": [
                    {"name": "ESPN", "title": "Mahomes expected to start", "url": "https://www.espn.com/nfl/story/example"},
                    {"name": "CBS Sports", "title": "Chiefs line update", "url": "https://www.cbssports.com/nfl/example"},
                ],
            }
        }
    }))


def test_provider_read_replaces_entire_legacy_read_and_rerenders_model_paragraph(tmp_path: Path):
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
    assert "This deliberately stale provider paragraph" not in preview["paragraphs"][1]
    assert "64.0% win probability" in preview["paragraphs"][1]
    assert "68.0% football-only signal" in preview["paragraphs"][1]
    assert "52.0% vig-free market signal" in preview["paragraphs"][1]
    assert preview["paragraphs"][1].endswith("The pick: Denver Broncos moneyline.")
    assert "old second paragraph" not in " ".join(preview["paragraphs"])
    assert preview["editorial_voice"]["copilot_researched"] is True
    assert preview["editorial_voice"]["two_paragraph_contract"] is True
    assert preview["reported_sources"][0]["source_name"] == "ESPN"


def test_missing_provider_artifact_leaves_fallback_untouched(tmp_path: Path):
    previews = {"2026_01_DEN_KC": {"headline": "fallback", "paragraphs": ["fallback one", "fallback two"]}}
    result, status = apply_copilot_reads(previews, _predictions(), tmp_path / "missing.json")
    assert status["status"] == "unavailable"
    assert status["games_applied"] == 0
    assert result["2026_01_DEN_KC"]["headline"] == "fallback"


def test_newer_reporting_is_advisory_and_does_not_erase_successful_provider_read(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    now = pd.Timestamp.now(tz="UTC")
    _generated(generated, (now - pd.Timedelta(minutes=30)).isoformat())
    previews = {
        "2026_01_DEN_KC": {
            "headline": "fresh deterministic fallback headline",
            "paragraphs": ["Fresh matchup paragraph.", "Fresh deterministic model paragraph."],
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
    assert status["games_applied"] == 1
    assert status["status"] == "healthy"
    assert status["advisories"]["2026_01_DEN_KC"] == "newer_reporting_available"
    assert result["2026_01_DEN_KC"]["headline"].startswith("Broncos-Chiefs")
    assert result["2026_01_DEN_KC"]["editorial_voice"]["provider_freshness_advisory"] == "newer_reporting_available"


def test_old_but_validated_provider_read_is_not_dropped_by_blanket_age_cutoff(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    now = pd.Timestamp.now(tz="UTC")
    _generated(generated, (now - pd.Timedelta(hours=12)).isoformat())
    previews = {"2026_01_DEN_KC": {"headline": "fallback", "paragraphs": ["fallback one", "fallback two"]}}
    result, status = apply_copilot_reads(previews, _predictions(), generated)
    assert status["games_applied"] == 1
    assert status["advisories"]["2026_01_DEN_KC"] == "provider_artifact_older_than_refresh_window"
    assert result["2026_01_DEN_KC"]["headline"].startswith("Broncos-Chiefs")


def test_missing_game_entry_fails_only_that_game(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    generated.write_text(json.dumps({"games": {}}))
    previews = {"2026_01_DEN_KC": {"headline": "fallback", "paragraphs": ["fallback one", "fallback two"]}}
    result, status = apply_copilot_reads(previews, _predictions(), generated)
    assert status["games_applied"] == 0
    assert status["skipped"] == {"2026_01_DEN_KC": "missing_entry"}
    assert result["2026_01_DEN_KC"]["headline"] == "fallback"

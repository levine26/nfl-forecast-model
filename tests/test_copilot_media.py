from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads


def _predictions():
    return pd.DataFrame([{
        "game_id":"2026_01_A_B",
        "away_team":"A",
        "home_team":"B",
        "pick":"B",
    }])


def _generated(path: Path):
    path.write_text(json.dumps({
        "games": {
            "2026_01_A_B": {
                "headline":"A real reported storyline",
                "read":"A human source-first paragraph about the current matchup, written from reporting instead of a reusable statistical template.",
                "generated_utc":"2026-09-09T12:00:00+00:00",
                "sources":[{"name":"ESPN","title":"Current matchup report","url":"https://www.espn.com/nfl/example"}],
            }
        }
    }))


def test_copilot_read_applies_when_validated_output_exists(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    _generated(generated)
    previews = {"2026_01_A_B":{"headline":"old","paragraphs":["old read"],"editorial_voice":{},"story_spine":{}}}
    evidence = {"2026_01_A_B":[]}
    previews, evidence, status = apply_copilot_reads(previews, evidence, _predictions(), generated)
    assert status["games_applied"] == 1
    assert previews["2026_01_A_B"]["headline"] == "A real reported storyline"
    assert previews["2026_01_A_B"]["editorial_voice"]["copilot_researched"] is True
    assert evidence["2026_01_A_B"][-1]["source_name"] == "ESPN"


def test_validated_copilot_read_can_supersede_curated_baseline(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    _generated(generated)
    previews = {
        "2026_01_A_B": {
            "headline":"curated",
            "paragraphs":["curated read"],
            "editorial_voice":{"source_first_reporting":True},
            "story_spine":{},
        }
    }
    evidence = {"2026_01_A_B":[]}
    result, evidence, status = apply_copilot_reads(previews, evidence, _predictions(), generated)
    assert status["games_applied"] == 1
    assert result["2026_01_A_B"]["headline"] == "A real reported storyline"
    assert result["2026_01_A_B"]["editorial_voice"]["copilot_researched"] is True
    assert evidence["2026_01_A_B"][-1]["source_name"] == "ESPN"

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


def test_copilot_read_applies_only_when_curated_read_is_absent(tmp_path: Path):
    generated = tmp_path / "copilot.json"
    _generated(generated)
    previews = {"2026_01_A_B":{"headline":"old","paragraphs":["old read"],"editorial_voice":{},"story_spine":{}}}
    evidence = {"2026_01_A_B":[]}
    previews, evidence, status = apply_copilot_reads(previews, evidence, _predictions(), generated)
    assert status["games_applied"] == 1
    assert previews["2026_01_A_B"]["headline"] == "A real reported storyline"
    assert previews["2026_01_A_B"]["editorial_voice"]["copilot_researched"] is True
    assert evidence["2026_01_A_B"][-1]["source_name"] == "ESPN"


def test_curated_source_first_read_beats_copilot_output(tmp_path: Path):
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
    result, _, status = apply_copilot_reads(previews, evidence, _predictions(), generated)
    assert status["games_applied"] == 0
    assert result["2026_01_A_B"]["headline"] == "curated"

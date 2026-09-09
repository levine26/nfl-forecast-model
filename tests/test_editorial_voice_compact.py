from __future__ import annotations

import pandas as pd

from nfl_forecast.editorial_voice import polish_preview_slate


def _preview(title: str, summary: str, leader: str) -> dict:
    item = {
        "title": title,
        "summary": summary,
        "category": "scheme",
        "strength": "Strong",
        "sample_size": 400,
        "advantage_team": leader,
        "metadata": {"family": "pressure", "advantage_team": leader},
    }
    return {
        "headline": "legacy",
        "paragraphs": ["legacy lead", "legacy model"],
        "key_factors": [item],
        "matchup_meter": [],
        "notebook": [],
        "story_spine": {"primary_title": title},
    }


def test_compact_structured_pressure_evidence_does_not_fall_back_to_generic_lead():
    predictions = pd.DataFrame([
        {"game_id": "g1", "away_team": "ARI", "home_team": "LAC", "pick": "LAC"},
        {"game_id": "g2", "away_team": "ATL", "home_team": "PIT", "pick": "PIT"},
    ])
    previews = {
        "g1": _preview("LAC protection vs ARI pass rush", "Pressure matchup tilts LAC.", "LAC"),
        "g2": _preview("ATL protection vs PIT pass rush", "Pressure matchup tilts PIT.", "PIT"),
    }

    result = polish_preview_slate(previews, predictions)
    lead1 = result["g1"]["paragraphs"][0]
    lead2 = result["g2"]["paragraphs"][0]

    assert "sourced lead unavailable" not in lead1.lower()
    assert "sourced lead unavailable" not in lead2.lower()
    assert "LAC protection vs ARI pass rush" in lead1
    assert "ATL protection vs PIT pass rush" in lead2
    assert lead1 != lead2
    assert result["g1"]["editorial_voice"]["game_specific"] is True
    assert result["g2"]["editorial_voice"]["game_specific"] is True

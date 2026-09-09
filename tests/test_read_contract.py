from __future__ import annotations

import pandas as pd

from nfl_forecast.media_editorial import rewrite_reads_with_media


def test_deterministic_read_has_exact_two_paragraph_contract():
    previews = {
        "2026_01_DEN_KC": {
            "headline": "legacy headline",
            "paragraphs": ["legacy one", "legacy two", "legacy three"],
            "editorial_voice": {},
        }
    }
    predictions = pd.DataFrame([
        {
            "game_id": "2026_01_DEN_KC",
            "away_team": "DEN",
            "home_team": "KC",
            "pick": "DEN",
            "final_home_prob": 0.40,
            "pure_home_prob": 0.30,
            "market_home_prob": 0.70,
            "expected_margin": -6.5,
            "spread_line": -3.5,
            "projected_score": "DEN 27.0 – KC 20.5",
        }
    ])
    evidence = {
        "2026_01_DEN_KC": [
            {
                "title": "KC protection vs DEN pass rush",
                "summary": "KC gave up sacks on 6.4% of pass plays last season; DEN got home on 9.3%.",
                "category": "pressure",
                "strength": "Strong",
                "metadata": {"family": "pressure"},
            }
        ]
    }
    media = {
        "2026_01_DEN_KC": [
            {
                "source_name": "ESPN",
                "source_url": "https://www.espn.com/nfl/story/example",
                "title": "Chiefs expect Patrick Mahomes to start opener vs Broncos",
                "as_of": "2026-09-09T12:00:00Z",
                "metadata": {"trusted_source": True, "substantive": True, "editorial_score": 10},
            },
            {
                "source_name": "CBS Sports",
                "source_url": "https://www.cbssports.com/nfl/news/example",
                "title": "Chiefs left tackle likely out against Broncos",
                "as_of": "2026-09-09T12:15:00Z",
                "metadata": {"trusted_source": True, "substantive": True, "editorial_score": 9},
            },
        ]
    }

    result = rewrite_reads_with_media(previews, predictions, evidence, media)
    preview = result["2026_01_DEN_KC"]
    assert len(preview["paragraphs"]) == 2
    paragraph1, paragraph2 = preview["paragraphs"]
    assert "legacy" not in " ".join(preview["paragraphs"]).lower()
    assert "Chiefs" in paragraph1 and "Broncos" in paragraph1
    assert "LevLine" in paragraph2
    assert "60.0%" in paragraph2
    assert "70.0%" in paragraph2
    assert "30.0%" in paragraph2
    assert "75% PURE / 25% market" in paragraph2
    assert "Denver Broncos -6.5" in paragraph2
    assert "Denver Broncos -3.5" in paragraph2
    assert "DEN 27.0 – KC 20.5" in paragraph2
    assert paragraph2.endswith("The pick: Denver Broncos moneyline.")
    assert preview["editorial_voice"]["two_paragraph_contract"] is True

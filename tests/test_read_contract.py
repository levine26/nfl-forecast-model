from __future__ import annotations

import re

import pandas as pd

from nfl_forecast.media_editorial import _football_preview, rewrite_reads_with_media


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
    assert "The Chiefs need clean early downs" in paragraph1
    assert "the Broncos want to force the Chiefs" in paragraph1
    assert "Chiefs needs" not in paragraph1
    assert "LevLine" in paragraph2
    assert "60.0%" in paragraph2
    assert "70.0%" in paragraph2
    assert "30.0%" in paragraph2
    assert "75% PURE / 25% market" in paragraph2
    assert "Denver Broncos -6.5" in paragraph2
    assert "Denver Broncos -3.5" in paragraph2
    assert "DEN 27.0 – KC 20.5" in paragraph2
    assert "KC protection vs DEN pass rush" in paragraph2
    assert paragraph2.endswith("The pick: Denver Broncos moneyline.")
    assert preview["editorial_voice"]["two_paragraph_contract"] is True


def _seven_grams(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return {" ".join(words[i:i + 7]) for i in range(max(0, len(words) - 6))}


def test_qb_history_uses_item_side_for_home_quarterback():
    item = {
        "title": "Jalen Hurts vs WAS: player history",
        "summary": "Historical quarterback evidence for the current matchup.",
        "side": "home",
        "metadata": {"family": "qb_opponent_history"},
    }
    headline, paragraph = _football_preview("WAS", "PHI", item)

    assert "Jalen Hurts" in headline
    assert "Commanders defense" in headline
    assert "Eagles protection" in paragraph
    assert "Commanders pressure" in paragraph
    assert "Commanders protection" not in paragraph
    assert "Commanders' job" in paragraph
    assert "Commanders's" not in paragraph


def test_qb_history_infers_home_offense_from_opponent_when_side_missing():
    item = {
        "title": "Matthew Stafford vs SF: player history",
        "summary": "Historical quarterback evidence for the current matchup.",
        "metadata": {"family": "qb_opponent_history"},
    }
    headline, paragraph = _football_preview("SF", "LA", item)

    assert "Matthew Stafford" in headline
    assert "49ers defense" in headline
    assert "Rams protection" in paragraph
    assert "49ers pressure" in paragraph
    assert "49ers' job" in paragraph
    assert "49ers's" not in paragraph


def test_qb_history_fallbacks_share_no_seven_word_template_spans():
    cases = [
        (
            "DAL", "NYG",
            {
                "title": "Dak Prescott vs NYG: player history",
                "summary": "Historical quarterback evidence for the current matchup.",
                "side": "away",
                "metadata": {"family": "qb_opponent_history"},
            },
        ),
        (
            "SF", "LA",
            {
                "title": "Matthew Stafford vs SF: player history",
                "summary": "Historical quarterback evidence for the current matchup.",
                "side": "home",
                "metadata": {"family": "qb_opponent_history"},
            },
        ),
        (
            "WAS", "PHI",
            {
                "title": "Jalen Hurts vs WAS: player history",
                "summary": "Historical quarterback evidence for the current matchup.",
                "side": "home",
                "metadata": {"family": "qb_opponent_history"},
            },
        ),
    ]
    paragraphs = [_football_preview(away, home, item)[1] for away, home, item in cases]
    grams = [_seven_grams(paragraph) for paragraph in paragraphs]

    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            assert not grams[i].intersection(grams[j])


def test_generic_fallback_uses_side_punctuation_and_avoids_shared_seven_word_spans():
    cases = [
        (
            "NE", "SEA",
            {
                "title": "NE: Ben Brown — Out",
                "summary": "New England has to account for an unavailable interior blocker",
                "side": "away",
                "metadata": {"family": "availability"},
            },
        ),
        (
            "SF", "LA",
            {
                "title": "Matthew Stafford vs SF: career game ledger",
                "summary": "The career sample supplies historical context without changing the forecast",
                "side": "home",
                "metadata": {"family": "career_qb_opponent_ledger"},
            },
        ),
    ]
    paragraphs = [_football_preview(away, home, item)[1] for away, home, item in cases]

    assert "blocker. For Patriots" in paragraphs[0]
    assert "Patriots' choices against Seahawks" in paragraphs[0]
    assert "forecast. For Rams" in paragraphs[1]
    assert "Rams' choices against 49ers" in paragraphs[1]
    assert not _seven_grams(paragraphs[0]).intersection(_seven_grams(paragraphs[1]))

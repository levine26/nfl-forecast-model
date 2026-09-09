from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_levline_paragraphs.py"
spec = importlib.util.spec_from_file_location("render_levline_paragraphs", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
render = module.render


def _grams(text: str, n: int = 7) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return {" ".join(words[i:i+n]) for i in range(max(0, len(words) - n + 1))}


def test_renderer_serializes_exact_pick_side_values_and_pick_sentence():
    row = pd.Series({
        "away_team": "DEN", "home_team": "KC", "pick": "DEN",
        "final_home_prob": 0.384, "pure_home_prob": 0.318, "market_home_prob": 0.583,
        "expected_margin": -5.5, "spread_line": 3.0,
        "projected_score": "KC 19.8 – DEN 25.3",
    })
    text = render(row, {"key_factors": [{"title": "KC protection vs DEN pass rush"}]})
    assert "61.6%" in text
    assert "68.2%" in text
    assert "41.7%" in text
    assert "75%" in text and "25%" in text
    assert "Denver Broncos -5.5" in text
    assert "Kansas City Chiefs -3.0" in text
    assert "KC 19.8 – DEN 25.3" in text
    assert text.endswith("The pick: Denver Broncos moneyline.")


def test_equal_rounded_values_do_not_create_cross_game_seven_word_collision():
    den = pd.Series({
        "away_team": "DEN", "home_team": "KC", "pick": "DEN",
        "final_home_prob": 0.384, "pure_home_prob": 0.318, "market_home_prob": 0.407,
        "expected_margin": -5.5, "spread_line": 3.0, "projected_score": "KC 19.8 – DEN 25.3",
    })
    det = pd.Series({
        "away_team": "NO", "home_team": "DET", "pick": "DET",
        "final_home_prob": 0.616, "pure_home_prob": 0.579, "market_home_prob": 0.726,
        "expected_margin": 3.8, "spread_line": 7.0, "projected_score": "DET 24.8 – NO 21.0",
    })
    a = render(den, {"key_factors": [{"title": "KC protection vs DEN pass rush"}]})
    b = render(det, {"key_factors": [{"title": "NO protection vs DET pass rush"}]})
    assert not (_grams(a) & _grams(b))


def test_same_pure_probability_remains_unique_by_matchup():
    hou = pd.Series({
        "away_team": "BUF", "home_team": "HOU", "pick": "HOU",
        "final_home_prob": 0.516, "pure_home_prob": 0.527, "market_home_prob": 0.483,
        "expected_margin": 0.3, "spread_line": -1.5, "projected_score": "HOU 22.9 – BUF 22.7",
    })
    dal = pd.Series({
        "away_team": "DAL", "home_team": "NYG", "pick": "DAL",
        "final_home_prob": 0.456, "pure_home_prob": 0.473, "market_home_prob": 0.407,
        "expected_margin": 0.6, "spread_line": -3.0, "projected_score": "NYG 22.0 – DAL 21.4",
    })
    a = render(hou, {"key_factors": [{"title": "BUF protection vs HOU pass rush"}]})
    b = render(dal, {"key_factors": [{"title": "NYG protection vs DAL pass rush"}]})
    assert not (_grams(a) & _grams(b))


def test_two_los_angeles_picks_do_not_share_pre_pick_seven_gram():
    lac = pd.Series({
        "away_team": "ARI", "home_team": "LAC", "pick": "LAC",
        "final_home_prob": 0.693, "pure_home_prob": 0.656, "market_home_prob": 0.804,
        "expected_margin": 6.7, "spread_line": 9.5, "projected_score": "LAC 25.5 – ARI 18.8",
    })
    lar = pd.Series({
        "away_team": "SF", "home_team": "LA", "pick": "LA",
        "final_home_prob": 0.620, "pure_home_prob": 0.615, "market_home_prob": 0.637,
        "expected_margin": 5.0, "spread_line": 3.5, "projected_score": "LA 26.4 – SF 21.4",
    })
    a = render(lac, {"key_factors": [{"title": "LAC protection vs ARI pass rush"}]})
    b = render(lar, {"key_factors": [{"title": "SF availability vs LA pressure"}]})
    assert not (_grams(a) & _grams(b))

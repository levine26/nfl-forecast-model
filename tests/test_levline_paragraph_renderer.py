from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_levline_paragraphs.py"
spec = importlib.util.spec_from_file_location("render_levline_paragraphs", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
render = module.render


def _row(**overrides):
    base = {
        "away_team": "DEN",
        "home_team": "KC",
        "pick": "DEN",
        "final_home_prob": 0.384,
        "fst_pure_home_prob": 0.318,
        "pure_home_prob": 0.49,
        "market_home_prob": 0.583,
        "margin_sigma": 13.5,
        "expected_total": 45.8,
        "expected_margin": 8.5,
        "spread_line": 3.0,
        "projected_score": "KC 40.0 – DEN 10.0",
    }
    base.update(overrides)
    return pd.Series(base)


def test_renderer_uses_fst_and_probability_implied_public_presentation():
    text = render(_row(), {"key_factors": [{"title": "KC protection vs DEN pass rush"}]})

    assert "LevLine 3.0" in text
    assert "61.6%" in text
    assert "68.2%" in text
    assert "41.7%" in text
    assert "frozen F-ST engine" in text
    assert "not a fixed arithmetic blend" in text
    assert "probability-implied presentation line of Denver Broncos -4.0" in text
    assert "market line of Kansas City Chiefs -3.0" in text
    assert "DEN 25 – KC 21" in text
    assert "Football context: KC protection vs DEN pass rush" in text
    assert text.endswith("The pick: Denver Broncos moneyline.")


def test_renderer_does_not_publish_independent_margin_or_legacy_score_as_official():
    text = render(_row(), {"key_factors": [{"title": "KC protection vs DEN pass rush"}]})

    assert "Kansas City Chiefs -8.5" not in text
    assert "KC 40.0 – DEN 10.0" not in text
    assert "75% PURE" not in text
    assert "25% market" not in text


def test_renderer_prefers_fst_football_signal_over_legacy_pure_probability():
    text = render(
        _row(fst_pure_home_prob=0.20, pure_home_prob=0.49),
        {"key_factors": [{"title": "DEN coverage leverage"}]},
    )

    # DEN is away, so F-ST football-only pick-side probability is 80.0%.
    assert "80.0% football-only signal" in text
    assert "51.0%" not in text


def test_probability_implied_line_stays_on_same_side_as_official_pick():
    text = render(
        _row(
            away_team="BUF",
            home_team="HOU",
            pick="HOU",
            final_home_prob=0.516,
            fst_pure_home_prob=0.527,
            market_home_prob=0.483,
            margin_sigma=13.5,
            expected_total=45.6,
            expected_margin=-7.0,
            spread_line=-1.5,
            projected_score="BUF 28.0 – HOU 18.0",
        ),
        {"key_factors": [{"title": "BUF early-down approach vs HOU"}]},
    )

    assert "LevLine 3.0 gives the Texans a 51.6%" in text
    assert "probability-implied presentation line of Houston Texans -0.5" in text
    assert "Houston Texans -7.0" not in text
    assert text.endswith("The pick: Houston Texans moneyline.")

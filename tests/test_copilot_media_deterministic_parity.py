from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from nfl_forecast.editorial_model_read import render_model_paragraph


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_copilot_media_reads.py"
spec = importlib.util.spec_from_file_location("validate_copilot_media_reads", SCRIPT)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


def _row() -> pd.Series:
    return pd.Series(
        {
            "game_id": "2026_01_CHI_CAR",
            "away_team": "CHI",
            "home_team": "CAR",
            "pick": "CHI",
            "final_home_prob": 0.3675904068594795,
            "fst_pure_home_prob": 0.4361715747693297,
            "market_home_prob": 0.3907637655417407,
            "margin_sigma": 13.0,
            "expected_total": 47.5,
            "spread_line": -3.0,
        }
    )


def test_canonical_deterministic_prefix_accepts_renderer_output_with_context():
    row = _row()
    final = "The pick: Chicago Bears moneyline."
    paragraph = render_model_paragraph(
        row,
        "Chicago's early-down efficiency is the matchup hinge against Carolina's front.",
    )
    prefix = validator._canonical_deterministic_prefix(row, final)

    assert paragraph.startswith(prefix)
    assert paragraph.endswith(final)


def test_canonical_deterministic_prefix_rejects_stale_probability_even_if_pick_is_current():
    row = _row()
    final = "The pick: Chicago Bears moneyline."
    paragraph = render_model_paragraph(row, "Current matchup context.")
    stale = paragraph.replace("63.2% win probability", "62.6% win probability", 1)
    prefix = validator._canonical_deterministic_prefix(row, final)

    assert stale.endswith(final)
    assert not stale.startswith(prefix)


def test_canonical_deterministic_prefix_rejects_stale_line_or_score():
    row = _row()
    final = "The pick: Chicago Bears moneyline."
    paragraph = render_model_paragraph(row, "Current matchup context.")
    prefix = validator._canonical_deterministic_prefix(row, final)

    stale_line = paragraph.replace("probability-implied presentation line of Chicago Bears -", "probability-implied presentation line of Chicago Bears -99", 1)
    assert not stale_line.startswith(prefix)

    score_marker = "an approximate coherent score of "
    assert score_marker in paragraph
    score_start = paragraph.index(score_marker) + len(score_marker)
    score_end = paragraph.index(".", score_start)
    stale_score = paragraph[:score_start] + "CHI 99 – CAR 0" + paragraph[score_end:]
    assert not stale_score.startswith(prefix)

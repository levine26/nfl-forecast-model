from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_v09d import (
    INTERACTION_COLUMNS,
    add_predeclared_matchup_interactions,
    matchup_interaction_columns,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "home_pass_epa_ewma": [0.20],
            "away_pass_epa_ewma": [0.10],
            "home_def_pass_epa_allowed_ewma": [-0.05],
            "away_def_pass_epa_allowed_ewma": [0.15],
            "home_rush_epa_ewma": [0.04],
            "away_rush_epa_ewma": [-0.02],
            "home_def_rush_epa_allowed_ewma": [0.01],
            "away_def_rush_epa_allowed_ewma": [0.06],
            "home_off_epa_ewma": [0.12],
            "away_off_epa_ewma": [0.03],
            "home_def_epa_allowed_ewma": [-0.02],
            "away_def_epa_allowed_ewma": [0.09],
            "home_success_rate_ewma": [0.48],
            "away_success_rate_ewma": [0.42],
            "home_def_success_allowed_ewma": [0.39],
            "away_def_success_allowed_ewma": [0.46],
        }
    )


def test_exact_four_predeclared_interactions_and_formulas():
    out = add_predeclared_matchup_interactions(_frame())
    assert matchup_interaction_columns(out) == INTERACTION_COLUMNS
    assert len(INTERACTION_COLUMNS) == 4
    row = out.iloc[0]
    assert np.isclose(row.diff_matchup_interaction_pass, 0.20 * 0.15 - 0.10 * -0.05)
    assert np.isclose(row.diff_matchup_interaction_rush, 0.04 * 0.06 - -0.02 * 0.01)
    assert np.isclose(row.diff_matchup_interaction_overall_epa, 0.12 * 0.09 - 0.03 * -0.02)
    assert np.isclose(row.diff_matchup_interaction_success, 0.48 * 0.46 - 0.42 * 0.39)


def test_missing_constituent_fails_closed():
    frame = _frame().drop(columns=["away_def_pass_epa_allowed_ewma"])
    with pytest.raises(ValueError, match="constituents unavailable"):
        add_predeclared_matchup_interactions(frame)


def test_undeclared_interaction_fails_closed():
    out = add_predeclared_matchup_interactions(_frame())
    out["diff_matchup_interaction_extra"] = 1.0
    with pytest.raises(RuntimeError, match="Undeclared"):
        matchup_interaction_columns(out)


def test_feature_builder_does_not_require_outcomes_or_market():
    frame = _frame()
    assert "home_win" not in frame.columns
    assert "market_home_prob" not in frame.columns
    out = add_predeclared_matchup_interactions(frame)
    assert out[INTERACTION_COLUMNS].notna().all().all()


def test_production_modules_do_not_import_v09d():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden = ("challenger_v09d", "run_challenger_v09d")
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(token in imported for imported in imports for token in forbidden)

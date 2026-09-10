from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from nfl_forecast.challenger_v09a import (
    HISTORICAL_END,
    TARGET_SEASONS,
    _assert_selection_data_contract,
    _historical_source,
)


def test_v09a_target_seasons_are_pre_2026_only():
    assert TARGET_SEASONS == (2022, 2023, 2024, 2025)
    assert HISTORICAL_END == 2025


def test_selection_contract_rejects_2026_row_even_without_outcome():
    frame = pd.DataFrame(
        {
            "season": [2025, 2026],
            "home_win": [1.0, None],
        }
    )
    with pytest.raises(ValueError, match="post-2025"):
        _assert_selection_data_contract(frame)


def test_selection_contract_accepts_historical_rows():
    frame = pd.DataFrame(
        {
            "season": [2022, 2023, 2024, 2025],
            "home_win": [1.0, 0.0, 1.0, 0.0],
        }
    )
    _assert_selection_data_contract(frame)


def test_advanced_source_is_hard_capped_at_2025_when_season_is_available():
    source = pd.DataFrame({"season": [2024, 2025, 2026], "value": [1, 2, 3]})
    filtered = _historical_source(source)
    assert filtered is not None
    assert filtered.season.tolist() == [2024, 2025]
    assert filtered.value.tolist() == [1, 2]


def test_production_prediction_modules_do_not_import_v09a_player_state():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden = ("challenger_v09a", "player_state_research")
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(token in imported for imported in imports for token in forbidden), (
            filename,
            imports,
        )

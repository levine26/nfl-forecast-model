from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_historical import build_historical_challenger_frame
from nfl_forecast.market_residual_research import DEFAULT_L2, fit_offset_logistic


def _synthetic_training(n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(26)
    x = rng.normal(size=n)
    market = np.full(n, 0.5)
    probability = 1.0 / (1.0 + np.exp(-(0.7 * x)))
    y = rng.binomial(1, probability)
    return pd.DataFrame(
        {
            "season": np.repeat([2018, 2019, 2020], n // 3),
            "home_win": y,
            "market_home_prob": market,
            "football_x": x,
        }
    )


def test_initial_market_residual_penalty_is_precommitted():
    assert DEFAULT_L2 == 5.0


def test_offset_model_is_deterministic_and_uses_fixed_market_offset():
    frame = _synthetic_training()
    model_a = fit_offset_logistic(frame, ["football_x"], l2=DEFAULT_L2)
    model_b = fit_offset_logistic(frame, ["football_x"], l2=DEFAULT_L2)
    assert np.allclose(model_a.coefficients, model_b.coefficients)
    pred = model_a.predict(frame.iloc[:20], frame.market_home_prob.iloc[:20])
    assert np.isfinite(pred).all()
    assert ((pred > 0) & (pred < 1)).all()
    assert model_a.coefficients[1] > 0


def test_historical_builder_refuses_2026_selection_horizon_before_loading_data():
    with pytest.raises(ValueError, match="may not exceed 2025"):
        build_historical_challenger_frame(end_season=2026)


def test_production_modules_do_not_import_market_residual_research():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any("market_residual_research" in imported for imported in imports)

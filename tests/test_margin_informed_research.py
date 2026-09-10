from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.margin_informed_research import (
    MAPPER_C,
    RIDGE_ALPHA,
    season_forward_margin_informed,
)


def _synthetic_history() -> tuple[pd.DataFrame, list[str]]:
    rng = np.random.default_rng(81)
    rows: list[dict] = []
    for season in range(2012, 2023):
        for game in range(100):
            x1 = rng.normal()
            x2 = rng.normal()
            margin = 5.0 * x1 - 2.0 * x2 + rng.normal(scale=11.0)
            rows.append(
                {
                    "game_id": f"{season}_{game}",
                    "season": season,
                    "week": 1 + game % 18,
                    "x1": x1,
                    "x2": x2,
                    "margin": margin,
                    "home_win": float(margin > 0),
                }
            )
    frame = pd.DataFrame(rows)
    return frame, ["x1", "x2"]


def test_precommitted_margin_hyperparameters_are_fixed():
    assert RIDGE_ALPHA == 20.0
    assert MAPPER_C == 1000.0


def test_margin_predictions_use_only_prior_season_outcomes():
    frame, features = _synthetic_history()
    result = season_forward_margin_informed(frame, features, target_seasons=[2022])
    predictions = result.predictions
    assert (predictions["margin_training_max_season"] < predictions["season"]).all()
    assert (predictions["calibration_max_season"] < predictions["season"]).all()
    assert int(result.calibration_oof["season"].max()) < 2022
    assert (result.calibration_oof["margin_training_max_season"] < result.calibration_oof["season"]).all()


def test_target_season_outcomes_cannot_change_target_predictions():
    frame, features = _synthetic_history()
    original = season_forward_margin_informed(frame, features, target_seasons=[2022]).predictions
    mutated = frame.copy()
    mask = mutated["season"].eq(2022)
    mutated.loc[mask, "margin"] = -mutated.loc[mask, "margin"] + 100.0
    mutated.loc[mask, "home_win"] = 1.0 - mutated.loc[mask, "home_win"]
    changed = season_forward_margin_informed(mutated, features, target_seasons=[2022]).predictions
    assert np.allclose(original["predicted_margin"], changed["predicted_margin"])
    assert np.allclose(original["probability"], changed["probability"])


def test_production_modules_do_not_import_margin_research():
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
        assert not any("margin_informed_research" in imported for imported in imports)

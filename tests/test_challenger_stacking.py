from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_stacking import STACK_C, build_chronological_logit_stack


def _oof_frame() -> pd.DataFrame:
    rows = []
    index = 0
    rng = np.random.default_rng(20260910)
    for season in range(2018, 2026):
        for game in range(80):
            market = float(np.clip(0.50 + 0.18 * np.sin((game + season) / 7.0), 0.08, 0.92))
            pure = float(np.clip(market + 0.08 * np.cos((2 * game + season) / 11.0), 0.05, 0.95))
            latent = 0.72 * np.log(market / (1.0 - market)) + 0.18 * np.log(pure / (1.0 - pure))
            probability = 1.0 / (1.0 + np.exp(-latent))
            home_win = int(rng.random() < probability)
            rows.append(
                {
                    "index": index,
                    "season": season,
                    "home_win": home_win,
                    "market_prob": market,
                    "pure_prob": pure,
                }
            )
            index += 1
    return pd.DataFrame(rows).set_index("index")


def test_target_season_outcomes_cannot_change_target_predictions():
    base = _oof_frame()
    changed = base.copy()
    changed.loc[changed.season.eq(2023), "home_win"] = 1 - changed.loc[
        changed.season.eq(2023), "home_win"
    ]

    left = build_chronological_logit_stack(base).predictions
    right = build_chronological_logit_stack(changed).predictions
    left_2023 = left[left.season.eq(2023)].stack_probability
    right_2023 = right[right.season.eq(2023)].stack_probability
    np.testing.assert_allclose(left_2023.to_numpy(), right_2023.to_numpy(), rtol=0, atol=1e-12)


def test_later_season_can_learn_from_completed_prior_target_season():
    base = _oof_frame()
    changed = base.copy()
    changed.loc[changed.season.eq(2023), "home_win"] = 1 - changed.loc[
        changed.season.eq(2023), "home_win"
    ]
    left = build_chronological_logit_stack(base).predictions
    right = build_chronological_logit_stack(changed).predictions
    assert not np.allclose(
        left[left.season.eq(2024)].stack_probability.to_numpy(),
        right[right.season.eq(2024)].stack_probability.to_numpy(),
    )


def test_fixed_two_input_architecture_and_regularization():
    result = build_chronological_logit_stack(_oof_frame())
    assert len(result.coefficients) == 4
    assert result.coefficients["C"].eq(STACK_C).all()
    assert set(result.coefficients.columns) == {
        "season",
        "training_games",
        "training_first_season",
        "training_last_season",
        "intercept",
        "market_logit_coefficient",
        "v08_logit_coefficient",
        "C",
    }
    assert result.predictions.stack_probability.between(0.0, 1.0).all()


def test_stacking_hard_rejects_2026_outcomes():
    frame = _oof_frame()
    extra = frame.iloc[:10].copy()
    extra["season"] = 2026
    combined = pd.concat([frame, extra])
    with pytest.raises(ValueError, match="after 2025"):
        build_chronological_logit_stack(combined)


def test_production_modules_do_not_import_stacking_research():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden = ("challenger_stacking", "run_challenger_stacking")
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(token in imported for imported in imports for token in forbidden)

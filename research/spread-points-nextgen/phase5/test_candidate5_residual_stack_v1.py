from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).with_name("candidate5_residual_stack_v1.py")
SPEC = importlib.util.spec_from_file_location("candidate5_residual_stack_v1", MODULE_PATH)
assert SPEC and SPEC.loader
c5 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c5)


def _cfg() -> dict:
    return {
        "lambda_grid": [0.1, 1.0, 10.0, 100.0],
        "default_lambda": 100.0,
        "lambda_tie_tolerance_log_loss": 0.0001,
        "minimum_meta_training_rows": 250,
    }


def _synthetic() -> pd.DataFrame:
    rng = np.random.default_rng(20260922)
    rows = []
    for season in (2022, 2023, 2024):
        for i in range(260):
            fst = float(rng.uniform(0.25, 0.75))
            y = int(rng.random() < fst)
            rows.append(
                {
                    "season": season,
                    "week": 1 + (i % 18),
                    "game_id": f"{season}_{i:03d}",
                    "home_win": y,
                    "fst_prob": fst,
                    "a0_logit_delta": rng.normal(0, 0.2),
                    "a0_expected_margin": rng.normal(0, 7),
                    "a0_score_uncertainty": rng.uniform(10, 18),
                    "a0_offense_strength_diff": rng.normal(),
                    "a0_defense_strength_diff": rng.normal(),
                }
            )
    return pd.DataFrame(rows)


def test_primary_feature_family_is_football_only():
    assert "market_logit_delta" not in c5.PRIMARY_FEATURES
    assert "c0_market_margin" not in c5.PRIMARY_FEATURES
    assert set(c5.A0_FEATURES).issubset(c5.PRIMARY_FEATURES)
    assert set(c5.B0_FEATURES).issubset(c5.PRIMARY_FEATURES)
    assert c5.MARKET_HORIZON == "historical_closing_late_benchmark_exact_horizon_opaque"


def test_strict_winner_rule():
    assert c5._strict_pick([0.49, 0.5, 0.5000001]).tolist() == [0, 0, 1]


def test_winner_change_identity():
    frame = pd.DataFrame(
        {
            "fst_prob": [0.6, 0.6, 0.4, 0.4],
            "home_win": [1, 0, 1, 0],
        }
    )
    candidate = np.array([0.6, 0.4, 0.6, 0.4])
    result = c5.evaluate_probs(frame, candidate)
    assert result["changed_winners"] == 2
    assert result["candidate_only_correct"] == 1
    assert result["fst_only_correct"] == 1
    assert result["accuracy_delta"] == pytest.approx(result["mechanism_identity_delta"])


def test_development_chronology_and_2022_fallback():
    frame = _synthetic()
    pred, fits, tuning = c5.development_predictions(frame, "FST_PLUS_A0", _cfg())
    mask_2022 = frame["season"].eq(2022)
    assert np.allclose(pred.loc[mask_2022], frame.loc[mask_2022, "fst_prob"])

    by_target = {row["target_season"]: row for row in fits}
    assert by_target[2022]["fallback"] is True
    assert by_target[2022]["training_seasons"] == []
    assert by_target[2023]["training_seasons"] == [2022]
    assert by_target[2023]["selected_lambda"] == 100.0
    assert by_target[2024]["training_seasons"] == [2022, 2023]
    assert all(max(row["training_seasons"], default=0) < row["target_season"] for row in fits)
    assert tuning[0]["target_season"] == 2024
    assert tuning[0]["validation_seasons"] == [2023]


def test_classification_rule_is_frozen_and_not_significance_gated():
    eligible = {
        "changed_winners": 10,
        "changed_winner_accuracy": 0.6,
        "accuracy_delta": 0.01,
        "brier_delta": -0.001,
        "log_loss_delta": -0.001,
    }
    assert c5.classification(eligible) == "ELIGIBLE_FOR_PROSPECTIVE_PHASE6_SHADOW_VALIDATION"
    negative = dict(eligible, accuracy_delta=0.0)
    assert c5.classification(negative) == "REJECTED"
    probability_tradeoff = dict(eligible, brier_delta=0.001)
    assert c5.classification(probability_tradeoff) == "INCONCLUSIVE_BUT_COHERENT"

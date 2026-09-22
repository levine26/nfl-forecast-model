from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).with_name("run_baseline_audit.py")
spec = importlib.util.spec_from_file_location("phase1_baseline_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


def test_numeric_metrics_exact_values():
    actual = pd.Series([1.0, 3.0, 5.0])
    pred = pd.Series([2.0, 2.0, 5.0])
    result = audit._numeric_metrics(actual, pred)
    assert result["games"] == 3
    assert np.isclose(result["mae"], 2.0 / 3.0)
    assert np.isclose(result["mean_signed_error_actual_minus_pred"], 0.0)


def test_probability_metrics_threshold_and_scores():
    y = pd.Series([1, 0, 1, 0])
    p = pd.Series([0.8, 0.2, 0.6, 0.4])
    result = audit._probability_metrics(y, p)
    assert result["games"] == 4
    assert result["winner_accuracy"] == 1.0
    assert 0.0 < result["brier"] < 0.25
    assert result["log_loss"] > 0.0


def test_block_bootstrap_error_delta_is_deterministic_and_oriented_model_minus_market():
    frame = pd.DataFrame({
        "season": [2022, 2022, 2023, 2023],
        "week": [1, 2, 1, 2],
    })
    model = pd.Series([2.0, 3.0, 4.0, 5.0])
    market = pd.Series([1.0, 2.0, 3.0, 4.0])
    first = audit._block_bootstrap_error_delta(frame, model, market, samples=200, seed=26)
    second = audit._block_bootstrap_error_delta(frame, model, market, samples=200, seed=26)
    assert first == second
    assert np.isclose(first["model_minus_market_mae"], 1.0)
    assert first["games"] == 4
    assert first["blocks"] == 4


def test_cover_probability_respects_home_margin_orientation():
    # A home-margin mean above the market-implied home margin must imply >50% home cover.
    p = audit._cover_probability(mean=7.0, sigma=10.0, threshold=3.0)
    assert p > 0.5

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[3] / "research" / "props" / "v21" / "diagnose_week2_miss.py"
SPEC = importlib.util.spec_from_file_location("diagnose_week2_miss", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(i: int, actual: float, model: float, market: float, model_p: float, market_p: float) -> dict:
    return {
        "forecast_id": f"f{i}",
        "graded": True,
        "actual_result": actual,
        "model_mean": model,
        "fair_line": model + 1.0,
        "market_line": market,
        "model_p_over": model_p,
        "market_p_over": market_p,
        "prop_type": "receiving_yards",
        "position": "WR",
        "role_state": "STARTER_EXPECTED",
        "availability_state": "ACTIVE",
        "workload_state": "STABLE",
        "market_liquidity_bucket": "MULTI_BOOK",
        "forecast_horizon_bin": "T120_OR_EARLIER",
    }


def test_prepare_matched_scores_projection_probability_and_pushes() -> None:
    frame = pd.DataFrame(
        [
            _row(1, 80.0, 70.0, 75.0, 0.70, 0.55),
            _row(2, 60.0, 70.0, 65.0, 0.70, 0.55),
            _row(3, 65.0, 70.0, 65.0, 0.70, 0.55),
        ]
    )
    projection, probability = MODULE.prepare_matched(frame)

    assert len(projection) == 3
    assert len(probability) == 2
    assert projection["fair_mae_delta"].mean() > 0
    assert projection["model_mean_mae_delta"].mean() > 0
    assert probability["model_confidence"].between(0.5, 1.0).all()
    assert probability["model_brier"].notna().all()
    assert probability["model_log_loss"].notna().all()


def test_group_summary_is_descriptive_and_thresholded() -> None:
    frame = pd.DataFrame(
        [_row(i, 80.0 if i % 2 else 60.0, 70.0, 65.0, 0.70, 0.55) for i in range(12)]
    )
    projection, probability = MODULE.prepare_matched(frame)
    table = MODULE.summarize_group(projection, probability, "prop_type", min_n=10)

    assert len(table) == 1
    row = table.iloc[0]
    assert row["projection_n"] == 12
    assert row["probability_n"] == 12
    assert "model_confidence_gap" in table.columns
    assert "fair_line_mae_delta" in table.columns
    assert "model_mean_mae_delta" in table.columns

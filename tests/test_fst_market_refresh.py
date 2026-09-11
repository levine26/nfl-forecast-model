from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.fst_production import (
    CANDIDATE_ID,
    frozen_fst_probability,
    legacy_final_home_probability,
    load_fst_artifact,
)
from scripts.refresh_market import _rescore_winner_probability


def _frame(*, include_fst_pure: bool = True) -> pd.DataFrame:
    frame = pd.DataFrame({
        "pure_home_prob": [0.60, 0.40],
        "market_home_prob": [0.65, np.nan],
        "expected_margin": [2.0, -1.0],
        "model_disagreement": [0.03, 0.04],
    })
    if include_fst_pure:
        frame["fst_pure_home_prob"] = [0.58, 0.42]
    return frame


def test_market_refresh_rescores_with_frozen_fst_and_preserves_legacy():
    p = _frame()
    _rescore_winner_probability(p)
    artifact = load_fst_artifact()

    expected_fst = frozen_fst_probability(
        np.array([0.65]), np.array([0.58]), artifact
    )[0]
    expected_legacy = legacy_final_home_probability(
        pd.Series([0.60, 0.40]), pd.Series([0.65, np.nan])
    )

    assert p.loc[0, "final_home_prob"] == pytest.approx(expected_fst, abs=1e-15)
    assert p.loc[1, "final_home_prob"] == pytest.approx(0.40, abs=0.0)
    np.testing.assert_array_equal(
        p["legacy_final_home_prob"].to_numpy(), expected_legacy.to_numpy()
    )
    assert set(p["final_probability_strategy"].astype(str)) == {CANDIDATE_ID}
    assert p["fst_fallback"].tolist() == [False, True]
    assert p.loc[1, "fst_fallback_reason"] == "market_missing"


def test_market_refresh_never_applies_fst_coefficients_to_legacy_pure():
    p = _frame(include_fst_pure=False)
    expected = legacy_final_home_probability(
        p["pure_home_prob"], p["market_home_prob"]
    )
    _rescore_winner_probability(p)

    np.testing.assert_array_equal(p["final_home_prob"].to_numpy(), expected.to_numpy())
    assert p["fst_fallback"].all()
    assert set(p["fst_fallback_reason"].astype(str)) == {
        "fst_nested_pure_not_materialized"
    }

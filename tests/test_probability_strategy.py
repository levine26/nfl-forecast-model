from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.probability_strategy import (
    CURRENT_PRODUCTION,
    DEFAULT_FINAL_PROBABILITY_STRATEGY,
    FST_STACK_V1,
    FSTStackParameters,
    final_home_probability,
)


def _legacy_current_production(pure: pd.Series, market: pd.Series) -> pd.Series:
    legacy = pure.copy()
    has_market = market.notna()
    legacy.loc[has_market] = 0.75 * pure.loc[has_market] + 0.25 * market.loc[has_market]
    return legacy


def test_default_strategy_is_current_production_and_value_identical_to_legacy_expression():
    pure = pd.Series([0.62, 0.48, 0.73, 0.51], index=["g1", "g2", "g3", "g4"], name="pure_home_prob")
    market = pd.Series([0.58, np.nan, 0.66, 0.49], index=pure.index, name="market_home_prob")
    expected = _legacy_current_production(pure, market)
    actual = final_home_probability(pure, market)

    assert DEFAULT_FINAL_PROBABILITY_STRATEGY == CURRENT_PRODUCTION
    pd.testing.assert_series_equal(actual, expected, check_exact=True)
    assert actual.to_csv(index=True) == expected.to_csv(index=True)


def test_named_current_production_is_identical_to_default():
    pure = pd.Series([0.2, 0.5, 0.8])
    market = pd.Series([0.3, 0.4, 0.9])
    default = final_home_probability(pure, market)
    named = final_home_probability(pure, market, strategy=CURRENT_PRODUCTION)
    pd.testing.assert_series_equal(default, named, check_exact=True)


def test_fst_stack_is_fail_closed_without_explicit_enable_and_parameters():
    pure = pd.Series([0.55])
    market = pd.Series([0.60])
    params = FSTStackParameters(
        intercept=0.01,
        market_logit_coefficient=1.1,
        pure_logit_coefficient=-0.1,
    )
    with pytest.raises(RuntimeError, match="disabled"):
        final_home_probability(
            pure, market, strategy=FST_STACK_V1, fst_parameters=params
        )
    with pytest.raises(RuntimeError, match="requires explicit frozen stack parameters"):
        final_home_probability(
            pure, market, strategy=FST_STACK_V1, experimental_enabled=True
        )


def test_fst_stack_requires_complete_market_and_matches_fixed_formula_when_explicitly_enabled():
    pure = pd.Series([0.55, 0.45], index=["a", "b"])
    market = pd.Series([0.60, 0.40], index=pure.index)
    params = FSTStackParameters(
        intercept=0.02,
        market_logit_coefficient=1.15,
        pure_logit_coefficient=-0.10,
    )
    actual = final_home_probability(
        pure,
        market,
        strategy=FST_STACK_V1,
        experimental_enabled=True,
        fst_parameters=params,
    )
    market_logit = np.log(market.to_numpy() / (1.0 - market.to_numpy()))
    pure_logit = np.log(pure.to_numpy() / (1.0 - pure.to_numpy()))
    score = 0.02 + 1.15 * market_logit - 0.10 * pure_logit
    expected = 1.0 / (1.0 + np.exp(-score))
    assert np.allclose(actual.to_numpy(), expected)

    with pytest.raises(RuntimeError, match="requires market probability"):
        final_home_probability(
            pure,
            pd.Series([0.60, np.nan], index=pure.index),
            strategy=FST_STACK_V1,
            experimental_enabled=True,
            fst_parameters=params,
        )


def test_unknown_strategy_and_index_mismatch_fail_closed():
    pure = pd.Series([0.55], index=["a"])
    market = pd.Series([0.60], index=["a"])
    with pytest.raises(ValueError, match="Unknown final probability strategy"):
        final_home_probability(pure, market, strategy="future_unregistered_strategy")
    with pytest.raises(ValueError, match="identical indexes"):
        final_home_probability(pure, pd.Series([0.60], index=["b"]))

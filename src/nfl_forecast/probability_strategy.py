from __future__ import annotations

"""Legacy/experimental probability adapter retained for compatibility and rollback tests.

Official production winner scoring now lives in ``fst_production.py`` because frozen
F-ST must consume the distinct validated nested ``fst_pure_home_prob`` rather than the
legacy pipeline PURE accepted by this older adapter.  The default here intentionally
remains the exact pre-F-ST 75/25 expression for downstream compatibility; it is not the
selector for the official production path.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

CURRENT_PRODUCTION = "current_production"
FST_STACK_V1 = "fst_stack_v1"
DEFAULT_FINAL_PROBABILITY_STRATEGY = CURRENT_PRODUCTION
EPS = 1e-6


@dataclass(frozen=True)
class FSTStackParameters:
    intercept: float
    market_logit_coefficient: float
    pure_logit_coefficient: float


def _logit(values: pd.Series | np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(probability / (1.0 - probability))


def _current_production(
    pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
) -> pd.Series:
    """Preserve the exact pre-F-ST 75% legacy PURE / 25% MARKET semantics."""
    result = pure_home_prob.copy()
    has_market = market_home_prob.notna()
    result.loc[has_market] = (
        0.75 * pure_home_prob.loc[has_market]
        + 0.25 * market_home_prob.loc[has_market]
    )
    return result


def _fst_stack_v1(
    pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
    parameters: FSTStackParameters,
) -> pd.Series:
    """Historical single-PURE experiment helper; not the official F-ST production path."""
    if market_home_prob.isna().any():
        raise RuntimeError("fst_stack_v1 requires market probability for every scored game")
    score = (
        float(parameters.intercept)
        + float(parameters.market_logit_coefficient) * _logit(market_home_prob)
        + float(parameters.pure_logit_coefficient) * _logit(pure_home_prob)
    )
    probability = np.clip(1.0 / (1.0 + np.exp(-score)), EPS, 1.0 - EPS)
    return pd.Series(probability, index=pure_home_prob.index, name=pure_home_prob.name)


def final_home_probability(
    pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
    *,
    strategy: str = DEFAULT_FINAL_PROBABILITY_STRATEGY,
    experimental_enabled: bool = False,
    fst_parameters: FSTStackParameters | None = None,
) -> pd.Series:
    """Compatibility adapter for legacy and historical experimental callers.

    This function deliberately cannot represent official F-ST production because its
    ``pure_home_prob`` argument is the legacy PURE. Official scoring must use
    ``fst_production.score_official_fst`` with the separately materialized nested PURE.
    """
    if not pure_home_prob.index.equals(market_home_prob.index):
        raise ValueError("PURE and market probabilities must have identical indexes")

    if strategy == CURRENT_PRODUCTION:
        return _current_production(pure_home_prob, market_home_prob)
    if strategy != FST_STACK_V1:
        raise ValueError(f"Unknown final probability strategy: {strategy!r}")
    if not experimental_enabled:
        raise RuntimeError("fst_stack_v1 is disabled unless explicitly enabled for an authorized run")
    if fst_parameters is None:
        raise RuntimeError("fst_stack_v1 requires explicit frozen stack parameters")
    return _fst_stack_v1(pure_home_prob, market_home_prob, fst_parameters)

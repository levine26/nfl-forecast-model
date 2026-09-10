from __future__ import annotations

"""Production winner-probability strategy router.

Rollback is intentionally one configuration-line change: set
``ACTIVE_PRODUCTION_STRATEGY`` to ``LEGACY_PRODUCTION_STRATEGY``. The underlying F-ST
and legacy counterfactuals continue to be computed and persisted so switching regimes
never rewrites prior official locks or erases evaluation evidence.
"""

from dataclasses import replace

import pandas as pd

from .fst_production import (
    CANDIDATE_ID,
    FSTArtifact,
    FSTScoreResult,
    score_official_fst,
)

LEGACY_PRODUCTION_STRATEGY = "current_production_75_25"
ACTIVE_PRODUCTION_STRATEGY = CANDIDATE_ID


def model_version_for_strategy(strategy: str) -> str:
    if strategy == CANDIDATE_ID:
        return "0.9.0-fst"
    if strategy == LEGACY_PRODUCTION_STRATEGY:
        return "0.9.0-legacy-rollback"
    raise RuntimeError(f"Unknown production probability strategy: {strategy!r}")


def score_for_strategy(
    legacy_pure_home_prob: pd.Series,
    fst_pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
    artifact: FSTArtifact,
    *,
    strategy: str = ACTIVE_PRODUCTION_STRATEGY,
) -> FSTScoreResult:
    scored = score_official_fst(
        legacy_pure_home_prob,
        fst_pure_home_prob,
        market_home_prob,
        artifact,
    )
    if strategy == CANDIDATE_ID:
        return scored
    if strategy == LEGACY_PRODUCTION_STRATEGY:
        return replace(scored, final_home_prob=scored.legacy_final_home_prob.copy())
    raise RuntimeError(f"Unknown production probability strategy: {strategy!r}")

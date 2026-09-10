from __future__ import annotations

"""Frozen production scoring boundary for F-ST-01.

The coefficient artifact is pinned in-package and validated before scoring. Missing or
non-finite market values fall back per-game to exact legacy LevLine behavior; artifact,
training-digest, or nested-PURE integrity failures remain fatal.

Rollback is deliberately one line: set ``ACTIVE_PRODUCTION_STRATEGY`` to
``LEGACY_PRODUCTION_STRATEGY``. F-ST and its legacy counterfactual continue to be
computed and persisted, so rollback does not erase or rewrite prior official locks.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CANDIDATE_ID = "F-ST-01-FROZEN-2026"
LEGACY_PRODUCTION_STRATEGY = "current_production_75_25"
ACTIVE_PRODUCTION_STRATEGY = CANDIDATE_ID
FINAL_PROBABILITY_STRATEGY = ACTIVE_PRODUCTION_STRATEGY
MODEL_VERSION = (
    "0.9.0-fst"
    if ACTIVE_PRODUCTION_STRATEGY == CANDIDATE_ID
    else "0.9.0-legacy-rollback"
)
EPS = 1e-6
ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "F-ST-01-FROZEN-2026.json"
EXPECTED_TRAINING_SHA256 = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
EXPECTED_INTERCEPT = -0.06954359363166639
EXPECTED_MARKET_COEF = 1.1939087340527093
EXPECTED_PURE_COEF = -0.19342747983803402
EXPECTED_TRAINING_GAMES = 1615
EXPECTED_FIRST_SEASON = 2020
EXPECTED_LAST_SEASON = 2025


@dataclass(frozen=True)
class FSTArtifact:
    candidate_id: str
    intercept: float
    market_logit_coefficient: float
    pure_logit_coefficient: float
    training_games: int
    training_first_season: int
    training_last_season: int
    training_data_sha256: str
    C: float
    penalty: str
    solver: str
    max_iter: int
    target_season: int
    training_cutoff: int
    outcomes_2026_used: int
    freeze_timestamp_utc: str
    freeze_implementation_sha: str


@dataclass(frozen=True)
class FSTScoreResult:
    final_home_prob: pd.Series
    legacy_final_home_prob: pd.Series
    fst_fallback: pd.Series
    fst_fallback_reason: pd.Series
    fst_vs_market_delta: pd.Series
    fst_vs_legacy_delta: pd.Series
    market_eligible: pd.Series


def _exact(value, expected, label: str) -> None:
    if value != expected:
        raise RuntimeError(f"Frozen F-ST artifact {label} mismatch: {value!r} != {expected!r}")


def load_fst_artifact(path: str | Path = ARTIFACT_PATH) -> FSTArtifact:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "candidate_id", "production_promotion_authorized", "target_season", "training_cutoff",
        "2026_outcomes_used_in_fitting", "intercept", "market_logit_coefficient",
        "pure_logit_coefficient", "training_games", "training_first_season",
        "training_last_season", "training_data_sha256", "C", "penalty", "solver",
        "max_iter", "freeze_timestamp_utc", "freeze_implementation_sha",
    }
    missing = required - set(payload)
    if missing:
        raise RuntimeError(f"Frozen F-ST artifact missing fields: {sorted(missing)}")
    _exact(payload["candidate_id"], CANDIDATE_ID, "candidate_id")
    _exact(payload["production_promotion_authorized"], True, "promotion authorization")
    _exact(float(payload["intercept"]), EXPECTED_INTERCEPT, "intercept")
    _exact(float(payload["market_logit_coefficient"]), EXPECTED_MARKET_COEF, "market coefficient")
    _exact(float(payload["pure_logit_coefficient"]), EXPECTED_PURE_COEF, "PURE coefficient")
    _exact(int(payload["training_games"]), EXPECTED_TRAINING_GAMES, "training_games")
    _exact(int(payload["training_first_season"]), EXPECTED_FIRST_SEASON, "training_first_season")
    _exact(int(payload["training_last_season"]), EXPECTED_LAST_SEASON, "training_last_season")
    _exact(payload["training_data_sha256"], EXPECTED_TRAINING_SHA256, "training digest")
    _exact(float(payload["C"]), 1.0, "C")
    _exact(str(payload["penalty"]), "l2", "penalty")
    _exact(str(payload["solver"]), "lbfgs", "solver")
    _exact(int(payload["max_iter"]), 3000, "max_iter")
    _exact(int(payload["target_season"]), 2026, "target_season")
    _exact(int(payload["training_cutoff"]), 2025, "training_cutoff")
    _exact(int(payload["2026_outcomes_used_in_fitting"]), 0, "2026 outcomes used")
    if int(payload["training_last_season"]) > 2025 or int(payload["training_cutoff"]) > 2025:
        raise RuntimeError("Frozen F-ST artifact training cutoff exceeds 2025")
    return FSTArtifact(
        candidate_id=str(payload["candidate_id"]),
        intercept=float(payload["intercept"]),
        market_logit_coefficient=float(payload["market_logit_coefficient"]),
        pure_logit_coefficient=float(payload["pure_logit_coefficient"]),
        training_games=int(payload["training_games"]),
        training_first_season=int(payload["training_first_season"]),
        training_last_season=int(payload["training_last_season"]),
        training_data_sha256=str(payload["training_data_sha256"]),
        C=float(payload["C"]),
        penalty=str(payload["penalty"]),
        solver=str(payload["solver"]),
        max_iter=int(payload["max_iter"]),
        target_season=int(payload["target_season"]),
        training_cutoff=int(payload["training_cutoff"]),
        outcomes_2026_used=int(payload["2026_outcomes_used_in_fitting"]),
        freeze_timestamp_utc=str(payload["freeze_timestamp_utc"]),
        freeze_implementation_sha=str(payload["freeze_implementation_sha"]),
    )


def canonical_training_hash(frame: pd.DataFrame) -> str:
    required = {"season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"F-ST training digest frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["season_num"] = pd.to_numeric(work["season"], errors="coerce")
    if work["season_num"].dropna().ge(2026).any():
        raise RuntimeError("F-ST digest validation refuses 2026-or-later outcomes")
    work["home_win_num"] = pd.to_numeric(work["home_win"], errors="coerce")
    work["market_prob_num"] = pd.to_numeric(work["market_prob"], errors="coerce")
    work["pure_prob_num"] = pd.to_numeric(work["pure_prob"], errors="coerce")
    work = work[
        work["season_num"].notna()
        & work["home_win_num"].notna()
        & work["market_prob_num"].notna()
        & work["pure_prob_num"].notna()
        & work["season_num"].le(2025)
    ].copy()
    canonical = work[["season_num", "home_win_num", "market_prob_num", "pure_prob_num"]].copy()
    canonical = canonical.sort_values(
        ["season_num", "market_prob_num", "pure_prob_num", "home_win_num"],
        kind="mergesort",
    )
    text = canonical.to_csv(index=False, float_format="%.12g", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_training_identity(frame: pd.DataFrame, artifact: FSTArtifact) -> str:
    digest = canonical_training_hash(frame)
    usable = frame.dropna(subset=["season", "home_win", "market_prob", "pure_prob"]).copy()
    if len(usable) != artifact.training_games:
        raise RuntimeError(
            "Frozen F-ST training game count changed; refusing to use pinned coefficients"
        )
    if digest != artifact.training_data_sha256:
        raise RuntimeError(
            f"Frozen F-ST historical training digest changed: {digest} != {artifact.training_data_sha256}"
        )
    season = pd.to_numeric(usable["season"], errors="coerce")
    if int(season.min()) != artifact.training_first_season:
        raise RuntimeError("Frozen F-ST training first season changed")
    if int(season.max()) != artifact.training_last_season:
        raise RuntimeError("Frozen F-ST training last season changed")
    return digest


def _logit(values) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def frozen_fst_probability(
    market_probability,
    fst_pure_probability,
    artifact: FSTArtifact,
) -> np.ndarray:
    market = np.asarray(market_probability, dtype=float)
    pure = np.asarray(fst_pure_probability, dtype=float)
    if market.shape != pure.shape:
        raise ValueError("F-ST market and nested PURE arrays must have identical shape")
    if not np.isfinite(market).all() or not np.isfinite(pure).all():
        raise ValueError("F-ST formula requires finite market and nested PURE probabilities")
    score = (
        artifact.intercept
        + artifact.market_logit_coefficient * _logit(market)
        + artifact.pure_logit_coefficient * _logit(pure)
    )
    return np.clip(1.0 / (1.0 + np.exp(-score)), EPS, 1.0 - EPS)


def legacy_final_home_probability(
    legacy_pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
) -> pd.Series:
    """Exact 75% legacy PURE / 25% market expression with invalid market treated absent."""
    if not legacy_pure_home_prob.index.equals(market_home_prob.index):
        raise ValueError("Legacy PURE and market indexes must match")
    pure = pd.to_numeric(legacy_pure_home_prob, errors="coerce")
    market = pd.to_numeric(market_home_prob, errors="coerce")
    if not np.isfinite(pure.to_numpy(dtype=float)).all():
        raise RuntimeError("Legacy production PURE contains a non-finite probability")
    result = pure.copy()
    usable_market = pd.Series(np.isfinite(market.to_numpy(dtype=float)), index=market.index)
    result.loc[usable_market] = (
        0.75 * pure.loc[usable_market] + 0.25 * market.loc[usable_market]
    )
    return result


def score_official_fst(
    legacy_pure_home_prob: pd.Series,
    fst_pure_home_prob: pd.Series,
    market_home_prob: pd.Series,
    artifact: FSTArtifact,
) -> FSTScoreResult:
    if ACTIVE_PRODUCTION_STRATEGY not in {CANDIDATE_ID, LEGACY_PRODUCTION_STRATEGY}:
        raise RuntimeError(
            f"Unknown production probability strategy: {ACTIVE_PRODUCTION_STRATEGY!r}"
        )
    if not (
        legacy_pure_home_prob.index.equals(fst_pure_home_prob.index)
        and legacy_pure_home_prob.index.equals(market_home_prob.index)
    ):
        raise ValueError("F-ST scoring inputs must have identical indexes")
    fst_pure = pd.to_numeric(fst_pure_home_prob, errors="coerce")
    market = pd.to_numeric(market_home_prob, errors="coerce")
    if not np.isfinite(fst_pure.to_numpy(dtype=float)).all():
        raise RuntimeError("F-ST nested PURE contains a non-finite probability")
    if ((fst_pure <= 0.0) | (fst_pure >= 1.0)).any():
        raise RuntimeError("F-ST nested PURE probability is outside (0, 1)")

    legacy = legacy_final_home_probability(legacy_pure_home_prob, market_home_prob)
    eligible = pd.Series(np.isfinite(market.to_numpy(dtype=float)), index=market.index)
    fst_candidate = legacy.copy()
    if eligible.any():
        fst_candidate.loc[eligible] = frozen_fst_probability(
            market.loc[eligible].to_numpy(dtype=float),
            fst_pure.loc[eligible].to_numpy(dtype=float),
            artifact,
        )
    final = (
        fst_candidate.copy()
        if ACTIVE_PRODUCTION_STRATEGY == CANDIDATE_ID
        else legacy.copy()
    )
    if not np.isfinite(final.to_numpy(dtype=float)).all():
        raise RuntimeError("Official probability scoring produced a non-finite probability")
    if ((final <= 0.0) | (final >= 1.0)).any():
        raise RuntimeError("Official probability is outside (0, 1)")

    missing = market.isna()
    reason = pd.Series("", index=market.index, dtype="object")
    reason.loc[~eligible & missing] = "market_missing"
    reason.loc[~eligible & ~missing] = "market_non_finite"
    fallback = ~eligible
    vs_market = pd.Series(np.nan, index=market.index, dtype=float)
    vs_market.loc[eligible] = fst_candidate.loc[eligible] - market.loc[eligible]
    vs_legacy = fst_candidate - legacy
    return FSTScoreResult(
        final_home_prob=final,
        legacy_final_home_prob=legacy,
        fst_fallback=fallback.astype(bool),
        fst_fallback_reason=reason,
        fst_vs_market_delta=vs_market,
        fst_vs_legacy_delta=vs_legacy,
        market_eligible=eligible.astype(bool),
    )

from __future__ import annotations

"""Frozen Stage-D uncertainty and evidence-synthesis primitives.

Research only.  This module does not fit, tune, calibrate, select, or rescue any
candidate.  It consumes already-frozen Q1/Q3 outer-OOF predictions and computes
the uncertainty diagnostics preregistered in ``PHASE2_STAGE_D_OPENING_RECEIPT.md``.
"""

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import beta

from nfl_forecast.challenger_ats_nextgen_q1 import QUANTILES
from nfl_forecast.challenger_ats_nextgen_q3 import LOGLOSS_FLOOR

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 26
BOOTSTRAP_ALPHA = 0.05
TARGET_SEASONS = (2022, 2023, 2024, 2025)
BLOCK_COLUMNS = ("season", "week")


@dataclass(frozen=True)
class PairedBootstrapResult:
    metric: str
    candidate: str
    reference: str
    block: str
    rows: int
    blocks: int
    samples: int
    observed_delta: float
    ci_lower: float
    ci_upper: float
    probability_better: float


@dataclass(frozen=True)
class HitRateInterval:
    arm: str
    rows: int
    wins: int
    hit_rate: float
    ci_lower: float
    ci_upper: float
    interval: str = "Clopper-Pearson"


def _validate_oof_identity(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    required = {"game_id", "season", "week"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} OOF missing identity columns: {sorted(missing)}")
    out = frame.copy()
    game_id = out["game_id"].astype("string")
    if game_id.isna().any() or game_id.str.strip().eq("").any():
        raise ValueError(f"{label} OOF contains missing/blank game_id")
    if game_id.duplicated().any():
        raise ValueError(f"{label} OOF contains duplicate game_id")
    season = pd.to_numeric(out["season"], errors="coerce")
    week = pd.to_numeric(out["week"], errors="coerce")
    if season.isna().any() or week.isna().any():
        raise ValueError(f"{label} OOF contains invalid season/week")
    seasons = tuple(sorted(season.astype(int).unique().tolist()))
    if seasons != TARGET_SEASONS:
        raise ValueError(f"{label} OOF seasons must be exactly {TARGET_SEASONS}; got {seasons}")
    out["season"] = season.astype(int)
    out["week"] = week.astype(int)
    return out


def align_q1_q3_oof(q1: pd.DataFrame, q3: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Require exact paired game identity and chronology across accepted OOF frames."""
    left = _validate_oof_identity(q1, "Q1")
    right = _validate_oof_identity(q3, "Q3")
    left_ids = set(left["game_id"].astype(str))
    right_ids = set(right["game_id"].astype(str))
    if left_ids != right_ids:
        missing_q3 = sorted(left_ids - right_ids)[:5]
        missing_q1 = sorted(right_ids - left_ids)[:5]
        raise ValueError(
            "Q1/Q3 OOF game identities differ: "
            f"missing_q3={missing_q3} missing_q1={missing_q1}"
        )
    left = left.sort_values("game_id", kind="mergesort").reset_index(drop=True)
    right = right.sort_values("game_id", kind="mergesort").reset_index(drop=True)
    if not left["game_id"].astype(str).equals(right["game_id"].astype(str)):
        raise RuntimeError("Q1/Q3 identity alignment failed after sorting")
    if not np.array_equal(left["season"].to_numpy(), right["season"].to_numpy()):
        raise ValueError("Q1/Q3 season labels differ on paired games")
    if not np.array_equal(left["week"].to_numpy(), right["week"].to_numpy()):
        raise ValueError("Q1/Q3 week labels differ on paired games")
    return left, right


def pinball_loss(y: Iterable[float], prediction: Iterable[float], tau: float) -> np.ndarray:
    if float(tau) not in QUANTILES:
        raise ValueError("Stage-D Q1 tau is outside the frozen quantile set")
    yy = np.asarray(y, dtype=float)
    pp = np.asarray(prediction, dtype=float)
    if yy.shape != pp.shape or yy.ndim != 1:
        raise ValueError("pinball inputs must be aligned one-dimensional arrays")
    if not np.isfinite(yy).all() or not np.isfinite(pp).all():
        raise ValueError("pinball inputs must be finite")
    error = yy - pp
    return np.where(error >= 0.0, float(tau) * error, (float(tau) - 1.0) * error)


def q1_row_losses(oof: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return per-game mean pinball loss for Q1 and its matching M2 null."""
    required = {"ats_residual"}
    for prefix in ("q1", "m2"):
        required.update({f"{prefix}_q_low", f"{prefix}_q_med", f"{prefix}_q_high"})
    missing = required - set(oof.columns)
    if missing:
        raise ValueError(f"Q1 OOF missing loss columns: {sorted(missing)}")
    y = pd.to_numeric(oof["ats_residual"], errors="raise").to_numpy(dtype=float)
    labels = ("low", "med", "high")
    arm_losses: dict[str, list[np.ndarray]] = {"q1": [], "m2": []}
    for label, tau in zip(labels, QUANTILES, strict=True):
        for prefix in ("q1", "m2"):
            pred = pd.to_numeric(oof[f"{prefix}_q_{label}"], errors="raise").to_numpy(dtype=float)
            arm_losses[prefix].append(pinball_loss(y, pred, float(tau)))
    q1 = np.mean(np.column_stack(arm_losses["q1"]), axis=1)
    m2 = np.mean(np.column_stack(arm_losses["m2"]), axis=1)
    return q1, m2


def _q3_probability(oof: pd.DataFrame, prefix: str) -> np.ndarray:
    columns = [f"{prefix}_p_cover", f"{prefix}_p_push", f"{prefix}_p_loss"]
    missing = set(columns) - set(oof.columns)
    if missing:
        raise ValueError(f"Q3 OOF missing probability columns: {sorted(missing)}")
    p = oof[columns].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p < 0.0).any() or (p > 1.0).any():
        raise ValueError("Q3 OOF contains invalid probabilities")
    if not np.allclose(p.sum(axis=1), 1.0, atol=1e-12, rtol=0.0):
        raise ValueError("Q3 OOF probabilities do not sum to one")
    return p


def _q3_outcome_index(oof: pd.DataFrame) -> np.ndarray:
    if "ats_outcome" not in oof.columns:
        raise ValueError("Q3 OOF missing ats_outcome")
    mapping = {"HOME_COVER": 0, "PUSH": 1, "HOME_LOSS": 2}
    outcome = oof["ats_outcome"].astype(str).map(mapping)
    if outcome.isna().any():
        raise ValueError("Q3 OOF contains unknown ATS outcome")
    return outcome.to_numpy(dtype=int)


def q3_multinomial_row_losses(oof: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    outcome = _q3_outcome_index(oof)
    q3 = _q3_probability(oof, "q3")
    m2 = _q3_probability(oof, "q3_m2")
    rows = np.arange(len(oof))
    q3_loss = -np.log(np.maximum(q3[rows, outcome], LOGLOSS_FLOOR))
    m2_loss = -np.log(np.maximum(m2[rows, outcome], LOGLOSS_FLOOR))
    return q3_loss, m2_loss


def q3_nonpush_brier_row_losses(
    oof: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    outcome = _q3_outcome_index(oof)
    q3 = _q3_probability(oof, "q3")
    m2 = _q3_probability(oof, "q3_m2")
    nonpush = outcome != 1
    actual_cover = (outcome == 0).astype(float)

    def conditional_cover(p: np.ndarray) -> np.ndarray:
        denom = p[:, 0] + p[:, 2]
        if not np.isfinite(denom).all() or (denom <= 0.0).any():
            raise ValueError("Q3 conditional-cover denominator is invalid")
        return p[:, 0] / denom

    q3_q = conditional_cover(q3)
    m2_q = conditional_cover(m2)
    return np.square(q3_q - actual_cover), np.square(m2_q - actual_cover), nonpush


def _block_codes(frame: pd.DataFrame) -> tuple[np.ndarray, int]:
    missing = set(BLOCK_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Stage-D bootstrap missing block columns: {sorted(missing)}")
    keys = frame[list(BLOCK_COLUMNS)].astype("string").agg("|".join, axis=1)
    codes, uniques = pd.factorize(keys, sort=False)
    if len(uniques) < 2:
        raise ValueError("Stage-D bootstrap requires at least two season+week blocks")
    return codes.astype(int), int(len(uniques))


def paired_block_bootstrap(
    frame: pd.DataFrame,
    candidate_loss: Iterable[float],
    reference_loss: Iterable[float],
    *,
    metric: str,
    candidate: str,
    reference: str,
    valid_mask: Iterable[bool] | None = None,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = BOOTSTRAP_ALPHA,
) -> PairedBootstrapResult:
    """Frozen season+week paired bootstrap on already-computed row losses."""
    if int(samples) != BOOTSTRAP_SAMPLES:
        raise ValueError(f"Stage-D bootstrap samples are frozen at {BOOTSTRAP_SAMPLES}")
    if int(seed) != BOOTSTRAP_SEED:
        raise ValueError(f"Stage-D bootstrap seed is frozen at {BOOTSTRAP_SEED}")
    if not np.isclose(float(alpha), BOOTSTRAP_ALPHA, atol=0.0, rtol=0.0):
        raise ValueError(f"Stage-D bootstrap alpha is frozen at {BOOTSTRAP_ALPHA}")

    data = _validate_oof_identity(frame, "Stage-D")
    c = np.asarray(candidate_loss, dtype=float).reshape(-1)
    r = np.asarray(reference_loss, dtype=float).reshape(-1)
    if len(c) != len(data) or len(r) != len(data):
        raise ValueError("Stage-D row-loss arrays are not aligned to OOF rows")
    if valid_mask is None:
        valid = np.ones(len(data), dtype=bool)
    else:
        valid = np.asarray(valid_mask, dtype=bool).reshape(-1)
        if len(valid) != len(data):
            raise ValueError("Stage-D valid mask is not aligned to OOF rows")
    finite = np.isfinite(c) & np.isfinite(r) & valid
    if not finite.any():
        raise ValueError("Stage-D paired loss has no valid rows")

    observed = float(np.mean(c[finite]) - np.mean(r[finite]))
    codes, n_blocks = _block_codes(data)
    block_indices = {block: np.flatnonzero(codes == block) for block in range(n_blocks)}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_SAMPLES, dtype=float)
    for draw in range(BOOTSTRAP_SAMPLES):
        chosen = rng.integers(0, n_blocks, size=n_blocks)
        idx = np.concatenate([block_indices[int(block)] for block in chosen])
        keep = finite[idx]
        if not keep.any():
            raise RuntimeError("Stage-D bootstrap draw contains no valid paired rows")
        sample_idx = idx[keep]
        draws[draw] = float(np.mean(c[sample_idx]) - np.mean(r[sample_idx]))

    lower, upper = np.quantile(draws, [BOOTSTRAP_ALPHA / 2.0, 1.0 - BOOTSTRAP_ALPHA / 2.0])
    return PairedBootstrapResult(
        metric=str(metric),
        candidate=str(candidate),
        reference=str(reference),
        block="season+week",
        rows=int(finite.sum()),
        blocks=n_blocks,
        samples=BOOTSTRAP_SAMPLES,
        observed_delta=observed,
        ci_lower=float(lower),
        ci_upper=float(upper),
        probability_better=float(np.mean(draws < 0.0)),
    )


def clopper_pearson(successes: int, trials: int, alpha: float = 0.05) -> tuple[float, float]:
    if not 0 <= int(successes) <= int(trials) or int(trials) <= 0:
        raise ValueError("Clopper-Pearson requires 0 <= successes <= trials and trials > 0")
    if not np.isclose(float(alpha), 0.05, atol=0.0, rtol=0.0):
        raise ValueError("Stage-D hit-rate interval is frozen at 95%")
    s = int(successes)
    n = int(trials)
    lower = 0.0 if s == 0 else float(beta.ppf(alpha / 2.0, s, n - s + 1))
    upper = 1.0 if s == n else float(beta.ppf(1.0 - alpha / 2.0, s + 1, n - s))
    return lower, upper


def q3_hit_rate_intervals(oof: pd.DataFrame) -> list[HitRateInterval]:
    outcome = _q3_outcome_index(oof)
    nonpush = outcome != 1
    actual_cover = outcome == 0
    results: list[HitRateInterval] = []
    for arm, prefix in (("Q3_M2", "q3_m2"), ("Q3", "q3")):
        p = _q3_probability(oof, prefix)
        conditional = p[:, 0] / (p[:, 0] + p[:, 2])
        predicted_cover = conditional >= 0.5
        correct = predicted_cover[nonpush] == actual_cover[nonpush]
        wins = int(correct.sum())
        n = int(nonpush.sum())
        lower, upper = clopper_pearson(wins, n)
        results.append(
            HitRateInterval(
                arm=arm,
                rows=n,
                wins=wins,
                hit_rate=float(wins / n),
                ci_lower=lower,
                ci_upper=upper,
            )
        )
    return results


def stage_d_uncertainty(q1_oof: pd.DataFrame, q3_oof: pd.DataFrame) -> pd.DataFrame:
    q1, q3 = align_q1_q3_oof(q1_oof, q3_oof)
    q1_loss, m2_loss = q1_row_losses(q1)
    q3_ll, q3_m2_ll = q3_multinomial_row_losses(q3)
    q3_brier, q3_m2_brier, nonpush = q3_nonpush_brier_row_losses(q3)
    results = [
        paired_block_bootstrap(
            q1,
            q1_loss,
            m2_loss,
            metric="mean_three_quantile_pinball",
            candidate="Q1",
            reference="M2",
        ),
        paired_block_bootstrap(
            q3,
            q3_ll,
            q3_m2_ll,
            metric="multinomial_cover_push_loss_log_loss",
            candidate="Q3",
            reference="Q3_M2",
        ),
        paired_block_bootstrap(
            q3,
            q3_brier,
            q3_m2_brier,
            valid_mask=nonpush,
            metric="nonpush_conditional_cover_brier",
            candidate="Q3",
            reference="Q3_M2",
        ),
    ]
    return pd.DataFrame([asdict(result) for result in results])


def descriptive_season_deltas(q1_oof: pd.DataFrame, q3_oof: pd.DataFrame) -> pd.DataFrame:
    """Carry forward season-level primary deltas without creating a new search surface."""
    q1, q3 = align_q1_q3_oof(q1_oof, q3_oof)
    q1_loss, m2_loss = q1_row_losses(q1)
    q3_ll, q3_m2_ll = q3_multinomial_row_losses(q3)
    q1 = q1.assign(_candidate=q1_loss, _reference=m2_loss)
    q3 = q3.assign(_candidate=q3_ll, _reference=q3_m2_ll)
    rows: list[dict] = []
    for season in TARGET_SEASONS:
        a = q1[q1["season"].eq(season)]
        b = q3[q3["season"].eq(season)]
        rows.append(
            {
                "season": season,
                "comparison": "Q1_minus_M2_mean_three_quantile_pinball",
                "rows": int(len(a)),
                "delta": float(a["_candidate"].mean() - a["_reference"].mean()),
            }
        )
        rows.append(
            {
                "season": season,
                "comparison": "Q3_minus_Q3_M2_multinomial_CPL_logloss",
                "rows": int(len(b)),
                "delta": float(b["_candidate"].mean() - b["_reference"].mean()),
            }
        )
    return pd.DataFrame(rows)

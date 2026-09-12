from __future__ import annotations

"""Accuracy-first paired evaluation for LevLine 4 research.

This module is reporting-only. It does not fit, retune, select, promote, or mutate any
forecast. The primary estimand is straight-up winner accuracy. Brier/log loss remain
secondary diagnostics. Production F-ST is untouched.
"""

from math import comb
from typing import Any

import numpy as np
import pandas as pd

BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260912
BRIER_GUARDRAIL_MARGIN = 0.0025
PRIMARY_HORIZONS = ("T-120m", "T-60m", "T-45m", "T-30m")


def _week_key(frame: pd.DataFrame) -> pd.Series:
    season = pd.to_numeric(frame.get("season", np.nan), errors="coerce")
    week = pd.to_numeric(frame.get("week", np.nan), errors="coerce")
    if not isinstance(season, pd.Series):
        season = pd.Series(np.nan, index=frame.index, dtype=float)
    if not isinstance(week, pd.Series):
        week = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = season.notna() & week.notna()
    result = pd.Series("unknown", index=frame.index, dtype=object)
    result.loc[valid] = (
        season.loc[valid].astype(int).astype(str)
        + "-W"
        + week.loc[valid].astype(int).astype(str)
    )
    return result


def _block_bootstrap_mean(
    frame: pd.DataFrame,
    column: str,
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if frame.empty:
        return {"mean": None, "ci95_low": None, "ci95_high": None, "draws": 0}
    work = frame.copy()
    work["week_key"] = _week_key(work)
    observed = float(pd.to_numeric(work[column], errors="coerce").mean())
    if work["week_key"].eq("unknown").any():
        return {
            "mean": observed,
            "ci95_low": None,
            "ci95_high": None,
            "draws": 0,
            "reason": "missing_week_metadata_fail_closed",
        }
    blocks = [
        pd.to_numeric(group[column], errors="coerce").dropna().to_numpy(dtype=float)
        for _, group in work.groupby("week_key", sort=True)
    ]
    blocks = [block for block in blocks if len(block)]
    if len(blocks) < 2:
        return {
            "mean": observed,
            "ci95_low": None,
            "ci95_high": None,
            "draws": 0,
            "reason": "fewer_than_two_week_blocks",
        }
    rng = np.random.default_rng(seed)
    values = np.empty(draws, dtype=float)
    n_blocks = len(blocks)
    for i in range(draws):
        chosen = rng.integers(0, n_blocks, size=n_blocks)
        sample = np.concatenate([blocks[int(j)] for j in chosen])
        values[i] = float(sample.mean())
    low, high = np.quantile(values, [0.025, 0.975])
    return {
        "mean": observed,
        "ci95_low": float(low),
        "ci95_high": float(high),
        "draws": int(draws),
        "week_blocks": int(n_blocks),
        "seed": int(seed),
    }


def _exact_mcnemar_two_sided(candidate_only_correct: int, benchmark_only_correct: int) -> float | None:
    """Exact non-clustered McNemar p-value; week-aware bootstrap remains primary."""
    b = int(candidate_only_correct)
    c = int(benchmark_only_correct)
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def paired_accuracy_comparison(
    candidate: pd.DataFrame,
    benchmark: pd.DataFrame,
    *,
    label: str,
    join_on_horizon: bool = True,
) -> dict[str, Any]:
    required = {"game_id", "winner_correct_eval"}
    if candidate.empty or benchmark.empty:
        return {"benchmark": label, "games": 0}
    if not required.issubset(candidate.columns) or not required.issubset(benchmark.columns):
        raise ValueError("paired accuracy comparison requires game_id and winner_correct_eval")

    keys = ["game_id"]
    if join_on_horizon:
        if "horizon" not in candidate.columns or "horizon" not in benchmark.columns:
            raise ValueError("same-horizon comparison requires horizon")
        keys.append("horizon")

    left = candidate.copy()
    right = benchmark.copy()
    left_cols = keys + ["winner_correct_eval"]
    right_cols = keys + ["winner_correct_eval"]
    for optional in ("brier_loss", "log_loss", "season", "week"):
        if optional in left.columns:
            left_cols.append(optional)
        if optional in right.columns:
            right_cols.append(optional)

    paired = left[left_cols].merge(
        right[right_cols],
        on=keys,
        suffixes=("_candidate", "_benchmark"),
    )
    if paired.empty:
        return {"benchmark": label, "games": 0}

    c_correct = pd.to_numeric(paired["winner_correct_eval_candidate"], errors="coerce")
    b_correct = pd.to_numeric(paired["winner_correct_eval_benchmark"], errors="coerce")
    valid = c_correct.notna() & b_correct.notna()
    paired = paired.loc[valid].copy()
    if paired.empty:
        return {"benchmark": label, "games": 0}

    c_correct = pd.to_numeric(paired["winner_correct_eval_candidate"], errors="coerce").astype(float)
    b_correct = pd.to_numeric(paired["winner_correct_eval_benchmark"], errors="coerce").astype(float)
    paired["accuracy_delta"] = c_correct - b_correct

    candidate_only = int(((c_correct == 1.0) & (b_correct == 0.0)).sum())
    benchmark_only = int(((c_correct == 0.0) & (b_correct == 1.0)).sum())
    discordant = candidate_only + benchmark_only
    switch_rate = (candidate_only / discordant) if discordant else None

    # Prefer candidate metadata for cluster identity; if absent, fall back to benchmark.
    for name in ("season", "week"):
        c_name = f"{name}_candidate"
        b_name = f"{name}_benchmark"
        if c_name in paired.columns and b_name in paired.columns:
            paired[name] = pd.to_numeric(paired[c_name], errors="coerce").where(
                pd.to_numeric(paired[c_name], errors="coerce").notna(),
                pd.to_numeric(paired[b_name], errors="coerce"),
            )
        elif c_name in paired.columns:
            paired[name] = pd.to_numeric(paired[c_name], errors="coerce")
        elif b_name in paired.columns:
            paired[name] = pd.to_numeric(paired[b_name], errors="coerce")

    result: dict[str, Any] = {
        "benchmark": label,
        "games": int(len(paired)),
        "candidate_accuracy": float(c_correct.mean()),
        "benchmark_accuracy": float(b_correct.mean()),
        "accuracy_delta": float(paired["accuracy_delta"].mean()),
        "candidate_only_correct": candidate_only,
        "benchmark_only_correct": benchmark_only,
        "discordant_games": int(discordant),
        "disagreement_rate": float(discordant / len(paired)),
        "switch_win_rate": float(switch_rate) if switch_rate is not None else None,
        "mcnemar_exact_two_sided_p_diagnostic": _exact_mcnemar_two_sided(candidate_only, benchmark_only),
        "accuracy_week_block_bootstrap": _block_bootstrap_mean(paired, "accuracy_delta"),
    }

    if {"brier_loss_candidate", "brier_loss_benchmark"}.issubset(paired.columns):
        paired["brier_delta"] = (
            pd.to_numeric(paired["brier_loss_candidate"], errors="coerce")
            - pd.to_numeric(paired["brier_loss_benchmark"], errors="coerce")
        )
        result["brier_delta"] = float(paired["brier_delta"].mean())
        result["brier_week_block_bootstrap"] = _block_bootstrap_mean(paired, "brier_delta")
        brier_ci = result["brier_week_block_bootstrap"]
        high = brier_ci.get("ci95_high")
        result["brier_secondary_guardrail_margin"] = BRIER_GUARDRAIL_MARGIN
        result["brier_secondary_guardrail_pass"] = (
            bool(high <= BRIER_GUARDRAIL_MARGIN) if high is not None else None
        )

    if {"log_loss_candidate", "log_loss_benchmark"}.issubset(paired.columns):
        paired["log_loss_delta"] = (
            pd.to_numeric(paired["log_loss_candidate"], errors="coerce")
            - pd.to_numeric(paired["log_loss_benchmark"], errors="coerce")
        )
        result["log_loss_delta"] = float(paired["log_loss_delta"].mean())

    acc_ci = result["accuracy_week_block_bootstrap"]
    low = acc_ci.get("ci95_low")
    result["accuracy_superiority_supported"] = bool(low > 0.0) if low is not None else None
    result["promotion_authorized"] = False
    return result


def horizon_pair_comparison(
    scored_market: pd.DataFrame,
    candidate_horizon: str,
    benchmark_horizon: str,
) -> dict[str, Any]:
    if candidate_horizon not in PRIMARY_HORIZONS or benchmark_horizon not in PRIMARY_HORIZONS:
        raise ValueError("unsupported horizon")
    candidate = scored_market[scored_market["horizon"].astype(str).eq(candidate_horizon)].copy()
    benchmark = scored_market[scored_market["horizon"].astype(str).eq(benchmark_horizon)].copy()
    return paired_accuracy_comparison(
        candidate,
        benchmark,
        label=benchmark_horizon,
        join_on_horizon=False,
    )

from __future__ import annotations

"""Reproduce the chronology-clean F-ST architecture winner-accuracy audit.

This is historical research only. Each validation season 2022-2025 is predicted by a
stack fitted exclusively on earlier seasons. The code does not change production and
uses no 2026 outcomes.
"""

from math import comb
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
BOOTSTRAP_SEED = 20260912
BOOTSTRAP_DRAWS = 10_000


def _exact_mcnemar_two_sided(candidate_only: int, benchmark_only: int) -> float | None:
    n = int(candidate_only) + int(benchmark_only)
    if n == 0:
        return None
    k = min(int(candidate_only), int(benchmark_only))
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def _log_loss(probability: pd.Series, outcome: pd.Series) -> float:
    p = np.clip(pd.to_numeric(probability, errors="coerce").to_numpy(float), 1e-15, 1 - 1e-15)
    y = pd.to_numeric(outcome, errors="coerce").to_numpy(float)
    return float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))


def _week_block_ci(frame: pd.DataFrame) -> dict[str, Any]:
    work = frame.copy()
    work["week"] = work["game_id"].astype(str).str.split("_").str[1].astype(int)
    blocks = [
        group["accuracy_delta"].to_numpy(float)
        for _, group in work.groupby(["season", "week"], sort=True)
    ]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_DRAWS, dtype=float)
    for i in range(BOOTSTRAP_DRAWS):
        selected = rng.integers(0, len(blocks), size=len(blocks))
        draws[i] = np.concatenate([blocks[int(j)] for j in selected]).mean()
    low, high = np.quantile(draws, [0.025, 0.975])
    return {
        "blocks": int(len(blocks)),
        "draws": BOOTSTRAP_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "ci95_low": float(low),
        "ci95_high": float(high),
    }


def audit(path: str | Path = SOURCE) -> dict[str, Any]:
    source = pd.read_csv(path)
    stack = build_chronological_logit_stack(source)
    pred = stack.predictions.copy()
    # build_chronological_logit_stack preserves original row index, allowing immutable
    # game identity to be reattached without a fuzzy merge.
    pred["game_id"] = source.loc[pred.index, "game_id"].astype(str)
    pred["season"] = pd.to_numeric(pred["season"], errors="raise").astype(int)
    pred["home_win"] = pd.to_numeric(pred["home_win"], errors="raise").astype(int)
    pred["stack_pick"] = (pred["stack_probability"] >= 0.5).astype(int)
    pred["market_pick"] = (pred["market_prob"] >= 0.5).astype(int)
    pred["stack_correct"] = (pred["stack_pick"] == pred["home_win"]).astype(int)
    pred["market_correct"] = (pred["market_pick"] == pred["home_win"]).astype(int)
    pred["accuracy_delta"] = pred["stack_correct"] - pred["market_correct"]
    pred["disagree"] = pred["stack_pick"] != pred["market_pick"]
    candidate_only = int((pred["disagree"] & pred["stack_correct"].eq(1)).sum())
    market_only = int((pred["disagree"] & pred["market_correct"].eq(1)).sum())
    disagreements = candidate_only + market_only

    by_season = []
    for season, group in pred.groupby("season", sort=True):
        group_disagree = group["disagree"]
        c_only = int((group_disagree & group["stack_correct"].eq(1)).sum())
        m_only = int((group_disagree & group["market_correct"].eq(1)).sum())
        d = c_only + m_only
        by_season.append({
            "season": int(season),
            "games": int(len(group)),
            "stack_correct": int(group["stack_correct"].sum()),
            "market_correct": int(group["market_correct"].sum()),
            "stack_accuracy": float(group["stack_correct"].mean()),
            "market_accuracy": float(group["market_correct"].mean()),
            "disagreements": int(d),
            "stack_only_correct": c_only,
            "market_only_correct": m_only,
            "switch_win_rate": float(c_only / d) if d else None,
        })

    return {
        "audit_id": "LEVLINE3-FST-CHRONOLOGICAL-ACCURACY-AUDIT-V1",
        "status": "chronology_clean_historical_architecture_evaluation",
        "games": int(len(pred)),
        "stack_correct": int(pred["stack_correct"].sum()),
        "stack_accuracy": float(pred["stack_correct"].mean()),
        "market_correct": int(pred["market_correct"].sum()),
        "market_accuracy": float(pred["market_correct"].mean()),
        "accuracy_delta": float(pred["accuracy_delta"].mean()),
        "stack_brier": float(np.mean((pred["stack_probability"] - pred["home_win"]) ** 2)),
        "market_brier": float(np.mean((pred["market_prob"] - pred["home_win"]) ** 2)),
        "stack_log_loss": _log_loss(pred["stack_probability"], pred["home_win"]),
        "market_log_loss": _log_loss(pred["market_prob"], pred["home_win"]),
        "disagreement_games": int(disagreements),
        "stack_only_correct": candidate_only,
        "market_only_correct": market_only,
        "switch_win_rate": float(candidate_only / disagreements) if disagreements else None,
        "mcnemar_exact_two_sided_p_diagnostic": _exact_mcnemar_two_sided(candidate_only, market_only),
        "accuracy_week_block_bootstrap": _week_block_ci(pred),
        "by_season": by_season,
        "coefficients": stack.coefficients.to_dict("records"),
        "2026_outcomes_used": 0,
        "production_changed": False,
        "promotion_authorized": False,
    }

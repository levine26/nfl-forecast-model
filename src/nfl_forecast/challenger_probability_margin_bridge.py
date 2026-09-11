from __future__ import annotations

"""Research-only audit of probability-derived fair margins.

PHASE3B-PROB-MARGIN-BRIDGE-001 is pre-registered before result generation.  This module
asks whether sigma * Phi^-1(P_home) is empirically competitive as a margin forecast; it
does not alter the production public-forecast bridge.
"""

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm

TARGET_SEASONS = (2022, 2023, 2024, 2025)
EPS = 1e-6


@dataclass(frozen=True)
class MarginBootstrap:
    candidate: str
    reference: str
    games: int
    blocks: int
    observed_mae_delta: float
    ci_lower: float
    ci_upper: float
    probability_better: float
    samples: int


def _validate_games(games: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "season", "week", "margin", "spread_line"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"margin-bridge games missing fields: {sorted(missing)}")
    work = games.copy()
    for col in ("season", "week", "margin", "spread_line"):
        work[col] = pd.to_numeric(work[col], errors="coerce")
    outcomes = work[work.margin.notna()].copy()
    if outcomes.season.ge(2026).any():
        raise ValueError("Probability-margin bridge refuses 2026-or-later outcomes")
    return outcomes


def chronological_probability_margin_bridge(
    games: pd.DataFrame,
    probabilities: pd.DataFrame,
    *,
    probability_cols: Sequence[str] = ("market_prob", "market_plus_pure_prob"),
    target_seasons: Sequence[int] = TARGET_SEASONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map probabilities to margins using only a prior-season market-error sigma."""
    outcomes = _validate_games(games)
    required_probs = {"game_id", "season", *probability_cols}
    missing = required_probs - set(probabilities.columns)
    if missing:
        raise ValueError(f"margin-bridge probabilities missing fields: {sorted(missing)}")
    probs = probabilities.copy()
    probs["season"] = pd.to_numeric(probs["season"], errors="coerce")
    if probs.season.dropna().ge(2026).any():
        raise ValueError("Probability-margin bridge refuses post-2025 probability rows")

    target = outcomes.merge(
        probs[["game_id", "season", *probability_cols]],
        on=["game_id", "season"],
        how="inner",
        validate="one_to_one",
    )
    parts: list[pd.DataFrame] = []
    diagnostics: list[dict] = []
    for season in [int(x) for x in target_seasons]:
        train = outcomes[
            outcomes.season.lt(season)
            & outcomes.margin.notna()
            & outcomes.spread_line.notna()
        ].copy()
        test = target[
            target.season.eq(season)
            & target.margin.notna()
            & target.spread_line.notna()
        ].copy()
        if test.empty:
            continue
        if len(train) < 300:
            raise ValueError(f"Insufficient pre-{season} market-margin history: {len(train)}")
        market_error = train.margin.to_numpy(float) - train.spread_line.to_numpy(float)
        sigma = float(np.std(market_error, ddof=1))
        if not np.isfinite(sigma) or sigma <= 1.0:
            raise ValueError(f"Invalid pre-{season} margin sigma: {sigma}")

        part = test[["game_id", "season", "week", "margin", "spread_line"]].copy()
        for probability_col in probability_cols:
            p = np.clip(pd.to_numeric(test[probability_col], errors="coerce").to_numpy(float), EPS, 1.0 - EPS)
            part[probability_col] = p
            part[f"{probability_col}_bridge_margin"] = sigma * norm.ppf(p)
            part[f"{probability_col}_bridge_abs_error"] = np.abs(
                part.margin - part[f"{probability_col}_bridge_margin"]
            )
        part["market_spread_abs_error"] = np.abs(part.margin - part.spread_line)
        part["sigma_margin"] = sigma
        parts.append(part)
        diagnostics.append(
            {
                "season": season,
                "training_games": int(len(train)),
                "test_games": int(len(test)),
                "sigma_margin": sigma,
                "sigma_source": "std(actual_margin_minus_market_spread)_on_seasons_before_test_season",
            }
        )
    if not parts:
        raise ValueError("No target seasons available for probability-margin bridge")
    return pd.concat(parts, ignore_index=True), pd.DataFrame(diagnostics)


def margin_metrics(predictions: pd.DataFrame, margin_col: str) -> dict[str, float]:
    required = {"margin", margin_col}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"margin metrics missing: {sorted(missing)}")
    data = predictions.dropna(subset=["margin", margin_col]).copy()
    error = pd.to_numeric(data[margin_col], errors="coerce") - pd.to_numeric(data.margin, errors="coerce")
    return {
        "games": int(len(data)),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.mean(error.to_numpy(float) ** 2))),
        "favorite_direction_accuracy": float(
            np.mean((pd.to_numeric(data[margin_col], errors="coerce") >= 0) == (pd.to_numeric(data.margin, errors="coerce") >= 0))
        ),
    }


def blocked_margin_bootstrap(
    predictions: pd.DataFrame,
    candidate_margin_col: str,
    reference_margin_col: str,
    *,
    samples: int = 2000,
    seed: int = 26,
) -> MarginBootstrap:
    required = {"season", "week", "margin", candidate_margin_col, reference_margin_col}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"margin bootstrap missing: {sorted(missing)}")
    data = predictions.dropna(subset=list(required)).copy()
    c = np.abs(pd.to_numeric(data[candidate_margin_col], errors="coerce") - pd.to_numeric(data.margin, errors="coerce"))
    r = np.abs(pd.to_numeric(data[reference_margin_col], errors="coerce") - pd.to_numeric(data.margin, errors="coerce"))
    data["_delta"] = c - r
    data["_block"] = data.season.astype(int).astype(str) + "|" + data.week.astype(int).astype(str)
    blocks = list(data._block.unique())
    values = {block: data.loc[data._block.eq(block), "_delta"].to_numpy(float) for block in blocks}
    observed = float(data._delta.mean())
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=float)
    for idx in range(int(samples)):
        chosen = rng.choice(blocks, size=len(blocks), replace=True)
        draws[idx] = float(np.mean(np.concatenate([values[block] for block in chosen])))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return MarginBootstrap(
        candidate=candidate_margin_col,
        reference=reference_margin_col,
        games=int(len(data)),
        blocks=int(len(blocks)),
        observed_mae_delta=observed,
        ci_lower=float(lo),
        ci_upper=float(hi),
        probability_better=float(np.mean(draws < 0.0)),
        samples=int(samples),
    )


def six_plus_disagreement_slice(
    predictions: pd.DataFrame,
    bridge_col: str,
    *,
    threshold: float = 6.0,
) -> dict[str, float]:
    data = predictions.dropna(subset=["margin", "spread_line", bridge_col]).copy()
    gap = (pd.to_numeric(data[bridge_col], errors="coerce") - pd.to_numeric(data.spread_line, errors="coerce")).abs()
    part = data.loc[gap >= float(threshold)].copy()
    if part.empty:
        return {"games": 0, "threshold_points": float(threshold)}
    bridge_error = (pd.to_numeric(part[bridge_col], errors="coerce") - pd.to_numeric(part.margin, errors="coerce")).abs()
    market_error = (pd.to_numeric(part.spread_line, errors="coerce") - pd.to_numeric(part.margin, errors="coerce")).abs()
    return {
        "games": int(len(part)),
        "threshold_points": float(threshold),
        "mean_abs_bridge_market_gap": float(gap.loc[part.index].mean()),
        "bridge_mae": float(bridge_error.mean()),
        "market_mae": float(market_error.mean()),
        "bridge_minus_market_mae": float((bridge_error - market_error).mean()),
        "bridge_closer_rate": float((bridge_error < market_error).mean()),
    }


def result_dict(result: MarginBootstrap) -> dict:
    return asdict(result)

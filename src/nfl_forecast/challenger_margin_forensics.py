from __future__ import annotations

"""Research-only forensics for large LevLine margin-vs-market disagreements.

This module reproduces the production margin ensemble's season-held-out validation logic
without importing it into production. Historical outcome use is hard-capped at 2025.
The resulting ensemble weights are descriptive because, like the current production
validation summary, they are estimated across the same 2022-25 OOF block being diagnosed.
They may diagnose failure modes but may not select a production model.
"""

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error

from .models import _reg_models

TARGET_SEASONS = (2022, 2023, 2024, 2025)
GAP_EDGES = (0.0, 2.0, 4.0, 6.0, 8.0, float("inf"))
GAP_LABELS = ("<2", "2-4", "4-6", "6-8", "8+")


@dataclass(frozen=True)
class MarginBootstrap:
    games: int
    blocks: int
    observed_model_minus_market_mae: float
    ci_lower: float
    ci_upper: float
    probability_model_better: float
    samples: int


def _validate(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"season", "margin", "spread_line"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"margin forensic frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["season"] = pd.to_numeric(work.season, errors="coerce")
    work["margin"] = pd.to_numeric(work.margin, errors="coerce")
    work["spread_line"] = pd.to_numeric(work.spread_line, errors="coerce")
    if work.loc[work.margin.notna(), "season"].ge(2026).any():
        raise ValueError("Historical margin forensics refuse 2026-or-later outcomes")
    return work


def walk_forward_margin_predictions(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    *,
    seed: int = 26,
    target_seasons: Sequence[int] = TARGET_SEASONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate season-held-out base-regressor predictions and current-like weights.

    Base predictions are strictly walk-forward by season. The final inverse-MAE weights are
    estimated across the completed OOF target block, matching the current production
    regression-weighting diagnostic. This makes the ensemble a descriptive forensic object,
    not a chronology-clean candidate-selection result.
    """
    work = _validate(frame)
    train = work[work.margin.notna()].copy()
    cols = list(feature_cols)
    missing = [c for c in cols if c not in train.columns]
    if missing:
        raise ValueError(f"margin forensic features missing: {missing[:10]}")
    templates = _reg_models(seed)
    errors = {name: [] for name in templates}
    parts: list[pd.DataFrame] = []

    for season in [int(x) for x in target_seasons]:
        tr = train[train.season < season]
        va = train[train.season == season]
        if va.empty:
            continue
        if len(tr) < 100:
            raise ValueError(f"Insufficient pre-{season} margin history")
        keep = [c for c in ("game_id", "season", "week", "gameday", "away_team", "home_team", "margin", "spread_line") if c in va.columns]
        part = va[keep].copy()
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[cols], tr.margin.astype(float))
            pred = model.predict(va[cols])
            part[name] = pred
            errors[name].append(float(mean_absolute_error(va.margin, pred)))
        parts.append(part)

    if not parts:
        raise ValueError("No target seasons available for margin forensics")
    oof = pd.concat(parts).sort_index()
    scores = {name: float(np.mean(values)) for name, values in errors.items() if values}
    inv = {name: 1.0 / max(value, 1e-9) for name, value in scores.items()}
    denom = sum(inv.values())
    weights = {name: value / denom for name, value in inv.items()}
    oof["model_margin"] = sum(weights[name] * oof[name].to_numpy(dtype=float) for name in weights)
    oof["market_margin"] = pd.to_numeric(oof.spread_line, errors="coerce")
    oof["actual_margin"] = pd.to_numeric(oof.margin, errors="coerce")
    oof["model_market_gap"] = oof.model_margin - oof.market_margin
    oof["abs_model_market_gap"] = oof.model_market_gap.abs()
    oof["model_abs_error"] = (oof.actual_margin - oof.model_margin).abs()
    oof["market_abs_error"] = (oof.actual_margin - oof.market_margin).abs()
    oof["model_minus_market_abs_error"] = oof.model_abs_error - oof.market_abs_error
    oof["market_residual"] = oof.actual_margin - oof.market_margin
    oof["model_closer"] = oof.model_abs_error < oof.market_abs_error
    oof["market_closer"] = oof.market_abs_error < oof.model_abs_error
    oof["ats_push"] = np.isclose(oof.market_residual, 0.0)
    oof["model_side_hit"] = np.where(
        oof.ats_push | np.isclose(oof.model_market_gap, 0.0),
        np.nan,
        np.sign(oof.market_residual) == np.sign(oof.model_market_gap),
    )
    oof["gap_bucket"] = pd.cut(
        oof.abs_model_market_gap,
        bins=list(GAP_EDGES),
        labels=list(GAP_LABELS),
        right=False,
        include_lowest=True,
    )

    weight_rows = [
        {
            "model": name,
            "mean_oof_mae": scores[name],
            "descriptive_weight": weights[name],
            "methodology": "same_2022_2025_oof_block_descriptive_not_candidate_selection",
        }
        for name in weights
    ]
    return oof, pd.DataFrame(weight_rows).sort_values("descriptive_weight", ascending=False)


def summarize_margin_disagreements(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {
        "gap_bucket", "model_abs_error", "market_abs_error", "model_closer",
        "model_side_hit", "abs_model_market_gap", "model_minus_market_abs_error",
    }
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"margin forensic predictions missing fields: {sorted(missing)}")
    rows: list[dict] = []
    for label in GAP_LABELS:
        part = predictions[predictions.gap_bucket.astype("string").eq(label)].copy()
        if part.empty:
            continue
        ats = pd.to_numeric(part.model_side_hit, errors="coerce").dropna()
        rows.append(
            {
                "gap_bucket_points": label,
                "games": int(len(part)),
                "mean_abs_gap_points": float(part.abs_model_market_gap.mean()),
                "model_margin_mae": float(part.model_abs_error.mean()),
                "market_spread_mae": float(part.market_abs_error.mean()),
                "model_minus_market_mae": float(part.model_minus_market_abs_error.mean()),
                "model_closer_rate": float(part.model_closer.mean()),
                "model_side_ats_hit_rate": float(ats.mean()) if len(ats) else np.nan,
                "ats_decisions": int(len(ats)),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_large_gap_error_delta(
    predictions: pd.DataFrame,
    *,
    minimum_gap_points: float = 6.0,
    samples: int = 5000,
    seed: int = 26,
) -> MarginBootstrap:
    part = predictions[predictions.abs_model_market_gap >= float(minimum_gap_points)].copy()
    part = part.dropna(subset=["model_minus_market_abs_error"])
    if part.empty:
        return MarginBootstrap(0, 0, np.nan, np.nan, np.nan, np.nan, int(samples))
    if "week" not in part.columns:
        part["week"] = 0
    part["_block"] = part.season.astype(str) + "_" + part.week.astype(str)
    blocks = list(part._block.unique())
    block_values = {
        block: part.loc[part._block.eq(block), "model_minus_market_abs_error"].to_numpy(dtype=float)
        for block in blocks
    }
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=float)
    for i in range(int(samples)):
        sampled = rng.choice(blocks, size=len(blocks), replace=True)
        values = np.concatenate([block_values[block] for block in sampled])
        draws[i] = float(np.mean(values))
    observed = float(part.model_minus_market_abs_error.mean())
    return MarginBootstrap(
        games=int(len(part)),
        blocks=int(len(blocks)),
        observed_model_minus_market_mae=observed,
        ci_lower=float(np.quantile(draws, 0.025)),
        ci_upper=float(np.quantile(draws, 0.975)),
        probability_model_better=float(np.mean(draws < 0.0)),
        samples=int(samples),
    )


def current_large_gap_probes(
    slate: pd.DataFrame,
    *,
    minimum_gap_points: float = 6.0,
) -> pd.DataFrame:
    """Extract ungraded current games with unusually large model-vs-market margin gaps."""
    required = {"game_id", "expected_margin", "spread_line"}
    missing = required - set(slate.columns)
    if missing:
        raise ValueError(f"current slate missing fields: {sorted(missing)}")
    work = slate.copy()
    work["model_margin"] = pd.to_numeric(work.expected_margin, errors="coerce")
    work["market_margin"] = pd.to_numeric(work.spread_line, errors="coerce")
    work["model_market_gap"] = work.model_margin - work.market_margin
    work["abs_model_market_gap"] = work.model_market_gap.abs()
    work = work[work.abs_model_market_gap >= float(minimum_gap_points)].copy()
    keep = [
        c for c in (
            "game_id", "away_team", "home_team", "gameday", "gametime",
            "model_margin", "market_margin", "model_market_gap", "abs_model_market_gap",
            "final_home_prob", "market_home_prob", "fst_pure_home_prob",
            "consistency_flag", "prediction_timestamp_utc",
        ) if c in work.columns
    ]
    out = work[keep].sort_values("abs_model_market_gap", ascending=False)
    out["research_only"] = True
    out["graded"] = False
    return out


def bootstrap_dict(result: MarginBootstrap) -> dict:
    return asdict(result)

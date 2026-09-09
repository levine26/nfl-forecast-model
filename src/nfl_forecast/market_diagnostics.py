from __future__ import annotations

"""Diagnostics for measuring PURE's independence from the betting market.

This module is research/accountability only. It never changes the published
LevLine probability. Historical nflverse market prices are closing-line data,
so any weight search performed here is explicitly descriptive unless the
market snapshot horizon is aligned with the production lock horizon.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss


EPS = 1e-6
DEFAULT_MARKET_WEIGHT = 0.25
DEFAULT_WEIGHT_GRID = tuple(round(x, 2) for x in np.linspace(0.0, 1.0, 21))


def _clip(values) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values) -> np.ndarray:
    p = _clip(values)
    return np.log(p / (1.0 - p))


def _sigmoid(values) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    return 1.0 / (1.0 + np.exp(-x))


def blend_probabilities(pure, market, market_weight: float, method: str = "linear") -> np.ndarray:
    """Blend PURE and market probabilities without mutating either source."""
    w = float(market_weight)
    if not 0.0 <= w <= 1.0:
        raise ValueError("market_weight must be between 0 and 1")
    p = _clip(pure)
    m = _clip(market)
    if method == "linear":
        return (1.0 - w) * p + w * m
    if method == "logit":
        return _sigmoid((1.0 - w) * _logit(p) + w * _logit(m))
    raise ValueError(f"Unknown blend method: {method}")


def probability_metrics(y, p) -> dict[str, float | int]:
    y_arr = np.asarray(y, dtype=int)
    p_arr = _clip(p)
    return {
        "games": int(len(y_arr)),
        "winner_pct": float(((p_arr >= 0.5).astype(int) == y_arr).mean()) if len(y_arr) else float("nan"),
        "brier": float(brier_score_loss(y_arr, p_arr)) if len(y_arr) else float("nan"),
        "log_loss": float(log_loss(y_arr, p_arr, labels=[0, 1])) if len(y_arr) else float("nan"),
    }


def prepare_market_frame(historical: pd.DataFrame, core_oof: pd.DataFrame) -> pd.DataFrame:
    """Build the common OOS sample used for PURE-vs-market evaluation."""
    idx = historical.index.intersection(core_oof.index)
    if len(idx) == 0:
        return pd.DataFrame(columns=["season", "home_win", "pure", "market", "gap"])
    h = historical.loc[idx]
    c = core_oof.loc[idx]
    frame = pd.DataFrame(index=idx)
    frame["season"] = pd.to_numeric(c.get("season", h.get("season")), errors="coerce")
    frame["home_win"] = pd.to_numeric(c.get("home_win", h.get("home_win")), errors="coerce")
    frame["pure"] = pd.to_numeric(c.get("stack"), errors="coerce")
    frame["market"] = pd.to_numeric(h.get("market_home_prob"), errors="coerce")
    for col in ["game_id", "home_team", "away_team"]:
        if col in h.columns:
            frame[col] = h[col]
    frame = frame.dropna(subset=["season", "home_win", "pure", "market"]).copy()
    frame["season"] = frame["season"].astype(int)
    frame["home_win"] = frame["home_win"].astype(int)
    frame["gap"] = (frame["pure"] - frame["market"]).abs()
    frame["favorite_flip"] = (frame["pure"] >= 0.5) != (frame["market"] >= 0.5)
    return frame


def build_weight_grid(
    frame: pd.DataFrame,
    weights: Iterable[float] = DEFAULT_WEIGHT_GRID,
) -> pd.DataFrame:
    rows: list[dict] = []
    if frame.empty:
        return pd.DataFrame(columns=["method", "market_weight", "games", "winner_pct", "brier", "log_loss"])
    y = frame["home_win"].to_numpy(dtype=int)
    pure = frame["pure"].to_numpy(dtype=float)
    market = frame["market"].to_numpy(dtype=float)
    for method in ("linear", "logit"):
        for weight in weights:
            metrics = probability_metrics(y, blend_probabilities(pure, market, weight, method))
            rows.append({"method": method, "market_weight": float(weight), **metrics})
    return pd.DataFrame(rows)


def analytic_linear_brier_weight(frame: pd.DataFrame) -> dict[str, float | None]:
    """Closed-form Brier-optimal linear market weight on the supplied sample.

    The unconstrained value is useful diagnostically. The constrained value is
    clipped to [0, 1]. This is NOT a production-weight selector when the market
    data are closing lines and production locks earlier.
    """
    if frame.empty:
        return {"unconstrained": None, "constrained": None}
    y = frame["home_win"].to_numpy(dtype=float)
    pure = frame["pure"].to_numpy(dtype=float)
    market = frame["market"].to_numpy(dtype=float)
    delta = market - pure
    denom = float(np.mean(delta * delta))
    if denom <= 1e-15:
        return {"unconstrained": 0.0, "constrained": 0.0}
    weight = -float(np.mean((pure - y) * delta)) / denom
    return {"unconstrained": weight, "constrained": float(np.clip(weight, 0.0, 1.0))}


def build_walk_forward_blend(
    frame: pd.DataFrame,
    weights: Iterable[float] = DEFAULT_WEIGHT_GRID,
) -> pd.DataFrame:
    """Choose a blend weight only from earlier OOS seasons, then test forward."""
    rows: list[dict] = []
    if frame.empty:
        return pd.DataFrame()
    seasons = sorted(int(x) for x in frame["season"].unique())
    for method in ("linear", "logit"):
        for test_season in seasons[1:]:
            train = frame[frame["season"] < test_season]
            test = frame[frame["season"] == test_season]
            if train.empty or test.empty:
                continue
            train_grid = build_weight_grid(train, weights)
            candidates = train_grid[train_grid["method"].eq(method)].sort_values(
                ["brier", "log_loss", "market_weight"], ascending=[True, True, True]
            )
            selected = float(candidates.iloc[0]["market_weight"])
            pred = blend_probabilities(test["pure"], test["market"], selected, method)
            test_metrics = probability_metrics(test["home_win"], pred)
            rows.append({
                "method": method,
                "test_season": int(test_season),
                "train_through": int(test_season - 1),
                "selected_market_weight": selected,
                "train_games": int(len(train)),
                **{f"test_{k}": v for k, v in test_metrics.items()},
            })
    return pd.DataFrame(rows)


def summarize_walk_forward(frame: pd.DataFrame, walk: pd.DataFrame) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if frame.empty or walk.empty:
        return out
    for method in sorted(walk["method"].unique()):
        preds: list[np.ndarray] = []
        actuals: list[np.ndarray] = []
        weights: list[float] = []
        sub = walk[walk["method"].eq(method)].sort_values("test_season")
        for _, row in sub.iterrows():
            test = frame[frame["season"].eq(int(row["test_season"]))]
            if test.empty:
                continue
            weight = float(row["selected_market_weight"])
            preds.append(blend_probabilities(test["pure"], test["market"], weight, method))
            actuals.append(test["home_win"].to_numpy(dtype=int))
            weights.append(weight)
        if preds:
            metrics = probability_metrics(np.concatenate(actuals), np.concatenate(preds))
            out[method] = {
                **metrics,
                "seasons": [int(x) for x in sub["test_season"].tolist()],
                "selected_market_weights": weights,
                "mean_selected_market_weight": float(np.mean(weights)),
            }
    return out


def disagreement_buckets(frame: pd.DataFrame, current_weight: float = DEFAULT_MARKET_WEIGHT) -> list[dict]:
    rows: list[dict] = []
    if frame.empty:
        return rows
    for threshold in (0.0, 0.03, 0.05, 0.10):
        sub = frame[frame["gap"].ge(threshold)]
        if sub.empty:
            continue
        y = sub["home_win"]
        pure_m = probability_metrics(y, sub["pure"])
        market_m = probability_metrics(y, sub["market"])
        current_m = probability_metrics(
            y,
            blend_probabilities(sub["pure"], sub["market"], current_weight, "linear"),
        )
        flips = sub[sub["favorite_flip"]]
        flip_pure_accuracy = float(((flips["pure"] >= 0.5).astype(int) == flips["home_win"]).mean()) if len(flips) else None
        flip_market_accuracy = float(((flips["market"] >= 0.5).astype(int) == flips["home_win"]).mean()) if len(flips) else None
        rows.append({
            "minimum_gap_pp": threshold * 100.0,
            "games": int(len(sub)),
            "favorite_flips": int(sub["favorite_flip"].sum()),
            "pure_brier": pure_m["brier"],
            "market_brier": market_m["brier"],
            "current_blend_brier": current_m["brier"],
            "pure_minus_market_brier": pure_m["brier"] - market_m["brier"],
            "pure_winner_pct": pure_m["winner_pct"],
            "market_winner_pct": market_m["winner_pct"],
            "current_blend_winner_pct": current_m["winner_pct"],
            "flip_pure_accuracy": flip_pure_accuracy,
            "flip_market_accuracy": flip_market_accuracy,
        })
    return rows


def current_slate_summary(predictions: pd.DataFrame) -> dict:
    required = {"pure_home_prob", "market_home_prob", "final_home_prob"}
    if predictions is None or predictions.empty or not required.issubset(predictions.columns):
        return {"games_with_market": 0}
    p = predictions.copy()
    for col in required:
        p[col] = pd.to_numeric(p[col], errors="coerce")
    p = p.dropna(subset=list(required))
    if p.empty:
        return {"games_with_market": 0}
    p["gap_pp"] = (p["pure_home_prob"] - p["market_home_prob"]).abs() * 100.0
    p["favorite_flip"] = (p["pure_home_prob"] >= 0.5) != (p["market_home_prob"] >= 0.5)
    correlation = float(p["pure_home_prob"].corr(p["market_home_prob"])) if len(p) > 1 else None
    top = p.sort_values("gap_pp", ascending=False).head(6)
    return {
        "games_with_market": int(len(p)),
        "pure_market_pearson": correlation,
        "mean_absolute_gap_pp": float(p["gap_pp"].mean()),
        "median_absolute_gap_pp": float(p["gap_pp"].median()),
        "favorite_flips": int(p["favorite_flip"].sum()),
        "gaps_5pp_or_more": int(p["gap_pp"].ge(5.0).sum()),
        "gaps_10pp_or_more": int(p["gap_pp"].ge(10.0).sum()),
        "largest_disagreements": [
            {
                "game_id": str(row.get("game_id") or ""),
                "away_team": str(row.get("away_team") or ""),
                "home_team": str(row.get("home_team") or ""),
                "pure_home_prob": float(row["pure_home_prob"]),
                "market_home_prob": float(row["market_home_prob"]),
                "final_home_prob": float(row["final_home_prob"]),
                "gap_pp": float(row["gap_pp"]),
                "favorite_flip": bool(row["favorite_flip"]),
            }
            for _, row in top.iterrows()
        ],
    }


def build_market_diagnostics(
    historical: pd.DataFrame,
    core_oof: pd.DataFrame,
    predictions: pd.DataFrame | None = None,
    current_weight: float = DEFAULT_MARKET_WEIGHT,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    frame = prepare_market_frame(historical, core_oof)
    grid = build_weight_grid(frame)
    walk = build_walk_forward_blend(frame)

    if frame.empty:
        return {
            "status": "unavailable",
            "historical_market_scope": "closing-line benchmark",
            "production_market_weight": current_weight,
            "warning": "No common PURE/market OOS sample was available.",
        }, grid, walk

    y = frame["home_win"]
    pure_metrics = probability_metrics(y, frame["pure"])
    market_metrics = probability_metrics(y, frame["market"])
    current_metrics = probability_metrics(
        y,
        blend_probabilities(frame["pure"], frame["market"], current_weight, "linear"),
    )
    best_rows = (
        grid.sort_values(["method", "brier", "log_loss"])
        .groupby("method", as_index=False)
        .first()
    )
    best = {
        str(row["method"]): {
            "market_weight": float(row["market_weight"]),
            "games": int(row["games"]),
            "winner_pct": float(row["winner_pct"]),
            "brier": float(row["brier"]),
            "log_loss": float(row["log_loss"]),
        }
        for _, row in best_rows.iterrows()
    }
    analytic = analytic_linear_brier_weight(frame)
    audit = {
        "status": "healthy",
        "historical_market_scope": "closing-line benchmark from nflverse schedules",
        "production_lock_scope": "T-120; starting in 2026 the immutable official row preserves the contemporaneous market probability",
        "production_market_weight": float(current_weight),
        "production_blend": "linear probability blend",
        "sample_games": int(len(frame)),
        "sample_seasons": sorted(int(x) for x in frame["season"].unique()),
        "pure_market_pearson": float(frame["pure"].corr(frame["market"])),
        "mean_absolute_pure_market_gap_pp": float(frame["gap"].mean() * 100.0),
        "median_absolute_pure_market_gap_pp": float(frame["gap"].median() * 100.0),
        "favorite_flip_rate": float(frame["favorite_flip"].mean()),
        "pure": pure_metrics,
        "market": market_metrics,
        "current_75_25": current_metrics,
        "current_minus_market_brier": float(current_metrics["brier"] - market_metrics["brier"]),
        "pure_minus_market_brier": float(pure_metrics["brier"] - market_metrics["brier"]),
        "descriptive_closing_line_best": best,
        "analytic_linear_brier_weight": analytic,
        "walk_forward_weight_selection": summarize_walk_forward(frame, walk),
        "disagreement_buckets": disagreement_buckets(frame, current_weight),
        "current_slate": current_slate_summary(predictions) if predictions is not None else None,
        "guardrails": [
            "Closing lines are a stronger and later information set than a T-120 production market snapshot; closing-line optimums must not be promoted directly into the live blend.",
            "2026 outcomes are forward-test evidence and are never used to retune the architecture or market weight.",
            "Any future production-weight change must be selected with chronology-preserving OOS validation and, once enough data exist, a market snapshot aligned to the same T-120 horizon as the official LevLine lock.",
            "StatMuse is research/manual QA only and is not a production market feed.",
        ],
    }
    return audit, grid, walk

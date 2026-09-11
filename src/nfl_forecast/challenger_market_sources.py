from __future__ import annotations

"""Research-only normalization and aggregation for multiple market sources.

This module never feeds production LevLine.  It keeps sportsbook and prediction-exchange
probabilities separately identifiable so source quality, freshness and aggregation methods
can be evaluated before any production use is considered.
"""

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

EPS = 1e-6
ALLOWED_SOURCE_TYPES = {"sportsbook", "prediction_exchange"}


def american_to_probability(value: float) -> float:
    x = float(value)
    if x == 0:
        raise ValueError("American odds cannot be zero")
    return (-x) / ((-x) + 100.0) if x < 0 else 100.0 / (x + 100.0)


def devig_two_way(home_odds: float, away_odds: float) -> float:
    home = american_to_probability(home_odds)
    away = american_to_probability(away_odds)
    denom = home + away
    if not np.isfinite(denom) or denom <= 0:
        raise ValueError("Invalid two-way market")
    return float(np.clip(home / denom, EPS, 1.0 - EPS))


def exchange_mid_probability(
    *,
    yes_bid: float | None = None,
    yes_ask: float | None = None,
    last_price: float | None = None,
) -> float:
    """Return a conservative exchange probability proxy from observable prices."""
    if yes_bid is not None and yes_ask is not None:
        bid, ask = float(yes_bid), float(yes_ask)
        if not (0 <= bid <= ask <= 1):
            raise ValueError("Exchange bid/ask must satisfy 0 <= bid <= ask <= 1")
        value = (bid + ask) / 2.0
    elif last_price is not None:
        value = float(last_price)
    else:
        raise ValueError("Need bid/ask midpoint or last_price")
    if not 0 < value < 1:
        raise ValueError("Exchange probability proxy must be inside (0, 1)")
    return value


def normalize_market_rows(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "game_id", "source_name", "source_type", "snapshot_timestamp_utc", "home_probability"
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"market source frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["source_type"] = work.source_type.astype(str)
    invalid = set(work.source_type) - ALLOWED_SOURCE_TYPES
    if invalid:
        raise ValueError(f"Unsupported market source types: {sorted(invalid)}")
    work["snapshot_timestamp_utc"] = pd.to_datetime(
        work.snapshot_timestamp_utc, utc=True, errors="coerce"
    )
    work["home_probability"] = pd.to_numeric(work.home_probability, errors="coerce")
    work = work.dropna(subset=["game_id", "source_name", "snapshot_timestamp_utc", "home_probability"])
    if ((work.home_probability <= 0.0) | (work.home_probability >= 1.0)).any():
        raise ValueError("Market source probabilities must be inside (0, 1)")
    if work.duplicated(["game_id", "source_name", "snapshot_timestamp_utc"]).any():
        raise ValueError("Duplicate market-source snapshot identity")
    return work


def _logit(values: np.ndarray) -> np.ndarray:
    p = np.clip(values.astype(float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def robust_logit_consensus(
    probabilities: Sequence[float],
    *,
    weights: Sequence[float] | None = None,
) -> float:
    p = np.asarray(probabilities, dtype=float)
    if len(p) == 0 or not np.isfinite(p).all():
        raise ValueError("Consensus requires finite probabilities")
    if ((p <= 0.0) | (p >= 1.0)).any():
        raise ValueError("Consensus probabilities must be inside (0, 1)")
    z = _logit(p)
    if weights is None:
        pooled = float(np.median(z))
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(z) or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
            raise ValueError("Invalid precommitted consensus weights")
        pooled = float(np.average(z, weights=w))
    return float(1.0 / (1.0 + np.exp(-pooled)))


def latest_source_snapshot(
    frame: pd.DataFrame,
    *,
    target_timestamp_utc: object,
    max_staleness_minutes: float = 15.0,
) -> pd.DataFrame:
    """Take each source's latest observation at-or-before a research target timestamp."""
    work = normalize_market_rows(frame)
    target = pd.Timestamp(target_timestamp_utc)
    if target.tzinfo is None:
        target = target.tz_localize("UTC")
    else:
        target = target.tz_convert("UTC")
    eligible = work[work.snapshot_timestamp_utc <= target].copy()
    if eligible.empty:
        return eligible
    eligible = eligible.sort_values("snapshot_timestamp_utc", kind="stable").drop_duplicates(
        ["game_id", "source_name"], keep="last"
    )
    eligible["staleness_minutes"] = (
        target - eligible.snapshot_timestamp_utc
    ).dt.total_seconds() / 60.0
    return eligible[eligible.staleness_minutes <= float(max_staleness_minutes)].copy()


def build_family_composites(
    frame: pd.DataFrame,
    *,
    target_timestamp_utc: object,
    source_weights: Mapping[str, float] | None = None,
    max_staleness_minutes: float = 15.0,
    min_sources: int = 2,
) -> pd.DataFrame:
    """Build sportsbook, exchange and all-source composites without erasing provenance."""
    latest = latest_source_snapshot(
        frame,
        target_timestamp_utc=target_timestamp_utc,
        max_staleness_minutes=max_staleness_minutes,
    )
    if latest.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for game_id, game in latest.groupby("game_id", sort=True):
        families = {
            "sportsbook_consensus": game[game.source_type.eq("sportsbook")],
            "exchange_consensus": game[game.source_type.eq("prediction_exchange")],
            "all_source_consensus": game,
        }
        for label, part in families.items():
            if len(part) < int(min_sources):
                continue
            probabilities = part.home_probability.to_numpy(dtype=float)
            if source_weights:
                weights = [float(source_weights.get(str(name), 0.0)) for name in part.source_name]
                if sum(weights) <= 0:
                    probability = robust_logit_consensus(probabilities)
                    weighting = "median_logit"
                else:
                    probability = robust_logit_consensus(probabilities, weights=weights)
                    weighting = "precommitted_weighted_logit"
            else:
                probability = robust_logit_consensus(probabilities)
                weighting = "median_logit"
            rows.append(
                {
                    "game_id": game_id,
                    "composite": label,
                    "home_probability": probability,
                    "sources": int(len(part)),
                    "source_names": "|".join(sorted(part.source_name.astype(str))),
                    "weighting": weighting,
                    "target_timestamp_utc": pd.Timestamp(target_timestamp_utc).isoformat(),
                    "max_staleness_minutes": float(max_staleness_minutes),
                    "max_observed_staleness_minutes": float(part.staleness_minutes.max()),
                    "research_only": True,
                    "production_authorized": False,
                }
            )
    return pd.DataFrame(rows)

from __future__ import annotations

"""Proper distribution metrics for LevLine Props research."""

import math
from typing import Iterable

import numpy as np


def empirical_crps(samples: Iterable[float], observation: float) -> float:
    """Exact CRPS for an equally weighted empirical predictive distribution.

    CRPS(F, y) = E|X-y| - 0.5 E|X-X'|.

    The pairwise term is computed from sorted samples in O(n log n), avoiding an O(n^2)
    distance matrix for 20,000-draw Monte Carlo forecasts.
    """
    values = np.asarray(list(samples) if not isinstance(samples, np.ndarray) else samples, dtype=float)
    values = values[np.isfinite(values)]
    y = float(observation)
    if not math.isfinite(y):
        raise ValueError("observation must be finite")
    if values.size == 0:
        raise ValueError("CRPS requires at least one finite sample")
    ordered = np.sort(values)
    n = ordered.size
    first = float(np.mean(np.abs(ordered - y)))
    weights = 2.0 * np.arange(n, dtype=float) - float(n) + 1.0
    half_pairwise = float(np.dot(weights, ordered) / float(n * n))
    score = first - half_pairwise
    return float(max(0.0, score))


def central_interval_score(
    lower: float,
    upper: float,
    observation: float,
    *,
    level: float,
) -> float:
    """Gneiting-Raftery interval score for a central prediction interval."""
    lo = float(lower)
    hi = float(upper)
    y = float(observation)
    level = float(level)
    if not all(math.isfinite(v) for v in (lo, hi, y, level)):
        raise ValueError("interval score inputs must be finite")
    if hi < lo:
        raise ValueError("upper interval endpoint must be >= lower")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be inside (0,1)")
    alpha = 1.0 - level
    penalty = 0.0
    if y < lo:
        penalty = (2.0 / alpha) * (lo - y)
    elif y > hi:
        penalty = (2.0 / alpha) * (y - hi)
    return float((hi - lo) + penalty)


def interval_covered(lower: float, upper: float, observation: float) -> bool:
    lo = float(lower)
    hi = float(upper)
    y = float(observation)
    if not all(math.isfinite(v) for v in (lo, hi, y)):
        raise ValueError("coverage inputs must be finite")
    return bool(lo <= y <= hi)

"""Exploratory, push-aware integer-margin/total distributions.

Independent of official F-ST moneyline estimates. The normal latent distribution
is deliberately NOT NFL-calibrated and must not be used for certified betting EV.
"""
from __future__ import annotations

from math import ceil, erf, floor, isfinite, sqrt


def _cdf(z: float) -> float:
    return (1.0 + erf(z / sqrt(2.0))) / 2.0


def approximate_integer_line_outcomes(mean: float, sigma: float, threshold: float, direction: str) -> dict[str,float]:
    """Probabilities for rounded integer outcome against integer/half-point threshold.

    direction='over': win if rounded outcome > threshold; under: win if < threshold.
    A whole-number threshold can push. Same support used for cover and totals.
    An exact integer margin is approximated as latent Normal rounded to nearest int.
    """
    if not all(isfinite(x) for x in (mean, sigma, threshold)) or sigma <= 0:
        raise ValueError('invalid uncalibrated distribution parameters')
    if direction not in ('over', 'under'):
        raise ValueError('direction must be over or under')
    if abs(threshold * 2 - round(threshold * 2)) > 1e-9:
        raise ValueError('whole/half-number line required; Asian quarter lines need separate settlement')
    # E.g. margin > 3 -> winning integers >=4 -> cutoff 3.5.
    first_win = floor(threshold) + 1
    over = 1.0 - _cdf((first_win - .5 - mean) / sigma)
    # E.g. margin < 3 -> winning integers <=2 -> cutoff 2.5.
    last_under = ceil(threshold) - 1
    under = _cdf((last_under + .5 - mean) / sigma)
    push = 1.0 - over - under
    # Floating-point normalization only, not artificial new push mass.
    if abs(threshold-round(threshold)) > 1e-9:
        push = 0.0
    vals = (over, under, push)
    if min(vals) < -1e-8 or max(vals) > 1 + 1e-8:
        raise ValueError('invalid derived outcome probabilities')
    return {'win': max(0., min(1., over if direction == 'over' else under)),
            'push':max(0.,min(1.,push)),
            'loss':max(0.,min(1.,under if direction == 'over' else over))}
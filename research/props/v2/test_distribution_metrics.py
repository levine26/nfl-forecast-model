from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from distribution_metrics import (
    central_interval_score,
    empirical_crps,
    interval_covered,
)


def test_empirical_crps_degenerate_distribution_is_absolute_error():
    assert empirical_crps(np.asarray([5.0, 5.0, 5.0]), 3.0) == pytest.approx(2.0)


def test_empirical_crps_two_point_distribution_matches_direct_formula():
    assert empirical_crps(np.asarray([0.0, 1.0]), 0.5) == pytest.approx(0.25)


def test_empirical_crps_is_zero_for_perfect_degenerate_forecast():
    assert empirical_crps(np.asarray([7.0]), 7.0) == pytest.approx(0.0)


def test_interval_score_penalizes_miss_by_alpha_scaled_distance():
    # 80% interval => alpha=.2, so miss penalty multiplier is 10.
    assert central_interval_score(10.0, 20.0, 25.0, level=0.80) == pytest.approx(60.0)
    assert central_interval_score(10.0, 20.0, 15.0, level=0.80) == pytest.approx(10.0)


def test_interval_coverage_is_inclusive():
    assert interval_covered(10.0, 20.0, 10.0)
    assert interval_covered(10.0, 20.0, 20.0)
    assert not interval_covered(10.0, 20.0, 21.0)

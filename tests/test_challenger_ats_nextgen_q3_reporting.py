from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_forecast.challenger_ats_nextgen_q3_reporting import (
    q3_cover_reliability,
    q3_fixed_slice_metrics,
    q3_metric_table,
    q3_push_calibration,
)


def _fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2022, 2022, 2023, 2023],
            "home_spread": [-3.0, -3.5, 7.0, 3.0],
            "favorite_size": [3.0, 3.5, 7.0, 3.0],
            "market_total": [44.0, 46.0, 41.0, 49.0],
            "ats_outcome": ["PUSH", "HOME_COVER", "HOME_LOSS", "HOME_COVER"],
            "q3_m2_p_cover": [0.40, 0.65, 0.25, 0.55],
            "q3_m2_p_push": [0.20, 0.00, 0.10, 0.15],
            "q3_m2_p_loss": [0.40, 0.35, 0.65, 0.30],
            "q3_p_cover": [0.35, 0.70, 0.20, 0.60],
            "q3_p_push": [0.25, 0.00, 0.12, 0.10],
            "q3_p_loss": [0.40, 0.30, 0.68, 0.30],
        }
    )


def test_metric_table_preserves_three_outcome_pushes_and_nonpush_cover_scores():
    metrics = q3_metric_table(_fixture())
    overall = metrics[metrics.season.eq("ALL")]
    assert set(overall.arm) == {"Q3_M2", "Q3"}
    assert set(overall.n) == {4}
    assert set(overall.nonpush_n) == {3}
    assert set(overall.push_n) == {1}
    assert np.isfinite(overall.multinomial_cpl_logloss).all()
    assert np.isfinite(overall.cover_brier_nonpush).all()


def test_cover_reliability_uses_exact_ten_fixed_bins_and_excludes_push_observation():
    reliability = q3_cover_reliability(_fixture())
    assert reliability.groupby("arm").size().eq(10).all()
    assert reliability.groupby("arm").n.sum().eq(3).all()
    assert reliability.lower.min() == 0.0
    assert reliability.upper.max() == 1.0


def test_push_calibration_reports_overall_season_and_frozen_exact_keys():
    calibration = q3_push_calibration(_fixture())
    assert set(calibration.group_type) == {"overall", "season", "key_number"}
    assert set(calibration[calibration.group_type.eq("overall")].group) == {"ALL"}
    assert {"K3", "K7"}.issubset(set(calibration[calibration.group_type.eq("key_number")].group))
    assert set(calibration.arm) == {"Q3_M2", "Q3"}


def test_fixed_slice_reporting_reuses_only_preregistered_bucket_types():
    slices = q3_fixed_slice_metrics(_fixture())
    assert set(slices.slice_type).issubset({"key_number", "favorite_size", "market_total"})
    assert set(slices.arm) == {"Q3_M2", "Q3"}

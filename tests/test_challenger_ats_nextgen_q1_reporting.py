from __future__ import annotations

import pandas as pd

from nfl_forecast.challenger_ats_nextgen_q1_reporting import (
    FAVORITE_SIZE_BUCKETS,
    KEY_NUMBER_BUCKETS,
    TOTAL_BUCKETS,
    fixed_slice_masks,
    q1_fixed_slice_metrics,
)


def _oof_fixture() -> pd.DataFrame:
    favorite = [2.5, 3.0, 3.5, 5.5, 6.0, 6.5, 7.0, 7.5, 9.5, 10.0, 10.5, 13.5, 14.0, 14.5]
    total = [41.0, 42.0, 44.5, 45.0, 47.5, 48.0, 40.0, 43.0, 46.0, 49.0, 44.0, 47.0, 50.0, 41.5]
    residual = [1.0, 0.0, -1.0, 2.0, -2.0, 1.5, -1.5, 0.5, -0.5, 3.0, -3.0, 4.0, -4.0, 2.5]
    frame = pd.DataFrame(
        {
            "favorite_size": favorite,
            "market_total": total,
            "ats_residual": residual,
        }
    )
    for prefix in ("m0", "m2", "q1"):
        frame[f"{prefix}_q_low"] = 0.0
        frame[f"{prefix}_q_med"] = 0.0
        frame[f"{prefix}_q_high"] = 0.0
    return frame


def test_fixed_slice_definitions_match_preregistered_protocol_exactly():
    assert KEY_NUMBER_BUCKETS == {
        "K3": (2.5, 3.0, 3.5),
        "K6": (5.5, 6.0, 6.5),
        "K7": (6.5, 7.0, 7.5),
        "K10": (9.5, 10.0, 10.5),
        "K14": (13.5, 14.0, 14.5),
    }
    assert FAVORITE_SIZE_BUCKETS == (
        ("FAV_LT3", 0.0, 3.0, False),
        ("FAV_3_LT7", 3.0, 7.0, False),
        ("FAV_7_LT10", 7.0, 10.0, False),
        ("FAV_10_LT14", 10.0, 14.0, False),
        ("FAV_GE14", 14.0, float("inf"), True),
    )
    assert TOTAL_BUCKETS == (
        ("TOTAL_LT42", float("-inf"), 42.0, False),
        ("TOTAL_42_LT45", 42.0, 45.0, False),
        ("TOTAL_45_LT48", 45.0, 48.0, False),
        ("TOTAL_GE48", 48.0, float("inf"), True),
    )


def test_key_bucket_overlap_at_6_5_is_preserved():
    frame = _oof_fixture()
    masks = {(kind, name): mask for kind, name, mask in fixed_slice_masks(frame)}
    index_65 = frame.index[frame.favorite_size.eq(6.5)][0]
    assert bool(masks[("key_number", "K6")].loc[index_65]) is True
    assert bool(masks[("key_number", "K7")].loc[index_65]) is True


def test_fixed_slice_metrics_emit_only_frozen_dimensions_and_all_three_arms():
    metrics = q1_fixed_slice_metrics(_oof_fixture())
    assert set(metrics["slice_type"]) == {"key_number", "favorite_size", "market_total"}
    assert set(metrics["arm"]) == {"M0", "M2", "Q1"}
    assert set(metrics["quantile_label"]) == {"low", "med", "high"}
    assert set(metrics.loc[metrics.slice_type.eq("key_number"), "slice"]) == set(
        KEY_NUMBER_BUCKETS
    )
    assert set(metrics.loc[metrics.slice_type.eq("favorite_size"), "slice"]) == {
        row[0] for row in FAVORITE_SIZE_BUCKETS
    }
    assert set(metrics.loc[metrics.slice_type.eq("market_total"), "slice"]) == {
        row[0] for row in TOTAL_BUCKETS
    }
    assert metrics["pinball_loss"].notna().all()
    assert metrics["empirical_coverage"].between(0.0, 1.0).all()

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_ats_nextgen_gate import build_historical_ats_gate
from nfl_forecast.challenger_ats_nextgen_q2 import SUPPORT, SUPPORT_SIZE, q1_median_center_for_target
from nfl_forecast.challenger_ats_nextgen_q2_experiment import (
    ARM_CONFIGS,
    EMP_ARM,
    select_spec,
    target_data,
)
from nfl_forecast.challenger_ats_nextgen_q2_reporting import (
    q2_cover_reliability,
    q2_fixed_slice_metrics,
    q2_metric_table,
)


def _source_frame(rows_per_season: int = 30) -> pd.DataFrame:
    rows: list[dict] = []
    for season in range(2015, 2026):
        for i in range(rows_per_season):
            center = float(((i % 11) - 5) * 0.5)
            margin = int(((season * 7 + i * 5) % 31) - 15)
            home_score = 24 + max(margin, 0)
            away_score = 24 + max(-margin, 0)
            base = (season - 2015) * 0.01 + (i % 9) * 0.004
            rows.append(
                {
                    "game_id": f"{season}_{i + 1:02d}_A_B",
                    "season": season,
                    "week": (i % 18) + 1,
                    "gameday": f"{season}-09-{(i % 28) + 1:02d}",
                    "gametime": "13:00",
                    "game_type": "REG",
                    "away_team": "A",
                    "home_team": "B",
                    "home_score": home_score,
                    "away_score": away_score,
                    "spread_line": center,
                    "total_line": 41.0 + (i % 10),
                    "home_moneyline": -120 - (i % 40),
                    "away_moneyline": 110 + (i % 40),
                    "home_elo": 1510.0 + season - 2015 + i * 0.1,
                    "away_elo": 1490.0 - i * 0.1,
                    "diff_off_epa_ewma": 0.10 + base,
                    "diff_def_epa_allowed_ewma": -0.04 + base,
                    "diff_pass_epa_ewma": 0.12 + base,
                    "diff_def_pass_epa_allowed_ewma": -0.05 + base,
                    "diff_rush_epa_ewma": 0.02 + base,
                    "diff_def_rush_epa_allowed_ewma": -0.01 + base,
                    "diff_success_rate_ewma": 0.03 + base,
                    "diff_def_success_allowed_ewma": -0.02 + base,
                    "diff_neutral_epa_ewma": 0.08 + base,
                    "rest_diff": float((i % 3) - 1),
                }
            )
    return pd.DataFrame(rows)


def _gate() -> pd.DataFrame:
    return build_historical_ats_gate(_source_frame())


def test_frozen_stage_b_arm_set_is_bounded():
    assert tuple(ARM_CONFIGS) == (
        "GN_NO_KEY",
        "GN_KEY_CONST",
        "GN_FULL",
        "N_FULL",
        "T_FULL",
    )
    expected = {
        f"{mode}_{suffix}"
        for mode in ("M1", "Q2")
        for suffix in (*ARM_CONFIGS.keys(), EMP_ARM)
    }
    assert len(expected) == 12


def test_q2_target_center_is_oos_and_aligned_to_frozen_q1_helper():
    gate = _gate()
    data = target_data(gate, 2022, "Q2", q1_cache={})
    upstream = q1_median_center_for_target(gate, 2022)
    market = pd.to_numeric(data.target.market_home_margin_center, errors="raise").to_numpy()
    assert tuple(data.target.game_id.astype(str)) == upstream.target_game_ids
    assert np.allclose(
        data.target_centers,
        market + np.asarray(upstream.target_residual_prediction),
    )
    assert data.q1_inner_targets_used == (2019, 2020, 2021)


def test_norm_no_key_selection_uses_only_2020_2021_for_outer_2022():
    gate = _gate()
    selected, table = select_spec(
        gate,
        outer_target_season=2022,
        center_mode="M1",
        family="norm",
        ablation="no_key_conditional_scale",
        q1_cache={},
        score_cache={},
    )
    assert selected.family == "norm"
    assert selected.shape is None
    assert selected.key_penalty is None
    assert table.shape[0] == 1
    assert table.iloc[0].inner_targets_used == "2020,2021"
    assert bool(table.iloc[0].inner_target_2019_omitted) is True
    assert bool(table.iloc[0].selected) is True


def _report_fixture() -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    metadata = pd.DataFrame(
        {
            "game_id": ["g1", "g2", "g3"],
            "season": [2022, 2022, 2023],
            "home_spread": [-3.0, -3.5, 3.0],
            "favorite_size": [3.0, 3.5, 3.0],
            "market_total": [44.0, 46.0, 41.0],
            "margin": [3.0, 7.0, -3.0],
            "ats_outcome": ["PUSH", "HOME_COVER", "PUSH"],
        }
    )
    pmf = np.full((3, SUPPORT_SIZE), 1e-12)
    pmf[0, int(3 - SUPPORT[0])] = 1.0
    pmf[1, int(7 - SUPPORT[0])] = 1.0
    pmf[2, int(-3 - SUPPORT[0])] = 1.0
    pmf /= pmf.sum(axis=1, keepdims=True)
    return metadata, {"M1_GN_FULL": pmf, "Q2_GN_FULL": pmf.copy()}


def test_reporting_preserves_pushes_and_fixed_reliability_bins():
    metadata, arms = _report_fixture()
    metrics = q2_metric_table(metadata, arms)
    overall = metrics[metrics.season.eq("ALL")]
    assert set(overall.arm) == set(arms)
    assert set(overall.nonpush_n) == {1}
    assert np.allclose(overall.empirical_push_rate, 2.0 / 3.0)
    reliability = q2_cover_reliability(metadata, arms)
    assert reliability.groupby("arm").size().eq(10).all()
    assert reliability.groupby("arm").n.sum().eq(1).all()


def test_reporting_uses_only_frozen_slice_definitions():
    metadata, arms = _report_fixture()
    slices = q2_fixed_slice_metrics(metadata, arms)
    assert set(slices.slice_type).issubset({"key_number", "favorite_size", "market_total"})
    assert "K3" in set(slices["slice"])
    assert set(slices.arm) == set(arms)

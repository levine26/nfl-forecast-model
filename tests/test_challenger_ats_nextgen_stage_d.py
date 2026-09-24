from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_ats_nextgen_q1 import QUANTILES
from nfl_forecast.challenger_ats_nextgen_stage_d import (
    BOOTSTRAP_SAMPLES,
    align_q1_q3_oof,
    clopper_pearson,
    paired_block_bootstrap,
    pinball_loss,
    q1_row_losses,
    q3_hit_rate_intervals,
    q3_multinomial_row_losses,
    q3_nonpush_brier_row_losses,
    stage_d_uncertainty,
)


def _identity(n_per_season: int = 2) -> pd.DataFrame:
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for i in range(n_per_season):
            rows.append(
                {
                    "game_id": f"{season}_{i + 1:02d}_A_B",
                    "season": season,
                    "week": i + 1,
                }
            )
    return pd.DataFrame(rows)


def _q1() -> pd.DataFrame:
    frame = _identity()
    y = np.array([-3.0, 2.0, -1.0, 4.0, -2.0, 1.0, 0.0, 3.0])
    frame["ats_residual"] = y
    for label, shift in (("low", -0.5), ("med", 0.0), ("high", 0.5)):
        frame[f"m2_q_{label}"] = y + shift + 0.20
        frame[f"q1_q_{label}"] = y + shift + 0.10
    return frame


def _q3() -> pd.DataFrame:
    frame = _identity()
    outcomes = [
        "HOME_COVER", "HOME_LOSS", "PUSH", "HOME_COVER",
        "HOME_LOSS", "HOME_COVER", "HOME_LOSS", "HOME_COVER",
    ]
    frame["ats_outcome"] = outcomes
    q3 = np.array(
        [
            [0.70, 0.05, 0.25], [0.25, 0.05, 0.70], [0.45, 0.10, 0.45], [0.65, 0.05, 0.30],
            [0.30, 0.05, 0.65], [0.60, 0.05, 0.35], [0.35, 0.05, 0.60], [0.65, 0.05, 0.30],
        ]
    )
    m2 = np.array(
        [
            [0.65, 0.05, 0.30], [0.30, 0.05, 0.65], [0.45, 0.10, 0.45], [0.60, 0.05, 0.35],
            [0.35, 0.05, 0.60], [0.55, 0.05, 0.40], [0.40, 0.05, 0.55], [0.60, 0.05, 0.35],
        ]
    )
    for prefix, values in (("q3", q3), ("q3_m2", m2)):
        frame[f"{prefix}_p_cover"] = values[:, 0]
        frame[f"{prefix}_p_push"] = values[:, 1]
        frame[f"{prefix}_p_loss"] = values[:, 2]
    return frame


def test_pinball_loss_uses_frozen_quantiles_and_orientation():
    y = np.array([2.0, -2.0])
    p = np.array([0.0, 0.0])
    low = pinball_loss(y, p, QUANTILES[0])
    assert low[0] == pytest.approx(2.0 * QUANTILES[0])
    assert low[1] == pytest.approx(2.0 * (1.0 - QUANTILES[0]))
    with pytest.raises(ValueError, match="outside the frozen quantile"):
        pinball_loss(y, p, 0.25)


def test_q1_primary_row_loss_is_mean_of_three_pinballs():
    frame = _q1()
    q1, m2 = q1_row_losses(frame)
    assert len(q1) == len(frame)
    assert len(m2) == len(frame)
    assert np.isfinite(q1).all()
    assert np.isfinite(m2).all()
    assert float(q1.mean()) < float(m2.mean())


def test_q3_primary_and_secondary_losses_use_matching_null():
    frame = _q3()
    q3, m2 = q3_multinomial_row_losses(frame)
    q3_brier, m2_brier, nonpush = q3_nonpush_brier_row_losses(frame)
    assert len(q3) == len(frame)
    assert len(q3_brier) == len(frame)
    assert int(nonpush.sum()) == 7
    assert float(q3.mean()) < float(m2.mean())
    assert float(q3_brier[nonpush].mean()) < float(m2_brier[nonpush].mean())


def test_alignment_requires_exact_game_season_week_identity():
    q1 = _q1()
    q3 = _q3()
    left, right = align_q1_q3_oof(q1, q3)
    assert left["game_id"].tolist() == right["game_id"].tolist()

    bad = q3.copy()
    bad.loc[0, "week"] = 18
    with pytest.raises(ValueError, match="week labels differ"):
        align_q1_q3_oof(q1, bad)

    duplicate = pd.concat([q1, q1.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate game_id"):
        align_q1_q3_oof(duplicate, q3)


def test_bootstrap_is_exactly_frozen_and_deterministic():
    frame = _q1()
    candidate = np.arange(len(frame), dtype=float) / 10.0
    reference = candidate + 0.1
    first = paired_block_bootstrap(
        frame,
        candidate,
        reference,
        metric="synthetic",
        candidate="candidate",
        reference="reference",
    )
    second = paired_block_bootstrap(
        frame,
        candidate,
        reference,
        metric="synthetic",
        candidate="candidate",
        reference="reference",
    )
    assert first == second
    assert first.samples == BOOTSTRAP_SAMPLES
    assert first.block == "season+week"
    assert first.observed_delta == pytest.approx(-0.1)
    assert first.probability_better == pytest.approx(1.0)

    with pytest.raises(ValueError, match="frozen at 10000"):
        paired_block_bootstrap(
            frame,
            candidate,
            reference,
            metric="synthetic",
            candidate="candidate",
            reference="reference",
            samples=9999,
        )
    with pytest.raises(ValueError, match="seed is frozen"):
        paired_block_bootstrap(
            frame,
            candidate,
            reference,
            metric="synthetic",
            candidate="candidate",
            reference="reference",
            seed=27,
        )


def test_clopper_pearson_is_exact_and_handles_boundaries():
    low0, high0 = clopper_pearson(0, 10)
    low1, high1 = clopper_pearson(10, 10)
    assert low0 == 0.0
    assert 0.0 < high0 < 1.0
    assert 0.0 < low1 < 1.0
    assert high1 == 1.0


def test_q3_hit_rate_interval_excludes_push_rows():
    rows = q3_hit_rate_intervals(_q3())
    assert {row.arm for row in rows} == {"Q3", "Q3_M2"}
    assert all(row.rows == 7 for row in rows)
    assert all(0.0 <= row.ci_lower <= row.hit_rate <= row.ci_upper <= 1.0 for row in rows)


def test_stage_d_uncertainty_emits_only_three_preregistered_comparisons():
    out = stage_d_uncertainty(_q1(), _q3())
    assert out["metric"].tolist() == [
        "mean_three_quantile_pinball",
        "multinomial_cover_push_loss_log_loss",
        "nonpush_conditional_cover_brier",
    ]
    assert out["candidate"].tolist() == ["Q1", "Q3", "Q3"]
    assert out["reference"].tolist() == ["M2", "Q3_M2", "Q3_M2"]
    assert set(out["samples"]) == {10_000}
    assert set(out["block"]) == {"season+week"}

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from nfl_forecast.challenger_ats_nextgen_gate import build_historical_ats_gate
from nfl_forecast.challenger_ats_nextgen_q1 import (
    _fit_quantile_model,
    select_alpha,
)
from nfl_forecast.challenger_ats_nextgen_q2 import (
    BOUNDARY_MASS_LIMIT,
    CANDIDATE_ID,
    EMP_PER_BIN_PSEUDOCOUNT,
    GN_BETA_GRID,
    KEY_PENALTY_GRID,
    SCALE_GUARD,
    SUPPORT,
    SUPPORT_SIZE,
    T_DF_GRID,
    ScaleFit,
    _apply_key_excess,
    _key_theta_lookup,
    continuous_base_pmf,
    cover_push_loss_probabilities,
    discrete_crps,
    empirical_residual_pmf,
    fit_scale,
    predict_scale,
    q1_median_center_for_target,
    select_simple_tie,
    validate_pmf,
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
                    "total_line": np.nan if i % 13 == 0 else 41.0 + (i % 10),
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


def test_q2_identity_and_grids_are_frozen():
    assert CANDIDATE_ID == "ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1"
    assert tuple(SUPPORT) == tuple(range(-75, 76))
    assert SUPPORT_SIZE == 151
    assert GN_BETA_GRID == (1.0, 1.25, 1.5, 1.75, 2.0)
    assert T_DF_GRID == (4.0, 6.0, 10.0)
    assert KEY_PENALTY_GRID == (1.0, 10.0, 100.0)
    assert BOUNDARY_MASS_LIMIT == 1e-3
    assert EMP_PER_BIN_PSEUDOCOUNT == pytest.approx(1.0 / 151.0)


def test_integrated_gaussian_pmf_is_symmetric_and_normalized():
    pmf = continuous_base_pmf(
        np.array([0.0]),
        np.array([10.0]),
        family="norm",
        shape=None,
    )
    validate_pmf(pmf)
    assert np.allclose(pmf[0], pmf[0, ::-1], atol=1e-14, rtol=0.0)
    assert pmf.sum() == pytest.approx(1.0)


def test_endpoint_bins_fold_continuous_tails_exactly():
    mu = 0.0
    sigma = 10.0
    pmf = continuous_base_pmf(
        np.array([mu]), np.array([sigma]), family="norm", shape=None
    )[0]
    assert pmf[0] == pytest.approx(norm.cdf(-74.5, loc=mu, scale=sigma))
    assert pmf[-1] == pytest.approx(1.0 - norm.cdf(74.5, loc=mu, scale=sigma))


def test_whole_line_push_and_half_line_structural_zero():
    pmf = continuous_base_pmf(
        np.array([3.0, 3.0]),
        np.array([10.0, 10.0]),
        family="norm",
        shape=None,
    )
    probs = cover_push_loss_probabilities(pmf, np.array([-3.0, -3.5]))
    push_bin = int(3 - SUPPORT[0])
    assert probs[0, 1] == pytest.approx(pmf[0, push_bin])
    assert probs[1, 1] == pytest.approx(0.0, abs=1e-15)
    assert np.allclose(probs.sum(axis=1), 1.0)


def test_key_lookup_shares_positive_negative_absolute_key_when_band_matches():
    positions, lookup = _key_theta_lookup(np.array([0.0]))
    plus_three_col = list(positions).index(int(3 - SUPPORT[0]))
    minus_three_col = list(positions).index(int(-3 - SUPPORT[0]))
    assert lookup[0, plus_three_col] == lookup[0, minus_three_col]


def test_key_adjustment_preserves_mass_and_changes_only_through_renormalization():
    base = continuous_base_pmf(
        np.array([0.0]), np.array([10.0]), family="norm", shape=None
    )
    theta = np.zeros(15)
    theta[0] = 0.5
    adjusted = _apply_key_excess(base, np.array([0.0]), theta)
    validate_pmf(adjusted)
    assert adjusted.sum() == pytest.approx(1.0)
    assert not np.allclose(adjusted, base)


def test_empirical_reference_is_deterministic_smoothed_and_normalized():
    y = np.array([-7, -3, 0, 3, 7], dtype=float)
    train_center = np.zeros(5)
    target = np.array([0.0, 2.5])
    a = empirical_residual_pmf(y, train_center, target)
    b = empirical_residual_pmf(y, train_center, target)
    assert np.array_equal(a, b)
    assert (a > 0).all()
    validate_pmf(a)


def test_discrete_crps_rewards_point_mass_on_truth():
    truth = 4
    perfect = np.zeros((1, SUPPORT_SIZE))
    perfect[0, truth - SUPPORT[0]] = 1.0
    diffuse = np.full((1, SUPPORT_SIZE), 1.0 / SUPPORT_SIZE)
    perfect_score = discrete_crps(perfect, np.array([truth]))[0]
    diffuse_score = discrete_crps(diffuse, np.array([truth]))[0]
    assert perfect_score == pytest.approx(0.0)
    assert perfect_score < diffuse_score


def test_total_centering_is_training_only_and_missing_maps_to_center():
    gate = _gate()
    train = gate[gate.season <= 2019].copy()
    centers = pd.to_numeric(train.market_home_margin_center, errors="raise").to_numpy()
    fit = fit_scale(train, centers, family="norm", shape=None, conditional=True)
    expected = float(pd.to_numeric(train.market_total, errors="coerce").median())
    assert fit.total_median == pytest.approx(expected)
    target = gate[gate.season == 2020].copy()
    target.loc[target.index[0], "market_total"] = np.nan
    scale = predict_scale(target, fit)
    assert np.isfinite(scale).all()
    assert (scale > SCALE_GUARD[0]).all()
    assert (scale < SCALE_GUARD[1]).all()


def test_scale_guard_fails_closed_at_prediction_time():
    gate = _gate().head(2).copy()
    bad = ScaleFit(
        family="norm",
        shape=None,
        conditional=False,
        total_median=45.0,
        coefficients=(20.0,),
        objective=0.0,
    )
    with pytest.raises(RuntimeError, match="scale touched"):
        predict_scale(gate, bad)


def test_q2_inner_2019_is_mechanically_unavailable_without_fallback_alpha():
    with pytest.raises(ValueError, match="2019 is mechanically omitted"):
        q1_median_center_for_target(_gate(), 2019)


def test_generic_q1_center_reproduces_frozen_outer_median_logic():
    gate = _gate()
    center = q1_median_center_for_target(gate, 2022)
    selection = select_alpha(
        gate,
        outer_target_season=2022,
        feature_set="full",
        quantile=0.5,
    )
    assert center.selected_alpha == selection.selected_alpha
    train = gate[gate.season < 2022].copy()
    target = gate[gate.season == 2022].copy()
    expected = _fit_quantile_model(
        train,
        target,
        feature_set="full",
        quantile=0.5,
        alpha=selection.selected_alpha,
    )
    assert center.target_game_ids == tuple(target.game_id.astype(str))
    assert np.allclose(np.asarray(center.target_residual_prediction), expected)


def test_q2_ties_prefer_larger_simpler_grid_value():
    selected, score = select_simple_tie({1.0: 0.8, 10.0: 0.7, 100.0: 0.7})
    assert selected == 100.0
    assert score == 0.7

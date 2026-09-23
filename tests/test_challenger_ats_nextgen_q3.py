from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_ats_nextgen_gate import build_historical_ats_gate
from nfl_forecast.challenger_ats_nextgen_q1 import FOOTBALL_FEATURES
from nfl_forecast.challenger_ats_nextgen_q3 import (
    C_GRID,
    KEY_SPREADS,
    MIN_TRAIN_ROWS,
    _select_pair,
    fit_hurdle,
    fit_push_preprocessor,
    line_lattice,
    multinomial_log_loss,
    predict_hurdle,
    select_c_pair,
)


def _source(*, seasons=range(2015, 2023), rows_per_season: int = 48) -> pd.DataFrame:
    rows: list[dict] = []
    lines = (3.0, 3.5, 6.0, 6.5, 7.0, 7.5, 10.0, 14.0)
    for season in seasons:
        for i in range(rows_per_season):
            line = float(lines[i % len(lines)])
            whole = float(line).is_integer()
            # nflverse spread_line is positive when the home team is favored.
            # Canonical home_spread becomes -line and residual is margin-line.
            if whole and i % 6 == 0:
                margin = int(line)  # push
            elif i % 2 == 0:
                margin = int(np.ceil(line)) + 6  # cover
            else:
                margin = int(np.floor(line)) - 6  # loss
            home_score = 28 + max(margin, 0)
            away_score = 28 + max(-margin, 0)
            base = (season - 2015) * 0.002 + (i % 7) * 0.003
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
                    "spread_line": line,
                    "total_line": 42.0 + (i % 8),
                    "home_moneyline": -120 - (i % 30),
                    "away_moneyline": 110 + (i % 30),
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


def _gate(**kwargs) -> pd.DataFrame:
    return build_historical_ats_gate(_source(**kwargs))


def test_q3_frozen_c_and_key_grids_are_exact():
    assert C_GRID == (0.01, 0.1, 1.0, 10.0)
    assert KEY_SPREADS == (3.0, 6.0, 7.0, 10.0, 14.0)
    assert len({(a, b) for a in C_GRID for b in C_GRID}) == 16
    assert MIN_TRAIN_ROWS == 100


def test_line_lattice_distinguishes_whole_half_and_rejects_quarter_lines():
    frame = pd.DataFrame({"home_spread": [-3.0, 3.5, 0.0, -7.5]})
    whole, half = line_lattice(frame)
    assert whole.tolist() == [True, False, True, False]
    assert half.tolist() == [False, True, False, True]
    with pytest.raises(ValueError, match="off-lattice"):
        line_lattice(pd.DataFrame({"home_spread": [-3.25]}))


def test_push_preprocessor_is_market_only_plus_exact_five_keys():
    gate = _gate(seasons=range(2019, 2022), rows_per_season=64)
    whole, _ = line_lattice(gate)
    prep = fit_push_preprocessor(gate.loc[whole].copy())
    assert prep.base.feature_set == "market"
    assert prep.design_columns[-5:] == tuple(
        f"abs_spread_is_{int(k)}" for k in KEY_SPREADS
    )
    assert not any(feature in prep.design_columns for feature in FOOTBALL_FEATURES)


def test_hurdle_structural_zero_push_and_exact_three_way_normalization():
    gate = _gate(seasons=range(2017, 2022), rows_per_season=64)
    train = gate[gate.season.lt(2021)].copy()
    target = gate[gate.season.eq(2021)].copy()
    fit = fit_hurdle(train, arm="Q3", C_push=0.1, C_cover=0.1)
    probability = predict_hurdle(target, fit)
    whole, half = line_lattice(target)

    assert probability.shape == (len(target), 3)
    assert np.all(probability >= 0.0)
    assert np.all(probability <= 1.0)
    assert np.allclose(probability.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)
    assert np.all(probability[half, 1] == 0.0)
    assert np.any(probability[whole, 1] > 0.0)
    assert fit.push_model.class_weight is None
    assert fit.cover_model.class_weight is None
    assert fit.push_model.solver == "lbfgs"
    assert fit.cover_model.solver == "lbfgs"
    assert fit.cover_preprocessor.feature_set == "full"


def test_market_null_cover_head_excludes_football_features():
    gate = _gate(seasons=range(2017, 2022), rows_per_season=64)
    train = gate[gate.season.lt(2021)].copy()
    fit = fit_hurdle(train, arm="Q3_M2", C_push=1.0, C_cover=1.0)
    assert fit.cover_preprocessor.feature_set == "market"
    assert not any(feature in fit.cover_preprocessor.design_columns for feature in FOOTBALL_FEATURES)


def test_half_point_realized_push_is_rejected_before_fit():
    gate = _gate(seasons=range(2017, 2022), rows_per_season=64)
    half_index = gate.index[np.isclose(np.mod(np.abs(gate.home_spread), 1.0), 0.5)][0]
    corrupted = gate.copy()
    corrupted.loc[half_index, "ats_outcome"] = "PUSH"
    with pytest.raises(RuntimeError, match="impossible push"):
        fit_hurdle(corrupted, arm="Q3_M2", C_push=0.1, C_cover=0.1)


def test_multinomial_loss_keeps_push_as_third_outcome_not_binary_loss():
    probability = np.asarray(
        [
            [0.70, 0.10, 0.20],
            [0.20, 0.60, 0.20],
            [0.10, 0.20, 0.70],
        ],
        dtype=float,
    )
    outcomes = pd.Series(["HOME_COVER", "PUSH", "HOME_LOSS"])
    loss = multinomial_log_loss(probability, outcomes)
    assert np.allclose(loss, -np.log([0.70, 0.60, 0.70]))


def test_pair_tie_break_prefers_stronger_regularization_in_fixed_order():
    losses = {(a, b): 1.0 for a in C_GRID for b in C_GRID}
    C_push, C_cover, value = _select_pair(losses)
    assert (C_push, C_cover, value) == (0.01, 0.01, 1.0)


def test_inner_pair_selection_uses_only_prior_rolling_origin_seasons():
    gate = _gate(seasons=range(2015, 2023), rows_per_season=48)
    selected = select_c_pair(gate, outer_target_season=2022, arm="Q3_M2")
    assert selected.outer_target_season == 2022
    assert selected.arm == "Q3_M2"
    assert selected.C_push in C_GRID
    assert selected.C_cover in C_GRID
    assert selected.inner_targets_used == (2019, 2020, 2021)
    assert selected.inner_rows == 48 * 3
    assert len(selected.pair_losses) == 16

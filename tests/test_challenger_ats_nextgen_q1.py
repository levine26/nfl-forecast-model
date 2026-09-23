from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_ats_nextgen_gate import build_historical_ats_gate
from nfl_forecast.challenger_ats_nextgen_q1 import (
    ALPHA_GRID,
    CANDIDATE_ID,
    FOOTBALL_FEATURES,
    INTERACTION_FEATURES,
    MANDATORY_MARKET_FEATURES,
    OPTIONAL_MARKET_FEATURES,
    QUANTILES,
    choose_alpha,
    fit_preprocessor,
    quantile_crossing_table,
    select_alpha,
)


def _source_frame() -> pd.DataFrame:
    rows: list[dict] = []
    for season in range(2015, 2026):
        for i in range(8):
            center = float(((i % 5) - 2) * 1.5)
            margin = float(((season + i * 3) % 17) - 8)
            home_score = 24 + max(int(margin), 0)
            away_score = 24 + max(-int(margin), 0)
            base = (season - 2015) * 0.01 + i * 0.005
            rows.append(
                {
                    "game_id": f"{season}_{i + 1:02d}_A_B",
                    "season": season,
                    "week": i + 1,
                    "gameday": f"{season}-09-{i + 1:02d}",
                    "gametime": "13:00",
                    "game_type": "REG",
                    "away_team": "A",
                    "home_team": "B",
                    "home_score": home_score,
                    "away_score": away_score,
                    # nflverse source convention: + means home favored.
                    "spread_line": center,
                    "total_line": np.nan if i == 0 else 42.0 + (i % 7),
                    "home_moneyline": np.nan if i == 1 else -120 - i,
                    "away_moneyline": np.nan if i == 1 else 110 + i,
                    "home_elo": 1510.0 + season - 2015 + i,
                    "away_elo": 1490.0 - i,
                    "diff_off_epa_ewma": np.nan if i == 0 else 0.10 + base,
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


def test_q1_identity_quantiles_and_alpha_grid_are_frozen():
    assert CANDIDATE_ID == "ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1"
    assert QUANTILES == (10.0 / 21.0, 0.5, 11.0 / 21.0)
    assert ALPHA_GRID == (0.001, 0.01, 0.1, 1.0)


def test_market_preprocessor_uses_training_only_medians_and_fixed_interactions():
    gate = _gate()
    train = gate[gate.season <= 2018].copy()
    target = gate[gate.season == 2019].copy()
    train.loc[train.index[0], "market_total"] = np.nan
    target.loc[:, "market_total"] = 999.0

    prep = fit_preprocessor(train, "market")
    expected = float(pd.to_numeric(train.market_total, errors="coerce").median())
    assert prep.medians["market_total"] == expected
    assert prep.medians["market_total"] != 999.0
    assert all(column in prep.design_columns for column in MANDATORY_MARKET_FEATURES)
    assert all(column in prep.design_columns for column in OPTIONAL_MARKET_FEATURES)
    assert all(f"{column}__missing" in prep.design_columns for column in OPTIONAL_MARKET_FEATURES)
    assert all(column in prep.design_columns for column in INTERACTION_FEATURES)
    transformed = prep.transform(target)
    assert transformed.shape[0] == len(target)
    assert np.isfinite(transformed).all()


def test_full_preprocessor_has_fixed_football_missing_indicators():
    gate = _gate()
    train = gate[gate.season <= 2019].copy()
    prep = fit_preprocessor(train, "full")
    for column in FOOTBALL_FEATURES:
        assert column in prep.design_columns
        assert f"{column}__missing" in prep.design_columns


def test_alpha_tie_break_prefers_stronger_regularization_only_on_equal_loss():
    selected, loss = choose_alpha({0.001: 1.0, 0.01: 0.8, 0.1: 0.8, 1.0: 1.1})
    assert selected == 0.1
    assert loss == 0.8

    selected, loss = choose_alpha({0.001: 0.7, 0.01: 0.8, 0.1: 0.9, 1.0: 1.0})
    assert selected == 0.001
    assert loss == 0.7


def test_alpha_selection_uses_only_registered_inner_targets():
    selection = select_alpha(
        _gate(),
        outer_target_season=2022,
        feature_set="market",
        quantile=0.5,
    )
    assert selection.outer_target_season == 2022
    assert selection.inner_targets_used == (2019, 2020, 2021)
    assert set(selection.alpha_losses) == set(ALPHA_GRID)
    assert selection.selected_alpha in ALPHA_GRID
    assert selection.inner_rows == 24


def test_q1_refuses_quantile_outside_preregistered_set():
    with pytest.raises(ValueError, match="frozen quantile"):
        select_alpha(
            _gate(),
            outer_target_season=2022,
            feature_set="market",
            quantile=0.25,
        )


def test_crossing_diagnostic_never_repairs_predictions():
    oof = pd.DataFrame(
        {
            "m2_q_low": [1.0],
            "m2_q_med": [0.0],
            "m2_q_high": [2.0],
            "q1_q_low": [-1.0],
            "q1_q_med": [0.0],
            "q1_q_high": [1.0],
        }
    )
    table = quantile_crossing_table(oof).set_index("arm")
    assert table.loc["M2", "crossing_rows"] == 1
    assert table.loc["Q1", "crossing_rows"] == 0
    assert bool(table["posthoc_repair_applied"].any()) is False

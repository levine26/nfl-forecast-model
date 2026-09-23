from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

S = importlib.import_module("research.spread-points-nextgen.phase3.phase3_scaffold")
A = importlib.import_module("research.spread-points-nextgen.phase3.phase3_a0")
B = importlib.import_module("research.spread-points-nextgen.phase3.phase3_b0")
C = importlib.import_module("research.spread-points-nextgen.phase3.phase3_c0")
D = importlib.import_module("research.spread-points-nextgen.phase3.phase3_data")
E = importlib.import_module("research.spread-points-nextgen.phase3.phase3_evaluation")


def test_2025_challenger_output_is_blocked():
    with pytest.raises(S.Phase3FirewallError):
        S.guard_phase3_target_seasons([2025])


def test_completed_2026_selection_is_blocked():
    with pytest.raises(S.Phase3FirewallError):
        S.guard_phase3_target_seasons([2026])


def test_loaded_universe_rejects_2025_source_rows():
    with pytest.raises(S.Phase3FirewallError):
        S.assert_phase3_loaded_universe(pd.DataFrame({"season": [2016, 2024, 2025]}))


def test_exact_temporal_folds():
    assert S.inner_validation_seasons(2022) == (2019, 2020, 2021)
    assert S.inner_validation_seasons(2023) == (2019, 2020, 2021, 2022)
    assert S.inner_validation_seasons(2024) == (2020, 2021, 2022, 2023)
    fold = S.outer_fold(2024)
    assert fold.train_start == 2016
    assert fold.train_end == 2023
    assert fold.inner_validation_seasons == (2020, 2021, 2022, 2023)


def test_future_or_same_season_training_is_rejected():
    tr = pd.DataFrame({"season": [2020, 2022]})
    va = pd.DataFrame({"season": [2022]})
    with pytest.raises(S.Phase3FirewallError):
        S.assert_prior_only(tr, va)


def test_shifted_state_excludes_same_game_information():
    x = pd.Series([10.0, 20.0, 30.0])
    state = S.shifted_ewma(x, 8)
    assert np.isnan(state.iloc[0])
    assert state.iloc[1] == pytest.approx(10.0)
    # Changing the current game cannot change its own pregame state.
    x2 = pd.Series([10.0, 9999.0, 30.0])
    state2 = S.shifted_ewma(x2, 8)
    assert state2.iloc[1] == pytest.approx(state.iloc[1])


def test_target_and_sign_contract():
    frame = pd.DataFrame({"home_score": [27], "away_score": [20], "spread_line": [3.5]})
    out = S.canonical_targets(frame)
    assert out.loc[0, "actual_margin"] == 7
    assert out.loc[0, "actual_total"] == 47
    assert S.market_margin_from_schedule(frame).iloc[0] == 3.5
    home, away = S.reconstruct_scores(np.array([47.0]), np.array([7.0]))
    assert home[0] == 27
    assert away[0] == 20


def test_game_identity_contract():
    good = pd.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2022, 2022],
            "week": [1, 1],
            "home_team": ["A", "C"],
            "away_team": ["B", "D"],
        }
    )
    S.assert_unique_game_identity(good)
    bad = pd.concat([good.iloc[[0]], good.iloc[[0]]], ignore_index=True)
    with pytest.raises(S.Phase3FirewallError):
        S.assert_unique_game_identity(bad)


def test_a0_exact_feature_schema_is_frozen():
    assert A.A0_CAT == ["offense_team", "defense_team"]
    assert A.A0_NUM == [
        "off_epa_state",
        "opp_def_epa_allowed_state",
        "pass_epa_state",
        "opp_def_pass_epa_allowed_state",
        "success_rate_state",
        "opp_def_success_allowed_state",
        "rest_diff_team",
        "home_indicator",
    ]
    assert S.A0_ALPHA_GRID == (0.1, 1.0, 10.0, 100.0)
    assert S.A0_HALF_LIFE_GRID == (4, 8, 16, 32)


def test_a0_recency_weights_use_only_team_game_index():
    frame = pd.DataFrame(
        {
            "team": ["A", "A", "A", "B", "B"],
            "team_game_index": [0, 1, 2, 0, 1],
        }
    )
    w = A._weights(frame, 4)
    assert w[2] == pytest.approx(1.0)
    assert w[1] == pytest.approx(0.5 ** 0.25)
    assert w[4] == pytest.approx(1.0)


def test_b0_is_structurally_independent_of_a0():
    all_features = set(B.DRIVE_NUM + B.OUTCOME_CAT + B.OUTCOME_NUM)
    assert not any("a0" in x.lower() for x in all_features)
    assert not any("expected_margin" in x.lower() for x in all_features)


def test_b0_drive_taxonomy_is_fixed():
    assert D._drive_outcome("Touchdown") == "TD"
    assert D._drive_outcome("Field goal") == "FG"
    assert D._drive_outcome("Missed field goal") == "EMPTY"
    assert D._drive_outcome("Punt") == "EMPTY"
    assert D._drive_outcome("Interception") == "EMPTY"


def test_b0_red_zone_formula_constants_are_frozen():
    assert S.RZ_PRIOR_STRENGTH == 20.0
    assert S.EWMA_HALF_LIFE == 8.0


def test_b0_simulation_seed_and_scores_are_reproducible():
    seed = S.stable_seed(S.B0_ID, "2024_01_A_B")
    assert seed == S.stable_seed(S.B0_ID, "2024_01_A_B")
    n = np.array([10, 11, 12, 9])
    probs = np.array([0.05, 0.90, 0.05])
    rare = np.array([0.0, 0.0, 0.0, 2.0])
    r1 = np.random.default_rng(seed)
    r2 = np.random.default_rng(seed)
    s1 = B._simulate_team_scores(r1, n, 0.20, 0.15, probs, rare)
    s2 = B._simulate_team_scores(r2, n, 0.20, 0.15, probs, rare)
    assert np.array_equal(s1, s2)


def test_c0_uses_a0_representation_and_exact_ridge_grid():
    joined = C.MARGIN_M3 + C.TOTAL_M3
    assert any(x.startswith("a0_") for x in joined)
    assert not any(x.startswith("b0_") for x in joined)
    assert S.C0_ALPHA_GRID == (0.01, 0.1, 1.0, 10.0, 100.0)
    assert C._ridge(1.0).named_steps["ridge"].__class__.__name__ == "Ridge"


def test_c0_market_horizon_is_explicitly_opaque_closing_late():
    assert S.MARKET_HORIZON_LABEL == "historical_closing_late_benchmark_exact_horizon_opaque"
    assert "T-120" not in S.MARKET_HORIZON_LABEL


def test_m0_m1_m2_m3_feature_hierarchy():
    assert C.MARGIN_M1 == ["market_margin"]
    assert "market_margin" not in C.MARGIN_M2
    assert C.MARGIN_M3[0] == "market_margin"
    assert C.TOTAL_M1 == ["market_total"]
    assert "market_total" not in C.TOTAL_M2
    assert C.TOTAL_M3[0] == "market_total"


def test_d_gate_exact_contract():
    gate = S.d_gate_contract()
    assert gate["abs_error_correlation_lt"] == 0.90
    assert gate["pooled_mae_gain_gte"] == 0.10
    assert gate["must_improve_seasons"] == [2023, 2024]
    assert gate["bootstrap_probability_gte"] == 0.75


def test_candidate_identities_are_deterministic():
    assert S.A0_ID == "A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1"
    assert S.B0_ID == "B0-POSSESSION-DRIVE-SCORE-PROCESS-V1"
    assert S.C0_ID == "C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1"


def test_oof_receipt_requires_prior_training_boundary():
    good = pd.DataFrame(
        {
            "game_id": ["g"],
            "season": [2024],
            "week": [1],
            "home_team": ["A"],
            "away_team": ["B"],
            "candidate_id": [S.A0_ID],
            "outer_target_season": [2024],
            "train_through_season": [2023],
            "source_contract_version": [S.SOURCE_CONTRACT_VERSION],
            "code_sha": ["abc"],
            "config_sha": ["def"],
            "fallback_state": ["NONE"],
        }
    )
    S.assert_prediction_receipt(good, S.A0_ID)
    bad = good.copy()
    bad["train_through_season"] = 2024
    with pytest.raises(S.Phase3FirewallError):
        S.assert_prediction_receipt(bad, S.A0_ID)


def test_block_bootstrap_is_deterministic_and_week_blocked():
    frame = pd.DataFrame({"season": [2022, 2022, 2022, 2022], "week": [1, 1, 2, 2]})
    candidate = pd.Series([1.0, 2.0, 1.0, 2.0])
    reference = pd.Series([2.0, 3.0, 2.0, 3.0])
    a = S.season_week_block_bootstrap(frame, candidate, reference, samples=200, seed=7)
    b = S.season_week_block_bootstrap(frame, candidate, reference, samples=200, seed=7)
    assert a == b
    assert a["blocks"] == 2
    assert a["probability_candidate_lower"] == 1.0


def test_training_only_pipeline_objects_are_not_prefit():
    a0 = A._pipeline(10.0)
    assert not hasattr(a0.named_steps["pre"], "transformers_")
    b0 = B._drive_pipeline(1.0)
    assert not hasattr(b0.named_steps["impute"], "statistics_")
    c0 = C._ridge(1.0)
    assert not hasattr(c0.named_steps["impute"], "statistics_")


def test_no_2025_in_development_constant():
    assert S.DEVELOPMENT_SEASONS == (2022, 2023, 2024)
    assert 2025 not in S.DEVELOPMENT_SEASONS

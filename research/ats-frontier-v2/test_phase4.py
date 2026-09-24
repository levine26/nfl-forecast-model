from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import phase4_core as core
import phase4_runner as runner


def test_frozen_config_and_firewalls():
    cfg = core.CONFIG
    assert cfg["outer_development_seasons"] == [2022, 2023, 2024, 2025]
    assert cfg["warmup_start_season"] == 2010
    assert cfg["completed_2026_outcomes_allowed"] is False
    assert cfg["market_horizon_label"] == "HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE"
    assert cfg["m3"]["q_team_grid"] == [0.04, 0.10, 0.25]
    assert cfg["m3"]["q_qb_grid"] == [0.10, 0.25, 0.50]
    assert cfg["m3"]["lambda_grid"] == [0.50, 0.75]
    assert cfg["m3"]["ridge_alpha_grid"] == [10.0, 100.0]
    assert cfg["m4"]["nu_grid"] == [4, 6, 10, 30]
    assert cfg["m4"]["lambda_scale_grid"] == [1.0, 10.0]
    assert cfg["m4"]["lambda_key_grid"] == [1.0, 10.0]
    assert cfg["bootstrap_resamples"] >= 10_000


def test_home_margin_and_ats_sign_contract():
    assert core.actual_margin(27, 20) == 7
    assert core.actual_margin(20, 27) == -7
    assert core.market_margin(3.5) == 3.5
    assert core.market_margin(-3.5) == -3.5
    assert core.observed_ats_class(7, 3.5) == 0
    assert core.observed_ats_class(3, 3.0) == 1
    assert core.observed_ats_class(0, 3.0) == 2
    assert core.observed_ats_class(-7, -3.5) == 2


def test_normal_push_structure():
    c, p, l = core.normal_cpl(3.0, 13.0, 3.0)
    assert p > 0.0
    assert math.isclose(c + p + l, 1.0, abs_tol=1e-12)
    c, p, l = core.normal_cpl(3.5, 13.0, 3.5)
    assert p == 0.0
    assert math.isclose(c + l, 1.0, abs_tol=1e-12)


def test_m3_scalar_state_update_and_transition():
    s0 = core.ScalarState()
    s1 = core.update_state(s0, 1.0, q=0.1)
    assert 0.0 < s1.mean < 1.0
    assert s1.var < 1.1
    assert s1.n == 1
    s2 = core.season_transition(s1, lam=0.5, q=0.1)
    assert math.isclose(s2.mean, 0.5 * s1.mean, abs_tol=1e-12)
    assert s2.var > 0.0


def test_m3_week_block_predict_then_update_prevents_target_game_leakage():
    games = pd.DataFrame([
        {"game_id": "g1", "season": 2020, "week": 1, "home_team": "A", "away_team": "B"},
        {"game_id": "g2", "season": 2020, "week": 2, "home_team": "A", "away_team": "B"},
    ])
    team_map = {
        (2020, 1, "g1", "A"): (2.0, 1.0),
        (2020, 1, "g1", "B"): (-2.0, -1.0),
        (2020, 2, "g2", "A"): (-50.0, -50.0),
        (2020, 2, "g2", "B"): (50.0, 50.0),
    }
    qb_map = {
        (2020, 1, "g1", "A"): ("qa", 2.0),
        (2020, 1, "g1", "B"): ("qb", -2.0),
        (2020, 2, "g2", "A"): ("qa2", -50.0),
        (2020, 2, "g2", "B"): ("qb2", 50.0),
    }
    feat = runner._state_features(games, team_map, qb_map, q_team=0.1, q_qb=0.25, lam=0.75)
    w1 = feat.loc[feat.week.eq(1)].iloc[0]
    w2 = feat.loc[feat.week.eq(2)].iloc[0]
    assert w1.dynamic_team_signal == 0.0
    assert w1.dynamic_qb_signal == 0.0
    assert w1.home_prior_qb == "LEAGUE_PRIOR"
    assert w2.dynamic_team_signal != 0.0
    assert w2.dynamic_qb_signal != 0.0
    assert w2.home_prior_qb == "qa"
    assert w2.away_prior_qb == "qb"
    # The deliberately extreme target-week g2 observations cannot affect g2 predictors.
    assert abs(w2.dynamic_team_signal) < 10.0
    assert abs(w2.dynamic_qb_signal) < 10.0


def test_m4_analytic_normalization_and_no_endpoint_folding():
    loc, sigma, nu, g = 4.0, 12.0, 6, [0.2, -0.1, 0.15]
    z = core.m4_normalizer(loc, sigma, nu, g)
    assert np.isfinite(z) and z > 0
    # Full-lattice CDF approaches one without a finite support endpoint.
    assert abs(core.m4_leq(1_000_000, loc, sigma, nu, g) - 1.0) < 1e-12
    left = core.m4_leq(-1_000_000, loc, sigma, nu, g)
    assert 0.0 <= left < 1e-12
    for m in (-100, -7, -3, 0, 3, 7, 100):
        p = core.m4_cell(m, loc, sigma, nu, g)
        assert np.isfinite(p) and p >= 0.0


def test_m4_push_mapping_and_cpl_normalization():
    g = [0.1, 0.2, -0.1]
    whole = core.m4_cpl(3.0, 13.0, 6, g, 3.0)
    half = core.m4_cpl(3.5, 13.0, 6, g, 3.5)
    assert math.isclose(sum(whole), 1.0, abs_tol=1e-12)
    assert math.isclose(sum(half), 1.0, abs_tol=1e-12)
    assert whole[1] == pytest.approx(core.m4_cell(3, 3.0, 13.0, 6, g), abs=1e-15)
    assert half[1] == 0.0


def test_m4_sign_reversal_symmetry():
    g = [0.2, 0.1, -0.1]
    for m in (-14, -7, -3, 0, 3, 7, 14):
        p1 = core.m4_cell(m, 4.0, 12.0, 6, g)
        p2 = core.m4_cell(-m, -4.0, 12.0, 6, g)
        assert math.isclose(p1, p2, rel_tol=1e-12, abs_tol=1e-12)


def test_extreme_m4_inputs_remain_finite():
    for loc, sigma, nu in ((60.0, 0.5, 4), (-60.0, 80.0, 30), (0.0, 0.25, 10)):
        cpl = core.m4_cpl(loc, sigma, nu, [0.5, -0.5, 0.25], loc if float(loc).is_integer() else loc + 0.5)
        assert np.isfinite(cpl).all()
        assert min(cpl) >= 0.0
        assert math.isclose(sum(cpl), 1.0, abs_tol=1e-12)


def test_preflight_is_result_blind_and_passes():
    receipt = runner.preflight()
    assert receipt["status"] == "PASS"
    assert receipt["candidate_performance_inspected"] is False
    assert receipt["completed_2026_outcomes_used"] == 0
    assert receipt["target_game_pbp_allowed"] is False
    assert receipt["same_week_update_order"] == "predict-all-then-update-all"
    assert receipt["m4_numerical_audit"]["status"] == "PASS"


def test_research_source_does_not_import_production_forecasting_modules():
    source = (ROOT / "phase4_runner.py").read_text(encoding="utf-8")
    forbidden = ["fst_production", "public_forecast", "scripts.run_week", "publish.py", "site/"]
    for token in forbidden:
        assert token not in source

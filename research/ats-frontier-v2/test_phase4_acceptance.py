from __future__ import annotations

import math
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import phase4_accepted_runner as accepted


def test_static_ablation_is_fixed_prior_only_ewma():
    games = pd.DataFrame([
        {"game_id": "g1", "season": 2020, "week": 1, "home_team": "A", "away_team": "B"},
        {"game_id": "g2", "season": 2020, "week": 2, "home_team": "A", "away_team": "B"},
        {"game_id": "g3", "season": 2020, "week": 3, "home_team": "A", "away_team": "B"},
    ])
    team_map = {
        (2020, 1, "g1", "A"): (1.0, 0.0), (2020, 1, "g1", "B"): (0.0, 0.0),
        (2020, 2, "g2", "A"): (3.0, 0.0), (2020, 2, "g2", "B"): (0.0, 0.0),
    }
    feat = accepted._state_features(games, team_map, {}, q_team=0.1, q_qb=0.25, lam=0.75)
    week3 = feat.loc[feat.week.eq(3)].iloc[0]
    alpha = 1.0 - math.exp(math.log(0.5) / 8.0)
    expected_a = alpha * 3.0 + (1.0 - alpha) * 1.0
    assert math.isclose(week3.static_team_signal, expected_a, rel_tol=0, abs_tol=1e-12)
    assert not math.isclose(week3.static_team_signal, 2.0, abs_tol=1e-6)


def test_acceptance_preflight_records_correction_and_complete_diagnostics():
    receipt = accepted._preflight()
    assert receipt["status"] == "PASS"
    assert receipt["static_pooling_rule"] == "prior_only_fixed_ewma_half_life_8_games"
    assert receipt["static_ewma_half_life_games"] == 8.0
    assert receipt["state_updates_include_prior_games_without_market_rows"] is True
    assert receipt["superseded_execution_accepted"] is False
    assert "ranked_probability_score" in receipt["m4_required_secondary_diagnostics"]
    assert len(receipt["accepted_code_sha256"]) == 64


def test_corrected_m3_builds_state_history_from_all_games_before_market_filtering():
    source = (ROOT / "phase4_accepted_runner.py").read_text(encoding="utf-8")
    assert "_state_features(\n                    games," in source
    assert "base_rows = games[games[\"spread_line\"].notna()]" in source


def test_no_new_candidate_or_hyperparameter_family_introduced():
    cfg = accepted.CONFIG
    assert cfg["m3"]["ablations"] == ["MARKET_ONLY", "STATIC_FOOTBALL_STATE", "DYNAMIC_NO_QB", "DYNAMIC_FULL"]
    assert cfg["m4"]["ablations"] == ["CONSTANT_SCALE_NO_KEY", "CONDITIONAL_SCALE_NO_KEY", "CONSTANT_SCALE_KEY", "FULL_CONDITIONAL_SCALE_KEY"]
    assert cfg["m3"]["q_team_grid"] == [0.04, 0.10, 0.25]
    assert cfg["m3"]["q_qb_grid"] == [0.10, 0.25, 0.50]
    assert cfg["m3"]["lambda_grid"] == [0.50, 0.75]
    assert cfg["m3"]["ridge_alpha_grid"] == [10.0, 100.0]
    assert cfg["m4"]["nu_grid"] == [4, 6, 10, 30]

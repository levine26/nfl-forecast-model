from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest

scaffold = importlib.import_module("research.spread-points-nextgen.phase3.phase3_scaffold")
p4 = importlib.import_module("research.spread-points-nextgen.phase4.phase4_holdout")


def test_frozen_contracts_pass_without_loading_holdout():
    result = p4.verify_frozen_contracts()
    assert result["status"] == "PASS"
    assert result["implementation_sha256"] == p4.FROZEN_IMPLEMENTATION_SHA256
    assert result["config_sha256"] == p4.FROZEN_CONFIG_SHA256
    assert result["candidate_ids"] == {"A0": p4.A0_ID, "B0": p4.B0_ID, "C0": p4.C0_ID}
    assert result["D_margin"] == "ENSEMBLE_NOT_ELIGIBLE"
    assert result["D_total"] == "ENSEMBLE_NOT_ELIGIBLE"
    assert result["candidate5_trained"] is False
    assert result["completed_2026_used"] is False


def test_original_phase3_firewall_still_blocks_2025():
    with pytest.raises(scaffold.Phase3FirewallError):
        scaffold.guard_phase3_target_seasons([2025])


def test_phase4_authorizes_only_through_2025():
    assert p4._phase4_guard_target_seasons([2025]) == (2025,)
    with pytest.raises(p4.Phase4HoldoutError):
        p4._phase4_guard_target_seasons([2026])


def test_phase4_loaded_universe_blocks_2026():
    p4._phase4_assert_loaded_universe(pd.DataFrame({"season": [2016, 2025]}))
    with pytest.raises(p4.Phase4HoldoutError):
        p4._phase4_assert_loaded_universe(pd.DataFrame({"season": [2025, 2026]}))


def test_opening_receipt_precedes_scoring_and_freezes_required_state():
    receipt = p4._read_json(p4.OPENING_RECEIPT)
    assert receipt["holdout_state_at_receipt"] == "UNOPENED"
    assert receipt["target_season"] == 2025
    assert receipt["Candidate5_state"] == "NOT_STARTED"
    assert receipt["Candidate5_trained"] is False
    assert receipt["completed_2026_outcomes_used"] is False
    assert receipt["production_changed"] is False
    assert receipt["D_margin_state"] == "ENSEMBLE_NOT_ELIGIBLE"
    assert receipt["D_total_state"] == "ENSEMBLE_NOT_ELIGIBLE"
    assert receipt["bootstrap_resamples"] >= 10_000
    assert receipt["simulation_draws_per_B0_game"] >= 10_000


def test_sign_convention_and_market_label_are_frozen():
    frame = scaffold.canonical_targets(pd.DataFrame({"home_score": [31.0], "away_score": [24.0]}))
    assert frame.loc[0, "actual_margin"] == 7.0
    assert frame.loc[0, "actual_total"] == 55.0
    assert p4.MARKET_LABEL == "historical_closing_late_benchmark_exact_horizon_opaque"


def test_runner_does_not_build_d_or_candidate5():
    source = Path(p4.__file__).read_text(encoding="utf-8")
    assert "evaluate_d_target(" not in source
    assert "D-CONVEX-MARGIN-V1" not in source
    assert "D-CONVEX-TOTAL-V1" not in source
    assert "LEVLINE-HISTORICAL-RESIDUAL-STACK-V1" not in source


def test_final_simulation_floor_fails_closed(tmp_path):
    with pytest.raises(p4.Phase4HoldoutError, match="10,000"):
        p4.run_holdout(tmp_path, simulations=9_999)


# Reproducibility trigger after the first completed 2025 holdout artifact; no scientific contract change.

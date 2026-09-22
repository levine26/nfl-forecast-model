from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRID = ROOT / "research" / "props" / "v22" / "CHALLENGER_GRID.json"


def test_props22_grid_is_fixed_research_only_and_non_outcome_fitted():
    payload = json.loads(GRID.read_text(encoding="utf-8"))
    assert payload["status"] == "FROZEN_BEFORE_FUTURE_HOLDOUT"
    assert payload["research_only"] is True
    assert payload["production_authorized"] is False
    assert payload["outcome_fit_allowed"] is False
    assert payload["baseline_model"] == "levline-props-2.1-sunday-v0.1"

    rows = {row["id"]: row for row in payload["challengers"]}
    assert list(rows) == [
        "P21_BASE",
        "P22_LINE_RESIDUAL_25",
        "P22_LINE_RESIDUAL_50",
        "P22_PROB_RESIDUAL_25",
        "P22_PROB_RESIDUAL_50",
        "P22_CAL_50",
        "P22_COMBINED_25",
        "P22_COMBINED_50",
    ]
    for row in rows.values():
        line_market = float(row["line_market_weight"])
        line_model = float(row["line_model_weight"])
        prob_market = float(row["probability_market_weight"])
        prob_model = float(row["probability_model_weight"])
        shrink = float(row["probability_shrink_to_half"])
        assert 0.0 <= line_market <= 1.0
        assert 0.0 <= line_model <= 1.0
        assert abs((line_market + line_model) - 1.0) < 1e-12
        assert 0.0 <= prob_market <= 1.0
        assert 0.0 <= prob_model <= 1.0
        assert abs((prob_market + prob_model) - 1.0) < 1e-12
        assert shrink in {0.0, 0.5}

    assert rows["P22_PROB_RESIDUAL_25"]["probability_market_weight"] == 0.75
    assert rows["P22_PROB_RESIDUAL_50"]["probability_market_weight"] == 0.5
    assert rows["P22_COMBINED_25"]["promotion_eligible"] is True
    assert rows["P22_COMBINED_50"]["promotion_eligible"] is True
    assert all(
        not row["promotion_eligible"]
        for key, row in rows.items()
        if key not in {"P22_COMBINED_25", "P22_COMBINED_50"}
    )

    selection = payload["selection_control"]
    assert selection["promotion_candidate_ids"] == [
        "P22_COMBINED_25",
        "P22_COMBINED_50",
    ]
    assert selection["multiplicity_method"] == "holm_bonferroni"
    assert selection["family_alpha"] == 0.05
    assert selection["comparator"] == "original_point_in_time_market"
    assert selection["require_brier_and_log_loss_non_degradation"] is True
    assert selection["require_clean_chronology"] is True

    minimum = payload["minimum_promotion_evidence"]
    assert minimum["future_weeks"] >= 3
    assert minimum["finalized_games"] >= 30
    assert minimum["market_matched_observations"] >= 1000
    assert minimum["prop_family_observations"] >= 250

    forbidden = set(payload["forbidden"])
    assert "week2_parameter_fit" in forbidden
    assert "week2_counterfactual_candidate_selection" in forbidden
    assert "retrospective_signal_relabel" in forbidden
    assert "postkickoff_market_use" in forbidden
    assert "mid_holdout_grid_change" in forbidden
    assert "production_winner_model_mutation" in forbidden

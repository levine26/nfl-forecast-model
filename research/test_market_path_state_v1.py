from __future__ import annotations

from research.market_path_state_v1 import derive_market_path_row, derive_market_paths


def _row(*probs: float | None) -> dict:
    values = dict(zip(
        ("market_home_prob_t120", "market_home_prob_t60", "market_home_prob_t45", "market_home_prob_t30"),
        probs,
    ))
    return {"game_id": "2026_01_A_B", **values}


def test_monotone_path_has_no_reversal() -> None:
    result = derive_market_path_row(_row(0.50, 0.52, 0.53, 0.55))
    assert result["complete_four_horizon_path"] is True
    assert result["reversal_count"] == 0
    assert result["late_reversal"] is False
    assert abs(result["net_move_pp_t30_minus_t120"] - 5.0) < 1e-9
    assert abs(result["total_variation_pp"] - 5.0) < 1e-9
    assert abs(result["path_efficiency"] - 1.0) < 1e-12


def test_reversal_path_records_geometry() -> None:
    result = derive_market_path_row(_row(0.50, 0.54, 0.52, 0.51))
    assert result["reversal_count"] == 1
    assert result["late_reversal"] is False
    assert result["adjacent_sign_pattern"] == "1|-1|-1"
    assert abs(result["net_move_pp_t30_minus_t120"] - 1.0) < 1e-9
    assert abs(result["total_variation_pp"] - 7.0) < 1e-9
    assert abs(result["path_efficiency"] - (1.0 / 7.0)) < 1e-12


def test_late_reversal_is_explicit() -> None:
    result = derive_market_path_row(_row(0.50, 0.52, 0.54, 0.53))
    assert result["reversal_count"] == 1
    assert result["late_reversal"] is True
    assert result["adjacent_sign_pattern"] == "1|1|-1"


def test_missing_horizon_fails_closed() -> None:
    result = derive_market_path_row(_row(0.50, 0.52, None, 0.53))
    assert result["complete_four_horizon_path"] is False
    assert result["net_move_pp_t30_minus_t120"] is None
    assert result["reversal_count"] is None
    assert result["production_authorized"] is False


def test_audit_is_outcome_blind_research_only() -> None:
    rows, audit = derive_market_paths([_row(0.50, 0.51, 0.52, 0.53)])
    assert len(rows) == 1
    assert audit["complete_four_horizon_paths"] == 1
    assert audit["outcome_blind"] is True
    assert audit["completed_2026_outcomes_used"] == 0
    assert audit["production_authorized"] is False
    assert audit["promotion_authorized"] is False

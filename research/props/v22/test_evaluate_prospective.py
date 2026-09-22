from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest

from research.props.v22.challengers import build_challenger_set, load_grid


SCRIPT = Path(__file__).with_name("evaluate_prospective.py")
SPEC = importlib.util.spec_from_file_location("props22_evaluator_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _source(
    *,
    forecast_id: str = "f1",
    game_id: str = "2026_03_AAA_BBB",
    prop_type: str = "rushing_yards",
    model_line: float = 120.0,
    market_line: float | None = 100.0,
    model_probability: float = 0.80,
    market_probability: float = 0.60,
):
    forecast = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)
    kickoff = forecast + timedelta(hours=3)
    source = {
        "forecast_id": forecast_id,
        "game_id": game_id,
        "player_id": f"p-{forecast_id}",
        "player_name": "Synthetic Player",
        "team": "AAA",
        "opponent": "BBB",
        "position": "RB",
        "prop_type": prop_type,
        "kickoff_utc": kickoff.isoformat(),
        "forecast_timestamp_utc": forecast.isoformat(),
        "model_median": model_line,
        "market_line": market_line,
        "role_state": {
            "state": "STARTER_EXPECTED",
            "availability": "AVAILABLE",
            "workload": "KNOWN",
        },
        "market_state": {
            "quote_as_of": (forecast - timedelta(minutes=5)).isoformat(),
            "book_count": 6,
        },
        "qa": {"classification": "RESEARCH_ELIGIBLE"},
        "provenance": {
            "challenger_model_version": "levline-props-2.1-sunday-v0.1",
            "source_data_horizon_utc": (forecast - timedelta(minutes=10)).isoformat(),
        },
        "outcome": None,
    }
    if prop_type in {"rushing_td", "receiving_td", "anytime_td"}:
        source.update(
            {
                "probability_td": model_probability,
                "market_probability_td": market_probability,
            }
        )
    else:
        source.update(
            {
                "probability_over": model_probability,
                "market_probability_over": market_probability,
            }
        )
    return source


def _receipts(source=None):
    return build_challenger_set(source or _source())


def _grade(receipt, actual: float):
    kickoff = datetime.fromisoformat(str(receipt["kickoff_utc"]).replace("Z", "+00:00"))
    return {
        "contract_version": MODULE.GRADE_CONTRACT_VERSION,
        "source_props21_forecast_sha256": receipt["source_props21_forecast_sha256"],
        "source_props21_forecast_id": receipt["source_props21_forecast_id"],
        "game_id": receipt["game_id"],
        "actual_result": actual,
        "grade_status": "GRADED",
        "finalized": True,
        "graded_utc": (kickoff + timedelta(hours=4)).isoformat(),
        "result_source": "synthetic_test",
    }


def test_evaluator_scores_frozen_line_challengers_against_original_market():
    receipts = _receipts()
    grades = [_grade(receipts[0], 108.0)]

    summary, detail = MODULE.evaluate(receipts, grades, bootstrap_replicates=100)

    combined = summary["candidate_metrics"]["P22_COMBINED_25"]
    line = combined["line"]
    assert line["n"] == 1
    assert line["mae_challenger"] == pytest.approx(3.0)
    assert line["mae_original_market"] == pytest.approx(8.0)
    assert line["paired_absolute_error_difference_challenger_minus_market"] == pytest.approx(-5.0)

    probability = combined["probability"]
    assert probability["n"] == 1
    assert probability["brier_challenger"] == pytest.approx((0.65 - 1.0) ** 2)
    assert probability["brier_original_market"] == pytest.approx((0.60 - 1.0) ** 2)

    baseline = summary["candidate_metrics"]["P21_BASE"]["line"]
    assert baseline["mae_challenger"] == pytest.approx(12.0)
    assert baseline["paired_absolute_error_difference_challenger_minus_market"] == pytest.approx(4.0)
    assert summary["promotion_decision"] == "NOT_READY_CONTINUE_FROZEN_HOLDOUT"
    assert detail["source_sha"].nunique() == 1


def test_line_market_push_is_excluded_from_probability_scoring():
    receipts = _receipts()
    grades = [_grade(receipts[0], 100.0)]

    summary, _ = MODULE.evaluate(receipts, grades, bootstrap_replicates=25)

    assert summary["candidate_metrics"]["P22_COMBINED_25"]["line"]["n"] == 1
    probability = summary["candidate_metrics"]["P22_COMBINED_25"]["probability"]
    assert probability["n"] == 0
    assert probability["status"] == "NO_MATCHED_PROBABILITY_OBSERVATIONS"


def test_td_probability_scoring_uses_one_plus_td_event():
    receipts = _receipts(
        _source(
            forecast_id="td1",
            game_id="2026_03_CCC_DDD",
            prop_type="anytime_td",
            model_line=0.0,
            market_line=None,
            model_probability=0.70,
            market_probability=0.50,
        )
    )
    grades = [_grade(receipts[0], 1.0)]

    summary, _ = MODULE.evaluate(receipts, grades, bootstrap_replicates=25)
    probability = summary["candidate_metrics"]["P22_COMBINED_50"]["probability"]
    assert probability["n"] == 1
    assert probability["brier_challenger"] == pytest.approx((0.60 - 1.0) ** 2)
    assert probability["brier_original_market"] == pytest.approx((0.50 - 1.0) ** 2)


def test_receipt_hash_tampering_fails_closed():
    receipts = _receipts()
    receipts[0]["line"]["challenger_line"] = 999.0

    with pytest.raises(MODULE.Props22EvaluationError, match="hash mismatch"):
        MODULE.validate_receipts(receipts)


def test_holm_bonferroni_adjustment_is_monotone_and_family_controlled():
    adjusted = MODULE.holm_bonferroni(
        {"P22_COMBINED_25": 0.01, "P22_COMBINED_50": 0.04}
    )
    assert adjusted["P22_COMBINED_25"] == pytest.approx(0.02)
    assert adjusted["P22_COMBINED_50"] == pytest.approx(0.04)


def test_terminal_readiness_reports_without_auto_selecting_winner():
    grid = deepcopy(load_grid())
    grid["minimum_promotion_evidence"] = {
        "future_weeks": 1,
        "finalized_games": 1,
        "market_matched_observations": 1,
        "prop_family_observations": 1,
    }
    receipts = _receipts()
    grades = [_grade(receipts[0], 108.0)]

    summary, _ = MODULE.evaluate(
        receipts,
        grades,
        grid=grid,
        bootstrap_replicates=25,
    )

    assert summary["terminal_readiness"]["terminal_evaluation_ready"] is True
    assert summary["terminal_readiness"]["prop_family_claim_ready"]["rushing_yards"] is True
    assert (
        summary["promotion_decision"]
        == "TERMINAL_EVALUATION_PERMITTED_BUT_NO_AUTOMATIC_WINNER_SELECTION"
    )


def test_conflicting_or_nonfinal_grade_fails_closed():
    receipt = _receipts()[0]
    grade = _grade(receipt, 108.0)
    grade["finalized"] = False
    with pytest.raises(MODULE.Props22EvaluationError, match="finalized grades only"):
        MODULE.validate_grades([grade])

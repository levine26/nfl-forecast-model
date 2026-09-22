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
    row = {
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
    row["grade_sha256"] = MODULE._sha(row)
    return row



def _closing_event(receipt, *, line_clv: float = 1.5, price_clv_pp: float = 2.0):
    forecast = datetime.fromisoformat(
        str(receipt["forecast_timestamp_utc"]).replace("Z", "+00:00")
    )
    kickoff = datetime.fromisoformat(
        str(receipt["kickoff_utc"]).replace("Z", "+00:00")
    )
    row = {
        "contract_version": MODULE.CLOSING_CONTRACT_VERSION,
        "source_props21_forecast_sha256": receipt["source_props21_forecast_sha256"],
        "source_props21_forecast_id": receipt["source_props21_forecast_id"],
        "game_id": receipt["game_id"],
        "player_id": receipt["player_id"],
        "prop_type": receipt["prop_type"],
        "forecast_timestamp_utc": receipt["forecast_timestamp_utc"],
        "kickoff_utc": receipt["kickoff_utc"],
        "frozen_model_side": "over",
        "original_market": {
            "line": (receipt.get("line") or {}).get("market_line"),
            "event_probability": (receipt.get("probability") or {}).get(
                "market_probability"
            ),
            "archive_price_basis": {"snapshot_id": "original"},
        },
        "closing_market": {
            "line": (
                ((receipt.get("line") or {}).get("market_line") or 0.0) + line_clv
            ),
            "event_probability": 0.56,
            "frozen_side_probability": 0.56,
            "archive": {
                "snapshot_id": "close",
                "captured_at_utc": (kickoff - timedelta(minutes=2)).isoformat(),
                "kickoff_utc": kickoff.isoformat(),
                "minutes_to_kickoff": 2.0,
            },
        },
        "line_clv": {
            "available": True,
            "raw_closing_minus_original_line": line_clv,
            "side_oriented_line_clv": line_clv,
        },
        "same_threshold_price_clv": {
            "available": True,
            "threshold": (receipt.get("line") or {}).get("market_line"),
            "side": "over",
            "original_best_price": {
                "sportsbook": "a",
                "american": -105,
                "decimal": 1.9523809524,
                "implied_probability": 0.512195122,
            },
            "closing_best_price": {
                "sportsbook": "b",
                "american": -115,
                "decimal": 1.8695652174,
                "implied_probability": 0.534883721,
            },
            "decimal_odds_clv_original_minus_close": 0.082815735,
            "implied_probability_clv_pp_close_minus_original": price_clv_pp,
        },
        "selection": {
            "latest_valid_capture_strictly_before_kickoff": True,
            "capture_at_or_after_forecast": True,
            "archive_settlement_grace_minutes": 60,
            "outcome_consulted": False,
        },
        "research_only": True,
        "production_authorized": False,
    }
    row["closing_event_sha256"] = MODULE._sha(row)
    return row

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


def test_nonfinal_grade_fails_closed_after_hash_validation():
    receipt = _receipts()[0]
    grade = _grade(receipt, 108.0)
    grade["finalized"] = False
    grade.pop("grade_sha256")
    grade["grade_sha256"] = MODULE._sha(grade)
    with pytest.raises(MODULE.Props22EvaluationError, match="finalized grades only"):
        MODULE.validate_grades([grade])


def test_grade_hash_tampering_fails_closed():
    receipt = _receipts()[0]
    grade = _grade(receipt, 108.0)
    grade["actual_result"] = 999.0
    with pytest.raises(MODULE.Props22EvaluationError, match="grade hash mismatch"):
        MODULE.validate_grades([grade])


def test_closing_market_evidence_is_secondary_and_keeps_readiness_unchanged():
    receipts = _receipts()
    grades = [_grade(receipts[0], 108.0)]
    closing = [_closing_event(receipts[0])]

    without, _ = MODULE.evaluate(receipts, grades, bootstrap_replicates=25)
    with_close, detail = MODULE.evaluate(
        receipts,
        grades,
        closing_events=closing,
        bootstrap_replicates=25,
    )

    evidence = with_close["closing_market_evidence"]
    assert evidence["status"] == "DESCRIPTIVE_SECONDARY"
    assert evidence["promotion_effect"] == "NONE"
    assert evidence["source_forecasts"] == 1
    assert evidence["original_market_matched_observations"] == 1
    assert evidence["closing_market_matched_observations"] == 1
    assert evidence["line_clv"]["n"] == 1
    assert evidence["line_clv"]["mean"] == pytest.approx(1.5)
    assert evidence["line_clv"]["positive_share"] == pytest.approx(1.0)
    assert evidence["same_threshold_price_clv_implied_probability_pp"]["n"] == 1
    assert evidence["same_threshold_price_clv_implied_probability_pp"]["mean"] == pytest.approx(2.0)
    assert with_close["terminal_readiness"] == without["terminal_readiness"]
    assert with_close["promotion_decision"] == without["promotion_decision"]
    assert detail["closing_market_matched"].all()
    assert detail["side_oriented_line_clv"].dropna().eq(1.5).all()


def test_closing_event_hash_tampering_fails_closed():
    receipts = _receipts()
    event = _closing_event(receipts[0])
    event["line_clv"]["side_oriented_line_clv"] = 99.0

    with pytest.raises(MODULE.Props22EvaluationError, match="closing-event hash mismatch"):
        MODULE.validate_closing_events([event], receipts)


def test_closing_event_wrong_source_identity_fails_closed():
    receipts = _receipts()
    event = _closing_event(receipts[0])
    event["player_id"] = "wrong-player"
    event.pop("closing_event_sha256")
    event["closing_event_sha256"] = MODULE._sha(event)

    with pytest.raises(MODULE.Props22EvaluationError, match="identity mismatch"):
        MODULE.validate_closing_events([event], receipts)


def test_closing_event_post_kickoff_timestamp_fails_closed():
    receipts = _receipts()
    event = _closing_event(receipts[0])
    event["closing_market"]["archive"]["captured_at_utc"] = event["kickoff_utc"]
    event.pop("closing_event_sha256")
    event["closing_event_sha256"] = MODULE._sha(event)

    with pytest.raises(MODULE.Props22EvaluationError, match="invalid forecast/close/kickoff chronology"):
        MODULE.validate_closing_events([event], receipts)

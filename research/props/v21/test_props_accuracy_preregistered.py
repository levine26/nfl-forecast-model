from __future__ import annotations

from copy import deepcopy

import pytest

from props_accuracy_preregistered import (
    EVALUATION_CONTRACT_VERSION,
    american_to_decimal,
    evaluate_history,
    original_sha256,
)


def _original(
    *,
    forecast_id: str,
    game_id: str,
    player_id: str,
    prop_type: str = "receiving_yards",
    actual_line: float = 70.5,
    model_mean: float = 80.0,
    fair_line: float = 79.5,
    p_over: float = 0.60,
    p_under: float = 0.40,
    market_p_over: float = 0.52,
    market_p_under: float = 0.48,
    over_price: float = -110,
    under_price: float = -110,
    signal_state: str = "WATCH",
):
    return {
        "forecast_id": forecast_id,
        "player_identity_resolved": True,
        "player_id": player_id,
        "player": f"Player {player_id}",
        "position": "WR",
        "team": "ARI",
        "opponent": "LAR",
        "game_id": game_id,
        "prop_type": prop_type,
        "forecast_timestamp_utc": "2026-09-17T20:00:00+00:00",
        "data_horizon_utc": "2026-09-17T19:00:00+00:00",
        "kickoff_utc": "2026-09-20T20:00:00+00:00",
        "signal_state": signal_state,
        "market": {
            "source": "test-consensus",
            "captured_utc": "2026-09-17T19:30:00+00:00",
            "line": actual_line,
            "over_price_american": over_price,
            "under_price_american": under_price,
            "no_vig_over_probability": market_p_over,
            "no_vig_under_probability": market_p_under,
        },
        "model": {
            "version": "levline-props-simulation-v0.1.0",
            "mean": model_mean,
            "median": fair_line,
            "fair_line": fair_line,
            "standard_deviation": 15.0,
            "over_probability": p_over,
            "under_probability": p_under,
            "push_probability": 0.0,
            "prediction_interval": {"low": 50.0, "high": 110.0, "coverage": 0.80},
            "simulation_accounting_ok": True,
        },
        "data_quality": {"state": "HIGH", "critical_ok": True},
    }


def _td_original(
    *,
    forecast_id: str,
    game_id: str,
    player_id: str,
    p_td: float = 0.60,
    market_p_td: float = 0.50,
    td_price: float = 120,
    signal_state: str = "MODEL EDGE",
):
    return {
        "forecast_id": forecast_id,
        "player_identity_resolved": True,
        "player_id": player_id,
        "player": f"Player {player_id}",
        "position": "WR",
        "team": "ARI",
        "opponent": "LAR",
        "game_id": game_id,
        "prop_type": "anytime_td",
        "forecast_timestamp_utc": "2026-09-17T20:00:00+00:00",
        "data_horizon_utc": "2026-09-17T19:00:00+00:00",
        "kickoff_utc": "2026-09-20T20:00:00+00:00",
        "signal_state": signal_state,
        "market": {
            "source": "test-consensus",
            "captured_utc": "2026-09-17T19:30:00+00:00",
            "td_price_american": td_price,
            "no_vig_probability": market_p_td,
        },
        "model": {
            "version": "levline-props-simulation-v0.1.0",
            "td_probability": p_td,
            "expected_tds": 0.7,
            "simulation_accounting_ok": True,
        },
        "data_quality": {"state": "HIGH", "critical_ok": True},
    }


def _receipt(original: dict):
    return {
        "history_contract_version": "levline-props-history-v0.1",
        "event_type": "FORECAST_ORIGINAL",
        "forecast_id": original["forecast_id"],
        "recorded_utc": "2026-09-17T20:01:00+00:00",
        "original_sha256": original_sha256(original),
        "original_forecast": deepcopy(original),
    }


def _grade(fid: str, actual: float):
    return {
        "history_contract_version": "levline-props-history-v0.1",
        "event_type": "GRADE",
        "forecast_id": fid,
        "graded_utc": "2026-09-20T23:00:00+00:00",
        "actual_result": actual,
    }


def _close(fid: str, line: float):
    return {
        "history_contract_version": "levline-props-history-v0.1",
        "event_type": "MARKET_CLOSE",
        "forecast_id": fid,
        "captured_utc": "2026-09-20T19:55:00+00:00",
        "source": "test-close",
        "line": line,
        "over_price_american": -110,
        "under_price_american": -110,
    }


def test_empty_history_is_explicit_n_zero_not_accuracy():
    summary, detail = evaluate_history(
        [],
        [],
        [],
        frozen_model_ref="research/props-integration@test",
        bootstrap_replicates=10,
    )
    assert summary["evaluation_contract_version"] == EVALUATION_CONTRACT_VERSION
    assert summary["sample"]["forecasts"] == 0
    assert summary["graded_sample"]["forecasts"] == 0
    assert summary["continuous"]["status"] == "NO_GRADED_CONTINUOUS_FORECASTS"
    assert summary["probability"]["status"] == "NO_GRADED_PROBABILITY_FORECASTS"
    assert summary["market_relative"]["status"] == "NO_MATCHED_MARKET_OUTCOMES"
    assert summary["betting"]["status"] == "NOT_MEASURABLE_NO_ORIGINAL_MODEL_EDGE_OBSERVATIONS"
    assert summary["betting"]["roi"] is None
    assert not any(summary["claim_readiness"].values())
    assert detail.empty


def test_invalid_original_hash_is_excluded():
    original = _original(forecast_id="f1", game_id="2026_03_ARI_LAR", player_id="p1")
    receipt = _receipt(original)
    receipt["original_sha256"] = "not-the-real-hash"
    summary, detail = evaluate_history(
        [receipt],
        grade_events=[_grade("f1", 90.0)],
        frozen_model_ref="test",
        bootstrap_replicates=10,
    )
    assert summary["audit"]["invalid_original_hashes"] == 1
    assert summary["sample"]["forecasts"] == 0
    assert detail.empty


def test_continuous_metrics_and_paired_market_error_are_correct():
    a = _original(
        forecast_id="f1",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        model_mean=80.0,
        fair_line=79.0,
        actual_line=70.0,
    )
    b = _original(
        forecast_id="f2",
        game_id="2026_03_BUF_MIA",
        player_id="p2",
        model_mean=60.0,
        fair_line=61.0,
        actual_line=65.0,
        p_over=0.40,
        p_under=0.60,
        market_p_over=0.48,
        market_p_under=0.52,
    )
    summary, _ = evaluate_history(
        [_receipt(a), _receipt(b)],
        grade_events=[_grade("f1", 85.0), _grade("f2", 55.0)],
        frozen_model_ref="test",
        bootstrap_replicates=20,
    )
    # Model-mean absolute errors are 5 and 5.
    assert summary["continuous"]["mae_model_mean"] == pytest.approx(5.0)
    # Fair-line errors are 6 and 6.
    assert summary["continuous"]["mae_fair_line"] == pytest.approx(6.0)
    # Market-line errors are 15 and 10, so Fair Line improves by 6.5 on average.
    assert summary["market_relative"]["mae_original_market_line"] == pytest.approx(12.5)
    assert summary["market_relative"]["paired_absolute_error_difference_fair_minus_market"] == pytest.approx(-6.5)


def test_probability_scores_compare_same_outcomes_to_market():
    a = _original(
        forecast_id="f1",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        actual_line=70.0,
        p_over=0.70,
        p_under=0.30,
        market_p_over=0.55,
        market_p_under=0.45,
    )
    b = _original(
        forecast_id="f2",
        game_id="2026_03_BUF_MIA",
        player_id="p2",
        actual_line=70.0,
        p_over=0.30,
        p_under=0.70,
        market_p_over=0.45,
        market_p_under=0.55,
    )
    summary, _ = evaluate_history(
        [_receipt(a), _receipt(b)],
        grade_events=[_grade("f1", 80.0), _grade("f2", 60.0)],
        frozen_model_ref="test",
        bootstrap_replicates=20,
    )
    assert summary["probability"]["brier_model"] == pytest.approx(0.09)
    assert summary["probability"]["brier_market_no_vig"] == pytest.approx(0.2025)
    assert summary["probability"]["brier_difference_model_minus_market"] == pytest.approx(-0.1125)


def test_push_is_not_mislabeled_as_binary_probability_win_or_loss():
    original = _original(
        forecast_id="push",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        prop_type="receptions",
        actual_line=5.0,
        model_mean=5.4,
        fair_line=5.0,
        p_over=0.45,
        p_under=0.40,
        market_p_over=0.50,
        market_p_under=0.50,
    )
    original["model"]["push_probability"] = 0.15
    summary, _ = evaluate_history(
        [_receipt(original)],
        grade_events=[_grade("push", 5.0)],
        frozen_model_ref="test",
        bootstrap_replicates=10,
    )
    assert summary["graded_sample"]["forecasts"] == 1
    assert summary["probability"]["sample"]["forecasts"] == 0


def test_model_edge_roi_is_price_aware_and_original_signal_only():
    win = _original(
        forecast_id="win",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        actual_line=70.5,
        p_over=0.62,
        p_under=0.38,
        market_p_over=0.52,
        market_p_under=0.48,
        over_price=120,
        under_price=-140,
        signal_state="MODEL EDGE",
    )
    loss = _original(
        forecast_id="loss",
        game_id="2026_03_BUF_MIA",
        player_id="p2",
        actual_line=70.5,
        p_over=0.62,
        p_under=0.38,
        market_p_over=0.52,
        market_p_under=0.48,
        over_price=-110,
        under_price=-110,
        signal_state="MODEL EDGE",
    )
    watch = _original(
        forecast_id="watch",
        game_id="2026_03_DAL_NYG",
        player_id="p3",
        actual_line=70.5,
        p_over=0.70,
        p_under=0.30,
        market_p_over=0.50,
        market_p_under=0.50,
        over_price=200,
        signal_state="WATCH",
    )
    summary, _ = evaluate_history(
        [_receipt(win), _receipt(loss), _receipt(watch)],
        grade_events=[
            _grade("win", 80.0),
            _grade("loss", 60.0),
            _grade("watch", 90.0),
        ],
        frozen_model_ref="test",
        bootstrap_replicates=20,
    )
    betting = summary["betting"]
    assert betting["eligible_bets"] == 2
    assert betting["wins"] == 1
    assert betting["losses"] == 1
    # +120 winner earns +1.2u; losing second bet loses 1u => +0.2 / 2 risked = 10% ROI.
    assert betting["net_units"] == pytest.approx(0.2)
    assert betting["roi"] == pytest.approx(0.10)
    assert american_to_decimal(120) == pytest.approx(2.2)


def test_td_model_edge_uses_preserved_yes_price():
    td = _td_original(
        forecast_id="td",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        p_td=0.62,
        market_p_td=0.50,
        td_price=150,
    )
    summary, _ = evaluate_history(
        [_receipt(td)],
        grade_events=[_grade("td", 1.0)],
        frozen_model_ref="test",
        bootstrap_replicates=10,
    )
    assert summary["betting"]["eligible_bets"] == 1
    assert summary["betting"]["wins"] == 1
    assert summary["betting"]["net_units"] == pytest.approx(1.5)
    assert summary["betting"]["roi"] == pytest.approx(1.5)


def test_closing_line_is_separate_and_clv_is_side_aware():
    over = _original(
        forecast_id="over",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        actual_line=70.5,
        fair_line=80.0,
        p_over=0.62,
        p_under=0.38,
        market_p_over=0.50,
        market_p_under=0.50,
    )
    under = _original(
        forecast_id="under",
        game_id="2026_03_BUF_MIA",
        player_id="p2",
        actual_line=70.5,
        fair_line=60.0,
        p_over=0.38,
        p_under=0.62,
        market_p_over=0.50,
        market_p_under=0.50,
    )
    summary, detail = evaluate_history(
        [_receipt(over), _receipt(under)],
        closing_events=[_close("over", 74.5), _close("under", 66.5)],
        grade_events=[_grade("over", 80.0), _grade("under", 60.0)],
        frozen_model_ref="test",
        bootstrap_replicates=20,
    )
    # Over: close-original = +4; Under: original-close = +4.
    assert summary["market_relative"]["threshold_clv_mean"] == pytest.approx(4.0)
    assert summary["market_relative"]["positive_threshold_clv_rate"] == pytest.approx(1.0)
    assert set(detail["close_line"]) == {74.5, 66.5}


def test_retrospective_original_is_excluded_even_with_valid_hash():
    original = _original(
        forecast_id="late-original",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
    )
    original["forecast_timestamp_utc"] = "2026-09-20T20:01:00+00:00"
    original["data_horizon_utc"] = "2026-09-20T19:00:00+00:00"
    receipt = _receipt(original)
    summary, detail = evaluate_history(
        [receipt],
        grade_events=[_grade("late-original", 80.0)],
        frozen_model_ref="test",
        bootstrap_replicates=5,
    )
    assert summary["sample"]["forecasts"] == 0
    assert summary["audit"]["excluded_reasons"]["original_not_point_in_time"] == 1
    assert detail.empty


def test_postkickoff_close_is_rejected_without_dropping_projection_grade():
    original = _original(
        forecast_id="late-close",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
    )
    close = _close("late-close", 75.5)
    close["captured_utc"] = "2026-09-20T20:01:00+00:00"
    summary, detail = evaluate_history(
        [_receipt(original)],
        closing_events=[close],
        grade_events=[_grade("late-close", 80.0)],
        frozen_model_ref="test",
        bootstrap_replicates=5,
    )
    assert summary["graded_sample"]["forecasts"] == 1
    assert summary["audit"]["excluded_reasons"]["closing_event_invalid_or_not_pregame"] == 1
    assert detail.iloc[0]["close_line"] is None or pytest.approx(detail.iloc[0]["close_line"]) != 75.5


def test_same_threshold_price_clv_uses_selected_side_price():
    original = _original(
        forecast_id="price-clv",
        game_id="2026_03_ARI_LAR",
        player_id="p1",
        actual_line=70.5,
        fair_line=80.0,
        p_over=0.62,
        p_under=0.38,
        market_p_over=0.50,
        market_p_under=0.50,
        over_price=120,
        under_price=-140,
    )
    close = {
        "event_type": "MARKET_CLOSE",
        "forecast_id": "price-clv",
        "captured_utc": "2026-09-20T19:55:00+00:00",
        "source": "test-close",
        "line": 70.5,
        "over_price_american": -110,
        "under_price_american": -110,
    }
    summary, _ = evaluate_history(
        [_receipt(original)],
        closing_events=[close],
        grade_events=[_grade("price-clv", 80.0)],
        frozen_model_ref="test",
        bootstrap_replicates=5,
    )
    expected = (1.0 / american_to_decimal(-110)) - (1.0 / american_to_decimal(120))
    market = summary["market_relative"]
    assert market["same_threshold_price_clv_n"] == 1
    assert market["same_threshold_price_clv_implied_probability_mean"] == pytest.approx(expected)
    assert market["positive_same_threshold_price_clv_rate"] == pytest.approx(1.0)

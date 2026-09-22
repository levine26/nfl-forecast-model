from __future__ import annotations

import json

import pandas as pd
import pytest

from research.props.v21.evaluate_prospective_props21 import (
    FROZEN_MODEL_VERSION,
    FROZEN_RECEIPT_VERSION,
    Props21EvaluationError,
    _receipt_to_evaluator_original,
    actual_player_stats,
    build_evaluation_events,
    read_frozen_receipts,
)


def _receipt(*, game_id="2026_02_ARI_SEA", prop_type="receiving_yards"):
    forecast = {
        "forecast_id": "p21_test",
        "forecast_timestamp_utc": "2026-09-20T00:00:22+00:00",
        "source_v1_forecast_timestamp_utc": "2026-09-19T23:59:43+00:00",
        "game_id": game_id,
        "kickoff_utc": "2026-09-20T20:25:00+00:00",
        "player_id": "00-0000002",
        "player_name": "Receiver Test",
        "position": "WR",
        "team": "ARI",
        "opponent": "SEA",
        "prop_type": prop_type,
        "model_mean": 70.0,
        "model_median": 68.5,
        "probability_over": 0.58,
        "probability_td": 0.30 if prop_type.endswith("td") else None,
        "market_line": 64.5,
        "market_probability_over": 0.52,
        "market_probability_td": 0.25 if prop_type.endswith("td") else None,
        "market_state": {
            "latest_capture_utc": "2026-09-19T23:59:41+00:00",
            "status": "MARKET_DISTRIBUTION_SUPPORTED",
            "book_count": 6,
            "line_dispersion": 1.0,
        },
        "qa": {
            "signal_state": "WATCH",
            "classification": "TEST",
            "research_eligible": True,
            "flag_codes": [],
        },
        "role_state": {
            "state": "STARTER_EXPECTED",
            "availability": "AVAILABLE",
            "workload": "NORMAL",
        },
        "provenance": {
            "challenger_model_version": FROZEN_MODEL_VERSION,
            "source_data_horizon_utc": "2026-09-19T23:56:50+00:00",
            "source_market_provider": ["propline"],
            "source_v1_model_version": "levline-props-simulation-v0.1.0",
            "research_only": True,
            "production_authorized": False,
            "pure_model_market_agnostic": True,
        },
    }
    return {
        "captured_utc": "2026-09-20T00:00:22+00:00",
        "forecast": forecast,
        "immutable": True,
        "model_version": FROZEN_MODEL_VERSION,
        "outcome": None,
        "production_authorized": False,
        "receipt_id": "p21_test",
        "receipt_version": FROZEN_RECEIPT_VERSION,
    }


def test_actual_player_stats_cover_all_supported_event_families():
    pbp = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "passer_player_id": "qb",
                "receiver_player_id": "wr",
                "rusher_player_id": "",
                "pass_attempt": 1,
                "complete_pass": 1,
                "passing_yards": 12,
                "receiving_yards": 12,
                "rushing_yards": 0,
                "pass_touchdown": 1,
                "rush_attempt": 0,
                "rush_touchdown": 0,
            },
            {
                "game_id": "g1",
                "passer_player_id": "",
                "receiver_player_id": "",
                "rusher_player_id": "rb",
                "pass_attempt": 0,
                "complete_pass": 0,
                "passing_yards": 0,
                "receiving_yards": 0,
                "rushing_yards": 7,
                "pass_touchdown": 0,
                "rush_attempt": 1,
                "rush_touchdown": 1,
            },
        ]
    )
    actuals = actual_player_stats(pbp)
    assert actuals[("g1", "qb", "passing_yards")] == 12
    assert actuals[("g1", "qb", "passing_tds")] == 1
    assert actuals[("g1", "wr", "receiving_yards")] == 12
    assert actuals[("g1", "wr", "receptions")] == 1
    assert actuals[("g1", "wr", "receiving_td")] == 1
    assert actuals[("g1", "wr", "anytime_td")] == 1
    assert actuals[("g1", "rb", "rushing_yards")] == 7
    assert actuals[("g1", "rb", "rushing_td")] == 1
    assert actuals[("g1", "rb", "anytime_td")] == 1


def test_receipt_adapter_preserves_fair_line_and_original_market():
    original = _receipt_to_evaluator_original(_receipt())
    assert original["model"]["fair_line"] == pytest.approx(68.5)
    assert original["model"]["mean"] == pytest.approx(70.0)
    assert original["model"]["over_probability"] == pytest.approx(0.58)
    assert original["market"]["line"] == pytest.approx(64.5)
    assert original["market"]["no_vig_over_probability"] == pytest.approx(0.52)
    assert original["market"]["captured_utc"] < original["forecast_timestamp_utc"]


def test_reader_rejects_future_component_forecast(tmp_path):
    row = _receipt()
    row["forecast"]["source_v1_forecast_timestamp_utc"] = "2026-09-20T00:00:23+00:00"
    path = tmp_path / "receipts.jsonl"
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(Props21EvaluationError, match="chronology"):
        read_frozen_receipts(path)


def test_postgame_join_leaves_unfinalized_game_ungraded():
    row = _receipt()
    forecasts, grades, audit, _ = build_evaluation_events(
        [row],
        completed_games=set(),
        outcome_pbp_games=set(),
        actuals={},
        participation={},
        graded_utc=pd.Timestamp("2026-09-21T12:00:00Z").to_pydatetime(),
    )
    assert len(forecasts) == 1
    assert grades == []
    assert audit["not_final"] == 1
    assert audit["graded"] == 0


def test_positive_snap_player_with_no_event_grades_zero():
    row = _receipt(prop_type="receiving_yards")
    game = row["forecast"]["game_id"]
    player = row["forecast"]["player_id"]
    forecasts, grades, audit, _ = build_evaluation_events(
        [row],
        completed_games={game},
        outcome_pbp_games={game},
        actuals={},
        participation={(game, player): 9},
        graded_utc=pd.Timestamp("2026-09-21T12:00:00Z").to_pydatetime(),
    )
    assert len(forecasts) == 1
    assert grades[0]["actual_result"] == 0.0
    assert audit["graded"] == 1

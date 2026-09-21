from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evaluate_props21_prospective as ev


def _v1_forecast():
    return {
        "forecast_id": "v1",
        "forecast_timestamp_utc": "2026-09-19T23:59:43+00:00",
        "data_horizon_utc": "2026-09-19T23:56:50+00:00",
        "kickoff_utc": "2026-09-20T17:00:00+00:00",
        "game_id": "2026_02_A_B",
        "player_id": "p1",
        "player": "Player One",
        "position": "WR",
        "team": "A",
        "opponent": "B",
        "prop_type": "receiving_yards",
        "signal_state": "WATCH",
        "data_quality": {"state": "MEDIUM"},
        "market": {
            "source": "consensus",
            "captured_utc": "2026-09-19T23:59:41+00:00",
            "line": 50.5,
            "no_vig_over_probability": 0.51,
            "no_vig_under_probability": 0.49,
            "over_price_american": -110,
            "under_price_american": -110,
        },
        "model": {
            "version": ev.V1_MODEL_VERSION,
            "mean": 55.0,
            "median": 54.0,
            "fair_line": 54.0,
            "standard_deviation": 12.0,
            "over_probability": 0.60,
            "under_probability": 0.40,
            "push_probability": 0.0,
            "prediction_interval": {"low": 30.0, "high": 80.0, "coverage": 0.8},
            "simulation_accounting_ok": True,
        },
    }


def _p21_receipt():
    return {
        "captured_utc": "2026-09-20T00:00:22+00:00",
        "immutable": True,
        "model_version": ev.P21_MODEL_VERSION,
        "outcome": None,
        "production_authorized": False,
        "receipt_id": "p21",
        "receipt_version": ev.P21_RECEIPT_VERSION,
        "forecast": {
            "forecast_id": "p21",
            "forecast_timestamp_utc": "2026-09-20T00:00:22+00:00",
            "source_v1_forecast_timestamp_utc": "2026-09-19T23:59:43+00:00",
            "source_v1_forecast_id": "v1",
            "kickoff_utc": "2026-09-20T17:00:00+00:00",
            "game_id": "2026_02_A_B",
            "player_id": "p1",
            "player_name": "Player One",
            "position": "WR",
            "team": "A",
            "opponent": "B",
            "prop_type": "receiving_yards",
            "model_mean": 55.0,
            "model_median": 54.0,
            "probability_over": 0.60,
            "probability_td": None,
            "market_line": 50.5,
            "market_probability_over": 0.51,
            "market_probability_td": None,
            "market_state": {
                "status": "MARKET_DISTRIBUTION_SUPPORTED",
                "latest_capture_utc": "2026-09-19T23:59:41+00:00",
                "book_count": 5,
                "reasons": [],
            },
            "qa": {
                "signal_state": "NO SIGNAL",
                "classification": "ROLE-UNCERTAIN DISAGREEMENT",
                "flag_codes": ["ROLE_UNCERTAINTY"],
                "reason_tag_codes": ["ROLE_UNCERTAINTY"],
            },
            "role_state": {
                "availability": "UNKNOWN",
                "state": "UNKNOWN",
                "workload": "UNKNOWN",
                "uncertainty": "ROLE_UNCERTAIN",
                "evidence_ids": [],
            },
            "xtd": None,
            "provenance": {
                "challenger_model_version": ev.P21_MODEL_VERSION,
                "source_v1_model_version": ev.V1_MODEL_VERSION,
                "source_data_horizon_utc": "2026-09-19T23:56:50+00:00",
                "source_market_sha256": "a" * 64,
                "research_only": True,
                "production_authorized": False,
            },
        },
    }


def test_adapter_restores_only_exact_frozen_v1_probability_complements():
    receipt = _p21_receipt()
    v1 = _v1_forecast()
    adapted, mapping, metadata = ev.adapt_receipts([receipt], {"v1": v1})
    original = adapted[0]["original_forecast"]
    assert original["model"]["over_probability"] == 0.60
    assert original["model"]["under_probability"] == 0.40
    assert original["model"]["push_probability"] == 0.0
    assert original["model"]["standard_deviation"] == 12.0
    assert original["signal_state"] == "NO SIGNAL"
    assert original["market"]["no_vig_under_probability"] == 0.49
    assert mapping == {"p21": "v1"}
    assert metadata["p21"]["source_v1_signal_state"] == "WATCH"


def test_actual_player_stats_constructs_all_supported_realized_stats():
    pbp = pd.DataFrame(
        [
            {
                "game_id": "g",
                "passer_player_id": "qb",
                "rusher_player_id": "",
                "receiver_player_id": "wr",
                "passing_yards": 20,
                "rushing_yards": 0,
                "receiving_yards": 20,
                "yards_gained": 20,
                "complete_pass": 1,
                "rush_attempt": 0,
                "pass_touchdown": 1,
                "rush_touchdown": 0,
            },
            {
                "game_id": "g",
                "passer_player_id": "",
                "rusher_player_id": "wr",
                "receiver_player_id": "",
                "passing_yards": 0,
                "rushing_yards": 8,
                "receiving_yards": 0,
                "yards_gained": 8,
                "complete_pass": 0,
                "rush_attempt": 1,
                "pass_touchdown": 0,
                "rush_touchdown": 1,
            },
            {
                "game_id": "g",
                "passer_player_id": "qb",
                "rusher_player_id": "",
                "receiver_player_id": "wr",
                "passing_yards": 5,
                "rushing_yards": 0,
                "receiving_yards": 5,
                "yards_gained": 5,
                "complete_pass": 1,
                "rush_attempt": 0,
                "pass_touchdown": 0,
                "rush_touchdown": 0,
            },
        ]
    )
    actuals = ev.actual_player_stats(pbp)
    assert actuals[("g", "qb", "passing_yards")] == 25
    assert actuals[("g", "qb", "passing_tds")] == 1
    assert actuals[("g", "wr", "receiving_yards")] == 25
    assert actuals[("g", "wr", "receptions")] == 2
    assert actuals[("g", "wr", "receiving_td")] == 1
    assert actuals[("g", "wr", "rushing_yards")] == 8
    assert actuals[("g", "wr", "rushing_td")] == 1
    assert actuals[("g", "wr", "anytime_td")] == 2


def test_unfinalized_game_is_never_scored_as_zero():
    receipt = _p21_receipt()
    adapted, _, _ = ev.adapt_receipts([receipt], {"v1": _v1_forecast()})
    events, audit = ev.build_grade_events(
        adapted,
        completed_games=set(),
        outcome_pbp_games=set(),
        actuals={},
        participation={},
        graded_utc="2026-09-21T20:00:00+00:00",
    )
    assert events == []
    assert audit["not_final"] == 1
    assert audit["graded"] == 0


def test_positive_snap_player_with_no_event_grades_zero():
    receipt = _p21_receipt()
    adapted, _, _ = ev.adapt_receipts([receipt], {"v1": _v1_forecast()})
    events, audit = ev.build_grade_events(
        adapted,
        completed_games={"2026_02_A_B"},
        outcome_pbp_games={"2026_02_A_B"},
        actuals={},
        participation={("2026_02_A_B", "p1"): 22},
        graded_utc="2026-09-21T20:00:00+00:00",
    )
    assert audit["graded"] == 1
    assert events[0]["actual_result"] == 0.0


def test_zero_offensive_snaps_are_void():
    receipt = _p21_receipt()
    adapted, _, _ = ev.adapt_receipts([receipt], {"v1": _v1_forecast()})
    events, audit = ev.build_grade_events(
        adapted,
        completed_games={"2026_02_A_B"},
        outcome_pbp_games={"2026_02_A_B"},
        actuals={("2026_02_A_B", "p1", "receiving_yards"): 99.0},
        participation={("2026_02_A_B", "p1"): 0},
        graded_utc="2026-09-21T20:00:00+00:00",
    )
    assert events == []
    assert audit["zero_offense_snaps_void"] == 1


def test_numeric_drift_from_v1_fails_closed(monkeypatch):
    receipt = _p21_receipt()
    v1 = _v1_forecast()
    receipt["forecast"]["model_mean"] = 56.0
    monkeypatch.setattr(ev, "EXPECTED_RECEIPTS", 1)
    monkeypatch.setattr(ev, "EXPECTED_GAMES", ("2026_02_A_B",))
    with pytest.raises(ev.Props21EvaluationError, match="numerical forecast drift"):
        ev.verify_frozen_cohort([receipt], [v1])

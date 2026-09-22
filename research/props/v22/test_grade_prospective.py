from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest

from research.props.v22.challengers import build_challenger_set


SCRIPT = Path(__file__).with_name("grade_prospective.py")
SPEC = importlib.util.spec_from_file_location("props22_grader_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _source(
    *,
    forecast_id: str = "f1",
    game_id: str = "2026_03_AAA_BBB",
    player_id: str = "p1",
    prop_type: str = "rushing_yards",
):
    forecast = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)
    kickoff = forecast + timedelta(hours=3)
    return {
        "forecast_id": forecast_id,
        "game_id": game_id,
        "player_id": player_id,
        "player_name": "Synthetic Player",
        "team": "AAA",
        "opponent": "BBB",
        "position": "RB",
        "prop_type": prop_type,
        "kickoff_utc": kickoff.isoformat(),
        "forecast_timestamp_utc": forecast.isoformat(),
        "model_median": 70.0,
        "market_line": 65.5,
        "probability_over": 0.60,
        "market_probability_over": 0.55,
        "role_state": {
            "state": "STARTER_EXPECTED",
            "availability": "AVAILABLE",
            "workload": "KNOWN",
        },
        "market_state": {
            "quote_as_of": (forecast - timedelta(minutes=5)).isoformat(),
            "book_count": 5,
        },
        "qa": {"classification": "RESEARCH_ELIGIBLE"},
        "provenance": {
            "challenger_model_version": "levline-props-2.1-sunday-v0.1",
            "source_data_horizon_utc": (forecast - timedelta(minutes=10)).isoformat(),
        },
        "outcome": None,
    }


def _receipts(**kwargs):
    return build_challenger_set(_source(**kwargs))


def test_builds_one_grade_for_complete_challenger_set():
    receipts = _receipts()
    source_sha = receipts[0]["source_props21_forecast_sha256"]
    grades, audit = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={("2026_03_AAA_BBB", "p1", "rushing_yards"): 82.0},
        participation={("2026_03_AAA_BBB", "p1"): 41},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )

    assert len(grades) == 1
    row = grades[0]
    assert row["source_props21_forecast_sha256"] == source_sha
    assert row["grade_status"] == "GRADED"
    assert row["actual_result"] == 82.0
    assert row["offense_snaps"] == 41
    assert len(row["grade_sha256"]) == 64
    assert audit["graded"] == 1


def test_legitimate_zero_stat_is_graded_when_player_participated():
    receipts = _receipts(prop_type="receiving_yards")
    grades, audit = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={},
        participation={("2026_03_AAA_BBB", "p1"): 12},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )

    assert grades[0]["grade_status"] == "GRADED"
    assert grades[0]["actual_result"] == 0.0
    assert audit["graded"] == 1


def test_zero_snap_player_is_void_not_zero_graded():
    receipts = _receipts()
    grades, audit = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={},
        participation={("2026_03_AAA_BBB", "p1"): 0},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )

    assert grades[0]["grade_status"] == "VOID"
    assert grades[0]["actual_result"] is None
    assert grades[0]["void_reason"] == "ZERO_OFFENSE_SNAPS"
    assert audit["zero_offense_snaps_void"] == 1


def test_missing_participation_stays_pending_without_grade():
    receipts = _receipts()
    grades, audit = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={},
        participation={},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )

    assert grades == []
    assert audit["missing_participation"] == 1


def test_incomplete_challenger_set_fails_closed():
    receipts = _receipts()[:-1]
    with pytest.raises(MODULE.Props22GradingError, match="incomplete frozen challenger set"):
        MODULE.build_grade_records(
            receipts,
            completed_games=set(),
            outcome_pbp_games=set(),
            actuals={},
            participation={},
        )


def test_existing_grade_is_not_rewritten():
    receipts = _receipts()
    first, _ = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={("2026_03_AAA_BBB", "p1", "rushing_yards"): 82.0},
        participation={("2026_03_AAA_BBB", "p1"): 41},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )
    source_sha = first[0]["source_props21_forecast_sha256"]

    second, audit = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={("2026_03_AAA_BBB", "p1", "rushing_yards"): 999.0},
        participation={("2026_03_AAA_BBB", "p1"): 41},
        existing_grades={source_sha: first[0]},
        graded_utc=datetime(2026, 9, 26, 4, 0, tzinfo=timezone.utc),
    )

    assert second == []
    assert audit["already_graded"] == 1


def test_append_immutable_grades_replays_identical_rows(tmp_path):
    path = tmp_path / "grades.jsonl"
    receipts = _receipts()
    rows, _ = MODULE.build_grade_records(
        receipts,
        completed_games={"2026_03_AAA_BBB"},
        outcome_pbp_games={"2026_03_AAA_BBB"},
        actuals={("2026_03_AAA_BBB", "p1", "rushing_yards"): 82.0},
        participation={("2026_03_AAA_BBB", "p1"): 41},
        graded_utc=datetime(2026, 9, 25, 4, 0, tzinfo=timezone.utc),
    )

    first = MODULE.append_immutable_grades(path, rows)
    second = MODULE.append_immutable_grades(path, rows)

    assert first == {"appended": 1, "total": 1}
    assert second == {"appended": 0, "total": 1}
    assert len(path.read_text().splitlines()) == 1


def test_allow_empty_is_clean_noop_before_first_holdout(tmp_path):
    status_path = tmp_path / "status.json"
    status = MODULE.run(
        tmp_path / "missing-receipts.jsonl",
        tmp_path / "grades.jsonl",
        status_path=status_path,
        allow_empty=True,
    )

    assert status["status"] == "NO_PROSPECTIVE_RECEIPTS"
    assert status["appended"] == 0
    assert status["production_authorized"] is False
    assert status_path.exists()

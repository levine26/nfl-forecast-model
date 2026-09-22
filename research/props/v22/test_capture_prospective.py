from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.props.v22.capture_prospective import (
    Props22CaptureError,
    append_immutable,
    build_capture,
    read_jsonl,
)


def _source(**overrides):
    row = {
        "forecast_id": "p21_capture_test",
        "player_id": "00-1",
        "player_name": "Test Player",
        "team": "ARI",
        "opponent": "SEA",
        "position": "WR",
        "game_id": "2026_03_ARI_SEA",
        "prop_type": "receiving_yards",
        "kickoff_utc": "2026-09-27T20:25:00+00:00",
        "forecast_timestamp_utc": "2026-09-27T16:00:00+00:00",
        "model_mean": 82.0,
        "model_median": 80.0,
        "probability_over": 0.70,
        "probability_td": None,
        "market_line": 70.0,
        "market_probability_over": 0.55,
        "market_probability_td": None,
        "role_state": {
            "state": "STARTER_EXPECTED",
            "availability": "ACTIVE",
            "workload": "STABLE",
        },
        "market_state": {
            "book_count": 6,
            "quote_as_of": "2026-09-27T15:59:00+00:00",
        },
        "qa": {"research_eligible": True},
        "provenance": {
            "challenger_model_version": "levline-props-2.1-sunday-v0.1",
            "source_data_horizon_utc": "2026-09-27T15:55:00+00:00",
        },
        "outcome": None,
    }
    row.update(overrides)
    return row


def test_build_capture_emits_complete_frozen_grid_without_outcomes():
    rows = build_capture([_source()])
    assert len(rows) == 8
    assert len({row["challenger_id"] for row in rows}) == 8
    assert len({row["source_props21_forecast_sha256"] for row in rows}) == 1
    assert all(row["outcome"] is None for row in rows)
    assert all(row["research_only"] is True for row in rows)
    assert all(row["production_authorized"] is False for row in rows)
    assert all(len(row["receipt_sha256"]) == 64 for row in rows)


def test_capture_rejects_outcome_bearing_or_wrong_baseline_source():
    with pytest.raises(Props22CaptureError, match="outcome-bearing"):
        build_capture([_source(outcome={"actual": 88.0})])

    bad = _source(
        provenance={
            "challenger_model_version": "different-model",
            "source_data_horizon_utc": "2026-09-27T15:55:00+00:00",
        }
    )
    with pytest.raises(Props22CaptureError, match="frozen baseline"):
        build_capture([bad])


def test_capture_rejects_duplicate_source_forecast_ids():
    with pytest.raises(Props22CaptureError, match="duplicate source forecast_id"):
        build_capture([_source(), _source()])


def test_immutable_append_is_idempotent_and_conflicts_fail_closed(tmp_path: Path):
    ledger = tmp_path / "props22.jsonl"
    rows = build_capture([_source()])

    first = append_immutable(ledger, rows)
    assert first == {"appended": 8, "replayed": 0, "total": 8}
    second = append_immutable(ledger, rows)
    assert second == {"appended": 0, "replayed": 8, "total": 8}
    assert len(read_jsonl(ledger)) == 8

    existing = read_jsonl(ledger)
    existing[0]["receipt_sha256"] = "0" * 64
    ledger.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in existing) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(Props22CaptureError, match="immutable challenger receipt conflict"):
        append_immutable(ledger, rows)

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research.props.v22.capture_prospective import append_immutable, build_capture
from research.props.v22.verify_capture_readiness import (
    Props22ReadinessError,
    audit_readiness,
)


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "levline_markets_live.yml"


def _source(**overrides):
    row = {
        "forecast_id": "p21_readiness_test",
        "player_id": "player-1",
        "player_name": "Test Player",
        "team": "AAA",
        "opponent": "BBB",
        "position": "WR",
        "game_id": "2026_03_AAA_BBB",
        "prop_type": "receiving_yards",
        "kickoff_utc": "2026-09-27T20:25:00+00:00",
        "forecast_timestamp_utc": "2026-09-27T15:59:00+00:00",
        "model_median": 71.5,
        "market_line": 68.5,
        "probability_over": 0.59,
        "market_probability_over": 0.53,
        "probability_td": None,
        "market_probability_td": None,
        "role_state": {"status": "STARTER_EXPECTED"},
        "market_state": {
            "book_count": 6,
            "quote_as_of": "2026-09-27T15:58:00+00:00",
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


def test_readiness_is_armed_before_first_future_capture(tmp_path: Path):
    result = audit_readiness(
        workflow_path=WORKFLOW,
        ledger_path=tmp_path / "missing.jsonl",
    )

    assert result["state"] == "ARMED_AWAITING_FIRST_CAPTURE"
    assert result["ledger_rows"] == 0
    assert result["source_forecasts"] == 0
    assert result["frozen_challenger_count"] == 8
    assert result["live_hook_present"] is True
    assert result["postkickoff_noop_precedes_capture"] is True
    assert result["promotion_candidate_ids"] == [
        "P22_COMBINED_25",
        "P22_COMBINED_50",
    ]


def test_first_future_capture_is_verified_as_complete_immutable_grid(tmp_path: Path):
    ledger = tmp_path / "forecast_originals.jsonl"
    rows = build_capture([_source()])
    result = append_immutable(ledger, rows)
    assert result == {"appended": 8, "replayed": 0, "total": 8}

    audit = audit_readiness(
        workflow_path=WORKFLOW,
        ledger_path=ledger,
    )

    assert audit["state"] == "FIRST_CAPTURE_VERIFIED"
    assert audit["ledger_rows"] == 8
    assert audit["source_forecasts"] == 1
    assert audit["challengers_per_source"] == 8
    assert audit["all_receipt_hashes_valid"] is True
    assert audit["all_sources_complete_grid"] is True
    assert audit["all_source_chronology_valid"] is True
    assert audit["all_receipts_research_only"] is True


def test_readiness_fails_closed_on_tampered_receipt(tmp_path: Path):
    ledger = tmp_path / "forecast_originals.jsonl"
    rows = build_capture([_source()])
    tampered = copy.deepcopy(rows)
    tampered[0]["line"]["challenger_line"] = 999.0
    ledger.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in tampered) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Props22ReadinessError, match="receipt SHA-256 mismatch"):
        audit_readiness(
            workflow_path=WORKFLOW,
            ledger_path=ledger,
        )


def test_readiness_fails_closed_on_incomplete_challenger_grid(tmp_path: Path):
    ledger = tmp_path / "forecast_originals.jsonl"
    rows = build_capture([_source()])
    ledger.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows[:-1]) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Props22ReadinessError, match="complete frozen challenger grid"):
        audit_readiness(
            workflow_path=WORKFLOW,
            ledger_path=ledger,
        )

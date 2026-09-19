import json
from datetime import datetime, timezone

from scripts.build_props21_challenger import _append_receipts, build


def source():
    forecast = {"forecast_id": "v1", "player_identity_resolved": True, "player_id": "p",
                "player": "Starter Player", "position": "QB", "team": "ATL", "opponent": "CAR",
                "game_id": "g", "kickoff_utc": "2026-09-20T17:00:00+00:00",
                "forecast_timestamp_utc": "2026-09-19T19:00:00+00:00",
                "data_horizon_utc": "2026-09-19T18:55:00+00:00", "prop_type": "passing_yards",
                "signal_state": "WATCH", "model": {"mean": 210.0, "fair_line": 211.0,
                "over_probability": .55, "simulation_count": 20000, "simulation_accounting_ok": True,
                "version": "v1"}, "market": {"captured_utc": "2026-09-19T18:59:00+00:00",
                "line": 205.5, "no_vig_over_probability": .50},
                "data_quality": {"critical_ok": True},
                "provenance": {"pure_simulation_market_agnostic": True, "market": {"individual_books": []}}}
    return {"contract_version": "levline-props-forecast-v0.1", "forecasts": [forecast]}


def test_coordinator_keeps_v1_separate_and_receipts_are_idempotent(tmp_path):
    generated = datetime(2026, 9, 19, 20, tzinfo=timezone.utc)
    previews = {"g": {"current_reported_sources": [{"title": "Starter Player will start Sunday",
        "source_name": "NFL.com", "source_url": "https://www.nfl.com/news/starter",
        "as_of": "2026-09-19T18:00:00+00:00"}]}}
    payload = build(source(), previews, generated=generated)
    assert payload["model_version"] == "levline-props-2.1-sunday-v0.1"
    assert payload["audit"]["v1_mutated"] is False
    assert payload["forecasts"][0]["source_v1_forecast_id"] == "v1"
    receipt = tmp_path / "receipts.jsonl"
    assert _append_receipts(receipt, payload) == 1
    assert _append_receipts(receipt, payload) == 0
    saved = json.loads(receipt.read_text().strip())
    assert saved["immutable"] is True and saved["outcome"] is None

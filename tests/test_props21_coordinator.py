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
                "over_probability": .55, "standard_deviation": 31.5,
                "prediction_interval": {"low": 152.0, "high": 272.0, "coverage": 0.90},
                "simulation_count": 20000, "simulation_accounting_ok": True,
                "td_count_distribution": {"0": 0.25, "1": 0.45, "2": 0.22, "3": 0.08},
                "expected_tds": 1.13, "version": "v1"}, "market": {"captured_utc": "2026-09-19T18:59:00+00:00",
                "line": 205.5, "no_vig_over_probability": .50},
                "data_quality": {"critical_ok": True},
                "provenance": {"pure_simulation_market_agnostic": True, "pure_simulation_seed": 20260920,
                "market": {"individual_books": []}}}
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



def manifest():
    common = {
        "game_id": "g",
        "team": "ATL",
        "prior_model_trained_through_season": 2025,
        "feature_data_horizon": "2026-09-19T18:00:00+00:00",
        "forecast_timestamp": "2026-09-19T19:00:00+00:00",
        "kickoff_timestamp": "2026-09-20T17:00:00+00:00",
    }
    return {
        "game_id": "g",
        "forecast_timestamp_utc": "2026-09-19T19:30:00+00:00",
        "kickoff_utc": "2026-09-20T17:00:00+00:00",
        "efficiency_player_parameters": [{
            **common,
            "player_id": "p",
            "player_name": "Starter Player",
            "position": "QB",
            "expected_passing_tds": 1.4,
            "expected_receiving_tds": 0.0,
            "expected_rushing_tds": 0.2,
            "expected_pass_attempts": 32.0,
            "expected_qb_rush_attempts": 4.0,
            "expected_carries": 0.0,
            "expected_routes": 0.0,
            "expected_targets": 0.0,
            "expected_red_zone_targets": 0.0,
            "expected_goal_line_carries": 1.0,
        }],
        "team_td_parameters": [{
            **common,
            "expected_passing_td_opportunities": 1.4,
            "expected_rushing_td_opportunities": 0.2,
        }],
    }


def test_coordinator_retains_manifest_opportunity_for_qa():
    generated = datetime(2026, 9, 19, 20, tzinfo=timezone.utc)
    payload = build(
        source(),
        {},
        generated=generated,
        manifests={"g": manifest()},
    )
    row = payload["forecasts"][0]
    assert row["opportunity_state"]["pass_attempts"] == 32.0
    assert row["opportunity_state"]["carries"] == 4.0
    assert "OPPORTUNITY_UNVERIFIED" not in {flag["code"] for flag in row["qa"]["flags"]}


def test_future_receipt_preserves_v1_distribution_diagnostics_without_public_mutation(tmp_path):
    generated = datetime(2026, 9, 19, 20, tzinfo=timezone.utc)
    src = source()
    payload = build(src, {}, generated=generated)
    public = payload["forecasts"][0]
    assert "source_v1_distribution_evidence" not in public

    receipt_path = tmp_path / "receipts.jsonl"
    assert _append_receipts(receipt_path, payload, source_payload=src) == 1
    saved = json.loads(receipt_path.read_text().strip())
    evidence = saved["forecast"]["source_v1_distribution_evidence"]
    assert evidence["contract_version"] == "levline-props21-source-distribution-evidence-v0.1"
    assert evidence["standard_deviation"] == 31.5
    assert evidence["prediction_interval"] == {"low": 152.0, "high": 272.0, "coverage": 0.9}
    assert evidence["simulation_count"] == 20000
    assert evidence["td_count_distribution"]["1"] == 0.45
    assert evidence["expected_tds"] == 1.13
    assert evidence["pure_simulation_seed"] == 20260920
    assert evidence["source_model_sha256"]
    assert evidence["lossless_continuous_distribution_preserved"] is False

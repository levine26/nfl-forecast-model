from __future__ import annotations

import json

from research.market_capture_observability_v1 import run_observed_capture


def test_missing_api_key_is_persisted_without_key_value(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    path = tmp_path / "status.json"

    def fake_capture(**kwargs):
        return {"status": "skipped", "reason": "missing_api_key", "external_request_made": False}

    receipt, code = run_observed_capture(
        status_path=str(path), quota_reserve=50, capture_fn=fake_capture
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert code == 2
    assert receipt == persisted
    assert persisted["reason"] == "missing_api_key"
    assert persisted["api_key_configured"] is False
    assert persisted["api_key_value_recorded"] is False
    assert persisted["production_authorized"] is False
    assert persisted["probability_feature_authorized"] is False
    assert persisted["completed_2026_outcomes_used"] == 0
    assert "THE_ODDS_API_KEY" not in path.read_text(encoding="utf-8")


def test_configured_key_records_boolean_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("THE_ODDS_API_KEY", "super-secret-test-value")
    path = tmp_path / "status.json"

    def fake_capture(**kwargs):
        return {
            "status": "captured",
            "reason": None,
            "external_request_made": True,
            "rows_added_this_request": 5,
        }

    receipt, code = run_observed_capture(
        status_path=str(path), quota_reserve=50, capture_fn=fake_capture
    )
    text = path.read_text(encoding="utf-8")
    assert code == 0
    assert receipt["api_key_configured"] is True
    assert receipt["api_key_value_recorded"] is False
    assert "super-secret-test-value" not in text


def test_collector_exception_is_persisted_then_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("THE_ODDS_API_KEY", "configured")
    path = tmp_path / "status.json"

    def fake_capture(**kwargs):
        raise RuntimeError("provider unavailable")

    receipt, code = run_observed_capture(
        status_path=str(path), quota_reserve=50, capture_fn=fake_capture
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert code == 1
    assert persisted == receipt
    assert persisted["status"] == "error"
    assert persisted["reason"] == "collector_exception"
    assert persisted["error_type"] == "RuntimeError"
    assert persisted["error"] == "provider unavailable"
    assert persisted["api_key_configured"] is True
    assert persisted["production_authorized"] is False


def test_quota_skip_is_observable_but_not_a_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("THE_ODDS_API_KEY", "configured")
    path = tmp_path / "status.json"

    def fake_capture(**kwargs):
        return {
            "status": "skipped",
            "reason": "free_quota_reserve_reached",
            "quota_remaining": 52,
            "required_credits": 3,
            "external_request_made": False,
        }

    receipt, code = run_observed_capture(
        status_path=str(path), quota_reserve=50, capture_fn=fake_capture
    )
    assert code == 0
    assert receipt["reason"] == "free_quota_reserve_reached"
    assert receipt["api_key_configured"] is True

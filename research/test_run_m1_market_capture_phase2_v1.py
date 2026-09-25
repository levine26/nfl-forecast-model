from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import research.run_m1_market_capture_phase2_v1 as phase2

NOW = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)


def test_early_skip_is_persisted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    status = tmp_path / "status.json"

    def fake_capture(**_: object) -> dict[str, object]:
        return {
            "status": "skipped",
            "reason": "missing_market_api_key",
            "external_request_made": False,
        }

    monkeypatch.setattr(phase2, "_phase1_capture", fake_capture)
    result = phase2.capture_phase2(status_path=str(status), now_utc=NOW)
    persisted = json.loads(status.read_text(encoding="utf-8"))

    assert result == persisted
    assert persisted["status"] == "skipped"
    assert persisted["reason"] == "missing_market_api_key"
    assert persisted["external_request_made"] is False
    assert persisted["completed_2026_outcomes_used"] == 0
    assert persisted["production_changed"] is False


def test_provider_failure_is_persisted_then_reraised(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    status = tmp_path / "status.json"

    def fake_capture(**_: object) -> dict[str, object]:
        raise RuntimeError("all configured market providers failed (propline:HTTPError:500)")

    monkeypatch.setattr(phase2, "_phase1_capture", fake_capture)
    with pytest.raises(RuntimeError):
        phase2.capture_phase2(status_path=str(status), now_utc=NOW)

    persisted = json.loads(status.read_text(encoding="utf-8"))
    assert persisted["status"] == "failed"
    assert persisted["reason"] == "provider_api_failure"
    assert persisted["external_request_made"] is True
    assert persisted["error_type"] == "RuntimeError"
    assert persisted["completed_2026_outcomes_used"] == 0


def test_successful_base_result_is_enriched_without_changing_scientific_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    status = tmp_path / "status.json"

    def fake_capture(**_: object) -> dict[str, object]:
        return {
            "status": "captured",
            "reason": None,
            "due_pairs": 2,
            "rows_added_this_request": 11,
            "market_provider": "propline",
            "quota_remaining": 88,
            "external_request_made": True,
            "minimum_complete_books": 2,
        }

    monkeypatch.setattr(phase2, "_phase1_capture", fake_capture)
    result = phase2.capture_phase2(status_path=str(status), quota_reserve=50, now_utc=NOW)

    assert result["status"] == "captured"
    assert result["due_pairs"] == 2
    assert result["rows_added_this_request"] == 11
    assert result["market_provider"] == "propline"
    assert result["minimum_complete_books"] == 2
    assert result["quota_reserve"] == 50
    assert result["completed_2026_outcomes_used"] == 0

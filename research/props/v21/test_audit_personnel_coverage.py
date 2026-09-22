from __future__ import annotations

import pytest

from research.props.v21.audit_personnel_coverage import PersonnelCoverageError, audit


def _receipt(
    forecast_id: str,
    *,
    role: str = "STARTER_EXPECTED",
    availability: str = "ACTIVE",
    workload: str = "STABLE",
    evidence=True,
    opportunity=True,
    forecast_time="2026-09-27T16:00:00+00:00",
    horizon="2026-09-27T15:55:00+00:00",
):
    return {
        "forecast": {
            "forecast_id": forecast_id,
            "game_id": "2026_03_ARI_SEA",
            "player_id": forecast_id,
            "position": "WR",
            "prop_type": "receiving_yards",
            "forecast_timestamp_utc": forecast_time,
            "kickoff_utc": "2026-09-27T20:25:00+00:00",
            "role_state": {
                "state": role,
                "availability": availability,
                "workload": workload,
                "evidence_ids": ["depth-chart:ARI:WR1"] if evidence else [],
            },
            "opportunity_state": {"routes": 32.0} if opportunity else {},
            "provenance": {
                "source_data_horizon_utc": horizon,
            },
        }
    }


def test_audit_reports_known_state_and_opportunity_coverage():
    receipts = [
        _receipt("a"),
        _receipt(
            "b",
            role="UNKNOWN",
            availability="UNKNOWN",
            workload="UNKNOWN",
            evidence=False,
            opportunity=False,
        ),
    ]
    summary, grouped = audit(receipts)

    assert summary["receipt_count"] == 2
    assert summary["coverage"]["role_known"]["rate"] == pytest.approx(0.5)
    assert summary["coverage"]["availability_known"]["rate"] == pytest.approx(0.5)
    assert summary["coverage"]["workload_known"]["rate"] == pytest.approx(0.5)
    assert summary["coverage"]["evidence_present"]["rate"] == pytest.approx(0.5)
    assert summary["coverage"]["opportunity_known"]["rate"] == pytest.approx(0.5)
    assert set(grouped["grouping"]) == {"position", "prop_type"}


def test_audit_fails_closed_on_nonpregame_chronology():
    receipt = _receipt(
        "bad",
        horizon="2026-09-27T16:05:00+00:00",
        forecast_time="2026-09-27T16:00:00+00:00",
    )
    with pytest.raises(PersonnelCoverageError, match="non-pregame"):
        audit([receipt])

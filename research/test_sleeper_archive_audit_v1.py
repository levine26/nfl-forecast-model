from __future__ import annotations

from research.sleeper_archive_audit_v1 import audit_snapshot, eligibility


def _snapshot() -> dict:
    return {
        "players": {
            "1": {
                "position": "QB",
                "status": "Active",
                "team": "ARI",
                "injury_status": None,
                "practice_participation": "Full",
                "practice_description": None,
                "depth_chart_order": 1,
            },
            "2": {
                "position": "WR",
                "status": "Active",
                "team": "LAR",
                "injury_status": "Questionable",
                "practice_participation": "Limited",
                "practice_description": "Hamstring",
                "depth_chart_order": 1,
            },
        }
    }


def test_verified_snapshot_is_point_in_time_eligible_when_data_gates_pass() -> None:
    audit = audit_snapshot(
        _snapshot(),
        commit_timestamp_utc="2026-09-10T18:00:00Z",
        decision_timestamp_utc="2026-09-10T20:00:00Z",
        resolved_player_ids={"1", "2"},
    )
    assert audit["technical_source_status"] == "VERIFIED"
    assert audit["point_in_time_safe"] is True
    assert audit["completed_2026_outcome_selection_authorized"] is False
    result = eligibility(
        audit,
        required_fields=["injury_status", "practice_participation", "depth_chart_order"],
    )
    assert result.eligible is True
    assert result.failures == ()


def test_commit_after_decision_time_fails_closed() -> None:
    audit = audit_snapshot(
        _snapshot(),
        commit_timestamp_utc="2026-09-10T20:01:00Z",
        decision_timestamp_utc="2026-09-10T20:00:00Z",
        resolved_player_ids={"1", "2"},
    )
    result = eligibility(audit, required_fields=["injury_status"])
    assert result.eligible is False
    assert "snapshot_persisted_after_decision_time" in result.failures


def test_missing_schema_field_is_a_data_failure_not_a_rights_failure() -> None:
    snapshot = _snapshot()
    snapshot["players"]["2"].pop("practice_participation")
    audit = audit_snapshot(
        snapshot,
        commit_timestamp_utc="2026-09-10T18:00:00Z",
        decision_timestamp_utc="2026-09-10T20:00:00Z",
        resolved_player_ids={"1", "2"},
    )
    result = eligibility(audit, required_fields=["practice_participation"])
    assert result.eligible is False
    assert "schema_presence_below_99.5pct:practice_participation" in result.failures


def test_identity_resolution_must_meet_99_5_percent_gate() -> None:
    players = {}
    for i in range(1, 201):
        players[str(i)] = {
            "position": "WR",
            "status": "Active",
            "team": "ARI",
            "injury_status": None,
            "practice_participation": None,
            "practice_description": None,
            "depth_chart_order": 1,
        }
    audit = audit_snapshot(
        {"players": players},
        commit_timestamp_utc="2026-09-10T18:00:00Z",
        decision_timestamp_utc="2026-09-10T20:00:00Z",
        resolved_player_ids={str(i) for i in range(1, 199)},
    )
    assert audit["identity_resolution_rate"] == 0.99
    result = eligibility(audit, required_fields=["injury_status"])
    assert result.eligible is False
    assert "identity_resolution_below_99.5pct" in result.failures


def test_null_injury_values_do_not_fail_schema_presence() -> None:
    audit = audit_snapshot(
        _snapshot(),
        commit_timestamp_utc="2026-09-10T18:00:00Z",
        decision_timestamp_utc="2026-09-10T20:00:00Z",
        resolved_player_ids={"1", "2"},
    )
    metrics = audit["state_fields"]["injury_status"]
    assert metrics["key_present_rate"] == 1.0
    assert metrics["non_null_rate"] == 0.5
    assert eligibility(audit, required_fields=["injury_status"]).eligible is True

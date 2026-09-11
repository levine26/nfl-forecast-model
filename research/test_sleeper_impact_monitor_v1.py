from __future__ import annotations

import copy

import pytest

from research.sleeper_archive_capture_v1 import build_capture
from research.sleeper_impact_monitor_v1 import (
    build_monitor_payload,
    build_qualified_availability_cards,
    build_state_change_events,
    validate_capture_for_decision,
)


def _source_snapshot(*, qb_injury: str = "Questionable", qb_practice: str = "Limited") -> dict:
    return {
        "players": {
            "qb1": {
                "full_name": "Quarter Back",
                "team": "ARI",
                "position": "QB",
                "status": "Active",
                "active": True,
                "injury_status": qb_injury,
                "practice_participation": qb_practice,
                "depth_chart_position": "QB",
                "depth_chart_order": 1,
                "gsis_id": "00-0000001",
            },
            "ot1": {
                "full_name": "Left Tackle",
                "team": "ARI",
                "position": "OT",
                "status": "Active",
                "active": True,
                "injury_status": "Out",
                "practice_participation": "DNP",
                "depth_chart_position": "LT",
                "depth_chart_order": 1,
                "gsis_id": "00-0000002",
            },
            "cb1": {
                "full_name": "Corner Back",
                "team": "LAC",
                "position": "CB",
                "status": "Active",
                "active": True,
                "injury_status": None,
                "practice_participation": "Full",
                "depth_chart_order": 1,
            },
            "wr1": {
                "full_name": "Healthy Receiver",
                "team": "LAC",
                "position": "WR",
                "status": "Active",
                "active": True,
                "injury_status": None,
                "practice_participation": "Full",
                "depth_chart_order": 1,
                "gsis_id": "00-0000004",
            },
        }
    }


def _capture(*, stamp: str = "2026-09-10T18:00:00Z", qb_injury: str = "Questionable", qb_practice: str = "Limited") -> dict:
    return build_capture(
        _source_snapshot(qb_injury=qb_injury, qb_practice=qb_practice),
        source_commit_sha=("a" if stamp.startswith("2026-09-10") else "b") * 40,
        source_commit_timestamp_utc=stamp,
        retrieval_timestamp_utc="2026-09-11T01:00:00Z",
    )


def _schedule() -> list[dict]:
    return [
        {
            "game_id": "2026_01_ARI_LAC",
            "season": "2026",
            "week": "1",
            "away_team": "ARI",
            "home_team": "LAC",
        }
    ]


def test_verified_capture_builds_all_position_qualified_cards_without_impacts() -> None:
    cards, audit = build_qualified_availability_cards(
        _capture(),
        _schedule(),
        season=2026,
        week=1,
        decision_timestamp_utc="2026-09-11T02:00:00Z",
    )
    by_name = {row["player_name"]: row for row in cards}

    assert set(by_name) == {"Quarter Back", "Left Tackle"}
    assert by_name["Left Tackle"]["position"] == "OT"
    assert by_name["Left Tackle"]["availability"]["source_status"] == "qualified"
    assert by_name["Left Tackle"]["availability"]["game_status"] == "Out"
    assert by_name["Quarter Back"]["player_id"] == "00-0000001"
    assert all(row["levline_impacts"] == [] for row in cards)
    assert all(row["observed_statistics"] == [] for row in cards)
    assert audit["cards_by_position"] == {"OT": 1, "QB": 1}
    assert audit["probability_feature_authorized"] is False
    assert audit["completed_2026_outcomes_used"] == 0


def test_healthy_players_are_suppressed_and_sleeper_id_is_valid_fallback() -> None:
    source = _source_snapshot()
    source["players"]["cb1"]["injury_status"] = "Questionable"
    capture = build_capture(
        source,
        source_commit_sha="c" * 40,
        source_commit_timestamp_utc="2026-09-10T18:00:00Z",
        retrieval_timestamp_utc="2026-09-11T01:00:00Z",
    )
    cards, audit = build_qualified_availability_cards(
        capture,
        _schedule(),
        season=2026,
        week=1,
        decision_timestamp_utc="2026-09-11T02:00:00Z",
    )
    cb = next(row for row in cards if row["player_name"] == "Corner Back")
    assert cb["player_id"] == "sleeper:cb1"
    assert cb["data_quality"]["identity_method"] == "sleeper_player_id"
    assert cb["data_quality"]["missing_fields"] == ["gsis_id"]
    assert audit["fallback_sleeper_ids"] == 1
    assert all(row["player_name"] != "Healthy Receiver" for row in cards)


def test_capture_integrity_and_point_in_time_gates_fail_closed() -> None:
    capture = _capture()
    validate_capture_for_decision(capture, decision_timestamp_utc="2026-09-11T02:00:00Z")

    tampered = copy.deepcopy(capture)
    tampered["players"]["qb1"]["injury_status"] = "Out"
    with pytest.raises(ValueError, match="content hash mismatch"):
        validate_capture_for_decision(tampered, decision_timestamp_utc="2026-09-11T02:00:00Z")

    with pytest.raises(ValueError, match="not available by the decision time"):
        validate_capture_for_decision(capture, decision_timestamp_utc="2026-09-10T17:59:59Z")


def test_state_changes_are_field_level_and_chronological() -> None:
    previous = _capture(stamp="2026-09-10T18:00:00Z", qb_injury="Questionable", qb_practice="Limited")
    current = _capture(stamp="2026-09-11T00:00:00Z", qb_injury="Out", qb_practice="DNP")
    events = build_state_change_events(
        previous,
        current,
        decision_timestamp_utc="2026-09-11T02:00:00Z",
    )
    qb = next(row for row in events if row["archive_player_id"] == "qb1")
    assert qb["changed_fields"]["injury_status"] == {
        "before": "Questionable",
        "after": "Out",
    }
    assert qb["changed_fields"]["practice_participation"] == {
        "before": "Limited",
        "after": "DNP",
    }
    assert qb["probability_feature_authorized"] is False

    with pytest.raises(ValueError, match="previous Sleeper capture is newer"):
        build_state_change_events(
            current,
            previous,
            decision_timestamp_utc="2026-09-11T02:00:00Z",
        )


def test_monitor_payload_is_explainability_only_and_preserves_change_events() -> None:
    previous = _capture(stamp="2026-09-10T18:00:00Z", qb_injury="Questionable", qb_practice="Limited")
    current = _capture(stamp="2026-09-11T00:00:00Z", qb_injury="Out", qb_practice="DNP")
    payload = build_monitor_payload(
        current,
        _schedule(),
        season=2026,
        week=1,
        decision_timestamp_utc="2026-09-11T02:00:00Z",
        previous_capture=previous,
    )

    assert payload["mode"] == "research_explainability_only"
    assert payload["probability_feature_authorized"] is False
    assert payload["live_site_consumes_this_file"] is False
    assert payload["source_scope"] == "verified_2026_sleeper_archive_all_positions"
    assert payload["capture_audit"]["modeled_player_impacts_created"] == 0
    assert payload["state_changes"]
    assert payload["games"][0]["players"]
    assert all(
        player["availability"]["source_status"] == "qualified"
        for player in payload["games"][0]["players"]
    )

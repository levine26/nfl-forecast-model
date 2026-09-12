from __future__ import annotations

import copy

import pytest

from research.levline4_upset_evidence_v1 import build_evidence_payload


def _market_row() -> dict[str, object]:
    row: dict[str, object] = {
        "game_id": "2026_01_AAA_BBB",
        "home_team": "BBB",
        "away_team": "AAA",
        "kickoff_timestamp_utc": "2026-09-13T17:00:00Z",
        "strict_no_later_than_cutoff": True,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    observations = {
        "t120": ("2026-09-13T14:58:00Z", 0.60, -2.0),
        "t60": ("2026-09-13T15:58:00Z", 0.61, -2.5),
        "t45": ("2026-09-13T16:13:00Z", 0.62, -3.0),
        "t30": ("2026-09-13T16:28:00Z", 0.615, -2.5),
    }
    for suffix, (stamp, prob, spread) in observations.items():
        row[f"request_timestamp_utc_{suffix}"] = stamp
        row[f"timing_error_minutes_{suffix}"] = -2.0
        row[f"market_home_prob_{suffix}"] = prob
        row[f"home_spread_{suffix}"] = spread
        row[f"total_points_{suffix}"] = 45.5
        row[f"probability_range_{suffix}"] = 0.02
        row[f"source_count_{suffix}"] = 6
        row[f"max_freshness_minutes_{suffix}"] = 3.0
    for pair, change in {
        "t60_minus_t120": 0.01,
        "t45_minus_t120": 0.02,
        "t30_minus_t120": 0.015,
    }.items():
        row[f"home_probability_{pair}"] = change
        row[f"home_probability_pp_{pair}"] = change * 100.0
        row[f"home_logit_{pair}"] = change * 4.0
        row[f"home_spread_{pair}"] = -0.5
        row[f"total_points_{pair}"] = 0.0
        row[f"probability_range_{pair}"] = 0.0
        row[f"book_common_count_{pair}"] = 5
        row[f"book_overlap_fraction_{pair}"] = 0.83
        row[f"book_home_move_share_{pair}"] = 0.6
        row[f"book_away_move_share_{pair}"] = 0.2
        row[f"book_unchanged_share_{pair}"] = 0.2
        row[f"book_movement_breadth_{pair}"] = 0.4
        row[f"book_median_probability_change_pp_{pair}"] = change * 100.0
        row[f"book_median_logit_change_{pair}"] = change * 4.0
    return row


def _component_row(generated: str = "2026-09-13T14:00:00Z") -> dict[str, object]:
    return {
        "game_id": "2026_01_AAA_BBB",
        "generated_utc": generated,
        "source_sha": "abc123",
        "feature_set": "pure_v1",
        "logistic_home_prob": 0.44,
        "extra_trees_home_prob": 0.47,
        "xgboost_home_prob": 0.46,
        "catboost_home_prob": 0.45,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }


def _personnel_payload(source_time: str = "2026-09-13T14:30:00Z") -> dict[str, object]:
    return {
        "generated_utc": "2026-09-13T14:31:00Z",
        "mode": "research_explainability_only",
        "source_scope": "verified_2026_sleeper_archive_all_positions",
        "probability_feature_authorized": False,
        "live_site_consumes_this_file": False,
        "capture_audit": {
            "source_commit_timestamp_utc": source_time,
            "source_commit_sha": "def456",
            "content_sha256": "hash",
            "probability_feature_authorized": False,
            "modeled_player_impacts_created": 0,
            "completed_2026_outcomes_used": 0,
        },
        "games": [
            {
                "game_id": "2026_01_AAA_BBB",
                "players": [
                    {
                        "team": "AAA",
                        "player_id": "p1",
                        "player_name": "Away Player",
                        "position": "WR",
                        "observed_statistics": [],
                        "levline_impacts": [],
                        "availability": {
                            "practice_status": "Limited",
                            "game_status": "Questionable",
                            "source_status": "qualified",
                            "source_data_as_of": source_time,
                        },
                    },
                    {
                        "team": "BBB",
                        "player_id": "p2",
                        "player_name": "Home Player",
                        "position": "OL",
                        "observed_statistics": [],
                        "levline_impacts": [],
                        "availability": {
                            "practice_status": "DNP",
                            "game_status": "Out",
                            "source_status": "qualified",
                            "source_data_as_of": source_time,
                        },
                    },
                ],
            }
        ],
        "state_changes": [
            {
                "team": "BBB",
                "player_id": "p2",
                "current_source_commit_timestamp_utc": source_time,
                "changed_fields": {"injury_status": {"before": "Questionable", "after": "Out"}},
                "research_only": True,
                "probability_feature_authorized": False,
            }
        ],
    }


def test_builds_four_strict_pit_evidence_records_without_pick_rule() -> None:
    payload, audit = build_evidence_payload(
        [_component_row()],
        [_market_row()],
        personnel_payloads=[_personnel_payload()],
        generated_utc="2026-09-13T14:40:00Z",
    )

    assert len(payload["records"]) == 4
    assert audit["strict_pit_complete_records"] == 4
    assert payload["winner_switch_rule_defined"] is False
    assert payload["threshold_defined"] is False
    assert payload["learned_cross_channel_weight_defined"] is False
    t45 = next(row for row in payload["records"] if row["horizon"] == "T-45m")
    assert t45["market"]["request_timestamp_utc"] == "2026-09-13T16:13:00Z"
    assert t45["market"]["movement_from_t120"]["same_book_common_count"] == 5
    assert t45["components"]["home_votes"] == 0
    assert t45["components"]["unanimous_side"] == "away"
    assert t45["player_state"]["home_attention_count"] == 1
    assert t45["player_state"]["away_attention_count"] == 1
    assert t45["player_state"]["home_state_change_count"] == 1


def test_post_cutoff_component_capture_is_not_backfilled_into_earlier_horizons() -> None:
    payload, audit = build_evidence_payload(
        [_component_row("2026-09-13T16:20:00Z")],
        [_market_row()],
        personnel_payloads=[_personnel_payload()],
    )

    availability = {
        row["horizon"]: row["channel_available"]["components"] for row in payload["records"]
    }
    assert availability == {
        "T-120m": False,
        "T-60m": False,
        "T-45m": False,
        "T-30m": True,
    }
    assert audit["records_with_components"] == 1


def test_post_cutoff_market_request_fails_closed() -> None:
    market = _market_row()
    market["request_timestamp_utc_t45"] = "2026-09-13T16:16:00Z"
    market["timing_error_minutes_t45"] = 1.0

    with pytest.raises(ValueError, match="after its nominal cutoff"):
        build_evidence_payload([_component_row()], [market])


def test_player_state_after_cutoff_is_preserved_as_missing_not_backfilled() -> None:
    payload, _ = build_evidence_payload(
        [_component_row()],
        [_market_row()],
        personnel_payloads=[_personnel_payload("2026-09-13T16:20:00Z")],
    )
    availability = {
        row["horizon"]: row["channel_available"]["player_state"] for row in payload["records"]
    }
    assert availability == {
        "T-120m": False,
        "T-60m": False,
        "T-45m": False,
        "T-30m": True,
    }


def test_forbidden_completed_outcome_field_is_rejected() -> None:
    component = _component_row()
    component["home_win"] = 1
    with pytest.raises(ValueError, match="forbidden outcome field"):
        build_evidence_payload([component], [_market_row()])


def test_output_never_contains_result_fields_or_nonempty_player_impacts() -> None:
    personnel = _personnel_payload()
    personnel_copy = copy.deepcopy(personnel)
    payload, _ = build_evidence_payload(
        [_component_row()], [_market_row()], personnel_payloads=[personnel_copy]
    )
    serialized = str(payload).lower()
    assert "home_score" not in serialized
    assert "away_score" not in serialized
    assert "actual_winner" not in serialized
    for row in payload["records"]:
        if row["player_state"]:
            assert row["player_state"]["modeled_player_impacts_created"] == 0
            assert row["player_state"]["probability_feature_authorized"] is False

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from research.adaptive_candidate4_shadow_v1 import (
    CANDIDATE_ID,
    PREREGISTRATION_SHA,
    append_immutable,
    build_candidate4_decisions,
)


def _production() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_A_B",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "home_team": "B",
            "away_team": "A",
            "final_home_prob": 0.46,
            "lock_status": "LOCKED",
            "lock_timestamp_utc": "2026-09-27T15:30:00Z",
            "kickoff_utc": "2026-09-27T17:00:00Z",
            "minutes_to_kickoff_at_lock": 90.0,
            "fst_artifact_id": "F-ST-01-FROZEN-2026",
            "final_probability_strategy": "F-ST-01-FROZEN-2026",
        }
    ])


def _market(*, provider_t120: str = "propline", provider_t60: str = "propline") -> pd.DataFrame:
    rows: list[dict] = []
    common = [f"book-{i}" for i in range(5)]
    for horizon, target, request, provider, home_prob in [
        ("T-120m", "2026-09-27T15:00:00Z", "2026-09-27T14:59:00Z", provider_t120, 0.40),
        ("T-60m", "2026-09-27T16:00:00Z", "2026-09-27T15:59:00Z", provider_t60, 0.55),
    ]:
        base = {
            "game_id": "2026_03_A_B",
            "market_provider": provider,
            "event_id": "evt-a-b",
            "provider_commence_time_utc": "2026-09-27T17:00:00+00:00",
            "home_team": "B",
            "away_team": "A",
            "kickoff_timestamp_utc": "2026-09-27T17:00:00+00:00",
            "horizon": horizon,
            "target_timestamp_utc": target,
            "request_timestamp_utc": request,
            "timing_error_minutes": -1.0,
            "research_only": True,
            "production_authorized": False,
        }
        for i, book in enumerate(common):
            # All books move toward the home team; preserve slight cross-book variation.
            p = home_prob + (i - 2) * 0.002
            rows.append(
                {
                    **base,
                    "row_type": "book",
                    "sportsbook_key": book,
                    "h2h_home_no_vig": p,
                }
            )
        rows.append(
            {
                **base,
                "row_type": "consensus",
                "sportsbook_key": "sportsbook_consensus",
                "h2h_home_no_vig": home_prob,
                "source_count": 5,
                "source_names": "|".join(common),
                "probability_range": 0.008,
                "max_freshness_minutes": 4.0,
            }
        )
    return pd.DataFrame(rows)


def _qb(*, direction: int = 1, known_by: str = "2026-09-27T15:50:00Z") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_A_B",
            "qb_state_complete": True,
            "source_qualified": True,
            "research_only": True,
            "production_authorized": False,
            "qb_shock_direction": direction,
            "qb_shock_known_by_utc": known_by,
            "home_t120_qb1_player_name": "Home Quarterback",
            "home_t120_qb1_gsis_id": "00-0000002",
            "home_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "away_t120_qb1_player_name": "Away Quarterback",
            "away_t120_qb1_gsis_id": "00-0000001",
            "away_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "inactive_raw_sha256": "a" * 64,
            "inactive_capture_timestamp_utc": known_by,
        }
    ])


def test_primary_candidate_switches_only_when_all_frozen_gates_agree() -> None:
    out = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=1),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    assert len(out) == 1
    row = out.iloc[0]
    assert row["candidate_id"] == CANDIDATE_ID
    assert row["preregistration_sha"] == PREREGISTRATION_SHA
    assert bool(row["eligible"]) is True
    assert row["incumbent_pick"] == "A"
    assert row["market_t60_pick"] == "B"
    assert row["common_sportsbook_count"] == 5
    assert row["market_path_breadth"] == pytest.approx(1.0)
    assert bool(row["gate_market_disagreement"]) is True
    assert bool(row["gate_path_direction"]) is True
    assert bool(row["gate_path_breadth"]) is True
    assert bool(row["gate_qb_nonzero"]) is True
    assert bool(row["gate_qb_direction"]) is True
    assert bool(row["candidate_switch"]) is True
    assert row["candidate_pick"] == "B"
    assert row["candidate_home_prob"] == pytest.approx(0.55)
    assert row["level_only_pick"] == "B"
    assert row["path_only_pick"] == "B"
    assert row["qb_only_pick"] == "B"
    assert row["completed_2026_outcomes_used"] == 0
    assert bool(row["production_authorized"]) is False


def test_missing_qb_state_fails_closed_and_never_switches() -> None:
    out = build_candidate4_decisions(
        _production(),
        _market(),
        pd.DataFrame(),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    row = out.iloc[0]
    assert bool(row["eligible"]) is False
    assert "missing_qb_state" in row["ineligibility_reasons"]
    assert bool(row["candidate_switch"]) is False
    assert row["candidate_pick"] == "A"
    assert row["candidate_home_prob"] == pytest.approx(0.46)


def test_qb_evidence_after_t60_fails_closed() -> None:
    out = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(known_by="2026-09-27T16:01:00Z"),
        generated_at_utc="2026-09-27T16:02:00Z",
    )
    row = out.iloc[0]
    assert bool(row["eligible"]) is False
    assert "qb_shock_after_t60" in row["ineligibility_reasons"]
    assert "inactive_capture_not_by_t60" in row["ineligibility_reasons"]
    assert bool(row["candidate_switch"]) is False


def test_opposite_qb_direction_preserves_incumbent() -> None:
    out = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=-1),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    row = out.iloc[0]
    assert bool(row["eligible"]) is True
    assert bool(row["gate_qb_nonzero"]) is True
    assert bool(row["gate_qb_direction"]) is False
    assert bool(row["candidate_switch"]) is False
    assert row["candidate_pick"] == "A"


def test_market_provider_change_between_primary_horizons_fails_closed() -> None:
    with pytest.raises(ValueError, match="market horizons disagree on event identity"):
        build_candidate4_decisions(
            _production(),
            _market(provider_t120="propline", provider_t60="other-provider"),
            _qb(direction=1),
            generated_at_utc="2026-09-27T16:01:00Z",
        )


def test_decision_hash_is_replay_stable_and_append_is_idempotent() -> None:
    first = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=1),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    replay = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=1),
        generated_at_utc="2026-09-27T16:05:00Z",
    )
    assert first.iloc[0]["decision_sha256"] == replay.iloc[0]["decision_sha256"]
    combined = append_immutable(first, replay)
    assert len(combined) == 1
    assert combined.iloc[0]["generated_at_utc"] == "2026-09-27T16:01:00Z"


def test_changed_scientific_evidence_cannot_rewrite_existing_decision() -> None:
    first = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=1),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    changed = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=-1),
        generated_at_utc="2026-09-27T16:01:00Z",
    )
    assert first.iloc[0]["decision_sha256"] != changed.iloc[0]["decision_sha256"]
    with pytest.raises(ValueError, match="rewrite attempted"):
        append_immutable(first, changed)


def test_postkickoff_recording_cannot_become_eligible() -> None:
    out = build_candidate4_decisions(
        _production(),
        _market(),
        _qb(direction=1),
        generated_at_utc="2026-09-27T17:01:00Z",
    )
    row = out.iloc[0]
    assert bool(row["eligible"]) is False
    assert "decision_recorded_postkickoff" in row["ineligibility_reasons"]
    assert bool(row["candidate_switch"]) is False

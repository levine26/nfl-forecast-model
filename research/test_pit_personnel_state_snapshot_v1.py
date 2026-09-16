from __future__ import annotations

import json

import pytest

from research.pit_personnel_state_snapshot_v1 import build_personnel_state_snapshot
from research.structured_beat_observation_v1 import validate_structured_observation


RAW_SHA = "c" * 64


def _raw_observation(
    *,
    observation_id: str = "obs-1",
    game_id: str = "2026_03_ARI_SEA",
    forecast_asof: str = "2026-09-27T18:00:00Z",
    captured_at: str = "2026-09-27T17:59:00Z",
    published_at: str = "2026-09-27T17:55:00Z",
    value_json: str = '{"expected_to_start":true,"position":"QB"}',
) -> dict:
    return {
        "observation_id": observation_id,
        "game_id": game_id,
        "team": "ARI",
        "observation_type": "expected_starter",
        "entity_type": "player",
        "entity_id": "player:ari-qb-example",
        "value_json": value_json,
        "confidence": 0.88,
        "confidence_basis": "coach statement plus beat confirmation",
        "source_priority": "recorded_but_not_adjudicated",
        "source": "Example credentialed beat report",
        "source_url_or_id": f"https://example.com/{observation_id}",
        "raw_evidence_ref": f"archive://beat/{observation_id}",
        "raw_evidence_sha256": RAW_SHA,
        "published_at_utc": published_at,
        "captured_at_utc": captured_at,
        "forecast_asof_utc": forecast_asof,
        "kickoff_timestamp_utc": "2026-09-27T20:05:00Z",
        "extraction_method": "llm_fact_extraction",
        "extractor_id": "structured-football-fact-extractor",
        "extractor_version": "v1.0.0",
    }


def _observation(**kwargs) -> dict:
    return validate_structured_observation(_raw_observation(**kwargs))


def test_latest_known_state_supersedes_earlier_state_without_backfill() -> None:
    earlier = _observation(
        observation_id="obs-earlier",
        forecast_asof="2026-09-27T17:00:00Z",
        captured_at="2026-09-27T16:59:00Z",
        published_at="2026-09-27T16:50:00Z",
        value_json='{"expected_to_start":false,"position":"QB"}',
    )
    later = _observation(observation_id="obs-later")
    rows, receipt = build_personnel_state_snapshot(
        [earlier, later],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert len(rows) == 1
    assert json.loads(rows[0]["value_json"])["expected_to_start"] is True
    assert rows[0]["selected_observation_id"] == "obs-later"
    assert rows[0]["superseded_observation_ids"] == ["obs-earlier"]
    assert receipt["superseded_observations"] == 1


def test_future_observation_is_excluded_and_cannot_back_propagate() -> None:
    known = _observation(observation_id="obs-known")
    future = _observation(
        observation_id="obs-future",
        forecast_asof="2026-09-27T19:30:00Z",
        captured_at="2026-09-27T19:29:00Z",
        published_at="2026-09-27T19:20:00Z",
        value_json='{"expected_to_start":false,"position":"QB"}',
    )
    rows, receipt = build_personnel_state_snapshot(
        [known, future],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert len(rows) == 1
    assert rows[0]["selected_observation_id"] == "obs-known"
    assert receipt["future_observations_excluded"] == 1


def test_coequal_conflicting_state_fails_closed_without_source_priority_override() -> None:
    first = _observation(observation_id="obs-a")
    second = _observation(
        observation_id="obs-b",
        value_json='{"expected_to_start":false,"position":"QB"}',
    )
    with pytest.raises(ValueError, match="coequal conflicting personnel observations fail closed"):
        build_personnel_state_snapshot(
            [first, second],
            game_id="2026_03_ARI_SEA",
            snapshot_asof_utc="2026-09-27T19:00:00Z",
        )


def test_coequal_identical_state_preserves_all_supporting_observations() -> None:
    first = _observation(observation_id="obs-a")
    second = _observation(observation_id="obs-b")
    rows, receipt = build_personnel_state_snapshot(
        [second, first],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert rows[0]["selected_observation_id"] == "obs-a"
    assert rows[0]["supporting_observation_ids"] == ["obs-a", "obs-b"]
    assert receipt["coequal_supporting_observations"] == 1
    assert receipt["source_priority_used_for_adjudication"] is False


def test_mutated_validated_observation_is_rejected_by_hash() -> None:
    row = _observation()
    row["value_json"] = '{"expected_to_start":false,"position":"QB"}'
    with pytest.raises(ValueError, match="observation_sha256 mismatch"):
        build_personnel_state_snapshot(
            [row],
            game_id="2026_03_ARI_SEA",
            snapshot_asof_utc="2026-09-27T19:00:00Z",
        )


def test_unicode_observation_uses_exact_upstream_digest_semantics() -> None:
    raw = _raw_observation(observation_id="obs-unicode")
    raw["source"] = "José beat report — Arizona"
    raw["confidence_basis"] = "Señal confirmada por el entrenador"
    validated = validate_structured_observation(raw)
    rows, receipt = build_personnel_state_snapshot(
        [validated],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert rows[0]["selected_observation_id"] == "obs-unicode"
    assert rows[0]["source"] == "José beat report — Arizona"
    assert receipt["snapshot_valid"] is True


def test_snapshot_at_or_after_kickoff_fails_closed() -> None:
    with pytest.raises(ValueError, match="snapshot_asof_utc must precede kickoff"):
        build_personnel_state_snapshot(
            [_observation()],
            game_id="2026_03_ARI_SEA",
            snapshot_asof_utc="2026-09-27T20:05:00Z",
        )


def test_other_game_rows_are_ignored_not_mixed() -> None:
    target = _observation(observation_id="obs-target")
    other = _observation(observation_id="obs-other", game_id="2026_03_LAR_SF")
    rows, receipt = build_personnel_state_snapshot(
        [target, other],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert len(rows) == 1
    assert receipt["other_game_observations_excluded"] == 1


def test_missingness_and_probability_firewalls_are_explicit() -> None:
    rows, receipt = build_personnel_state_snapshot(
        [_observation()],
        game_id="2026_03_ARI_SEA",
        snapshot_asof_utc="2026-09-27T19:00:00Z",
    )
    assert len(rows) == 1
    assert receipt["absence_of_observation_means_healthy_or_active"] is False
    assert receipt["absence_of_observation_means_starter"] is False
    assert receipt["missing_state_imputation_used"] is False
    assert receipt["complete_lineup_claim_authorized"] is False
    assert receipt["availability_probability_mapping_authorized"] is False
    assert receipt["starter_probability_mapping_authorized"] is False
    assert receipt["role_share_numeric_mapping_authorized"] is False
    assert receipt["football_to_win_probability_mapping_authorized"] is False
    assert receipt["probability_feature_authorized"] is False
    assert receipt["production_authorized"] is False
    assert receipt["official_forecast_mutation_authorized"] is False
    assert receipt["completed_2026_outcomes_used"] == 0
    assert len(receipt["snapshot_sha256"]) == 64
    assert len(rows[0]["state_row_sha256"]) == 64

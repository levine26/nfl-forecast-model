from __future__ import annotations

import pytest

from research.structured_beat_observation_v1 import (
    validate_structured_observation,
    validate_structured_observations,
)


RAW_SHA = "b" * 64


def _row() -> dict:
    return {
        "observation_id": "obs-2026_03_ARI_SEA-ari-rt-v1",
        "game_id": "2026_03_ARI_SEA",
        "team": "ARI",
        "observation_type": "expected_starter",
        "entity_type": "player",
        "entity_id": "player:example-right-tackle",
        "value_json": '{"expected_to_start":true,"position":"RT"}',
        "confidence": 0.91,
        "confidence_basis": "coach statement plus full practice participation",
        "source_priority": "primary_or_credentialed_beat",
        "source": "Example credentialed beat report",
        "source_url_or_id": "https://example.com/report/123",
        "raw_evidence_ref": "archive://beat/example/123",
        "raw_evidence_sha256": RAW_SHA,
        "published_at_utc": "2026-09-27T16:00:00Z",
        "captured_at_utc": "2026-09-27T16:02:00Z",
        "forecast_asof_utc": "2026-09-27T18:00:00Z",
        "kickoff_timestamp_utc": "2026-09-27T20:05:00Z",
        "extraction_method": "llm_fact_extraction",
        "extractor_id": "structured-football-fact-extractor",
        "extractor_version": "v1.0.0",
    }


def test_valid_fact_is_outcome_blind_and_has_no_probability_authority() -> None:
    out = validate_structured_observation(_row())
    assert out["observation_type"] == "expected_starter"
    assert out["confidence"] == pytest.approx(0.91)
    assert out["probability_effect_authorized"] is False
    assert out["llm_directional_judgment_authorized"] is False
    assert out["completed_2026_outcomes_used"] == 0
    assert len(out["observation_sha256"]) == 64


def test_forecast_effect_fields_are_rejected() -> None:
    for field in ("pick", "sentiment_score", "edge", "win_probability_delta", "recommendation"):
        row = _row()
        row[field] = "nonempty"
        with pytest.raises(ValueError, match="forecast-effect fields are prohibited"):
            validate_structured_observation(row)


def test_observation_not_known_by_forecast_asof_fails_closed() -> None:
    row = _row()
    row["captured_at_utc"] = "2026-09-27T18:01:00Z"
    with pytest.raises(ValueError, match="captured_at_utc"):
        validate_structured_observation(row)


def test_publication_after_capture_fails_closed() -> None:
    row = _row()
    row["published_at_utc"] = "2026-09-27T16:03:00Z"
    with pytest.raises(ValueError, match="published_at_utc"):
        validate_structured_observation(row)


def test_post_kickoff_forecast_state_fails_closed() -> None:
    row = _row()
    row["forecast_asof_utc"] = row["kickoff_timestamp_utc"]
    with pytest.raises(ValueError, match="forecast_asof_utc"):
        validate_structured_observation(row)


def test_unknown_observation_type_is_rejected() -> None:
    row = _row()
    row["observation_type"] = "analyst_likes_matchup"
    with pytest.raises(ValueError, match="unsupported observation_type"):
        validate_structured_observation(row)


def test_invalid_confidence_or_hash_is_rejected() -> None:
    row = _row()
    row["confidence"] = 1.01
    with pytest.raises(ValueError, match="confidence"):
        validate_structured_observation(row)

    row = _row()
    row["raw_evidence_sha256"] = "bad"
    with pytest.raises(ValueError, match="raw_evidence_sha256"):
        validate_structured_observation(row)


def test_duplicate_observation_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate observation_id"):
        validate_structured_observations([_row(), _row()])


def test_audit_preserves_extraction_forecasting_separation() -> None:
    rows, audit = validate_structured_observations([_row()])
    assert len(rows) == 1
    assert audit["outcome_blind"] is True
    assert audit["production_authorized"] is False
    assert audit["probability_effect_authorized"] is False
    assert audit["llm_directional_judgment_authorized"] is False

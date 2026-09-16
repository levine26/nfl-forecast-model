from __future__ import annotations

import pytest

from research.expected_lineup_state_v1 import (
    validate_expected_lineup_observation,
    validate_expected_lineup_snapshot,
)
from research.qb_scenario_state_v1 import validate_qb_candidate, validate_qb_snapshot


RAW_SHA = "c" * 64


def _lineup_row(player_id: str = "00-0030001") -> dict:
    return {
        "observation_id": f"obs-{player_id}",
        "snapshot_id": "lineup-2026_03_ARI_SEA-ARI-T120",
        "game_id": "2026_03_ARI_SEA",
        "team": "ARI",
        "opponent": "SEA",
        "player_id": player_id,
        "player_name": "Example Player",
        "position": "RT",
        "unit": "OL",
        "membership_state": "confirmed_team_roster",
        "availability_state": "questionable",
        "expected_role_tier": "starter",
        "availability_probability": "",
        "availability_probability_method": "",
        "expected_role_share": "",
        "expected_role_share_method": "",
        "source": "Official/credentialed source",
        "source_url_or_id": "https://example.com/source/1",
        "raw_evidence_ref": "archive://source/1",
        "raw_evidence_sha256": RAW_SHA,
        "published_at_utc": "2026-09-27T16:00:00Z",
        "captured_at_utc": "2026-09-27T16:02:00Z",
        "forecast_asof_utc": "2026-09-27T18:05:00Z",
        "kickoff_timestamp_utc": "2026-09-27T20:05:00Z",
        "extractor_or_parser_id": "lineup-fact-extractor",
        "extractor_or_parser_version": "v1",
        "identity_method": "gsis_exact",
    }


def _qb_row(player_id: str, candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "snapshot_id": "qb-2026_03_ARI_SEA-ARI-T120",
        "game_id": "2026_03_ARI_SEA",
        "team": "ARI",
        "opponent": "SEA",
        "player_id": player_id,
        "player_name": "Example QB",
        "starter_state": "possible_starter",
        "continuity_state": "same_starter_same_system",
        "pregame_depth_order": 1,
        "starter_probability": "",
        "starter_probability_method": "",
        "source": "Credentialed beat report",
        "source_url_or_id": "https://example.com/qb/1",
        "raw_evidence_ref": "archive://qb/1",
        "raw_evidence_sha256": RAW_SHA,
        "published_at_utc": "2026-09-27T15:00:00Z",
        "captured_at_utc": "2026-09-27T15:02:00Z",
        "forecast_asof_utc": "2026-09-27T18:05:00Z",
        "kickoff_timestamp_utc": "2026-09-27T20:05:00Z",
        "extractor_or_parser_id": "qb-fact-extractor",
        "extractor_or_parser_version": "v1",
    }


def test_lineup_categorical_state_can_be_captured_without_invented_probability() -> None:
    out = validate_expected_lineup_observation(_lineup_row())
    assert out["availability_state"] == "questionable"
    assert out["availability_probability"] is None
    assert out["expected_role_share"] is None
    assert out["probability_feature_authorized"] is False
    assert out["forecast_mutation_authorized"] is False


def test_lineup_rejects_forecast_effect_fields() -> None:
    row = _lineup_row()
    row["win_probability_delta"] = -0.04
    with pytest.raises(ValueError, match="forecast-effect fields are prohibited"):
        validate_expected_lineup_observation(row)


def test_lineup_rejects_hindsight_chronology() -> None:
    row = _lineup_row()
    row["captured_at_utc"] = "2026-09-27T18:06:00Z"
    with pytest.raises(ValueError, match="captured_at_utc"):
        validate_expected_lineup_observation(row)

    row = _lineup_row()
    row["forecast_asof_utc"] = row["kickoff_timestamp_utc"]
    with pytest.raises(ValueError, match="forecast_asof_utc"):
        validate_expected_lineup_observation(row)


def test_absence_or_unknown_cannot_be_silently_promoted_to_healthy_probability() -> None:
    row = _lineup_row()
    row["availability_state"] = "not_listed_on_qualified_report"
    row["availability_probability"] = 1.0
    row["availability_probability_method"] = "deterministic_official_confirmation"
    with pytest.raises(ValueError, match="unknown/not-listed"):
        validate_expected_lineup_observation(row)

    row = _lineup_row()
    row["membership_state"] = "unknown"
    row["expected_role_share"] = 1.0
    row["expected_role_share_method"] = "deterministic_role_rule"
    with pytest.raises(ValueError, match="unknown membership"):
        validate_expected_lineup_observation(row)


def test_continuous_lineup_inputs_require_frozen_or_source_method() -> None:
    row = _lineup_row()
    row["availability_probability"] = 0.7
    row["availability_probability_method"] = "llm_judgment"
    with pytest.raises(ValueError, match="allowed frozen/source method"):
        validate_expected_lineup_observation(row)

    row = _lineup_row()
    row["expected_role_share"] = 0.9
    row["expected_role_share_method"] = "analyst_judgment"
    with pytest.raises(ValueError, match="allowed frozen/source method"):
        validate_expected_lineup_observation(row)


def test_official_confirmations_can_only_encode_deterministic_extremes() -> None:
    row = _lineup_row()
    row["availability_state"] = "out"
    row["availability_probability"] = 0.2
    row["availability_probability_method"] = "deterministic_official_confirmation"
    with pytest.raises(ValueError, match="probability 0"):
        validate_expected_lineup_observation(row)

    row = _lineup_row()
    row["availability_state"] = "available_confirmed"
    row["availability_probability"] = 1.0
    row["availability_probability_method"] = "deterministic_official_confirmation"
    out = validate_expected_lineup_observation(row)
    assert out["availability_probability"] == 1.0


def test_lineup_snapshot_requires_single_point_in_time_and_unique_players() -> None:
    a = _lineup_row("00-0030001")
    b = _lineup_row("00-0030002")
    b["observation_id"] = "obs-2"
    rows, audit = validate_expected_lineup_snapshot([a, b])
    assert len(rows) == 2
    assert audit["complete_expected_lineup_feature_authorized"] is False

    duplicate = _lineup_row("00-0030001")
    duplicate["observation_id"] = "different-observation"
    with pytest.raises(ValueError, match="duplicate player_id"):
        validate_expected_lineup_snapshot([a, duplicate])


def test_qb_categorical_state_requires_no_invented_starter_probability() -> None:
    out = validate_qb_candidate(_qb_row("00-0035001", "qb1"))
    assert out["starter_probability"] is None
    assert out["scenario_mixture_authorized"] is False
    assert out["conditional_win_probability_authorized"] is False


def test_qb_rejects_editorial_probability_and_conditional_win_fields() -> None:
    row = _qb_row("00-0035001", "qb1")
    row["starter_probability"] = 0.6
    row["starter_probability_method"] = "analyst_judgment"
    with pytest.raises(ValueError, match="allowed frozen/source method"):
        validate_qb_candidate(row)

    row = _qb_row("00-0035001", "qb1")
    row["conditional_win_probability"] = 0.55
    with pytest.raises(ValueError, match="prohibited"):
        validate_qb_candidate(row)


def test_qb_partial_probability_distribution_is_rejected() -> None:
    a = _qb_row("00-0035001", "qb1")
    a["starter_probability"] = 0.7
    a["starter_probability_method"] = "frozen_pregame_estimator"
    b = _qb_row("00-0035002", "qb2")
    b["pregame_depth_order"] = 2
    with pytest.raises(ValueError, match="partial QB starter-probability distribution"):
        validate_qb_snapshot([a, b])


def test_qb_complete_distribution_must_sum_to_one_and_still_has_no_scenario_authority() -> None:
    a = _qb_row("00-0035001", "qb1")
    a["starter_probability"] = 0.7
    a["starter_probability_method"] = "frozen_pregame_estimator"
    b = _qb_row("00-0035002", "qb2")
    b["pregame_depth_order"] = 2
    b["starter_probability"] = 0.3
    b["starter_probability_method"] = "frozen_pregame_estimator"
    rows, audit = validate_qb_snapshot([a, b])
    assert len(rows) == 2
    assert audit["probability_complete"] is True
    assert audit["probability_sum"] == pytest.approx(1.0)
    assert audit["scenario_mixture_authorized"] is False
    assert audit["conditional_win_probability_authorized"] is False

    b["starter_probability"] = 0.2
    with pytest.raises(ValueError, match="must sum to 1"):
        validate_qb_snapshot([a, b])


def test_deterministic_confirmed_qb_must_be_one() -> None:
    row = _qb_row("00-0035001", "qb1")
    row["starter_state"] = "confirmed_starter"
    row["starter_probability"] = 0.9
    row["starter_probability_method"] = "deterministic_official_confirmation"
    with pytest.raises(ValueError, match="probability 1"):
        validate_qb_candidate(row)


def test_qb_chronology_and_raw_hash_fail_closed() -> None:
    row = _qb_row("00-0035001", "qb1")
    row["published_at_utc"] = "2026-09-27T15:03:00Z"
    with pytest.raises(ValueError, match="published_at_utc"):
        validate_qb_candidate(row)

    row = _qb_row("00-0035001", "qb1")
    row["raw_evidence_sha256"] = "bad"
    with pytest.raises(ValueError, match="raw_evidence_sha256"):
        validate_qb_candidate(row)

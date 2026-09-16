from __future__ import annotations

import pytest

from research.inactive_information_event_v1 import (
    derive_inactive_event_row,
    derive_inactive_events,
)


RAW_SHA = "a" * 64


def _row() -> dict:
    return {
        "game_id": "2026_03_ARI_SEA",
        "event_id": "inactive-2026_03_ARI_SEA-v1",
        "home_team": "SEA",
        "away_team": "ARI",
        "kickoff_timestamp_utc": "2026-09-27T20:05:00Z",
        "inactive_event_at_utc": "2026-09-27T18:35:00Z",
        "inactive_timestamp_basis": "published_at",
        "inactive_source": "NFL official inactive article",
        "inactive_source_url_or_id": "https://www.nfl.com/news/example",
        "inactive_raw_sha256": RAW_SHA,
        "pre_lineup_asof_utc": "2026-09-27T18:30:00Z",
        "post_lineup_asof_utc": "2026-09-27T18:40:00Z",
        "pre_market_asof_utc": "2026-09-27T18:30:00Z",
        "post_market_asof_utc": "2026-09-27T18:45:00Z",
        "home_expected_lineup_value_pre": 12.0,
        "home_expected_lineup_value_post": 10.5,
        "away_expected_lineup_value_pre": 11.0,
        "away_expected_lineup_value_post": 10.8,
        "market_home_prob_pre": 0.58,
        "market_home_prob_post": 0.55,
    }


def test_valid_event_keeps_football_and_market_changes_separate() -> None:
    out = derive_inactive_event_row(_row())
    assert out["complete_event_measurement"] is True
    assert out["home_lineup_value_change"] == pytest.approx(-1.5)
    assert out["away_lineup_value_change"] == pytest.approx(-0.2)
    assert out["net_home_lineup_shock_native_units"] == pytest.approx(-1.3)
    assert out["market_home_probability_move_pp"] == pytest.approx(-3.0)
    assert out["football_to_probability_mapping_authorized"] is False
    assert "football_implied_probability_delta" not in out
    assert "residual_edge" not in out
    assert "outcome" not in out


def test_missing_measurement_remains_missing_without_imputation() -> None:
    row = _row()
    row["away_expected_lineup_value_post"] = ""
    out = derive_inactive_event_row(row)
    assert out["lineup_state_complete"] is False
    assert out["market_state_complete"] is True
    assert out["complete_event_measurement"] is False
    assert out["net_home_lineup_shock_native_units"] is None
    assert out["market_home_probability_move_pp"] == pytest.approx(-3.0)


def test_pre_state_after_event_fails_closed() -> None:
    row = _row()
    row["pre_market_asof_utc"] = "2026-09-27T18:36:00Z"
    with pytest.raises(ValueError, match="pre-market state"):
        derive_inactive_event_row(row)


def test_post_state_at_or_after_kickoff_fails_closed() -> None:
    row = _row()
    row["post_lineup_asof_utc"] = row["kickoff_timestamp_utc"]
    with pytest.raises(ValueError, match="post-lineup state"):
        derive_inactive_event_row(row)


def test_invalid_source_hash_or_timestamp_basis_fails_closed() -> None:
    row = _row()
    row["inactive_raw_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="inactive_raw_sha256"):
        derive_inactive_event_row(row)

    row = _row()
    row["inactive_timestamp_basis"] = "inferred"
    with pytest.raises(ValueError, match="inactive_timestamp_basis"):
        derive_inactive_event_row(row)


def test_duplicate_game_event_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate inactive event identity"):
        derive_inactive_events([_row(), _row()])


def test_audit_is_outcome_blind_and_nonproduction() -> None:
    rows, audit = derive_inactive_events([_row()])
    assert len(rows) == 1
    assert audit["complete_event_measurements"] == 1
    assert audit["outcome_blind"] is True
    assert audit["production_authorized"] is False
    assert audit["probability_feature_authorized"] is False
    assert audit["completed_2026_outcomes_used"] == 0
    assert audit["measurement_contract"]["football_to_probability_mapping"] == "not_authorized"

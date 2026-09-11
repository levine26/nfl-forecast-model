from __future__ import annotations

import pytest

from nfl_forecast.player_impact_monitor import build_impact_monitor_payload, public_safe_card


def _card() -> dict:
    return {
        "schema_version": 1,
        "research_only": True,
        "game_id": "2026_01_AWAY_HOME",
        "team": "HOME",
        "player_id": "stable-123",
        "player_name": "Example Receiver",
        "position": "WR",
        "observed_statistics": [
            {
                "kind": "source_observed",
                "metric": "target_share",
                "value": 0.24,
                "unit": "share",
                "source_name": "approved source",
                "source_url": "https://example.com/approved",
                "source_data_as_of": "2026-09-10T12:00:00Z",
                "sample_size": 50,
                "redistribution_review_status": "approved",
            },
            {
                "kind": "source_observed",
                "metric": "route_share",
                "value": 0.82,
                "unit": "share",
                "source_name": "restricted source",
                "source_url": "https://example.com/restricted",
                "source_data_as_of": "2026-09-10T12:00:00Z",
                "sample_size": 50,
                "redistribution_review_status": "restricted",
            },
        ],
        "levline_impacts": [
            {
                "kind": "levline_modeled_impact",
                "metric": "levline_player_impact",
                "estimate": 0.17,
                "uncertainty": 0.08,
                "model_version": "impact-test-v1",
                "feature_data_horizon": "pregame research state",
                "interpretation": "LevLine explanatory impact scale; not an official league statistic.",
            }
        ],
        "availability": {
            "practice_status": "Limited Participation",
            "game_status": "Questionable",
            "source_status": "prospective_unqualified",
            "source_name": "official current injury report",
            "source_url": "https://example.com/injury",
            "source_data_as_of": "2026-09-10T18:00:00Z",
        },
        "data_quality": {
            "identity_confidence": "stable_id",
            "coverage_status": "partial",
            "missing_fields": [],
        },
    }


def test_monitor_emits_only_redistribution_approved_observed_stats() -> None:
    safe = public_safe_card(_card())
    assert len(safe["observed_statistics"]) == 1
    assert safe["observed_statistics"][0]["metric"] == "target_share"
    assert safe["suppressed_observed_statistics"] == 1
    assert safe["probability_feature_authorized"] is False
    assert safe["levline_impacts"][0]["research_only"] is True
    assert safe["levline_impacts"][0]["probability_feature_authorized"] is False


def test_unqualified_availability_is_context_only_not_probability_input() -> None:
    safe = public_safe_card(_card())
    assert safe["availability"]["source_status"] == "prospective_unqualified"
    assert safe["availability"]["probability_feature_authorized"] is False


def test_payload_is_deterministic_explainability_only() -> None:
    first = _card()
    second = _card()
    second["player_id"] = "stable-456"
    second["player_name"] = "Another Receiver"
    payload = build_impact_monitor_payload([second, first], generated_utc="FIXED")
    assert payload["mode"] == "research_explainability_only"
    assert payload["probability_feature_authorized"] is False
    assert payload["fantasy_style_projections"] is False
    assert payload["games"][0]["players"][0]["player_name"] == "Another Receiver"
    assert payload["games"][0]["approved_observed_statistics"] == 2
    assert payload["games"][0]["suppressed_observed_statistics"] == 2


def test_retroactive_outcome_or_snap_fields_fail_closed_even_when_nested() -> None:
    card = _card()
    card["data_quality"]["actual_snap_share"] = 0.83
    with pytest.raises(ValueError, match="retrospective/outcome"):
        public_safe_card(card)

    card = _card()
    card["availability"]["actual_home_score"] = 27
    with pytest.raises(ValueError, match="retrospective/outcome"):
        public_safe_card(card)


def test_invalid_availability_source_state_fails_closed() -> None:
    card = _card()
    card["availability"]["source_status"] = "assumed_active"
    with pytest.raises(ValueError, match="Invalid availability"):
        public_safe_card(card)

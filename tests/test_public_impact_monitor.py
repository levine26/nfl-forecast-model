from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_public_impact_monitor import run


def _card() -> dict:
    return {
        "schema_version": 1,
        "research_only": True,
        "game_id": "2026_01_DEN_KC",
        "team": "KC",
        "player_id": "00-0030000",
        "player_name": "Example Player",
        "position": "WR",
        "observed_statistics": [
            {
                "kind": "source_observed",
                "metric": "target_share",
                "value": 0.24,
                "unit": "share",
                "source_name": "approved source",
                "source_url": "https://example.com/approved",
                "source_data_as_of": "2026-09-10T20:00:00Z",
                "sample_size": 10,
                "redistribution_review_status": "approved",
            },
            {
                "kind": "source_observed",
                "metric": "route_share",
                "value": 0.81,
                "unit": "share",
                "source_name": "pending source",
                "source_url": "https://example.com/pending",
                "source_data_as_of": "2026-09-10T20:00:00Z",
                "sample_size": 10,
                "redistribution_review_status": "pending",
            },
        ],
        "levline_impacts": [
            {
                "kind": "levline_modeled_impact",
                "metric": "levline_player_impact",
                "estimate": 0.4,
                "uncertainty": 0.7,
                "model_version": "research-test",
                "feature_data_horizon": "pregame",
                "interpretation": "Research-only modeled impact.",
            }
        ],
        "availability": {
            "practice_status": "limited",
            "game_status": "questionable",
            "source_status": "qualified",
            "source_name": "approved source",
            "source_url": "https://example.com/approved",
            "source_data_as_of": "2026-09-10T20:00:00Z",
        },
        "data_quality": {
            "identity_confidence": "stable_id",
            "coverage_status": "test_fixture",
            "missing_fields": [],
        },
    }


def test_missing_staging_fails_closed_to_empty_payload(tmp_path: Path) -> None:
    destination = tmp_path / "impact_monitor.json"
    payload = run(
        staging_json=str(tmp_path / "missing.json"),
        output=str(destination),
        generated_utc="TEST",
    )
    assert payload["games"] == []
    assert payload["source_governance_review_status"] == "no_staging_input"
    assert payload["probability_feature_authorized"] is False
    assert json.loads(destination.read_text())["games"] == []


def test_nonempty_staging_requires_explicit_governance_approval(tmp_path: Path) -> None:
    staging = tmp_path / "staging.json"
    staging.write_text(json.dumps({"cards": [_card()]}), encoding="utf-8")
    with pytest.raises(ValueError, match="approved_for_publication"):
        run(staging_json=str(staging), output=str(tmp_path / "out.json"), generated_utc="TEST")


def test_approved_staging_is_sanitized_and_never_authorizes_probability_feature(tmp_path: Path) -> None:
    staging = tmp_path / "staging.json"
    staging.write_text(
        json.dumps(
            {
                "source_governance_review_status": "approved_for_publication",
                "probability_feature_authorized": False,
                "cards": [_card()],
            }
        ),
        encoding="utf-8",
    )
    payload = run(staging_json=str(staging), output=str(tmp_path / "out.json"), generated_utc="TEST")
    assert payload["source_governance_review_status"] == "approved_for_publication"
    assert payload["probability_feature_authorized"] is False
    assert payload["public_game_count"] == 1
    player = payload["games"][0]["players"][0]
    assert [row["metric"] for row in player["observed_statistics"]] == ["target_share"]
    assert player["suppressed_observed_statistics"] == 1
    assert player["probability_feature_authorized"] is False
    assert all(row["probability_feature_authorized"] is False for row in player["levline_impacts"])

from __future__ import annotations

from research.source_qualification_effective_v2 import effective_source


def test_sleeper_archive_effective_qualification_is_verified_2026_research() -> None:
    row = effective_source("sleeper_historical_player_archive_candidate")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert row["technical_status"] == "VERIFIED"
    assert row["historical_research"] is True
    assert row["prospective_use"] is True
    assert row["supports_2025_reconstruction"] is False
    assert row["supports_completed_2026_outcome_model_selection"] is False
    assert row["supports_production_dependency"] is False
    assert row["public_display"] is False
    assert "2026-02-01+" in row["historical_coverage"]
    assert "shadow research" in row["probability_features"]


def test_unoverridden_source_preserves_registry_classification() -> None:
    row = effective_source("nflverse_ftn_charting")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert row["historical_research"] is True

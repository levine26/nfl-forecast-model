from __future__ import annotations

from research.source_qualification_effective_v2 import effective_policy, effective_source


def test_effective_policy_qualifies_on_data_integrity_not_rights() -> None:
    policy = effective_policy()
    assert policy["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert policy["rights_and_licensing"]["qualification_blocker"] is False
    assert policy["rights_and_licensing"]["technical_validity_input"] is False
    assert policy["rights_and_licensing"]["retain_as_metadata"] is True
    assert policy["fail_closed_on_rights_failure"] is False
    assert policy["fail_closed_on_point_in_time_failure"] is True
    assert policy["fail_closed_on_data_integrity_failure"] is True
    assert "point_in_time_integrity" in policy["technical_blocker_categories"]
    assert "identity_integrity" in policy["technical_blocker_categories"]
    assert policy["completed_2026_outcome_model_selection_allowed"] is False


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
    assert row["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert row["rights_qualification_blocker"] is False
    assert row["rights_metadata_retained"] is True
    assert row["license_usage_rights"]
    assert row["redistribution_rights"]
    assert row["qualification_record"].endswith("sleeper_archive_qualification_v1.json")
    assert "2026-02-01+" in row["historical_coverage"]
    assert "shadow research" in row["probability_features"]
    assert all("license" not in failure.lower() for failure in row["technical_known_source_failures"])
    assert all("rights" not in failure.lower() for failure in row["technical_known_source_failures"])
    assert any("2025" in limitation for limitation in row["technical_limitations"])


def test_2025_availability_composite_is_verified_research_only() -> None:
    row = effective_source("availability_2025_composite_reconstruction")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert row["technical_status"] == "VERIFIED"
    assert row["historical_coverage"] == "2025 NFL Weeks 1-22"
    assert row["historical_research"] is True
    assert row["prospective_use"] is False
    assert row["supports_2025_reconstruction"] is True
    assert row["supports_2022_2025_unified_backtest"] is False
    assert row["supports_completed_2026_outcome_model_selection"] is False
    assert row["supports_production_dependency"] is False
    assert row["historical_game_status_feature_authorized"] is False
    assert row["probability_features"] is False
    assert row["public_display"] is False
    assert row["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert row["rights_qualification_blocker"] is False
    assert row["rights_metadata_retained"] is True
    assert row["qualification_record"].endswith("2025_reconstruction_qualification_v1.json")
    assert any("four player-week" in failure.lower() for failure in row["technical_known_source_failures"])
    assert any("2022-2025" in limitation for limitation in row["technical_limitations"])


def test_2025_composite_does_not_rewrite_sleeper_scope() -> None:
    sleeper = effective_source("sleeper_historical_player_archive_candidate")
    availability = effective_source("availability_2025_composite_reconstruction")
    assert sleeper["supports_2025_reconstruction"] is False
    assert "no 2025 reconstruction" in sleeper["historical_coverage"]
    assert availability["supports_2025_reconstruction"] is True
    assert sleeper["source_id"] != availability["source_id"]


def test_rights_metadata_never_enters_the_technical_failure_axis() -> None:
    row = effective_source("sleeper_live_players")
    assert row["classification"] == "CONTEXT_ONLY"
    assert row["rights_qualification_blocker"] is False
    assert row["rights_metadata_retained"] is True
    assert row["license_usage_rights"]
    assert row["redistribution_rights"]
    assert row["rights_governance_notes"] == []
    assert all("rights" not in failure.lower() for failure in row["technical_known_source_failures"])
    assert all("license" not in failure.lower() for failure in row["technical_known_source_failures"])
    assert any(
        "cannot reconstruct past state" in failure.lower()
        for failure in row["technical_known_source_failures"]
    )


def test_registry_classification_is_preserved_when_no_scope_supplement_is_needed() -> None:
    row = effective_source("nflverse_ftn_charting")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert row["historical_research"] is True
    assert row["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert row["rights_qualification_blocker"] is False

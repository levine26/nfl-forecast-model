from __future__ import annotations

import json
from pathlib import Path

from research.source_qualification_effective_v2 import effective_policy, effective_source


REGISTRY = Path("research/source_qualification_registry_v2.json")
SLEEPER_QUALIFICATION = Path("research/sleeper_archive_qualification_v1.json")
AVAILABILITY_2025_QUALIFICATION = Path("research/availability/2025_reconstruction_qualification_v1.json")
V09B_RESOLUTION = Path("research/availability/V09B_source_blocker_resolution_v1.json")
VALID = {
    "QUALIFIED_RESEARCH",
    "PROSPECTIVE_ONLY",
    "CONTEXT_ONLY",
    "IDENTITY_ONLY",
    "BLOCKED",
    "REJECTED",
}
REQUIRED_FIELDS = {
    "source_id",
    "provider",
    "classification",
    "cost",
    "license_usage_rights",
    "redistribution_rights",
    "rights_qualification_blocker",
    "historical_coverage",
    "current_2026_support",
    "refresh_cadence",
    "stable_ids",
    "timestamp_semantics",
    "publication_lag",
    "revision_history",
    "missingness",
    "known_source_failures",
    "historical_research",
    "prospective_use",
    "public_display",
    "probability_features",
}
RIGHTS_ONLY_MARKERS = (
    "license",
    "licensing",
    "rights",
    "redistribution",
    "commercial use",
    "terms of use",
)


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _sources() -> list[dict]:
    return _registry()["sources"]


def _sleeper_qualification() -> dict:
    return json.loads(SLEEPER_QUALIFICATION.read_text(encoding="utf-8"))


def _availability_qualification() -> dict:
    return json.loads(AVAILABILITY_2025_QUALIFICATION.read_text(encoding="utf-8"))


def test_registry_is_zero_cost_and_fails_closed_only_on_data_integrity() -> None:
    registry = _registry()
    raw = registry["policy"]
    policy = effective_policy()
    assert raw["cost_ceiling_usd"] == 0
    assert raw["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert raw["rights_qualification_blocker"] is False
    assert raw["rights_metadata_only"] is True
    assert raw["source_availability_does_not_authorize_features"] is True
    assert raw["completed_2026_outcomes_for_selection"] is False
    assert raw["fail_closed_on_data_integrity_failure"] is True
    assert raw["fail_closed_on_point_in_time_failure"] is True
    assert raw["fail_closed_on_rights_failure"] is False
    assert "fail_closed_on_rights_or_point_in_time_failure" not in raw

    assert policy["qualification_basis"] == "DATA_INTEGRITY_ONLY"
    assert policy["fail_closed_on_rights_failure"] is False
    assert policy["fail_closed_on_point_in_time_failure"] is True
    assert policy["rights_and_licensing"]["qualification_blocker"] is False


def test_every_registry_source_has_complete_qualification_record_and_unique_id() -> None:
    sources = _sources()
    ids = [row["source_id"] for row in sources]
    assert len(ids) == len(set(ids))
    for row in sources:
        assert REQUIRED_FIELDS.issubset(row)
        assert row["classification"] in VALID
        assert str(row["cost"]).startswith("$0")
        assert row["rights_qualification_blocker"] is False


def test_rights_metadata_can_never_be_a_technical_failure_or_sole_block_reason() -> None:
    for row in _sources():
        technical_failures = [str(item) for item in row["known_source_failures"]]
        for failure in technical_failures:
            lowered = failure.lower()
            assert not any(marker in lowered for marker in RIGHTS_ONLY_MARKERS), (
                row["source_id"],
                failure,
            )

        if row["classification"] in {"BLOCKED", "REJECTED"}:
            assert technical_failures, row["source_id"]
            assert row["rights_qualification_blocker"] is False


def test_verified_sleeper_archive_is_qualified_for_2026_research_only() -> None:
    qualification = _sleeper_qualification()
    raw = next(r for r in _sources() if r["source_id"] == "sleeper_historical_player_archive_candidate")
    effective = effective_source("sleeper_historical_player_archive_candidate")

    assert qualification["source_id"] == "sleeper_historical_player_archive_candidate"
    assert qualification["technical_status"] == "VERIFIED"
    assert qualification["research_classification"] == "QUALIFIED_RESEARCH_2026_ONLY"
    assert qualification["treat_source_as_valid_unless_data_audit_fails"] is True
    scope = qualification["effective_scope"]
    assert scope["supports_2025_reconstruction"] is False
    assert scope["supports_2026_point_in_time_research"] is True
    assert scope["supports_prospective_shadow_capture"] is True
    assert scope["supports_completed_2026_outcome_model_selection"] is False
    assert scope["supports_public_raw_redistribution"] is False
    assert scope["supports_production_dependency"] is False
    provenance = qualification["verified_provenance"]
    assert provenance["snapshot_path"] == "data/sleeper_players.json"
    assert provenance["workflow_schedule"] == "0 8 * * *"
    assert provenance["earliest_verified_snapshot_commit_utc"].startswith("2026-02-01")
    assert any(">=99.5%" in gate for gate in qualification["data_quality_gates"])

    assert raw["classification"] == "QUALIFIED_RESEARCH"
    assert raw["historical_research"] is True
    assert raw["prospective_use"] is True
    assert raw["rights_qualification_blocker"] is False
    assert all("license" not in failure.lower() for failure in raw["known_source_failures"])
    assert all("rights" not in failure.lower() for failure in raw["known_source_failures"])

    assert effective["classification"] == "QUALIFIED_RESEARCH"
    assert effective["rights_qualification_blocker"] is False
    assert effective["supports_2025_reconstruction"] is False


def test_verified_2025_availability_receipt_is_narrow_and_fail_closed() -> None:
    qualification = _availability_qualification()
    assert qualification["source_id"] == "availability_2025_composite_reconstruction"
    assert qualification["technical_status"] == "VERIFIED"
    assert qualification["research_classification"] == "QUALIFIED_RESEARCH_2025_ONLY"
    assert qualification["research_source_qualified"] is True
    assert qualification["supports_2025_reconstruction"] is True
    assert qualification["supports_2022_2025_unified_backtest"] is False
    assert qualification["probability_feature_authorized"] is False
    assert qualification["production_dependency_authorized"] is False
    assert qualification["historical_game_status_feature_authorized"] is False
    assert qualification["completed_2026_outcome_model_selection_allowed"] is False
    metrics = qualification["qualification_metrics"]
    assert metrics["nflverse_rows"] == 6068
    assert metrics["external_crosscheck_rows"] == 6068
    assert metrics["identity_match_rows"] == 6064
    assert metrics["identity_match_rate"] >= 0.995
    assert metrics["practice_status_agreement_rate"] == 1.0
    assert metrics["known_by_t120_rate_among_matched_rows"] == 1.0
    assert metrics["unresolved_practice_state_rows"] == 4
    assert metrics["actual_snaps_used"] == 0
    assert metrics["postgame_participation_used"] == 0
    assert metrics["completed_2026_outcomes_used"] == 0
    evidence = qualification["exact_head_evidence"]
    assert evidence["pull_request"] == 142
    assert evidence["validated_head_sha"] == "75a4a901a6273b1312e89129d24cda1988727101"
    assert evidence["artifact_zip_sha256"] == "8f5a0c5a98602de857d9823133797a52e3f92a8fd8a387ffbd41fd00995dcf44"


def test_v09b_blocker_resolution_does_not_rewrite_or_authorize_experiment() -> None:
    record = json.loads(V09B_RESOLUTION.read_text(encoding="utf-8"))
    assert record["experiment_id"] == "V09B-AVAILABILITY-001"
    assert record["original_disposition_preserved"] is True
    assert record["original_status"] == "rejected"
    assert record["original_result_type"] == "source_qualification_blocker"
    assert record["experiment_retroactively_run"] is False
    assert record["historical_result_rewritten"] is False
    assert record["current_authorization"]["source_research_qualified"] is True
    assert record["current_authorization"]["v09b_execution_authorized"] is False
    assert record["current_authorization"]["probability_feature_authorized"] is False
    assert record["current_authorization"]["production_dependency_authorized"] is False


def test_sleeper_live_context_limit_is_point_in_time_not_rights() -> None:
    row = effective_source("sleeper_live_players")
    assert row["classification"] == "CONTEXT_ONLY"
    assert row["rights_qualification_blocker"] is False
    assert row["license_usage_rights"]
    assert row["public_display"] is False
    assert any(
        "cannot reconstruct past state" in failure.lower()
        for failure in row["technical_known_source_failures"]
    )


def test_depth_chart_state_cannot_become_injury_state() -> None:
    row = effective_source("nflverse_depth_charts_2025_plus")
    assert "never direct injury substitution" in row["probability_features"]
    assert any("not injury status" in item.lower() for item in row["technical_known_source_failures"])


def test_market_history_cannot_sneak_in_through_paid_endpoint() -> None:
    row = effective_source("the_odds_api_free_tier")
    assert row["classification"] == "PROSPECTIVE_ONLY"
    assert "paid historical" in row["historical_coverage"].lower()
    assert row["historical_research"] is False


def test_exchange_family_stays_separate_from_sportsbook_consensus() -> None:
    row = effective_source("polymarket_public_market_data")
    assert "never blend" in row["probability_features"].lower()


def test_weather_reconstruction_encodes_publication_lag() -> None:
    row = effective_source("open_meteo_archived_runs")
    assert row["classification"] == "QUALIFIED_RESEARCH"
    assert "initialisation time is not publication time" in row["technical_known_source_failures"]
    assert "4-6h" in row["publication_lag"]

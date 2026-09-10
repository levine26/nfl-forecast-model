from __future__ import annotations

from pathlib import Path

import pytest

from nfl_forecast.experiment_registry import (
    feature_manifest_hash,
    load_registry,
    reproducibility_metadata,
    validate_experiment,
)


def test_registry_records_completed_evidence_and_excludes_2026_selection():
    registry = load_registry(Path("research/experiments.json"))
    by_id = {row["experiment_id"]: row for row in registry}
    required = {
        "BASELINE-V08-UNCERTAINTY-001",
        "V09A-PLAYER-VALUE-001",
        "V09B-AVAILABILITY-001",
        "V09C-UNIT-STATE-001",
        "V09D-MATCHUP-INTERACTIONS-001",
        "V09D-EWMA-INTERACTIONS-002",
        "F-MR-01",
        "F-MI-01",
        "F-LS-01",
        "F-ST-01",
    }
    assert required.issubset(by_id)
    assert len(by_id) == len(registry)

    for row in registry:
        assert max(row["validation_seasons"]) <= 2025
        assert 2026 not in row["training_seasons"]
        assert 2026 not in row["validation_seasons"]
        assert any("2026 outcomes" in item for item in row["prohibited_inputs"])

        if row["status"] in {"planned", "running"}:
            assert row["historical_result"] is None
        if row["status"] in {"complete", "rejected", "historically_qualified", "shadowing"}:
            assert row["historical_result"] is not None

    assert by_id["V09A-PLAYER-VALUE-001"]["status"] == "rejected"
    assert by_id["V09B-AVAILABILITY-001"]["status"] == "rejected"
    assert by_id["V09C-UNIT-STATE-001"]["status"] == "rejected"
    assert by_id["V09D-EWMA-INTERACTIONS-002"]["status"] == "rejected"
    assert by_id["F-MR-01"]["status"] == "rejected"
    assert by_id["F-MI-01"]["status"] == "rejected"
    assert by_id["F-LS-01"]["status"] == "rejected"

    dependency_blocked = by_id["V09D-MATCHUP-INTERACTIONS-001"]
    assert dependency_blocked["status"] == "complete"
    assert dependency_blocked["historical_result"]["result_type"] == "dependency_blocked"
    assert dependency_blocked["historical_result"]["blocked_by"] == "V09C-UNIT-STATE-001"

    fst = by_id["F-ST-01"]
    assert fst["status"] == "complete"
    assert fst["primary_metric"] == "brier"
    assert fst["historical_result"]["historical_qualification"].startswith("promising_but_not_established")
    assert "frozen_prospective_research_shadow" in fst["prospective_shadow_status"]


def test_registry_validation_rejects_future_validation_and_missing_prohibitions():
    row = load_registry()[0].copy()
    row["validation_seasons"] = [2026]
    with pytest.raises(ValueError, match="2026 outcomes"):
        validate_experiment(row)

    row = load_registry()[0].copy()
    row["prohibited_inputs"] = []
    with pytest.raises(ValueError, match="prohibited_inputs"):
        validate_experiment(row)


def test_feature_hash_is_order_invariant_and_metadata_is_complete():
    assert feature_manifest_hash(["b", "a"]) == feature_manifest_hash(["a", "b"])
    metadata = reproducibility_metadata(
        candidate_version="test-v0",
        features=["a", "b"],
        data_seasons=[2022, 2023],
        max_pbp_season=2023,
        random_seed=26,
        games=10,
        player_observations=20,
        play_observations=100,
        exclusions={"ambiguous_ids": 2},
        missing_data_rates={"player_value": 0.1},
    )
    required = {
        "git_sha",
        "generated_utc",
        "candidate_version",
        "data_seasons",
        "maximum_pbp_season",
        "feature_set_hash",
        "random_seed",
        "games",
        "player_observations",
        "play_observations",
        "exclusions",
        "missing_data_rates",
        "package_versions",
    }
    assert required.issubset(metadata)
    assert metadata["random_seed"] == 26

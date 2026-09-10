from __future__ import annotations

import json
from pathlib import Path

import pytest

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID, FrozenStackFit
from nfl_forecast.fst_reconstruction import (
    REFIT_ABS_TOLERANCE,
    frozen_fit_from_identity,
    verify_fst_reconstruction_identity,
)


EXPECTED = {
    "candidate_id": FROZEN_CANDIDATE_ID,
    "training_data_sha256": "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0",
    "training_games": 1615,
    "training_first_season": 2020,
    "training_last_season": 2025,
    "intercept": -0.06954359363166639,
    "market_logit_coefficient": 1.1939087340527093,
    "pure_logit_coefficient": -0.19342747983803402,
    "reconstruction_abs_tolerance": 1e-12,
    "source": {
        "workflow_run_id": 34482487521,
        "head_sha": "5b26693e5d97ec49543b1d778baef63a1d600311",
        "artifact_name": "levline-challenger-34482487521",
        "artifact_path": "fst/runtime_model.json",
        "evidence_role": "surviving successful frozen-shadow identity evidence; not original pre-fit freeze provenance",
    },
}


def _fit(**overrides) -> FrozenStackFit:
    values = {
        "intercept": EXPECTED["intercept"],
        "market_logit_coefficient": EXPECTED["market_logit_coefficient"],
        "pure_logit_coefficient": EXPECTED["pure_logit_coefficient"],
        "training_games": EXPECTED["training_games"],
        "training_first_season": EXPECTED["training_first_season"],
        "training_last_season": EXPECTED["training_last_season"],
        "training_data_sha256": EXPECTED["training_data_sha256"],
    }
    values.update(overrides)
    return FrozenStackFit(**values)


def _input_manifest() -> dict:
    return {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "capture_context": "prospective_shadow_reconstruction",
    }


def test_registered_fst_identity_matches_and_writes_pre_scoring_check(tmp_path):
    check = verify_fst_reconstruction_identity(
        tmp_path, _input_manifest(), _fit(), EXPECTED
    )

    assert check["matches"] is True
    assert check["mismatched_fields"] == []
    assert check["check_stage"] == "post_refit_pre_scoring"
    assert check["capture_context"] == "prospective_shadow_reconstruction"
    assert check["expected_source"] == EXPECTED["source"]
    assert check["authoritative_scoring_source"] == "registered_frozen_identity_literals"
    assert check["refit_abs_tolerance"] == REFIT_ABS_TOLERANCE
    assert all(delta == 0.0 for delta in check["numerical_absolute_deltas"].values())
    persisted = json.loads((tmp_path / "frozen_identity_check.json").read_text())
    assert persisted == check


def test_registered_fst_tiny_numeric_reconstruction_delta_is_within_fixed_parity_bound(tmp_path):
    reconstructed = _fit(
        intercept=EXPECTED["intercept"] + 2e-16,
        market_logit_coefficient=EXPECTED["market_logit_coefficient"] - 3e-16,
        pure_logit_coefficient=EXPECTED["pure_logit_coefficient"] + 2e-16,
    )

    check = verify_fst_reconstruction_identity(
        tmp_path, _input_manifest(), reconstructed, EXPECTED
    )

    assert check["matches"] is True
    assert check["mismatched_fields"] == []
    assert max(check["numerical_absolute_deltas"].values()) < 1e-12


def test_registered_fst_identity_mismatch_is_persisted_before_fail_closed(tmp_path):
    drifted = _fit(
        training_data_sha256="3" * 64,
        market_logit_coefficient=EXPECTED["market_logit_coefficient"] + 1.1e-12,
    )

    with pytest.raises(RuntimeError, match="training_data_sha256, market_logit_coefficient"):
        verify_fst_reconstruction_identity(
            tmp_path, _input_manifest(), drifted, EXPECTED
        )

    check = json.loads((tmp_path / "frozen_identity_check.json").read_text())
    assert check["matches"] is False
    assert check["mismatched_fields"] == [
        "training_data_sha256",
        "market_logit_coefficient",
    ]
    assert check["field_matches"]["intercept"] is True
    assert check["field_matches"]["training_games"] is True
    assert check["actual_refit"]["training_data_sha256"] == "3" * 64
    assert check["expected"]["training_data_sha256"] == EXPECTED["training_data_sha256"]
    assert check["numerical_absolute_deltas"]["market_logit_coefficient"] > 1e-12


def test_registered_fst_identity_refuses_tolerance_relaxation(tmp_path):
    relaxed = dict(EXPECTED)
    relaxed["reconstruction_abs_tolerance"] = 1.0001e-12

    with pytest.raises(ValueError, match="<= 1e-12"):
        verify_fst_reconstruction_identity(
            tmp_path, _input_manifest(), _fit(), relaxed
        )


def test_frozen_fit_materializes_exact_registered_literals():
    fit = frozen_fit_from_identity(EXPECTED)
    assert fit.intercept == EXPECTED["intercept"]
    assert fit.market_logit_coefficient == EXPECTED["market_logit_coefficient"]
    assert fit.pure_logit_coefficient == EXPECTED["pure_logit_coefficient"]
    assert fit.training_data_sha256 == EXPECTED["training_data_sha256"]
    assert fit.training_games == EXPECTED["training_games"]


def test_fst01_spec_pins_registered_identity_without_claiming_original_freeze_provenance():
    spec = json.loads(Path("research/fst/F-ST-01-FROZEN-2026.json").read_text())
    identity = spec["frozen_identity"]

    for field, value in EXPECTED.items():
        assert identity[field] == value
    assert identity["source"]["workflow_run_id"] == 34482487521
    assert "not original pre-fit freeze provenance" in identity["source"]["evidence_role"]
    assert "1e-12" in spec["training_policy"]["post_freeze_refit_policy"]
    assert "registered constants" in spec["training_policy"]["post_freeze_refit_policy"]

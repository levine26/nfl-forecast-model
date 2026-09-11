from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID
import scripts.run_challenger_fst_shadow_portable as portable


def _spec() -> dict:
    return json.loads(Path("research/fst/F-ST-01-FROZEN-2026.json").read_text())


def _receipt(spec_path: Path, *, source_sha: str = "abc123") -> dict:
    spec = json.loads(spec_path.read_text())
    registered = spec["frozen_identity"]
    fit = {
        "intercept": registered["intercept"],
        "market_logit_coefficient": registered["market_logit_coefficient"],
        "pure_logit_coefficient": registered["pure_logit_coefficient"],
        "training_games": registered["training_games"],
        "training_first_season": registered["training_first_season"],
        "training_last_season": registered["training_last_season"],
        "training_data_sha256": registered["training_data_sha256"],
        "C": 1.0,
        "penalty": "l2",
        "solver": "lbfgs",
        "max_iter": 3000,
    }
    return {
        "schema_version": 1,
        "candidate_id": FROZEN_CANDIDATE_ID,
        "status": "verified",
        "source_sha": source_sha,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "runtime": {
            "matches": True,
            "environment": {"OPENBLAS_CORETYPE": "SKYLAKEX"},
            "threadpools": [{"internal_api": "openblas", "architecture": "SkylakeX", "num_threads": 4}],
        },
        "reconstruction_fit": fit,
        "identity_check": {
            "matches": True,
            "numeric_abs_tolerance": 1e-12,
        },
        "immutable_training_artifact": {
            "canonical_training_digest": registered["training_data_sha256"],
            "rows": registered["training_games"],
        },
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "execution_policy": "strict_reconstruction_only_no_current_week_scoring",
    }


def _install_receipt(tmp_path: Path, monkeypatch, *, mutate=None):
    spec_path = Path("research/fst/F-ST-01-FROZEN-2026.json")
    receipt = _receipt(spec_path)
    if mutate:
        mutate(receipt)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    monkeypatch.setattr(portable, "RECEIPT_PATH", receipt_path)
    monkeypatch.setattr(portable, "SPEC_PATH", spec_path)
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.delenv("OPENBLAS_CORETYPE", raising=False)
    return receipt_path


def test_portable_shadow_accepts_only_verified_bound_receipt(tmp_path, monkeypatch):
    _install_receipt(tmp_path, monkeypatch)
    receipt, fit = portable._load_verified_receipt()
    registered = _spec()["frozen_identity"]
    assert receipt["runtime"]["matches"] is True
    assert fit.training_data_sha256 == registered["training_data_sha256"]
    assert fit.training_games == registered["training_games"]
    assert fit.intercept == registered["intercept"]


def test_portable_shadow_refuses_forced_cpu_target(tmp_path, monkeypatch):
    _install_receipt(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENBLAS_CORETYPE", "SKYLAKEX")
    with pytest.raises(RuntimeError, match="must not inherit OPENBLAS_CORETYPE"):
        portable._load_verified_receipt()


def test_portable_shadow_refuses_tolerance_relaxation(tmp_path, monkeypatch):
    _install_receipt(
        tmp_path,
        monkeypatch,
        mutate=lambda receipt: receipt["identity_check"].update({"numeric_abs_tolerance": 1.0001e-12}),
    )
    with pytest.raises(RuntimeError, match="widened"):
        portable._load_verified_receipt()


def test_portable_shadow_refuses_cross_sha_receipt(tmp_path, monkeypatch):
    _install_receipt(tmp_path, monkeypatch)
    monkeypatch.setenv("GITHUB_SHA", "different")
    with pytest.raises(RuntimeError, match="different workflow source SHA"):
        portable._load_verified_receipt()


def test_probe_bound_fit_manifest_preserves_reconstruction_runtime(tmp_path, monkeypatch):
    receipt_path = _install_receipt(tmp_path, monkeypatch)
    receipt, fit = portable._load_verified_receipt()
    out = tmp_path / "provenance"
    out.mkdir()
    input_manifest = {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "capture_context": "prospective_shadow_reconstruction",
        "base_oof": {"raw_sha256": "a" * 64},
        "training_frame": {
            "raw_sha256": "b" * 64,
            "canonical_game_keyed_sha256": "c" * 64,
        },
    }
    (out / "inputs_manifest.json").write_text(json.dumps(input_manifest))
    write = portable._probe_bound_fit_provenance(receipt)
    manifest = write(out, input_manifest, fit)
    assert manifest["runtime"] == receipt["runtime"]
    assert manifest["reconstruction_execution_policy"] == "isolated_strict_probe"
    assert manifest["shadow_scoring_execution_policy"] == "native_cpu"
    assert manifest["reconstruction_probe_receipt_sha256"] == hashlib.sha256(receipt_path.read_bytes()).hexdigest()

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.verify_fst_reconstruction_evidence import (
    EVIDENCE_PATH,
    SPEC_PATH,
    build_receipt,
    verify_durable_evidence,
)


def _copy_json(source: Path, target: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def test_committed_durable_forensic_evidence_verifies_under_frozen_tolerance() -> None:
    verified = verify_durable_evidence()
    check = verified["identity_check"]
    assert check["matches"] is True
    assert check["numeric_abs_tolerance"] == 1e-12
    assert max(check["numeric_absolute_deltas"].values()) <= 1e-12
    assert check["forensic_result_exact_equality_flag"] is False
    assert verified["runtime"]["matches"] is True
    assert verified["runtime"]["environment"]["OPENBLAS_CORETYPE"] == "SKYLAKEX"
    assert verified["evidence"]["completed_2026_outcomes_used"] == 0
    assert verified["evidence"]["production_authorized"] is False


def test_durable_receipt_is_bound_to_current_spec_evidence_and_workflow_sha(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    receipt = build_receipt()
    assert receipt["status"] == "verified"
    assert receipt["receipt_scope"] == "durable_forensic_evidence_verification"
    assert receipt["source_sha"] == "a" * 40
    assert receipt["spec_sha256"] == hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()
    assert receipt["forensic_evidence_sha256"] == hashlib.sha256(EVIDENCE_PATH.read_bytes()).hexdigest()
    assert receipt["identity_check"]["matches"] is True
    assert receipt["completed_2026_outcomes_used"] == 0
    assert receipt["production_authorized"] is False


def test_registered_identity_drift_fails_closed(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec = _copy_json(SPEC_PATH, spec_path)
    spec["frozen_identity"]["market_logit_coefficient"] += 1e-6
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(RuntimeError, match="registered forensic identity market_logit_coefficient"):
        verify_durable_evidence(spec_path=spec_path)


def test_reconstruction_fit_drift_beyond_tolerance_fails_closed(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    evidence = _copy_json(EVIDENCE_PATH, evidence_path)
    evidence["reconstruction_fit"]["pure_logit_coefficient"] += 2e-12
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(RuntimeError, match="reconstruction delta"):
        verify_durable_evidence(evidence_path=evidence_path)


def test_registered_tolerance_cannot_be_widened(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec = _copy_json(SPEC_PATH, spec_path)
    spec["frozen_identity"]["reconstruction_abs_tolerance"] = 1.0001e-12
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not finite and <= 1e-12"):
        verify_durable_evidence(spec_path=spec_path)


def test_forensic_source_artifact_or_git_identity_drift_fails_closed(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    evidence = _copy_json(EVIDENCE_PATH, evidence_path)
    evidence["forensic_workflow"]["artifact_id"] += 1
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact identity drifted"):
        verify_durable_evidence(evidence_path=evidence_path)

    evidence = _copy_json(EVIDENCE_PATH, evidence_path)
    evidence["forensic_workflow"]["head_sha"] = "b" * 64
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(RuntimeError, match="40-character lowercase hex identity"):
        verify_durable_evidence(evidence_path=evidence_path)

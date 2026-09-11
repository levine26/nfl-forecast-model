from __future__ import annotations

"""Verify durable compatible-hardware F-ST-01 reconstruction evidence.

Routine shadow CI must not force a CPU instruction set that the hosted runner may not
support. Instead, it verifies the immutable forensic reconstruction captured on compatible
hardware, binds that evidence to the current frozen spec, and emits a current-run receipt.
A fresh refit remains available through ``run_fst_reconstruction_probe.py`` when compatible
hardware is explicitly available.
"""

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID
from nfl_forecast.fst_nested_pure import (
    FROZEN_TRAINING_DIGEST,
    FROZEN_TRAINING_FIRST_SEASON,
    FROZEN_TRAINING_LAST_SEASON,
    FROZEN_TRAINING_ROWS,
    RECOVERED_BASE_OOF_RAW_SHA256,
    RECOVERED_TRAINING_GZIP_SHA256,
    RECOVERED_TRAINING_RAW_SHA256,
)
from nfl_forecast.fst_reconstruction import (
    REFIT_ABS_TOLERANCE,
    REQUIRED_ENVIRONMENT,
    REQUIRED_PACKAGE_VERSIONS,
    REQUIRED_PYTHON_VERSION,
)

EVIDENCE_PATH = Path("research/fst/F-ST-01-reconstruction-evidence.json")
SPEC_PATH = Path("research/fst/F-ST-01-FROZEN-2026.json")
DEFAULT_RECEIPT_PATH = Path("challenger_outputs/fst/reconstruction_probe/receipt.json")
NUMERIC_FIELDS = (
    "intercept",
    "market_logit_coefficient",
    "pure_logit_coefficient",
)
EXACT_FIELDS = (
    "training_data_sha256",
    "training_games",
    "training_first_season",
    "training_last_season",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(message: str) -> None:
    raise RuntimeError(f"F-ST durable reconstruction evidence invalid: {message}")


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        _fail(f"{label}={actual!r} expected {expected!r}")


def verify_durable_evidence(
    evidence_path: str | Path = EVIDENCE_PATH,
    spec_path: str | Path = SPEC_PATH,
) -> dict[str, Any]:
    evidence_path = Path(evidence_path)
    spec_path = Path(spec_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    registered = spec["frozen_identity"]

    _require_equal("candidate_id", evidence.get("candidate_id"), FROZEN_CANDIDATE_ID)
    _require_equal("spec candidate_id", spec.get("candidate_id"), FROZEN_CANDIDATE_ID)
    _require_equal("research_only", evidence.get("research_only"), True)
    _require_equal("production_authorized", evidence.get("production_authorized"), False)
    _require_equal("completed_2026_outcomes_used", evidence.get("completed_2026_outcomes_used"), 0)
    _require_equal(
        "evidence_role",
        evidence.get("evidence_role"),
        "durable_compatible_hardware_forensic_reconstruction",
    )
    _require_equal("original_freeze_provenance", evidence.get("original_freeze_provenance"), False)

    immutable = evidence["immutable_inputs"]
    _require_equal("base_oof_raw_sha256", immutable.get("base_oof_raw_sha256"), RECOVERED_BASE_OOF_RAW_SHA256)
    _require_equal("training_frame_raw_sha256", immutable.get("training_frame_raw_sha256"), RECOVERED_TRAINING_RAW_SHA256)
    _require_equal("training_frame_gzip_sha256", immutable.get("training_frame_gzip_sha256"), RECOVERED_TRAINING_GZIP_SHA256)
    _require_equal("canonical_training_digest", immutable.get("canonical_training_digest"), FROZEN_TRAINING_DIGEST)
    _require_equal("training_games", int(immutable.get("training_games")), FROZEN_TRAINING_ROWS)
    _require_equal("training_first_season", int(immutable.get("training_first_season")), FROZEN_TRAINING_FIRST_SEASON)
    _require_equal("training_last_season", int(immutable.get("training_last_season")), FROZEN_TRAINING_LAST_SEASON)

    forensic_registered = evidence["registered_identity_at_forensic_run"]
    for field in EXACT_FIELDS + NUMERIC_FIELDS:
        _require_equal(f"registered forensic identity {field}", forensic_registered.get(field), registered.get(field))

    fit = evidence["reconstruction_fit"]
    for field in EXACT_FIELDS:
        _require_equal(f"reconstruction fit {field}", fit.get(field), registered.get(field))

    tolerance = float(registered.get("reconstruction_abs_tolerance", REFIT_ABS_TOLERANCE))
    if not math.isfinite(tolerance) or tolerance < 0 or tolerance > REFIT_ABS_TOLERANCE:
        _fail(f"registered reconstruction tolerance {tolerance!r} is not finite and <= 1e-12")
    tolerance_record = evidence["registered_tolerance_interpretation"]
    _require_equal("evidence numeric_abs_tolerance", float(tolerance_record.get("numeric_abs_tolerance")), tolerance)

    deltas: dict[str, float] = {}
    abs_deltas: dict[str, float] = {}
    for field in NUMERIC_FIELDS:
        delta = float(fit[field]) - float(registered[field])
        deltas[field] = delta
        abs_deltas[field] = abs(delta)
        if abs(delta) > tolerance:
            _fail(f"{field} reconstruction delta {delta!r} exceeds {tolerance}")
        recorded = float(tolerance_record["numeric_absolute_deltas"][field])
        if not math.isclose(abs(delta), recorded, rel_tol=0.0, abs_tol=1e-30):
            _fail(f"{field} recorded absolute delta drifted")
    _require_equal("tolerance interpretation matches", tolerance_record.get("matches"), True)

    exact_result = evidence["forensic_exact_equality_result"]
    _require_equal("forensic exact-equality flag", exact_result.get("matches_registered_identity"), False)
    _require_equal(
        "forensic exact-equality mismatches",
        exact_result.get("mismatched_fields"),
        ["market_logit_coefficient", "pure_logit_coefficient"],
    )

    runtime_evidence = evidence["runtime"]
    _require_equal("runtime python", runtime_evidence.get("python_version"), REQUIRED_PYTHON_VERSION)
    _require_equal("runtime packages", runtime_evidence.get("package_versions"), REQUIRED_PACKAGE_VERSIONS)
    _require_equal("runtime environment", runtime_evidence.get("environment"), REQUIRED_ENVIRONMENT)
    blas = [p for p in runtime_evidence.get("threadpools", []) if p.get("user_api") == "blas"]
    if not blas:
        _fail("forensic runtime has no BLAS pool")
    for pool in blas:
        if str(pool.get("architecture") or "").lower() != "skylakex":
            _fail(f"forensic BLAS architecture drifted: {pool.get('architecture')!r}")
        if int(pool.get("num_threads") or 0) != 4:
            _fail(f"forensic BLAS thread count drifted: {pool.get('num_threads')!r}")

    source = evidence["forensic_workflow"]
    for field in ("artifact_zip_sha256", "result_sha256", "head_sha", "workflow_github_sha"):
        value = str(source.get(field) or "")
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            _fail(f"forensic source {field} is not a lowercase SHA-256/SHA identity")
    if int(source.get("workflow_run_id", 0)) != 34538432305:
        _fail("forensic workflow run identity drifted")
    if int(source.get("artifact_id", 0)) != 10176440471:
        _fail("forensic artifact identity drifted")

    identity_check = {
        "schema_version": 3,
        "check_stage": "durable_forensic_evidence_pre_scoring",
        "capture_context": "prospective_shadow_reconstruction",
        "authoritative_scoring_source": "registered_frozen_identity_literals",
        "exact_identity_fields": ["candidate_id", *EXACT_FIELDS],
        "numerical_refit_fields": list(NUMERIC_FIELDS),
        "numeric_abs_tolerance": tolerance,
        "refit_abs_tolerance": tolerance,
        "expected": {
            "candidate_id": FROZEN_CANDIDATE_ID,
            **{field: registered[field] for field in EXACT_FIELDS + NUMERIC_FIELDS},
        },
        "actual_refit": {
            "candidate_id": FROZEN_CANDIDATE_ID,
            **{field: fit[field] for field in EXACT_FIELDS + NUMERIC_FIELDS},
        },
        "numerical_deltas": deltas,
        "numerical_absolute_deltas": abs_deltas,
        "numeric_absolute_deltas": abs_deltas,
        "mismatched_fields": [],
        "matches": True,
        "forensic_result_exact_equality_flag": False,
    }
    runtime = {
        "python_version": runtime_evidence["python_version"],
        "required_python_version": REQUIRED_PYTHON_VERSION,
        "package_versions": runtime_evidence["package_versions"],
        "required_package_versions": REQUIRED_PACKAGE_VERSIONS,
        "environment": runtime_evidence["environment"],
        "required_environment": REQUIRED_ENVIRONMENT,
        "threadpools": runtime_evidence["threadpools"],
        "matches": True,
        "failures": [],
        "forensic_source": source,
    }
    return {
        "evidence": evidence,
        "identity_check": identity_check,
        "runtime": runtime,
        "evidence_sha256": _sha256(evidence_path),
        "spec_sha256": _sha256(spec_path),
    }


def build_receipt(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    spec_path: str | Path = SPEC_PATH,
) -> dict[str, Any]:
    verified = verify_durable_evidence(evidence_path=evidence_path, spec_path=spec_path)
    evidence = verified["evidence"]
    immutable = evidence["immutable_inputs"]
    receipt = {
        "schema_version": 2,
        "candidate_id": FROZEN_CANDIDATE_ID,
        "status": "verified",
        "receipt_scope": "durable_forensic_evidence_verification",
        "source_sha": os.environ.get("GITHUB_SHA"),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "runtime": verified["runtime"],
        "reconstruction_fit": evidence["reconstruction_fit"],
        "identity_check": verified["identity_check"],
        "immutable_training_artifact": {
            "canonical_training_digest": immutable["canonical_training_digest"],
            "raw_sha256": immutable["training_frame_raw_sha256"],
            "gzip_sha256": immutable["training_frame_gzip_sha256"],
            "rows": immutable["training_games"],
        },
        "spec_sha256": verified["spec_sha256"],
        "forensic_evidence_sha256": verified["evidence_sha256"],
        "forensic_source": evidence["forensic_workflow"],
        "execution_policy": "verify_immutable_compatible_hardware_evidence_then_score_registered_literals_natively",
    }
    return receipt


def write_receipt(
    output_path: str | Path = DEFAULT_RECEIPT_PATH,
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    spec_path: str | Path = SPEC_PATH,
) -> dict[str, Any]:
    receipt = build_receipt(evidence_path=evidence_path, spec_path=spec_path)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "verified", "receipt": str(path)}, indent=2))
    return receipt


if __name__ == "__main__":
    write_receipt()

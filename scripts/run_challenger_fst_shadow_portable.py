from __future__ import annotations

"""Launch F-ST-01 shadow scoring natively after reconstruction evidence verifies.

The underlying shadow materializer remains authoritative for current-week scoring. This
launcher accepts either a fresh compatible-hardware reconstruction receipt or a current-run
receipt produced by verifying the immutable compatible-hardware forensic evidence. In both
cases, the long process stays on the native CPU and scores only with registered frozen
coefficient literals.
"""

import hashlib
import json
import os
from pathlib import Path

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID, FrozenStackFit
from nfl_forecast.fst_reconstruction import verify_fst_reconstruction_identity
import scripts.run_challenger_fst_shadow as shadow

RECEIPT_PATH = Path("challenger_outputs/fst/reconstruction_probe/receipt.json")
SPEC_PATH = Path("research/fst/F-ST-01-FROZEN-2026.json")
FORENSIC_EVIDENCE_PATH = Path("research/fst/F-ST-01-reconstruction-evidence.json")
ALLOWED_RECEIPT_SCOPES = {
    "fresh_compatible_runtime_probe",
    "durable_forensic_evidence_verification",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fit_from_receipt(receipt: dict) -> FrozenStackFit:
    values = receipt["reconstruction_fit"]
    return FrozenStackFit(
        intercept=float(values["intercept"]),
        market_logit_coefficient=float(values["market_logit_coefficient"]),
        pure_logit_coefficient=float(values["pure_logit_coefficient"]),
        training_games=int(values["training_games"]),
        training_first_season=int(values["training_first_season"]),
        training_last_season=int(values["training_last_season"]),
        training_data_sha256=str(values["training_data_sha256"]),
    )


def _load_verified_receipt() -> tuple[dict, FrozenStackFit]:
    if os.environ.get("OPENBLAS_CORETYPE"):
        raise RuntimeError(
            "Portable F-ST shadow must not inherit OPENBLAS_CORETYPE; reconstruction belongs in isolated evidence generation"
        )
    if not RECEIPT_PATH.exists():
        raise RuntimeError("Portable F-ST shadow requires a verified reconstruction receipt")
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    registered = spec["frozen_identity"]

    if receipt.get("candidate_id") != FROZEN_CANDIDATE_ID or receipt.get("status") != "verified":
        raise RuntimeError("F-ST reconstruction receipt identity/status invalid")
    scope = receipt.get("receipt_scope")
    if scope not in ALLOWED_RECEIPT_SCOPES:
        raise RuntimeError(f"F-ST reconstruction receipt scope invalid: {scope!r}")
    if receipt.get("research_only") is not True or receipt.get("production_authorized") is not False:
        raise RuntimeError("F-ST reconstruction receipt crossed research/production boundary")
    if int(receipt.get("completed_2026_outcomes_used", -1)) != 0:
        raise RuntimeError("F-ST reconstruction receipt is contaminated by 2026 outcomes")
    if receipt.get("spec_sha256") != _sha256(SPEC_PATH):
        raise RuntimeError("F-ST reconstruction receipt was generated against a different frozen spec")
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha and receipt.get("source_sha") and receipt["source_sha"] != github_sha:
        raise RuntimeError("F-ST reconstruction receipt came from a different workflow source SHA")
    if receipt.get("identity_check", {}).get("matches") is not True:
        raise RuntimeError("F-ST reconstruction receipt did not pass identity verification")
    tolerance = float(receipt["identity_check"]["numeric_abs_tolerance"])
    if tolerance > 1e-12:
        raise RuntimeError("F-ST reconstruction receipt widened the fixed 1e-12 tolerance")
    if receipt.get("runtime", {}).get("matches") is not True:
        raise RuntimeError("F-ST reconstruction receipt runtime was not verified")

    if scope == "durable_forensic_evidence_verification":
        if not FORENSIC_EVIDENCE_PATH.exists():
            raise RuntimeError("F-ST durable forensic evidence file is missing")
        expected_evidence_sha = _sha256(FORENSIC_EVIDENCE_PATH)
        if receipt.get("forensic_evidence_sha256") != expected_evidence_sha:
            raise RuntimeError("F-ST reconstruction receipt is not bound to current forensic evidence")
        if not isinstance(receipt.get("forensic_source"), dict):
            raise RuntimeError("F-ST durable reconstruction receipt lacks forensic source identity")

    fit = _fit_from_receipt(receipt)
    exact = {
        "training_data_sha256": str(registered["training_data_sha256"]),
        "training_games": int(registered["training_games"]),
        "training_first_season": int(registered["training_first_season"]),
        "training_last_season": int(registered["training_last_season"]),
    }
    actual = {
        "training_data_sha256": fit.training_data_sha256,
        "training_games": fit.training_games,
        "training_first_season": fit.training_first_season,
        "training_last_season": fit.training_last_season,
    }
    if actual != exact:
        raise RuntimeError("F-ST reconstruction receipt exact training identity drifted")
    for field in ("intercept", "market_logit_coefficient", "pure_logit_coefficient"):
        if abs(float(getattr(fit, field)) - float(registered[field])) > 1e-12:
            raise RuntimeError(f"F-ST reconstruction receipt coefficient drift: {field}")
    return receipt, fit


def _probe_bound_fit_provenance(receipt: dict):
    def write(output_dir, input_manifest, fit):
        out = Path(output_dir)
        input_path = out / "inputs_manifest.json"
        if not input_path.exists():
            raise RuntimeError("F-ST receipt-bound provenance requires persisted pre-fit inputs")
        persisted = json.loads(input_path.read_text(encoding="utf-8"))
        if persisted != input_manifest:
            raise RuntimeError("F-ST pre-fit inputs changed before reconstruction-evidence binding")
        if fit != _fit_from_receipt(receipt):
            raise RuntimeError("F-ST fit passed to receipt-bound provenance differs from receipt")
        manifest = {
            "schema_version": 4,
            "candidate_id": input_manifest["candidate_id"],
            "capture_context": input_manifest["capture_context"],
            "inputs_manifest_sha256": _sha256(input_path),
            "base_oof_raw_sha256": input_manifest["base_oof"]["raw_sha256"],
            "training_frame_raw_sha256": input_manifest["training_frame"]["raw_sha256"],
            "training_frame_canonical_game_keyed_sha256": input_manifest["training_frame"]["canonical_game_keyed_sha256"],
            "model_training_data_sha256": fit.training_data_sha256,
            "fit": fit.as_dict(),
            "runtime": receipt["runtime"],
            "reconstruction_probe_receipt": str(RECEIPT_PATH),
            "reconstruction_probe_receipt_sha256": _sha256(RECEIPT_PATH),
            "reconstruction_execution_policy": receipt["receipt_scope"],
            "reconstruction_forensic_evidence_sha256": receipt.get("forensic_evidence_sha256"),
            "shadow_scoring_execution_policy": "native_cpu_registered_literals",
        }
        (out / "fit_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
    return write


def main() -> None:
    receipt, fit = _load_verified_receipt()

    # Inject only already-proven reconstruction facts. All input capture, artifact
    # validation, native current-PURE fitting, final probability calculation, and output
    # construction stay in the existing frozen shadow materializer.
    shadow.require_fst_reconstruction_runtime = lambda: receipt["runtime"]
    shadow.fit_frozen_2026_stack = lambda training: fit
    shadow.write_fst_fit_provenance = _probe_bound_fit_provenance(receipt)
    shadow.verify_fst_reconstruction_identity = verify_fst_reconstruction_identity
    shadow.main()


if __name__ == "__main__":
    main()

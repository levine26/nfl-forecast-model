from __future__ import annotations

"""Run only the strict F-ST-01 historical reconstruction under the recovered runtime.

The probe is deliberately tiny. It validates the immutable recovered training artifact,
refits the frozen two-input stack, enforces the <=1e-12 identity contract, and emits a
cryptographically bound receipt. Long-lived current-week shadow scoring must consume a
verified reconstruction receipt from a native-CPU process rather than inherit a forced
historical CPU target. This fresh probe is intended only for compatible hardware; routine
shadow CI may instead verify the durable compatible-hardware forensic evidence.
"""

import hashlib
import json
import os
from pathlib import Path

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID, fit_frozen_2026_stack
from nfl_forecast.fst_nested_pure import (
    FROZEN_TRAINING_DIGEST,
    RECOVERED_TRAINING_GZIP_SHA256,
    RECOVERED_TRAINING_RAW_SHA256,
    load_frozen_training_frame,
)
from nfl_forecast.fst_reconstruction import (
    require_fst_reconstruction_runtime,
    verify_fst_reconstruction_identity,
)

SPEC_PATH = Path("research/fst/F-ST-01-FROZEN-2026.json")
DEFAULT_OUT = Path("challenger_outputs/fst/reconstruction_probe")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output_dir: str | Path = DEFAULT_OUT) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if spec.get("candidate_id") != FROZEN_CANDIDATE_ID:
        raise RuntimeError("F-ST reconstruction probe candidate identity mismatch")
    registered = spec["frozen_identity"]

    # This is the only stage that is allowed to require the recovered CPU-specific
    # numerical runtime. Keep it short and independent of all current-week model work.
    runtime = require_fst_reconstruction_runtime()
    training = load_frozen_training_frame()
    reconstructed = fit_frozen_2026_stack(training)
    input_manifest = {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "capture_context": "prospective_shadow_reconstruction",
    }
    identity_check = verify_fst_reconstruction_identity(
        out,
        input_manifest,
        reconstructed,
        registered,
    )
    if not identity_check["matches"]:
        raise RuntimeError("F-ST reconstruction probe did not reproduce frozen identity")

    receipt = {
        "schema_version": 2,
        "candidate_id": FROZEN_CANDIDATE_ID,
        "status": "verified",
        "receipt_scope": "fresh_compatible_runtime_probe",
        "source_sha": os.environ.get("GITHUB_SHA"),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "runtime": runtime,
        "reconstruction_fit": reconstructed.as_dict(),
        "identity_check": identity_check,
        "immutable_training_artifact": {
            "canonical_training_digest": FROZEN_TRAINING_DIGEST,
            "raw_sha256": RECOVERED_TRAINING_RAW_SHA256,
            "gzip_sha256": RECOVERED_TRAINING_GZIP_SHA256,
            "rows": int(len(training)),
        },
        "spec_sha256": _sha256(SPEC_PATH),
        "forensic_evidence_sha256": None,
        "execution_policy": "fresh_compatible_hardware_reconstruction_only_no_current_week_scoring",
    }
    receipt_path = out / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}, indent=2))
    return receipt


if __name__ == "__main__":
    run()

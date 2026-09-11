from __future__ import annotations

"""Run the frozen FTN-PROCESS-01 experiment with the corrected source-identity gate.

This wrapper changes only the pre-result FTN/PBP key-join implementation. It deliberately
reuses the frozen runner, preregistration, model family, features, chronology, thresholds,
and evaluation code unchanged.
"""

import json
from pathlib import Path

import research.run_ftn_process_v1 as frozen_runner
from research.ftn_identity_v1 import FTNIdentityGateError, join_ftn_to_pbp


FAILURE_PATH = Path("research_outputs/ftn_process_v1/source_gate_failure.json")


def main() -> None:
    # Replace only the module-level source join binding used by frozen_runner.run().
    frozen_runner.join_ftn_to_pbp = join_ftn_to_pbp
    try:
        frozen_runner.main()
    except FTNIdentityGateError as exc:
        FAILURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAILURE_PATH.write_text(
            json.dumps(
                {
                    "experiment_id": "FTN-PROCESS-01",
                    "status": "SOURCE_GATE_FAILED",
                    "error": str(exc),
                    "audit": exc.audit,
                    "research_only": True,
                    "production_authorized": False,
                    "completed_2026_outcomes_used": 0,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()

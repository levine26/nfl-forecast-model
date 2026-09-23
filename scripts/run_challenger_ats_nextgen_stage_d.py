from __future__ import annotations

"""Run frozen ATS NextGen Phase-2 Stage-D evidence synthesis.

This is research-only final evidence synthesis.  It regenerates Q1 and Q3 using
their frozen runners solely to prove accepted evidence reproducibility, verifies
every regenerated evidence-file SHA-256 against the accepted result registries,
then computes the preregistered Stage-D uncertainty diagnostics.  It does not
reconstruct Q2, tune any candidate, inspect completed-2026 outcomes, or modify
production forecasting.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_ats_nextgen_stage_d import (
    BOOTSTRAP_SAMPLES,
    BOOTSTRAP_SEED,
    descriptive_season_deltas,
    q3_hit_rate_intervals,
    stage_d_uncertainty,
)
from run_challenger_ats_nextgen_q1 import run as run_q1
from run_challenger_ats_nextgen_q3 import run as run_q3

OPENING_REGISTRY = Path("research/ats-nextgen/phase2_stage_d_opening_registry.json")
Q1_RESULT_REGISTRY = Path("research/ats-nextgen/phase2_q1_result_registry.json")
Q2_RESULT_REGISTRY = Path("research/ats-nextgen/phase2_q2_result_registry.json")
Q3_RESULT_REGISTRY = Path("research/ats-nextgen/phase2_q3_result_registry.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_upstream_registries() -> tuple[dict, dict, dict, dict]:
    opening = _load_json(OPENING_REGISTRY)
    q1 = _load_json(Q1_RESULT_REGISTRY)
    q2 = _load_json(Q2_RESULT_REGISTRY)
    q3 = _load_json(Q3_RESULT_REGISTRY)

    if opening.get("status") != "FROZEN_PRE_EXECUTION":
        raise RuntimeError("Stage-D opening registry is not a frozen pre-execution boundary")
    if opening.get("candidate_fitting_authorized") is not False:
        raise RuntimeError("Stage-D registry unexpectedly authorizes new candidate fitting")
    if opening.get("candidate_retuning_authorized") is not False:
        raise RuntimeError("Stage-D registry unexpectedly authorizes candidate retuning")
    if opening.get("candidate_rescue_authorized") is not False:
        raise RuntimeError("Stage-D registry unexpectedly authorizes candidate rescue")
    if opening.get("completed_2026_outcomes_authorized") is not False:
        raise RuntimeError("Stage-D registry crossed the completed-2026 firewall")
    if opening["uncertainty"].get("bootstrap_samples") != BOOTSTRAP_SAMPLES:
        raise RuntimeError("Stage-D bootstrap sample count drifted from frozen contract")
    if opening["uncertainty"].get("seed") != BOOTSTRAP_SEED:
        raise RuntimeError("Stage-D bootstrap seed drifted from frozen contract")
    if opening["uncertainty"].get("block_columns") != ["season", "week"]:
        raise RuntimeError("Stage-D bootstrap block definition drifted")

    if q1.get("classification") != "VALID_NEGATIVE_INCREMENTAL_RESULT":
        raise RuntimeError("Accepted Q1 classification drifted")
    if q1.get("q1_rescue_allowed") is not False:
        raise RuntimeError("Accepted Q1 registry unexpectedly allows rescue")
    if q2.get("classification") != "STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT":
        raise RuntimeError("Accepted Q2 structural classification drifted")
    if q2.get("accepted_q2_outer_oof_artifact") is not None:
        raise RuntimeError("Stage D refuses unexpected Q2 OOF evidence")
    if q2.get("accepted_q2_primary_performance") is not None:
        raise RuntimeError("Stage D refuses unexpected Q2 performance evidence")
    if q3.get("classification") != "NOT_INCREMENTAL_VS_Q3_M2":
        raise RuntimeError("Accepted Q3 classification drifted")
    if q3.get("candidate_repair_or_rescue_performed") is not False:
        raise RuntimeError("Accepted Q3 registry unexpectedly records rescue")
    if q3.get("q2_complementarity_available") is not False:
        raise RuntimeError("Stage D refuses a reopened Q2 complementarity cell")
    if q3.get("q2_q3_blend_available") is not False:
        raise RuntimeError("Stage D refuses a reopened Q2/Q3 blend cell")

    accepted = opening["accepted_inputs"]
    if accepted["q1"]["oof_sha256"] != q1["evidence_sha256"]["q1_outer_oof_2022_2025.csv"]:
        raise RuntimeError("Stage-D Q1 accepted OOF identity disagrees with Q1 result registry")
    if accepted["q3"]["oof_sha256"] != q3["artifact"]["files_sha256"]["q3_outer_oof_2022_2025.csv"]:
        raise RuntimeError("Stage-D Q3 accepted OOF identity disagrees with Q3 result registry")
    if accepted["q2"]["accepted_oof_available"] is not False:
        raise RuntimeError("Stage-D opening registry unexpectedly exposes Q2 OOF")
    return opening, q1, q2, q3


def _verify_regenerated_files(directory: Path, expected: dict[str, str], label: str) -> dict[str, str]:
    observed: dict[str, str] = {}
    for filename, expected_sha in sorted(expected.items()):
        path = directory / filename
        if not path.is_file():
            raise RuntimeError(f"{label} regeneration missing accepted evidence file: {filename}")
        actual = _sha256(path)
        if actual != expected_sha:
            raise RuntimeError(
                f"{label} regenerated evidence drifted for {filename}: "
                f"expected={expected_sha} actual={actual}"
            )
        observed[filename] = actual
    return observed


def run(
    output_dir: str = "research_outputs/ats_nextgen/stage_d",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    opening, q1_registry, q2_registry, q3_registry = _verify_upstream_registries()

    q1_dir = out / "reproduced_q1"
    q3_dir = out / "reproduced_q3"
    # These calls reproduce already-frozen evidence under the exact accepted runners.
    # They do not create a new candidate or reopen model selection.
    run_q1(str(q1_dir), config_path=config_path)
    q1_hashes = _verify_regenerated_files(
        q1_dir,
        q1_registry["evidence_sha256"],
        "Q1",
    )
    run_q3(str(q3_dir), config_path=config_path)
    q3_hashes = _verify_regenerated_files(
        q3_dir,
        q3_registry["artifact"]["files_sha256"],
        "Q3",
    )

    q1_oof_path = q1_dir / "q1_outer_oof_2022_2025.csv"
    q3_oof_path = q3_dir / "q3_outer_oof_2022_2025.csv"
    if _sha256(q1_oof_path) != opening["accepted_inputs"]["q1"]["oof_sha256"]:
        raise RuntimeError("Stage-D Q1 OOF does not match frozen opening identity")
    if _sha256(q3_oof_path) != opening["accepted_inputs"]["q3"]["oof_sha256"]:
        raise RuntimeError("Stage-D Q3 OOF does not match frozen opening identity")

    q1_oof = pd.read_csv(q1_oof_path)
    q3_oof = pd.read_csv(q3_oof_path)
    uncertainty = stage_d_uncertainty(q1_oof, q3_oof)
    hit_rate = pd.DataFrame([row.__dict__ for row in q3_hit_rate_intervals(q3_oof)])
    season_deltas = descriptive_season_deltas(q1_oof, q3_oof)

    uncertainty_path = out / "phase2_stage_d_paired_uncertainty.csv"
    hit_rate_path = out / "phase2_stage_d_hit_rate_intervals.csv"
    season_path = out / "phase2_stage_d_season_deltas.csv"
    uncertainty.to_csv(uncertainty_path, index=False, float_format="%.17g")
    hit_rate.to_csv(hit_rate_path, index=False, float_format="%.17g")
    season_deltas.to_csv(season_path, index=False, float_format="%.17g")

    comparisons = {
        row["metric"]: {
            "candidate": row["candidate"],
            "reference": row["reference"],
            "observed_delta": float(row["observed_delta"]),
            "ci_lower": float(row["ci_lower"]),
            "ci_upper": float(row["ci_upper"]),
            "probability_better": float(row["probability_better"]),
            "rows": int(row["rows"]),
            "blocks": int(row["blocks"]),
            "samples": int(row["samples"]),
        }
        for row in uncertainty.to_dict(orient="records")
    }
    summary = {
        "status": "COMPLETE_UNINTERPRETED",
        "program": "LEVLINE_ATS_NEXTGEN",
        "phase": 2,
        "stage": "D_FINAL_EVIDENCE_SYNTHESIS_AND_UNCERTAINTY",
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
        "new_candidate_fit_or_selection_performed": False,
        "q1_repair_or_rescue_performed": False,
        "q2_reconstruction_or_rescue_performed": False,
        "q3_repair_or_rescue_performed": False,
        "historical_evidence_class": "development_non_pristine",
        "bootstrap": {
            "samples": BOOTSTRAP_SAMPLES,
            "seed": BOOTSTRAP_SEED,
            "block": "season+week",
            "interval": "percentile_95pct",
        },
        "upstream_reproducibility": {
            "q1_all_accepted_files_match": True,
            "q3_all_accepted_files_match": True,
            "q1_evidence_sha256": q1_hashes,
            "q3_evidence_sha256": q3_hashes,
            "q2_classification": q2_registry["classification"],
            "q2_valid_oof_available": False,
            "q2_q3_blend_available": False,
        },
        "paired_uncertainty": comparisons,
        "simple_hit_rate_diagnostic": hit_rate.to_dict(orient="records"),
        "fixed_slice_evidence_recomputed_by_upstream_runners": True,
        "new_slices_created": False,
        "synthetic_historical_juice_used": False,
        "roi_or_ats_used_for_candidate_rescue": False,
        "phase3_classification_performed": False,
        "next_stage": "PHASE_3_SCIENTIFIC_SYNTHESIS_CANDIDATE_SELECTION_AND_FREEZE",
        "outputs": {
            "paired_uncertainty": str(uncertainty_path),
            "hit_rate_intervals": str(hit_rate_path),
            "season_deltas": str(season_path),
        },
    }
    summary_path = out / "phase2_stage_d_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/ats_nextgen/stage_d")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()

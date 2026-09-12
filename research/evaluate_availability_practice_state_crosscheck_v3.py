from __future__ import annotations

"""Evaluate the V09B validation-source practice-state contract (V3).

Research-only. Consumes preserved strict-V2 outputs and asks the narrower source
question: among official rows carrying a recognized practice participation state,
does reverse identity resolve at the frozen rate while the existing chronology,
practice-state, schedule, and source-integrity gates remain satisfied?
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import normalize_practice_status

CONTRACT_PATH = Path("research/availability/harmonization_practice_state_crosscheck_v3.json")
V2_OUTPUT_DIR = Path("research_outputs/availability_harmonization_regular_v2")
V2_RECEIPT_PATH = Path("research/availability/harmonization_regular_v2_diagnostic_receipt.json")
V09B_GOVERNANCE_PATH = Path("research/availability/v09b_execution_governance_v1.json")
SCHEDULE_HASH_COLUMNS = [
    "season", "week", "game_id", "gameday", "gametime",
    "home_team", "away_team", "game_type",
]
RECOGNIZED = {"full", "limited", "dnp"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_schedule_hash(frame: pd.DataFrame) -> str:
    missing = set(SCHEDULE_HASH_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"schedule missing V3 hash columns: {sorted(missing)}")
    out = frame[SCHEDULE_HASH_COLUMNS].copy()
    out = out.sort_values(["season", "week", "game_id"], kind="stable", na_position="last")
    for column in SCHEDULE_HASH_COLUMNS:
        out[column] = out[column].fillna("").astype(str)
    payload = out.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _recognized_mask(values: pd.Series) -> pd.Series:
    return values.map(normalize_practice_status).isin(RECOGNIZED)


def practice_state_reverse_identity_metrics(
    official: pd.DataFrame,
    unresolved: pd.DataFrame,
) -> dict[str, Any]:
    if "external_practice_status" not in official.columns:
        raise ValueError("official crosscheck missing external_practice_status")
    if len(unresolved) and "external_practice_status" not in unresolved.columns:
        raise ValueError("unresolved crosscheck missing external_practice_status")

    official_recognized = int(_recognized_mask(official["external_practice_status"]).sum())
    unresolved_recognized = (
        int(_recognized_mask(unresolved["external_practice_status"]).sum()) if len(unresolved) else 0
    )
    if official_recognized <= 0:
        raise ValueError("no recognized official practice-state rows")
    if unresolved_recognized > official_recognized:
        raise ValueError("unresolved recognized rows exceed official recognized rows")

    resolved_recognized = official_recognized - unresolved_recognized
    return {
        "official_recognized_practice_rows": official_recognized,
        "unresolved_recognized_practice_rows": unresolved_recognized,
        "resolved_recognized_practice_rows": resolved_recognized,
        "official_practice_state_to_canonical_identity_resolution_rate": resolved_recognized / official_recognized,
        "official_rows_without_recognized_practice_state": int(len(official) - official_recognized),
        "unresolved_rows_without_recognized_practice_state": int(len(unresolved) - unresolved_recognized),
    }


def evaluate(
    *,
    v2_output_dir: Path = V2_OUTPUT_DIR,
    contract_path: Path = CONTRACT_PATH,
    v2_receipt_path: Path = V2_RECEIPT_PATH,
    governance_path: Path = V09B_GOVERNANCE_PATH,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    v2_receipt = _load_json(v2_receipt_path)
    governance = _load_json(governance_path)

    if v2_receipt.get("disposition") != "FAILED_CLOSED_WITH_DIAGNOSTIC_EXPLANATION":
        raise RuntimeError("V3 requires preserved terminal strict-v2 failure receipt")
    if contract["source_semantics_revision"].get("v2_reclassified_as_pass") is not False:
        raise RuntimeError("V3 may not reclassify strict v2")
    if contract["source_semantics_revision"].get("v2_thresholds_relaxed") is not False:
        raise RuntimeError("V3 may not relax strict-v2 thresholds")

    season_summaries = pd.read_csv(v2_output_dir / "season_summaries.csv")
    schedule = pd.read_csv(v2_output_dir / "model_eligible_schedule_2022_2025.csv")
    schedule_hash = _stable_schedule_hash(schedule)
    expected_schedule_hash = contract["pinned_source_evidence"]["derived_schedule_subset_sha256"]

    required = [int(x) for x in contract["target_seasons"]]
    observed = sorted(pd.to_numeric(season_summaries["season"], errors="raise").astype(int).tolist())
    hard_blockers: list[str] = []
    if observed != required:
        hard_blockers.append("required seasons mismatch")
    if schedule_hash != expected_schedule_hash:
        hard_blockers.append("derived schedule subset hash mismatch")

    gates = contract["frozen_qualification_gates"]
    pinned_official = contract["pinned_source_evidence"]["official_semantic_bundle_sha256"]
    metrics_by_season: dict[str, Any] = {}
    summary_by_season = {int(row["season"]): row for _, row in season_summaries.iterrows()}

    for season in required:
        row = summary_by_season.get(season)
        if row is None:
            hard_blockers.append(f"missing season summary: {season}")
            continue
        official = pd.read_csv(v2_output_dir / f"official_nfl_regular_crosscheck_{season}.csv")
        try:
            unresolved = pd.read_csv(v2_output_dir / f"official_identity_unresolved_{season}.csv")
        except pd.errors.EmptyDataError:
            unresolved = pd.DataFrame(columns=official.columns)

        reverse = practice_state_reverse_identity_metrics(official, unresolved)
        season_metrics = {
            "season": season,
            **reverse,
            "canonical_to_official_identity_rate": float(row["canonical_to_official_identity_rate"]),
            "practice_status_agreement_rate": float(row["practice_status_agreement_rate"]),
            "known_by_t120_rate_among_identity_matched_rows": float(row["known_by_t120_rate_among_identity_matched_rows"]),
            "fully_qualified_practice_state_rate": float(row["fully_qualified_practice_state_rate"]),
            "date_modified_parse_rate": None if pd.isna(row["date_modified_parse_rate"]) else float(row["date_modified_parse_rate"]),
            "schedule_match_rate": float(row["schedule_match_rate"]),
            "non_exception_schedule_unmatched_rows": int(row["non_exception_schedule_unmatched_rows"]),
            "duplicate_canonical_identity_rows": int(row["duplicate_canonical_identity_rows"]),
            "official_pages_collected": int(row["official_pages_collected"]),
            "official_semantic_sha256": str(row["official_semantic_sha256"]),
            "diagnostic_game_status_agreement_rate": float(row["diagnostic_game_status_agreement_rate"]),
            "game_status_qualifying_gate": False,
        }
        metrics_by_season[str(season)] = season_metrics

        if season_metrics["official_semantic_sha256"] != pinned_official[str(season)]:
            hard_blockers.append(f"official semantic source hash mismatch: {season}")
        if season_metrics["official_pages_collected"] != int(gates["official_nfl_pages_required_per_season"]):
            hard_blockers.append(f"official page coverage failed: {season}")
        if season_metrics["canonical_to_official_identity_rate"] < float(gates["canonical_to_official_unique_identity_match_rate_min"]):
            hard_blockers.append(f"canonical-to-official identity gate failed: {season}")
        if reverse["official_practice_state_to_canonical_identity_resolution_rate"] < float(gates["official_practice_state_to_canonical_identity_resolution_rate_min"]):
            hard_blockers.append(f"practice-state reverse identity gate failed: {season}")
        if season_metrics["practice_status_agreement_rate"] < float(gates["practice_status_agreement_rate_min"]):
            hard_blockers.append(f"practice-state agreement gate failed: {season}")
        if season_metrics["known_by_t120_rate_among_identity_matched_rows"] != float(gates["known_by_t120_rate_required_among_identity_matched_rows"]):
            hard_blockers.append(f"T-120 chronology gate failed: {season}")
        if season_metrics["fully_qualified_practice_state_rate"] < float(gates["fully_qualified_practice_state_rate_min"]):
            hard_blockers.append(f"fully qualified practice-state gate failed: {season}")
        if season in (2022, 2023, 2024):
            rate = season_metrics["date_modified_parse_rate"]
            if rate is None or rate < float(gates["legacy_date_modified_parse_rate_min"]):
                hard_blockers.append(f"date_modified integrity gate failed: {season}")
        if season_metrics["schedule_match_rate"] != float(gates["schedule_match_rate_required_among_model_eligible_rows"]):
            hard_blockers.append(f"schedule match gate failed: {season}")
        if season_metrics["non_exception_schedule_unmatched_rows"] > int(gates["non_exception_schedule_unmatched_rows_allowed"]):
            hard_blockers.append(f"non-exception schedule unmatched rows failed: {season}")
        if season_metrics["duplicate_canonical_identity_rows"] > int(gates["duplicate_canonical_identity_rows_allowed"]):
            hard_blockers.append(f"duplicate canonical identity gate failed: {season}")

    validation_source_qualified = not hard_blockers
    current = governance.get("current_evidence", {})
    training_source_ok = bool(current.get("training_source_chronology_qualified"))
    training_label_ok = bool(current.get("training_label_semantics_qualified"))
    v09b_execution_authorized = bool(
        validation_source_qualified
        and training_source_ok
        and training_label_ok
        and current.get("original_preregistration_unchanged") is True
        and current.get("completed_2026_outcomes_used") == 0
    )

    return {
        "contract_id": contract["contract_id"],
        "technical_status": "QUALIFIED" if validation_source_qualified else "BLOCKED",
        "validation_source_qualified": validation_source_qualified,
        "hard_blockers": hard_blockers,
        "metrics_by_season": metrics_by_season,
        "schedule_subset_sha256": schedule_hash,
        "v2_failure_preserved": True,
        "game_status_qualifying_gate": False,
        "final_game_status_feature_authorized": False,
        "probability_model_built": False,
        "completed_2026_outcomes_used": 0,
        "game_outcomes_used": 0,
        "training_source_chronology_qualified": training_source_ok,
        "training_label_semantics_qualified": training_label_ok,
        "v09b_execution_authorized": v09b_execution_authorized,
        "production_dependency_authorized": False,
        "candidate_promotion_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-output-dir", type=Path, default=V2_OUTPUT_DIR)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--output", type=Path, default=Path("research_outputs/availability_practice_v3/qualification.json"))
    args = parser.parse_args()
    result = evaluate(v2_output_dir=args.v2_output_dir, contract_path=args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Cross-publisher metadata consistency audit for LevLine 4 identity research.

This experiment compares already-frozen, status-free official-club roster metadata with
an already-frozen nflverse Week 2 identity projection. Resolution is team + exact
normalized full name only. Jersey is a post-resolution corroboration diagnostic and can
never rescue a row. The frozen nflverse projection does not contain position, so no
position comparison is performed. A PASS is metadata-consistency evidence only, not
GSIS truth.
"""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import polars as pl

from research.levline4_prospective_inactive_gsis_resolver_v1 import (
    SOURCE_FIELDS,
    build_identity_index,
    normalize_name,
    normalize_team,
)

CONTRACT_PATH = Path("research/levline4_2026_official_club_nflverse_metadata_consistency_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_official_club_nflverse_metadata_consistency_v1")
CONTRACT_ID = "LEVLINE-4-2026-OFFICIAL-CLUB-NFLVERSE-METADATA-CONSISTENCY-V1"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    c = json.loads(path.read_text(encoding="utf-8"))
    assert c["contract_id"] == CONTRACT_ID
    assert c["status"] == "PREREGISTERED_CROSS_PUBLISHER_METADATA_CONSISTENCY_ONLY"
    assert c["qualification_gate"]["exact_unique_resolution_rate_min"] == 0.995
    assert c["qualification_gate"]["ambiguities_allowed"] == 0
    assert c["qualification_gate"]["jersey_agreement_rate_required"] == 1.0
    assert c["frozen_sources"]["nflverse_identity"]["position_field_present"] is False
    assert c["post_resolution_metadata_audit"]["position_comparison_performed"] is False
    assert c["frozen_resolution"]["jersey_used_for_resolution"] is False
    assert c["frozen_resolution"]["position_used_for_resolution"] is False
    assert c["frozen_resolution"]["fuzzy_matching_allowed"] is False
    assert c["authority_if_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert c["authority_if_gate_passes"]["production_authorized"] is False
    return c


def load_official_rows(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    observed = sha256_path(path)
    if observed != expected_sha256:
        raise RuntimeError(f"official roster metadata sha256 mismatch: {observed}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_identity_frame(path: Path, expected_sha256: str) -> pl.DataFrame:
    observed = sha256_path(path)
    if observed != expected_sha256:
        raise RuntimeError(f"nflverse identity projection sha256 mismatch: {observed}")
    frame = pl.read_parquet(path)
    if tuple(frame.columns) != SOURCE_FIELDS:
        raise RuntimeError(f"unexpected identity projection fields: {tuple(frame.columns)}")
    return frame


def normalize_jersey(value: Any) -> tuple[str | None, bool]:
    """Return canonical jersey string plus invalid-nonempty flag."""
    if value is None:
        return None, False
    if isinstance(value, float) and math.isnan(value):
        return None, False
    text = str(value).strip()
    if not text or text.casefold() in {"none", "null", "nan"}:
        return None, False
    try:
        number = float(text)
    except ValueError:
        return None, True
    if not math.isfinite(number) or not number.is_integer():
        return None, True
    integer = int(number)
    if integer < 0 or integer > 99:
        return None, True
    return str(integer), False


def _week2_identity_metadata(frame: pl.DataFrame) -> tuple[dict[tuple[str, str], dict[str, Any]], set[tuple[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in frame.to_dicts():
        if int(row.get("season") or -1) != 2026 or str(row.get("game_type") or "") != "REG":
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if week != 2:
            continue
        team = normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if team and gsis:
            grouped[(team, gsis)].append(row)

    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    conflicts: set[tuple[str, str]] = set()
    for key, rows in grouped.items():
        variants = {normalize_jersey(row.get("jersey_number")) for row in rows}
        if len(variants) != 1:
            conflicts.add(key)
            continue
        jersey_number, jersey_invalid = next(iter(variants))
        metadata[key] = {
            "jersey_number": jersey_number,
            "jersey_invalid": jersey_invalid,
            "row_count": len(rows),
        }
    return metadata, conflicts


def evaluate(
    official_rows: list[dict[str, Any]],
    identity_frame: pl.DataFrame,
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    identity_index = build_identity_index(identity_frame)
    identity_metadata, identity_conflicts = _week2_identity_metadata(identity_frame)

    results: list[dict[str, Any]] = []
    resolved_assignments: Counter[tuple[str, str]] = Counter()
    invalid_jersey_count = 0
    comparable_jersey = 0
    jersey_agreements = 0

    for source in official_rows:
        team = normalize_team(source.get("team"))
        visible_name = str(source.get("visible_name") or "").strip()
        normalized = normalize_name(visible_name)
        candidates = sorted(identity_index.get((2, team, normalized), set()))
        if len(candidates) == 1:
            state = "RESOLVED_EXACT_UNIQUE"
            resolved = candidates[0]
            resolved_assignments[(team, resolved)] += 1
        elif len(candidates) == 0:
            state = "UNRESOLVED"
            resolved = None
        else:
            state = "AMBIGUOUS"
            resolved = None

        official_jersey, official_invalid = normalize_jersey(source.get("jersey_number"))
        jersey_comparable = False
        jersey_agrees = None
        identity_jersey = None
        identity_metadata_conflict = False
        identity_invalid = False

        if resolved is not None:
            key = (team, resolved)
            if key in identity_conflicts or key not in identity_metadata:
                identity_metadata_conflict = True
            else:
                meta = identity_metadata[key]
                identity_jersey = meta.get("jersey_number")
                identity_invalid = bool(meta.get("jersey_invalid"))
                if official_invalid:
                    invalid_jersey_count += 1
                if identity_invalid:
                    invalid_jersey_count += 1
                if not official_invalid and not identity_invalid and official_jersey is not None and identity_jersey is not None:
                    jersey_comparable = True
                    comparable_jersey += 1
                    jersey_agrees = official_jersey == identity_jersey
                    jersey_agreements += int(jersey_agrees)

        results.append(
            {
                "team": team,
                "visible_name": visible_name,
                "normalized_name": normalized,
                "profile_path": str(source.get("profile_path") or ""),
                "resolution_state": state,
                "candidate_gsis_ids": candidates,
                "resolved_candidate_gsis_id": resolved,
                "resolution_basis": "week2_team_exact_normalized_visible_name_unique" if resolved else None,
                "position_used_for_resolution": False,
                "jersey_used_for_resolution": False,
                "status_used_for_resolution": False,
                "fuzzy_matching_used": False,
                "manual_override_used": False,
                "official_jersey_number": official_jersey,
                "nflverse_jersey_number": identity_jersey,
                "jersey_comparable": jersey_comparable,
                "jersey_agrees": jersey_agrees,
                "official_position_recorded_but_not_compared": str(source.get("position") or "").strip().upper() or None,
                "nflverse_position_available": False,
                "position_comparison_performed": False,
                "identity_metadata_conflict": identity_metadata_conflict,
                "player_identity_to_gsis_qualified": False,
                "availability_state_authorized": False,
                "forecast_probability_effect_authorized": False,
                "production_authorized": False,
            }
        )

    counts = Counter(row["resolution_state"] for row in results)
    total = len(results)
    exact = counts["RESOLVED_EXACT_UNIQUE"]
    exact_rate = exact / total if total else 0.0
    duplicate_assignments = [
        {"team": team, "candidate_gsis_id": gsis, "official_row_count": count}
        for (team, gsis), count in resolved_assignments.items()
        if count > 1
    ]
    duplicate_assignments.sort(key=lambda row: (row["team"], row["candidate_gsis_id"]))
    comparable_fraction = comparable_jersey / exact if exact else 0.0
    jersey_agreement_rate = jersey_agreements / comparable_jersey if comparable_jersey else 0.0
    teams = sorted({normalize_team(row.get("team")) for row in official_rows if normalize_team(row.get("team"))})
    exact_identity_conflict_rows = sum(1 for row in results if row["identity_metadata_conflict"])

    gate = contract["qualification_gate"]
    gate_pass = (
        total == int(gate["official_row_count_must_equal"])
        and len(teams) == int(gate["official_team_count_must_equal"])
        and exact_rate >= float(gate["exact_unique_resolution_rate_min"])
        and counts["AMBIGUOUS"] <= int(gate["ambiguities_allowed"])
        and len(duplicate_assignments) <= int(gate["duplicate_candidate_gsis_assignments_within_team_allowed"])
        and exact_identity_conflict_rows <= int(gate["nflverse_identity_metadata_conflicts_allowed"])
        and invalid_jersey_count <= int(gate["invalid_nonempty_jersey_values_allowed"])
        and comparable_fraction >= float(gate["jersey_comparable_fraction_of_exact_unique_min"])
        and comparable_jersey > 0
        and jersey_agreement_rate >= float(gate["jersey_agreement_rate_required"])
    )

    summary = {
        "official_row_count": total,
        "official_team_count": len(teams),
        "resolved_exact_unique_count": exact,
        "unresolved_count": counts["UNRESOLVED"],
        "ambiguous_count": counts["AMBIGUOUS"],
        "exact_unique_resolution_rate": exact_rate,
        "duplicate_candidate_gsis_assignment_count": len(duplicate_assignments),
        "nflverse_identity_metadata_conflict_row_count": exact_identity_conflict_rows,
        "invalid_nonempty_jersey_value_count": invalid_jersey_count,
        "jersey_comparable_count": comparable_jersey,
        "jersey_comparable_fraction_of_exact_unique": comparable_fraction,
        "jersey_agreement_count": jersey_agreements,
        "jersey_disagreement_count": comparable_jersey - jersey_agreements,
        "jersey_agreement_rate": jersey_agreement_rate,
        "position_comparison_performed": False,
        "gate_pass": gate_pass,
    }
    return results, summary, duplicate_assignments


def run(official_path: Path, identity_path: Path, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    c = load_contract()
    official = load_official_rows(official_path, c["frozen_sources"]["official_club"]["roster_metadata_sha256"])
    identity = load_identity_frame(identity_path, c["frozen_sources"]["nflverse_identity"]["projection_sha256"])
    rows, summary, duplicates = evaluate(official, identity, c)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "row_results.jsonl").open("w", encoding="utf-8") as handle:
        for row in sorted(rows, key=lambda x: (x["team"], x["profile_path"], x["visible_name"])):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "duplicate_candidate_assignments.json").write_text(json.dumps(duplicates, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gate_pass = bool(summary["gate_pass"])
    receipt = {
        "schema_version": "levline4-2026-official-club-nflverse-metadata-consistency-v1",
        "contract_id": CONTRACT_ID,
        "status": "PASS" if gate_pass else "FAIL",
        "official_roster_metadata_sha256": c["frozen_sources"]["official_club"]["roster_metadata_sha256"],
        "nflverse_identity_projection_sha256": c["frozen_sources"]["nflverse_identity"]["projection_sha256"],
        **summary,
        "official_club_vs_nflverse_metadata_consistency_validated": gate_pass,
        "cross_publisher_metadata_agreement_observed": gate_pass,
        "underlying_source_independence_proven": False,
        "official_stable_player_identifier_qualified": False,
        "official_identifier_to_gsis_bridge_qualified": False,
        "player_identity_to_gsis_qualified": False,
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
        "general_2026_player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_state_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "target_inactive_rows_used_for_design_or_selection": False,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "f_st_01_frozen_2026_unchanged": True,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--official-roster-metadata", type=Path, required=True)
    p.add_argument("--identity-projection", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    a = p.parse_args()
    receipt = run(a.official_roster_metadata, a.identity_projection, a.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

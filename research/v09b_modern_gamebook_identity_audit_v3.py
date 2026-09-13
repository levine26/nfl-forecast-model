from __future__ import annotations

"""Independently calibrated V3 follow-up for modern Game Book identity.

V2 is immutable and failed with two 2019 WAS M.Smith #46 ambiguity rows. V3 first
calibrates a secondary-vs-linebacker family mapping on independent 2017-2021 V1
exact-unique identities. All ten V1 ambiguity rows are excluded from calibration.
Only a passing frozen calibration gate may authorize the family tie-break on the two
V2-retained rows. No roster status, membership semantics, postgame participation,
or outcomes are used.
"""

import argparse
import gzip
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as identity_v1
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as gamebook_parser
from research import v09b_modern_gamebook_identity_audit_v1 as modern_v1
from research import v09b_modern_gamebook_roster_universe_v1 as archive_guard
from research import v09b_modern_position_identity_source_capture_v2 as position_capture

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V3"
V1_RECEIPT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V1-FAILED"
V2_RECEIPT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V2-FAILED"
SEASONS = (2017, 2018, 2019, 2020, 2021)
SECTIONS = ("lineup", "substitutions", "did_not_play", "not_active")
POSITION_SPLIT_RE = re.compile(r"[/\-]+")

SECONDARY_TOKENS = {"CB", "DB", "FS", "LCB", "NB", "RCB", "S", "SAF", "SFTY", "SS"}
LINEBACKER_TOKENS = {"ILB", "LB", "LILB", "LLB", "LOLB", "MLB", "OLB", "RILB", "RLB", "ROLB", "SLB", "WLB"}
FAMILY_BY_TOKEN = {
    **{token: "secondary" for token in SECONDARY_TOKENS},
    **{token: "linebacker" for token in LINEBACKER_TOKENS},
}

MIN_TOTAL_COMPARABLE = 5000
MIN_FAMILY_ROWS = 1000
MIN_OVERALL_AGREEMENT = 0.95
MIN_FAMILY_AGREEMENT = 0.95
MIN_FAMILY_WILSON_LOWER = 0.94
MIN_FINAL_RESOLUTION_RATE = 0.995
EXPECTED_V2_TOTAL = 138205
EXPECTED_V2_RESOLVED = 137798
EXPECTED_V2_UNRESOLVED = 405
EXPECTED_V2_AMBIGUOUS = 2


def normalize_position_token(value: object) -> list[str]:
    text = str(value or "").strip().upper().replace(".", "")
    return [part for part in POSITION_SPLIT_RE.split(text) if part] if text else []


def classify_position_family(values: Iterable[object]) -> dict[str, Any]:
    raw = sorted({str(v or "").strip().upper() for v in values if str(v or "").strip()})
    if not raw:
        return {"valid": False, "family": None, "reason": "empty", "raw_tokens": []}
    families: set[str] = set()
    unknown: set[str] = set()
    components: set[str] = set()
    for token in raw:
        parts = normalize_position_token(token)
        if not parts:
            return {"valid": False, "family": None, "reason": "empty", "raw_tokens": raw}
        for part in parts:
            components.add(part)
            family = FAMILY_BY_TOKEN.get(part)
            if family is None:
                unknown.add(part)
            else:
                families.add(family)
    if unknown:
        return {
            "valid": False,
            "family": None,
            "reason": "unknown_or_other_family",
            "raw_tokens": raw,
            "normalized_components": sorted(components),
            "unknown_components": sorted(unknown),
        }
    if len(families) != 1:
        return {
            "valid": False,
            "family": None,
            "reason": "mixed",
            "raw_tokens": raw,
            "normalized_components": sorted(components),
            "unknown_components": [],
        }
    return {
        "valid": True,
        "family": next(iter(families)),
        "reason": "ok",
        "raw_tokens": raw,
        "normalized_components": sorted(components),
        "unknown_components": [],
    }


def wilson_lower_bound(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total)
    return (centre - margin) / denom


def _read_receipt(path: Path, expected_id: str) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("receipt_id") != expected_id:
        raise RuntimeError(f"unexpected predecessor receipt: {path}")
    return receipt


def _validate_predecessors(v1_path: Path, v2_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    v1 = _read_receipt(v1_path, V1_RECEIPT_ID)
    v2 = _read_receipt(v2_path, V2_RECEIPT_ID)
    a1 = v1.get("aggregate_result", {})
    a2 = v2.get("aggregate_result", {})
    if not (
        v1.get("status") == "EMPIRICAL_AUDIT_COMPLETE_QUALIFICATION_GATE_FAILED"
        and a1.get("final_ambiguous") == 10
        and a1.get("source_identity_conflicts") == 0
        and len(v1.get("ambiguity_examples", [])) == 10
        and v2.get("status") == "EMPIRICAL_AUDIT_COMPLETE_QUALIFICATION_GATE_FAILED"
        and a2.get("gamebook_identities_total") == EXPECTED_V2_TOTAL
        and a2.get("final_resolved") == EXPECTED_V2_RESOLVED
        and a2.get("final_unresolved") == EXPECTED_V2_UNRESOLVED
        and a2.get("final_ambiguous") == EXPECTED_V2_AMBIGUOUS
        and a2.get("source_identity_conflicts") == 0
        and len(v2.get("remaining_ambiguities", [])) == EXPECTED_V2_AMBIGUOUS
        and v2.get("scientific_disposition", {}).get("follow_up_requires_separately_preregistered_experiment") is True
    ):
        raise RuntimeError("predecessor V1/V2 receipts failed frozen replay checks")
    return v1, v2


def _ambiguity_coordinate(row: dict[str, Any]) -> tuple[int, int, str, str, str, str]:
    return (
        int(row["season"]),
        int(row["week"]),
        str(row["game_id"]),
        identity_v1.normalize_team(row["team"]),
        identity_v1.normalize_jersey(row["jersey_number"]),
        str(row["display_name"]),
    )


def _load_position_projection(root: Path, season: int) -> tuple[pl.DataFrame, dict[str, Any]]:
    receipt = json.loads((root / "receipts" / f"{season}.json").read_text(encoding="utf-8"))
    if not (
        receipt.get("capture_contract_id") == position_capture.CAPTURE_CONTRACT_ID
        and int(receipt.get("season")) == season
        and receipt.get("raw_source_sha256") == position_capture.RAW_SOURCE_SHA256[season]
        and receipt.get("source_rows_selected") == position_capture.EXPECTED_REG_ROWS[season]
        and receipt.get("missing_gsis_rows") == position_capture.EXPECTED_MISSING_GSIS_ROWS[season]
        and receipt.get("capture_gate_pass") is True
        and receipt.get("status_fields_selected") is False
        and receipt.get("status_fields_read") is False
        and receipt.get("projection_contains_status_fields") is False
    ):
        raise RuntimeError(f"position-source capture failed for {season}")
    frame = pl.read_parquet(root / str(receipt["projection_relpath"]))
    if tuple(frame.columns) != position_capture.ALLOWED_FIELDS:
        raise RuntimeError("position projection allowlist mismatch")
    if any(field in frame.columns for field in position_capture.FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("status field leaked into position projection")
    return frame, receipt


def _position_index(frame: pl.DataFrame) -> dict[tuple[int, str, str, str], set[str]]:
    out: dict[tuple[int, str, str, str], set[str]] = defaultdict(set)
    for row in frame.to_dicts():
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = identity_v1.normalize_team(row.get("team"))
        jersey = identity_v1.normalize_jersey(row.get("jersey_number"))
        if not team or not jersey:
            continue
        position = str(row.get("position") or "").strip()
        if position:
            out[(week, team, jersey, gsis)].add(position)
        else:
            out.setdefault((week, team, jersey, gsis), set())
    return out


def _section_positions(text: str, *, side: int) -> tuple[dict[tuple[str, str], set[str]], bool]:
    markers, sections = gamebook_parser._section_entries(text, side=side)
    exact = all(markers.get(k) == 1 for k in ("lineups", "substitutions", "did_not_play", "not_active"))
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    for section in SECTIONS:
        for entry in sections[section]:
            out[entry.parser_identity].add(entry.position)
    return out, exact


def _calibrate_season(
    season: int,
    *,
    archive_root: Path,
    identity_root: Path,
    position_root: Path,
    excluded: set[tuple[int, int, str, str, str, str]],
) -> dict[str, Any]:
    upstream = archive_guard.validate_upstream_archive(archive_root, season)
    identity_frame, identity_receipt = modern_v1._load_projection(identity_root, season)
    exact_source = identity_v1.build_identity_index(season=season, frame=identity_frame)
    exact_index = exact_source.pop("index")
    position_frame, position_receipt = _load_position_projection(position_root, season)
    position_index = _position_index(position_frame)
    manifest = [
        json.loads(line)
        for line in (archive_root / "manifests" / f"{season}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    comparable = agreement = examined = excluded_count = 0
    non_gamebook = non_source = lookup_misses = 0
    by_family = {"secondary": {"rows": 0, "agreement": 0}, "linebacker": {"rows": 0, "agreement": 0}}
    errors: list[dict[str, str]] = []

    for source_row in manifest:
        try:
            with gzip.open(archive_root / str(source_row["raw_object_relpath"]), "rb") as handle:
                text = raw_helpers._extract_pdf_text(handle.read())
            week = int(source_row["week"])
            for side, team in (
                (0, identity_v1.normalize_team(source_row["away_team"])),
                (1, identity_v1.normalize_team(source_row["home_team"])),
            ):
                identities, marker_exact = _section_positions(text, side=side)
                if not marker_exact:
                    raise RuntimeError("Game Book roster markers are not exact")
                for (jersey, display_name), gb_positions in sorted(identities.items()):
                    jersey_key = identity_v1.normalize_jersey(jersey)
                    coord = (season, week, str(source_row["game_id"]), team, jersey_key, display_name)
                    if coord in excluded:
                        excluded_count += 1
                        continue
                    exact_key = (week, team, jersey_key, identity_v1.compact_name(display_name))
                    candidates = sorted(exact_index.get(exact_key, set()))
                    if len(candidates) != 1:
                        continue
                    examined += 1
                    gb_family = classify_position_family(gb_positions)
                    if not gb_family["valid"]:
                        non_gamebook += 1
                        continue
                    source_positions = position_index.get((week, team, jersey_key, candidates[0]), set())
                    if not source_positions:
                        lookup_misses += 1
                        continue
                    src_family = classify_position_family(source_positions)
                    if not src_family["valid"]:
                        non_source += 1
                        continue
                    family = str(gb_family["family"])
                    comparable += 1
                    by_family[family]["rows"] += 1
                    if src_family["family"] == family:
                        agreement += 1
                        by_family[family]["agreement"] += 1
        except Exception as exc:
            errors.append({"game_id": str(source_row.get("game_id")), "error": f"{type(exc).__name__}: {exc}"})

    for family in by_family:
        rows = int(by_family[family]["rows"])
        successes = int(by_family[family]["agreement"])
        by_family[family]["agreement_rate"] = successes / rows if rows else 0.0
        by_family[family]["wilson95_lower_bound"] = wilson_lower_bound(successes, rows)

    return {
        "season": season,
        "gamebook_archive_qualified": bool(upstream.get("upstream_passed")),
        "identity_source_capture_gate_pass": bool(identity_receipt.get("capture_gate_pass")),
        "position_source_capture_gate_pass": bool(position_receipt.get("capture_gate_pass")),
        "identity_source_conflicts": int(identity_receipt.get("source_identity_conflicts", 0)),
        "exact_unique_examined": examined,
        "ambiguity_rows_excluded": excluded_count,
        "comparable_rows": comparable,
        "agreement_rows": agreement,
        "agreement_rate": agreement / comparable if comparable else 0.0,
        "by_gamebook_family": by_family,
        "noncomparable_gamebook_family": non_gamebook,
        "noncomparable_source_family": non_source,
        "source_lookup_misses": lookup_misses,
        "source_error_count": len(errors),
        "source_error_examples": errors[:50],
    }


def _target_gamebook_positions(archive_root: Path, ambiguity: dict[str, Any]) -> set[str]:
    season = int(ambiguity["season"])
    manifest = [
        json.loads(line)
        for line in (archive_root / "manifests" / f"{season}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    source_row = next((r for r in manifest if str(r["game_id"]) == str(ambiguity["game_id"])), None)
    if source_row is None:
        raise RuntimeError("target game missing from frozen archive")
    team = identity_v1.normalize_team(ambiguity["team"])
    away = identity_v1.normalize_team(source_row["away_team"])
    home = identity_v1.normalize_team(source_row["home_team"])
    side = 0 if team == away else 1 if team == home else None
    if side is None:
        raise RuntimeError("target team absent from Game Book")
    with gzip.open(archive_root / str(source_row["raw_object_relpath"]), "rb") as handle:
        text = raw_helpers._extract_pdf_text(handle.read())
    identities, marker_exact = _section_positions(text, side=side)
    if not marker_exact:
        raise RuntimeError("target Game Book markers are not exact")
    key = (identity_v1.normalize_jersey(ambiguity["jersey_number"]), str(ambiguity["display_name"]))
    return set(identities.get(key, set()))


def audit_v3(
    *,
    archive_root: Path,
    identity_root: Path,
    position_root: Path,
    v1_receipt_path: Path,
    v2_receipt_path: Path,
) -> dict[str, Any]:
    v1, v2 = _validate_predecessors(v1_receipt_path, v2_receipt_path)
    excluded = {_ambiguity_coordinate(row) for row in v1["ambiguity_examples"]}
    per_season = [
        _calibrate_season(
            season,
            archive_root=archive_root,
            identity_root=identity_root,
            position_root=position_root,
            excluded=excluded,
        )
        for season in SEASONS
    ]

    total_rows = sum(int(s["comparable_rows"]) for s in per_season)
    total_agree = sum(int(s["agreement_rows"]) for s in per_season)
    family_totals: dict[str, dict[str, int | float]] = {}
    for family in ("secondary", "linebacker"):
        rows = sum(int(s["by_gamebook_family"][family]["rows"]) for s in per_season)
        successes = sum(int(s["by_gamebook_family"][family]["agreement"]) for s in per_season)
        family_totals[family] = {
            "rows": rows,
            "agreement": successes,
            "agreement_rate": successes / rows if rows else 0.0,
            "wilson95_lower_bound": wilson_lower_bound(successes, rows),
        }

    calibration_pass = bool(
        total_rows >= MIN_TOTAL_COMPARABLE
        and (total_agree / total_rows if total_rows else 0.0) >= MIN_OVERALL_AGREEMENT
        and all(int(v["rows"]) >= MIN_FAMILY_ROWS for v in family_totals.values())
        and all(float(v["agreement_rate"]) >= MIN_FAMILY_AGREEMENT for v in family_totals.values())
        and all(float(v["wilson95_lower_bound"]) >= MIN_FAMILY_WILSON_LOWER for v in family_totals.values())
        and sum(int(s["ambiguity_rows_excluded"]) for s in per_season) == 10
        and sum(int(s["source_error_count"]) for s in per_season) == 0
        and all(int(s["identity_source_conflicts"]) == 0 for s in per_season)
        and all(s["gamebook_archive_qualified"] is True for s in per_season)
        and all(s["identity_source_capture_gate_pass"] is True for s in per_season)
        and all(s["position_source_capture_gate_pass"] is True for s in per_season)
    )

    position_indices = {
        season: _position_index(_load_position_projection(position_root, season)[0])
        for season in SEASONS
    }
    targets: list[dict[str, Any]] = []
    lookup_misses = resolved = 0
    target_errors: list[str] = []

    for ambiguity in v2["remaining_ambiguities"]:
        try:
            season = int(ambiguity["season"])
            gb_positions = _target_gamebook_positions(archive_root, ambiguity)
            gb_family = classify_position_family(gb_positions)
            candidate_positions: dict[str, set[str]] = {}
            candidate_families: dict[str, dict[str, Any]] = {}
            for gsis in sorted(str(x) for x in ambiguity["candidate_positions"].keys()):
                key = (
                    int(ambiguity["week"]),
                    identity_v1.normalize_team(ambiguity["team"]),
                    identity_v1.normalize_jersey(ambiguity["jersey_number"]),
                    gsis,
                )
                evidence = set(position_indices[season].get(key, set()))
                candidate_positions[gsis] = evidence
                if not evidence:
                    lookup_misses += 1
                candidate_families[gsis] = classify_position_family(evidence)
            all_valid = all(v["valid"] for v in candidate_families.values())
            matching = [
                gsis for gsis, evidence in candidate_families.items()
                if evidence["valid"] and gb_family["valid"] and evidence["family"] == gb_family["family"]
            ]
            resolved_gsis = matching[0] if calibration_pass and all_valid and gb_family["valid"] and len(matching) == 1 else None
            if resolved_gsis:
                resolved += 1
            targets.append({
                "season": season,
                "week": int(ambiguity["week"]),
                "game_id": str(ambiguity["game_id"]),
                "team": identity_v1.normalize_team(ambiguity["team"]),
                "jersey_number": identity_v1.normalize_jersey(ambiguity["jersey_number"]),
                "display_name": str(ambiguity["display_name"]),
                "gamebook_positions": sorted(gb_positions),
                "gamebook_family": gb_family,
                "candidate_positions": {k: sorted(v) for k, v in candidate_positions.items()},
                "candidate_families": candidate_families,
                "resolution": "resolved" if resolved_gsis else "ambiguous",
                "resolved_gsis_id": resolved_gsis,
                "reason": "unique_calibrated_family_candidate" if resolved_gsis else "calibration_or_family_gate_not_unique",
            })
        except Exception as exc:
            target_errors.append(f"{type(exc).__name__}: {exc}")

    final_resolved = EXPECTED_V2_RESOLVED + resolved
    final_ambiguous = EXPECTED_V2_AMBIGUOUS - resolved
    final_rate = final_resolved / EXPECTED_V2_TOTAL
    aggregate_pass = bool(
        calibration_pass
        and len(targets) == EXPECTED_V2_AMBIGUOUS
        and not target_errors
        and lookup_misses == 0
        and final_rate >= MIN_FINAL_RESOLUTION_RATE
        and final_ambiguous == 0
        and int(v2["aggregate_result"]["source_identity_conflicts"]) == 0
    )

    return {
        "contract_id": CONTRACT_ID,
        "calibration": {
            "seasons": list(SEASONS),
            "per_season": per_season,
            "total_comparable_rows": total_rows,
            "total_agreement_rows": total_agree,
            "overall_agreement_rate": total_agree / total_rows if total_rows else 0.0,
            "by_gamebook_family": family_totals,
            "v1_ambiguity_rows_excluded": sum(int(s["ambiguity_rows_excluded"]) for s in per_season),
            "minimum_total_comparable_rows": MIN_TOTAL_COMPARABLE,
            "minimum_family_rows": MIN_FAMILY_ROWS,
            "minimum_overall_family_agreement": MIN_OVERALL_AGREEMENT,
            "minimum_family_agreement": MIN_FAMILY_AGREEMENT,
            "minimum_family_wilson95_lower_bound": MIN_FAMILY_WILSON_LOWER,
            "calibration_gate_pass": calibration_pass,
        },
        "target_follow_up": {
            "expected_rows": EXPECTED_V2_AMBIGUOUS,
            "rows_replayed": len(targets),
            "resolved_rows": resolved,
            "candidate_projection_lookup_misses": lookup_misses,
            "source_error_count": len(target_errors),
            "source_errors": target_errors,
            "rows": targets,
        },
        "gamebook_identities_total": EXPECTED_V2_TOTAL,
        "v2_final_resolved": EXPECTED_V2_RESOLVED,
        "v2_final_unresolved": EXPECTED_V2_UNRESOLVED,
        "v2_final_ambiguous": EXPECTED_V2_AMBIGUOUS,
        "final_resolved": final_resolved,
        "final_unresolved": EXPECTED_V2_UNRESOLVED,
        "final_ambiguous": final_ambiguous,
        "final_identity_resolution_rate": final_rate,
        "source_identity_conflicts": int(v2["aggregate_result"]["source_identity_conflicts"]),
        "aggregate_qualification_gate_pass": aggregate_pass,
        "modern_player_team_game_identity_qualified": aggregate_pass,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_status_used": False,
        "raw_weekly_roster_consumed_by_calibration_or_target_resolver": False,
        "postgame_participation_used": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--identity-root", type=Path, required=True)
    parser.add_argument("--position-root", type=Path, required=True)
    parser.add_argument("--v1-receipt", type=Path, required=True)
    parser.add_argument("--v2-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_v3(
        archive_root=args.archive_root,
        identity_root=args.identity_root,
        position_root=args.position_root,
        v1_receipt_path=args.v1_receipt,
        v2_receipt_path=args.v2_receipt,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "calibration"}, indent=2, sort_keys=True))
    if result["aggregate_qualification_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

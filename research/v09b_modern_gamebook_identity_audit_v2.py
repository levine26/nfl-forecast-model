from __future__ import annotations

"""Blinded V2 follow-up for the 2017-2021 modern Game Book identity audit.

V1 is immutable and preserved as failed because 10 exact-key ambiguities remained. V2 reopens
only those 10 ambiguity rows. It uses official Game Book position tokens plus a separately
persisted, status-free 2019 weekly-roster position projection. It compares only side of ball
(offense/defense/special teams), never detailed-position equality, roster status, membership,
postgame participation, or outcomes.
"""

import argparse
import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as identity_v1
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as gamebook_parser
from research import v09b_modern_gamebook_roster_universe_v1 as archive_guard
from research import v09b_modern_position_identity_source_capture_v1 as position_capture

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V2"
V1_RECEIPT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V1-FAILED"
SEASON = 2019
EXPECTED_V1_TOTAL = 138205
EXPECTED_V1_RESOLVED = 137790
EXPECTED_V1_UNRESOLVED = 405
EXPECTED_V1_AMBIGUOUS = 10
MINIMUM_RESOLUTION_RATE = 0.995
EXPECTED_GAMES_2019 = 256
SECTIONS = ("lineup", "substitutions", "did_not_play", "not_active")
POSITION_SPLIT_RE = re.compile(r"[/\-]+")

OFFENSE_TOKENS = {
    "C", "FB", "FL", "G", "HB", "LG", "LT", "OC", "OG", "OL", "OT",
    "QB", "RB", "RG", "RT", "SE", "T", "TB", "TE", "WR",
}
DEFENSE_TOKENS = {
    "CB", "DB", "DE", "DL", "DT", "EDGE", "FS", "ILB", "LB", "LCB", "LDE",
    "LDT", "LE", "LILB", "LLB", "LOLB", "MLB", "NB", "NT", "OLB", "RCB",
    "RDE", "RDT", "RE", "RILB", "RLB", "ROLB", "S", "SAF", "SFTY", "SLB", "SS", "WLB",
}
SPECIAL_TEAMS_TOKENS = {
    "H", "K", "KOS", "KR", "LS", "P", "PK", "PR", "RET", "RS", "SNAP", "ST",
}
POSITION_SIDE_BY_TOKEN = {
    **{token: "offense" for token in OFFENSE_TOKENS},
    **{token: "defense" for token in DEFENSE_TOKENS},
    **{token: "special_teams" for token in SPECIAL_TEAMS_TOKENS},
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_position_token(value: object) -> list[str]:
    text = str(value or "").strip().upper().replace(".", "")
    if not text:
        return []
    return [part for part in POSITION_SPLIT_RE.split(text) if part]


def classify_position_evidence(values: Iterable[object]) -> dict[str, Any]:
    raw_tokens = sorted({str(value or "").strip().upper() for value in values if str(value or "").strip()})
    if not raw_tokens:
        return {"valid": False, "side": None, "reason": "empty", "raw_tokens": []}

    sides: set[str] = set()
    unknown_components: set[str] = set()
    normalized_components: set[str] = set()
    for raw in raw_tokens:
        components = normalize_position_token(raw)
        if not components:
            return {
                "valid": False,
                "side": None,
                "reason": "empty",
                "raw_tokens": raw_tokens,
                "normalized_components": [],
                "unknown_components": [],
            }
        for component in components:
            normalized_components.add(component)
            side = POSITION_SIDE_BY_TOKEN.get(component)
            if side is None:
                unknown_components.add(component)
            else:
                sides.add(side)

    if unknown_components:
        return {
            "valid": False,
            "side": None,
            "reason": "unknown",
            "raw_tokens": raw_tokens,
            "normalized_components": sorted(normalized_components),
            "unknown_components": sorted(unknown_components),
        }
    if len(sides) != 1:
        return {
            "valid": False,
            "side": None,
            "reason": "mixed",
            "raw_tokens": raw_tokens,
            "normalized_components": sorted(normalized_components),
            "unknown_components": [],
        }
    return {
        "valid": True,
        "side": next(iter(sides)),
        "reason": "ok",
        "raw_tokens": raw_tokens,
        "normalized_components": sorted(normalized_components),
        "unknown_components": [],
    }


def resolve_ambiguity_by_side(
    *,
    gamebook_positions: Iterable[object],
    candidate_positions: dict[str, Iterable[object]],
) -> dict[str, Any]:
    gamebook = classify_position_evidence(gamebook_positions)
    candidate_evidence = {
        gsis: classify_position_evidence(values)
        for gsis, values in sorted(candidate_positions.items())
    }

    if not gamebook["valid"]:
        return {
            "resolution": "ambiguous",
            "resolved_gsis_id": None,
            "reason": f"gamebook_position_{gamebook['reason']}",
            "gamebook_position_evidence": gamebook,
            "candidate_position_evidence": candidate_evidence,
        }
    invalid_candidates = [
        gsis for gsis, evidence in candidate_evidence.items() if not evidence["valid"]
    ]
    if invalid_candidates:
        return {
            "resolution": "ambiguous",
            "resolved_gsis_id": None,
            "reason": "candidate_position_incomplete",
            "invalid_candidate_gsis_ids": invalid_candidates,
            "gamebook_position_evidence": gamebook,
            "candidate_position_evidence": candidate_evidence,
        }

    matching = [
        gsis
        for gsis, evidence in candidate_evidence.items()
        if evidence["side"] == gamebook["side"]
    ]
    if len(matching) == 1:
        return {
            "resolution": "resolved",
            "resolved_gsis_id": matching[0],
            "reason": "unique_same_side_candidate",
            "gamebook_position_evidence": gamebook,
            "candidate_position_evidence": candidate_evidence,
        }
    return {
        "resolution": "ambiguous",
        "resolved_gsis_id": None,
        "reason": "zero_same_side_candidate" if not matching else "multiple_same_side_candidates",
        "matching_candidate_gsis_ids": matching,
        "gamebook_position_evidence": gamebook,
        "candidate_position_evidence": candidate_evidence,
    }


def _validate_predecessor(receipt_path: Path) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    aggregate = receipt.get("aggregate_result", {})
    disposition = receipt.get("scientific_disposition", {})
    if not (
        receipt.get("receipt_id") == V1_RECEIPT_ID
        and receipt.get("status") == "EMPIRICAL_AUDIT_COMPLETE_QUALIFICATION_GATE_FAILED"
        and aggregate.get("gamebook_identities_total") == EXPECTED_V1_TOTAL
        and aggregate.get("final_resolved") == EXPECTED_V1_RESOLVED
        and aggregate.get("final_unresolved") == EXPECTED_V1_UNRESOLVED
        and aggregate.get("final_ambiguous") == EXPECTED_V1_AMBIGUOUS
        and aggregate.get("source_identity_conflicts") == 0
        and aggregate.get("all_five_seasons_integrity_pass") is True
        and aggregate.get("aggregate_qualification_gate_pass") is False
        and disposition.get("modern_player_team_game_identity_qualified") is False
        and disposition.get("follow_up_requires_separately_preregistered_experiment") is True
        and len(receipt.get("ambiguity_examples", [])) == EXPECTED_V1_AMBIGUOUS
    ):
        raise RuntimeError("predecessor V1 receipt does not match the frozen failed experiment")
    return receipt


def _load_position_projection(position_root: Path) -> tuple[pl.DataFrame, dict[str, Any]]:
    receipt_path = position_root / "receipts" / f"{SEASON}.json"
    if not receipt_path.exists():
        raise RuntimeError("persisted position-source receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not (
        receipt.get("capture_contract_id") == position_capture.CAPTURE_CONTRACT_ID
        and receipt.get("season") == SEASON
        and receipt.get("raw_source_sha256") == position_capture.RAW_SOURCE_SHA256
        and receipt.get("source_rows_selected") == position_capture.EXPECTED_REG_ROWS
        and receipt.get("missing_gsis_rows") == position_capture.EXPECTED_MISSING_GSIS_ROWS
        and receipt.get("capture_gate_pass") is True
        and receipt.get("status_fields_selected") is False
        and receipt.get("status_fields_read") is False
    ):
        raise RuntimeError("persisted position-source receipt failed the frozen capture gate")

    projection_path = position_root / str(receipt["projection_relpath"])
    if not projection_path.exists():
        raise RuntimeError("persisted position projection is missing")
    if _sha256_file(projection_path) != str(receipt["projection_sha256"]):
        raise RuntimeError("persisted position projection SHA256 mismatch")
    frame = pl.read_parquet(projection_path)
    if tuple(frame.columns) != position_capture.ALLOWED_FIELDS:
        raise RuntimeError("persisted position projection fields do not match the allowlist")
    if any(field in frame.columns for field in position_capture.FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("status field leaked into persisted position projection")
    return frame, receipt


def _position_index(frame: pl.DataFrame) -> dict[tuple[int, str, str, str], set[str]]:
    index: dict[tuple[int, str, str, str], set[str]] = defaultdict(set)
    for row in frame.to_dicts():
        if int(row.get("season") or -1) != SEASON or str(row.get("game_type") or "") != "REG":
            continue
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = identity_v1.normalize_team(row.get("team"))
        jersey = identity_v1.normalize_jersey(row.get("jersey_number"))
        position = str(row.get("position") or "").strip()
        if not team or not jersey:
            continue
        if position:
            index[(week, team, jersey, gsis)].add(position)
        else:
            index.setdefault((week, team, jersey, gsis), set())
    return index


def _gamebook_positions(
    *,
    source_row: dict[str, Any],
    ambiguity: dict[str, Any],
    archive_root: Path,
) -> tuple[set[str], bool]:
    raw_path = archive_root / str(source_row["raw_object_relpath"])
    with gzip.open(raw_path, "rb") as handle:
        text = raw_helpers._extract_pdf_text(handle.read())

    target_team = identity_v1.normalize_team(ambiguity["team"])
    away = identity_v1.normalize_team(source_row["away_team"])
    home = identity_v1.normalize_team(source_row["home_team"])
    if target_team == away:
        side = 0
    elif target_team == home:
        side = 1
    else:
        raise RuntimeError("ambiguity team does not match either Game Book team")

    markers, sections = gamebook_parser._section_entries(text, side=side)
    marker_exact = all(
        markers.get(key) == 1
        for key in ("lineups", "substitutions", "did_not_play", "not_active")
    )
    target_identity = (
        identity_v1.normalize_jersey(ambiguity["jersey_number"]),
        str(ambiguity["display_name"]),
    )
    positions: set[str] = set()
    for section in SECTIONS:
        for entry in sections[section]:
            parser_identity = (
                identity_v1.normalize_jersey(entry.jersey_number),
                entry.display_name,
            )
            if parser_identity == target_identity:
                positions.add(entry.position)
    return positions, marker_exact


def audit_v2(
    *,
    archive_root: Path,
    position_root: Path,
    predecessor_receipt_path: Path,
) -> dict[str, Any]:
    predecessor = _validate_predecessor(predecessor_receipt_path)
    upstream = archive_guard.validate_upstream_archive(archive_root, SEASON)
    position_frame, position_receipt = _load_position_projection(position_root)
    position_index = _position_index(position_frame)

    manifest_path = archive_root / "manifests" / f"{SEASON}.jsonl"
    manifest = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest_by_game = {str(row["game_id"]): row for row in manifest}
    if len(manifest) != EXPECTED_GAMES_2019 or len(manifest_by_game) != EXPECTED_GAMES_2019:
        raise RuntimeError("2019 Game Book manifest does not match the frozen archive")

    results: list[dict[str, Any]] = []
    source_errors: list[dict[str, str]] = []
    lookup_misses = 0
    candidate_position_conflicts = 0
    candidate_unknown_position_evidence = 0
    gamebook_position_evidence_failures = 0
    resolved_by_position = 0

    for ambiguity in predecessor["ambiguity_examples"]:
        try:
            if int(ambiguity.get("season")) != SEASON or ambiguity.get("stage") != "exact":
                raise RuntimeError("V2 scope contains a non-2019 or non-exact V1 ambiguity")
            game_id = str(ambiguity["game_id"])
            source_row = manifest_by_game.get(game_id)
            if source_row is None:
                raise RuntimeError("V1 ambiguity game is missing from the frozen archive")
            positions, marker_exact = _gamebook_positions(
                source_row=source_row,
                ambiguity=ambiguity,
                archive_root=archive_root,
            )
            if not marker_exact:
                raise RuntimeError("Game Book roster markers are not exact for ambiguity row")

            week = int(ambiguity["week"])
            team = identity_v1.normalize_team(ambiguity["team"])
            jersey = identity_v1.normalize_jersey(ambiguity["jersey_number"])
            candidate_ids = sorted({str(x) for x in ambiguity["candidate_gsis_ids"]})
            if len(candidate_ids) < 2:
                raise RuntimeError("V1 ambiguity candidate set is not actually ambiguous")

            candidate_positions: dict[str, set[str]] = {}
            for gsis in candidate_ids:
                evidence = set(position_index.get((week, team, jersey, gsis), set()))
                candidate_positions[gsis] = evidence
                if not evidence:
                    lookup_misses += 1
                classified = classify_position_evidence(evidence)
                if classified["reason"] == "mixed":
                    candidate_position_conflicts += 1
                elif classified["reason"] in {"empty", "unknown"}:
                    candidate_unknown_position_evidence += 1

            tie = resolve_ambiguity_by_side(
                gamebook_positions=positions,
                candidate_positions=candidate_positions,
            )
            if not tie["gamebook_position_evidence"]["valid"]:
                gamebook_position_evidence_failures += 1
            if tie["resolution"] == "resolved":
                resolved_by_position += 1

            results.append(
                {
                    "season": SEASON,
                    "week": week,
                    "game_id": game_id,
                    "team": team,
                    "jersey_number": jersey,
                    "display_name": ambiguity["display_name"],
                    "v1_candidate_gsis_ids": candidate_ids,
                    "gamebook_position_tokens": sorted(positions),
                    **tie,
                }
            )
        except Exception as exc:
            source_errors.append(
                {
                    "game_id": str(ambiguity.get("game_id")),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    v1_aggregate = predecessor["aggregate_result"]
    final_resolved = int(v1_aggregate["final_resolved"]) + resolved_by_position
    final_unresolved = int(v1_aggregate["final_unresolved"])
    final_ambiguous = int(v1_aggregate["final_ambiguous"]) - resolved_by_position
    total = int(v1_aggregate["gamebook_identities_total"])
    final_rate = final_resolved / total if total else 0.0
    all_rows_replayed = len(results) == EXPECTED_V1_AMBIGUOUS and not source_errors

    qualified = bool(
        upstream.get("upstream_passed") is True
        and position_receipt.get("capture_gate_pass") is True
        and all_rows_replayed
        and lookup_misses == 0
        and candidate_position_conflicts == 0
        and candidate_unknown_position_evidence == 0
        and gamebook_position_evidence_failures == 0
        and int(v1_aggregate["source_identity_conflicts"]) == 0
        and final_rate >= MINIMUM_RESOLUTION_RATE
        and final_ambiguous == 0
    )

    return {
        "audit_version": 2,
        "contract_id": CONTRACT_ID,
        "predecessor_receipt_id": predecessor["receipt_id"],
        "predecessor_v1_qualification_failed": True,
        "predecessor_v1_ambiguities": EXPECTED_V1_AMBIGUOUS,
        "predecessor_v1_unresolved_rows_reopened": 0,
        "position_source_capture_contract_id": position_capture.CAPTURE_CONTRACT_ID,
        "position_source_projection_sha256": position_receipt["projection_sha256"],
        "position_source_capture_gate_pass": position_receipt["capture_gate_pass"],
        "position_projection_fields": list(position_frame.columns),
        "weekly_roster_status_used": False,
        "raw_weekly_roster_consumed_by_identity_resolver": False,
        "gamebook_archive_qualified": upstream.get("upstream_passed") is True,
        "ambiguity_rows_expected": EXPECTED_V1_AMBIGUOUS,
        "ambiguity_rows_replayed": len(results),
        "all_10_v1_ambiguity_rows_replayed": all_rows_replayed,
        "position_tiebreak_resolved": resolved_by_position,
        "candidate_projection_lookup_misses": lookup_misses,
        "candidate_position_side_conflicts": candidate_position_conflicts,
        "candidate_unknown_position_evidence": candidate_unknown_position_evidence,
        "gamebook_position_evidence_failures": gamebook_position_evidence_failures,
        "source_error_count": len(source_errors),
        "source_errors": source_errors,
        "v1_gamebook_identities_total": total,
        "v1_final_resolved": int(v1_aggregate["final_resolved"]),
        "v1_final_unresolved": int(v1_aggregate["final_unresolved"]),
        "v1_final_ambiguous": int(v1_aggregate["final_ambiguous"]),
        "final_resolved": final_resolved,
        "final_unresolved": final_unresolved,
        "final_ambiguous": final_ambiguous,
        "final_identity_resolution_rate": final_rate,
        "minimum_required_resolution_rate": MINIMUM_RESOLUTION_RATE,
        "source_identity_conflicts": int(v1_aggregate["source_identity_conflicts"]),
        "aggregate_qualification_gate_pass": qualified,
        "modern_player_team_game_identity_qualified": qualified,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "postgame_participation_used": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
        "ambiguity_results": results,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--position-root", type=Path, required=True)
    parser.add_argument("--predecessor-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = audit_v2(
        archive_root=args.archive_root,
        position_root=args.position_root,
        predecessor_receipt_path=args.predecessor_receipt,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"ambiguity_results", "source_errors"}
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

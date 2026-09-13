from __future__ import annotations

"""Status-free 2017-2021 Game Book -> GSIS identity audit.

The audit consumes only the immutable qualified modern Game Book archive and the immutable
status-free weekly-roster identity projection. It resolves identities independently of the
semantic meaning of Game Book roster sections. In particular, Did Not Play is included in
the identity universe but is never assumed active. Qualification authority belongs only to
the five-season aggregate gate.
"""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as identity_v1
from research import v09b_legacy_gamebook_identity_audit_v4 as identity_v4
from research import v09b_legacy_gamebook_identity_diagnostic_v2 as jersey_diag
from research import v09b_legacy_gamebook_identity_name_compat_v3 as compat_v3
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as gamebook_parser
from research import v09b_modern_gamebook_roster_universe_v1 as archive_guard
from research import v09b_modern_identity_source_capture_v1 as identity_capture

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-IDENTITY-AUDIT-V1"
SEASONS = (2017, 2018, 2019, 2020, 2021)
EXPECTED_GAMES = {2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272}
EXPECTED_TEAM_PARTITIONS = {season: games * 2 for season, games in EXPECTED_GAMES.items()}
EXPECTED_SOURCE_ROWS = {2017: 49210, 2018: 50113, 2019: 49561, 2020: 41972, 2021: 44539}
EXPECTED_MISSING_GSIS = {2017: 0, 2018: 35, 2019: 2, 2020: 5, 2021: 23}
EXPECTED_PROJECTION_SHA256 = {
    2017: "1ade2f94b602f52f53046f9efb868c441edf4f5f64ef1e205fa716327b9d4db0",
    2018: "237a75521207ea59be030fdf1d469ce04440e35cf8302fa8edbfabab506e45d2",
    2019: "ebc3e761749b956e809dfbb3e8d3556d65df22f3dcd8d7e103c70807077df7b7",
    2020: "49f770d6293cfab446165e5571274e44c2be61c3dfc4ee7321139006ce50ce1a",
    2021: "29860c837236401e1750f4902eda15ae809a62c62236ff17f16b75ca58b33fac",
}
SECTIONS = ("lineup", "substitutions", "did_not_play", "not_active")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_projection(identity_root: Path, season: int) -> tuple[pl.DataFrame, dict[str, Any]]:
    projection_sha = EXPECTED_PROJECTION_SHA256[season]
    projection_path = identity_root / "projections" / f"{season}-{projection_sha}.parquet"
    receipt_path = identity_root / "receipts" / f"{season}.json"
    if not projection_path.exists() or not receipt_path.exists():
        raise RuntimeError("immutable modern identity source is incomplete")
    if _sha256_file(projection_path) != projection_sha:
        raise RuntimeError("modern identity projection SHA does not match frozen capture")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not (
        receipt.get("contract_id") == identity_capture.CONTRACT_ID
        and int(receipt.get("season")) == season
        and receipt.get("projection_sha256") == projection_sha
        and receipt.get("source_rows_selected") == EXPECTED_SOURCE_ROWS[season]
        and receipt.get("missing_gsis_rows") == EXPECTED_MISSING_GSIS[season]
        and receipt.get("source_identity_conflicts") == 0
        and receipt.get("capture_gate_pass") is True
        and receipt.get("status_fields_selected") is False
        and receipt.get("status_fields_read_for_resolution") is False
    ):
        raise RuntimeError("modern identity-source receipt failed frozen replay checks")
    frame = pl.read_parquet(projection_path)
    if tuple(frame.columns) != identity_capture.ALLOWED_FIELDS:
        raise RuntimeError("modern identity projection does not exactly match frozen allowlist")
    if any(field in frame.columns for field in identity_capture.FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("status field leaked into modern identity projection")
    return frame, receipt


def _all_section_identities(text: str, *, side: int) -> tuple[set[tuple[str, str]], bool]:
    markers, sections = gamebook_parser._section_entries(text, side=side)
    marker_exact = all(markers.get(key) == 1 for key in ("lineups", "substitutions", "did_not_play", "not_active"))
    identities: set[tuple[str, str]] = set()
    for section in SECTIONS:
        identities.update(entry.parser_identity for entry in sections[section])
    return identities, marker_exact


def _authorized_structural_candidates(
    *,
    display_name: str,
    week: int,
    team: str,
    jersey: str,
    jersey_index: dict[tuple[int, str, str], set[str]],
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]],
) -> list[dict[str, str]]:
    authorized: list[dict[str, str]] = []
    for gsis in sorted(jersey_index.get((week, team, jersey), set())):
        signature = signatures_by_gsis.get((week, team, gsis))
        if signature is None:
            continue
        _source_jersey, first_name, football_name, last_name = signature
        classification = compat_v3.classify_candidate(
            display_name,
            first_name=first_name,
            football_name=football_name,
            last_name=last_name,
        )
        if not identity_v4.structural_candidate_authorized(classification):
            continue
        authorized.append(
            {
                "gsis_id": gsis,
                "method": str(classification["compatibility_method"]),
                "first_name": first_name,
                "football_name": football_name,
                "last_name": last_name,
            }
        )
    return authorized


def audit_season(season: int, *, archive_root: Path, identity_root: Path) -> dict[str, Any]:
    if season not in SEASONS:
        raise ValueError(f"season must be one of {SEASONS}")

    upstream = archive_guard.validate_upstream_archive(archive_root, season)
    projection, identity_receipt = _load_projection(identity_root, season)

    exact_source = identity_v1.build_identity_index(season=season, frame=projection)
    exact_index: dict[tuple[int, str, str, str], set[str]] = exact_source.pop("index")
    jersey_source = jersey_diag.build_same_week_team_jersey_index(season=season, frame=projection)
    jersey_index: dict[tuple[int, str, str], set[str]] = jersey_source.pop("index")
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]] = jersey_source.pop(
        "signatures_by_gsis"
    )
    source_accounting_consistent = bool(
        exact_source["source_rows_selected"] == jersey_source["source_rows_selected"] == EXPECTED_SOURCE_ROWS[season]
        and exact_source["missing_gsis_rows"] == jersey_source["missing_gsis_rows"] == EXPECTED_MISSING_GSIS[season]
        and exact_source["source_identity_conflicts"] == jersey_source["source_identity_conflicts"] == 0
    )

    manifest_path = archive_root / "manifests" / f"{season}.jsonl"
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    total = 0
    exact_resolved = 0
    exact_zero = 0
    exact_ambiguous = 0
    structural_resolved = 0
    structural_ambiguous = 0
    final_unresolved = 0
    parsed_games = 0
    parsed_partitions = 0
    marker_exact_games = 0
    source_errors: list[dict[str, str]] = []
    method_counts: Counter[str] = Counter()
    unresolved_examples: list[dict[str, object]] = []
    ambiguous_examples: list[dict[str, object]] = []
    structural_examples: list[dict[str, object]] = []

    for source_row in manifest:
        try:
            raw_path = archive_root / str(source_row["raw_object_relpath"])
            with gzip.open(raw_path, "rb") as handle:
                text = raw_helpers._extract_pdf_text(handle.read())
            week = int(source_row["week"])
            game_marker_exact = True
            for side, team, side_name in (
                (0, identity_v1.normalize_team(source_row["away_team"]), "visitor_left"),
                (1, identity_v1.normalize_team(source_row["home_team"]), "home_right"),
            ):
                identities, marker_exact = _all_section_identities(text, side=side)
                game_marker_exact = game_marker_exact and marker_exact
                parsed_partitions += 1
                for jersey, display_name in sorted(identities):
                    total += 1
                    jersey_key = identity_v1.normalize_jersey(jersey)
                    exact_key = (week, team, jersey_key, identity_v1.compact_name(display_name))
                    exact_candidates = sorted(exact_index.get(exact_key, set()))
                    if len(exact_candidates) == 1:
                        exact_resolved += 1
                        continue
                    base = {
                        "season": season,
                        "week": week,
                        "game_id": str(source_row["game_id"]),
                        "team": team,
                        "side": side_name,
                        "jersey_number": jersey_key,
                        "display_name": display_name,
                    }
                    if len(exact_candidates) > 1:
                        exact_ambiguous += 1
                        if len(ambiguous_examples) < 100:
                            ambiguous_examples.append({**base, "stage": "exact", "candidate_gsis_ids": exact_candidates})
                        continue

                    exact_zero += 1
                    authorized = _authorized_structural_candidates(
                        display_name=display_name,
                        week=week,
                        team=team,
                        jersey=jersey_key,
                        jersey_index=jersey_index,
                        signatures_by_gsis=signatures_by_gsis,
                    )
                    if len(authorized) == 1:
                        structural_resolved += 1
                        method_counts[authorized[0]["method"]] += 1
                        if len(structural_examples) < 200:
                            structural_examples.append({**base, "resolution": authorized[0]})
                    elif len(authorized) > 1:
                        structural_ambiguous += 1
                        if len(ambiguous_examples) < 100:
                            ambiguous_examples.append({**base, "stage": "structural", "authorized_candidates": authorized})
                    else:
                        final_unresolved += 1
                        if len(unresolved_examples) < 200:
                            unresolved_examples.append(
                                {
                                    **base,
                                    "same_week_team_jersey_candidate_count": len(
                                        jersey_index.get((week, team, jersey_key), set())
                                    ),
                                }
                            )
            parsed_games += 1
            if game_marker_exact:
                marker_exact_games += 1
        except Exception as exc:
            source_errors.append(
                {"game_id": str(source_row.get("game_id")), "error": f"{type(exc).__name__}: {exc}"}
            )

    if exact_resolved + exact_zero + exact_ambiguous != total:
        raise RuntimeError("exact identity accounting mismatch")
    if structural_resolved + structural_ambiguous + final_unresolved != exact_zero:
        raise RuntimeError("structural identity accounting mismatch")

    final_resolved = exact_resolved + structural_resolved
    final_ambiguous = exact_ambiguous + structural_ambiguous
    resolution_rate = final_resolved / total if total else 0.0
    expected_games = EXPECTED_GAMES[season]
    expected_partitions = EXPECTED_TEAM_PARTITIONS[season]
    integrity_pass = bool(
        upstream.get("upstream_passed") is True
        and identity_receipt.get("capture_gate_pass") is True
        and source_accounting_consistent
        and len(manifest) == expected_games
        and len({str(row["game_id"]) for row in manifest}) == expected_games
        and parsed_games == expected_games
        and marker_exact_games == expected_games
        and parsed_partitions == expected_partitions
        and not source_errors
        and tuple(projection.columns) == identity_capture.ALLOWED_FIELDS
        and not any(field in projection.columns for field in identity_capture.FORBIDDEN_STATUS_FIELDS)
    )

    return {
        "audit_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_gamebook_archive_qualified": upstream.get("upstream_passed") is True,
        "identity_source_capture_gate_pass": identity_receipt.get("capture_gate_pass") is True,
        "projection_sha256": EXPECTED_PROJECTION_SHA256[season],
        "projection_fields": list(projection.columns),
        "weekly_roster_status_used": False,
        "source_rows_selected": exact_source["source_rows_selected"],
        "expected_source_rows_selected": EXPECTED_SOURCE_ROWS[season],
        "missing_gsis_rows": exact_source["missing_gsis_rows"],
        "expected_missing_gsis_rows": EXPECTED_MISSING_GSIS[season],
        "source_identity_conflicts": exact_source["source_identity_conflicts"],
        "source_accounting_consistent": source_accounting_consistent,
        "canonical_games": len(manifest),
        "expected_games": expected_games,
        "parsed_games": parsed_games,
        "marker_exact_games": marker_exact_games,
        "parsed_team_partitions": parsed_partitions,
        "expected_team_partitions": expected_partitions,
        "source_error_count": len(source_errors),
        "source_errors": source_errors[:100],
        "gamebook_identities_total": total,
        "exact_resolved": exact_resolved,
        "exact_zero_candidate": exact_zero,
        "exact_ambiguous": exact_ambiguous,
        "structural_resolved": structural_resolved,
        "structural_ambiguous": structural_ambiguous,
        "final_resolved": final_resolved,
        "final_unresolved": final_unresolved,
        "final_ambiguous": final_ambiguous,
        "final_identity_resolution_rate": resolution_rate,
        "authorized_structural_method_counts": dict(sorted(method_counts.items())),
        "season_source_and_rule_integrity_pass": integrity_pass,
        "season_has_identity_qualification_authority": False,
        "modern_player_team_game_identity_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "postgame_participation_used": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
        "structural_resolution_examples": structural_examples,
        "unresolved_examples": unresolved_examples,
        "ambiguity_examples": ambiguous_examples,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=SEASONS)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--identity-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, archive_root=args.archive_root, identity_root=args.identity_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"source_errors", "structural_resolution_examples", "unresolved_examples", "ambiguity_examples"}
            },
            indent=2,
            sort_keys=True,
        )
    )
    if result["season_source_and_rule_integrity_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

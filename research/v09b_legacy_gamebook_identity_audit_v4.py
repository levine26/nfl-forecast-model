from __future__ import annotations

"""Narrow structural Game Book -> GSIS identity audit for 2012-2016.

V1 exact identity remains primary. Only exact zero-candidate misses may consult the same
season/week/team/jersey candidate set, and only deterministic structural name methods
preregistered after the preserved V3 diagnostic are eligible. Weekly-roster status is never
selected. Per-season runs verify source/replay integrity; qualification authority belongs
only to the separate aggregate frozen gate.
"""

import argparse
import gzip
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as v1
from research import v09b_legacy_gamebook_identity_diagnostic_v2 as jersey_diag
from research import v09b_legacy_gamebook_identity_name_compat_v3 as compat_v3
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1
from research import v09b_legacy_gamebook_roster_universe_v2 as roster_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-IDENTITY-V4"
SEASONS = compat_v3.SEASONS
EXPECTED_TOTAL = {2012: 27108, 2013: 27122, 2014: 27119, 2015: 27112, 2016: 27111}
EXPECTED_V1_EXACT = {2012: 26795, 2013: 26824, 2014: 26855, 2015: 26860, 2016: 26406}
EXPECTED_V1_MISSES = dict(compat_v3.EXPECTED_MISSES)
EXPECTED_SOURCE_SHA256 = dict(compat_v3.EXPECTED_SOURCE_SHA256)
EXPECTED_SOURCE_ROWS = dict(compat_v3.EXPECTED_SOURCE_ROWS)
AUTHORIZED_METHODS = frozenset(
    {
        "given_full_prefix+surname_exact",
        "given_full_prefix+compound_component_prefix",
        "given_initial_only+compound_component_prefix",
        "given_initial_only+gamebook_surname_is_source_leading_components",
        "given_initial_only+source_surname_is_gamebook_leading_components",
    }
)


def structural_candidate_authorized(classification: dict[str, object]) -> bool:
    method = str(classification.get("compatibility_method") or "")
    if method not in AUTHORIZED_METHODS:
        return False
    if method == "given_initial_only+compound_component_prefix":
        return classification.get("strong_compatible") is True
    if method in {
        "given_full_prefix+surname_exact",
        "given_full_prefix+compound_component_prefix",
    }:
        return classification.get("strong_compatible") is True
    return classification.get("extended_compatible") is True


def _candidate_signature(
    *,
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]],
    week: int,
    team: str,
    gsis_id: str,
) -> tuple[str, str, str, str] | None:
    return signatures_by_gsis.get((week, team, gsis_id))


def audit_season(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 60.0,
    attempts: int = 3,
) -> dict[str, Any]:
    if season not in SEASONS:
        raise ValueError(f"season must be one of {list(SEASONS)}")

    upstream = roster_v2.audit_season_v2(
        season,
        archive_root=archive_root,
        timeout=min(timeout, 30.0),
        attempts=attempts,
    )
    upstream_passed = upstream.get("all_frozen_audit_gates_pass") is True

    raw_roster, source_url = v1.fetch_identity_source(season, timeout=timeout)
    source_sha = v1._sha256(raw_roster)
    frame = pl.read_parquet(io.BytesIO(raw_roster))
    exact_source = v1.build_identity_index(season=season, frame=frame)
    exact_index: dict[tuple[int, str, str, str], set[str]] = exact_source.pop("index")
    jersey_source = jersey_diag.build_same_week_team_jersey_index(season=season, frame=frame)
    jersey_index: dict[tuple[int, str, str], set[str]] = jersey_source.pop("index")
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]] = jersey_source.pop(
        "signatures_by_gsis"
    )

    source_accounting_consistent = bool(
        exact_source["source_identity_conflicts"] == jersey_source["source_identity_conflicts"]
        and exact_source["missing_gsis_rows"] == jersey_source["missing_gsis_rows"]
    )

    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    total = 0
    exact_resolved = 0
    exact_unresolved = 0
    exact_ambiguous = 0
    structural_resolved = 0
    structural_ambiguous = 0
    final_unresolved = 0
    method_counts: Counter[str] = Counter()
    unresolved_examples: list[dict[str, object]] = []
    ambiguity_examples: list[dict[str, object]] = []
    structural_examples: list[dict[str, object]] = []

    for source_row in manifest:
        raw_path = archive_root / str(source_row["raw_object_relpath"])
        with gzip.open(raw_path, "rb") as handle:
            text = raw_v1._extract_pdf_text(handle.read())
        week = int(source_row["week"])
        for side, team, side_name in (
            (0, v1.normalize_team(source_row["away_team"]), "visitor_left"),
            (1, v1.normalize_team(source_row["home_team"]), "home_right"),
        ):
            for jersey, display_name in sorted(v1._gamebook_identities_for_side(text, side=side)):
                total += 1
                jersey_key = v1.normalize_jersey(jersey)
                exact_key = (week, team, jersey_key, v1.compact_name(display_name))
                exact_candidates = sorted(exact_index.get(exact_key, set()))
                if len(exact_candidates) == 1:
                    exact_resolved += 1
                    continue
                if len(exact_candidates) > 1:
                    exact_ambiguous += 1
                    if len(ambiguity_examples) < 100:
                        ambiguity_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": jersey_key,
                                "display_name": display_name,
                                "stage": "v1_exact",
                                "candidate_gsis_ids": exact_candidates,
                            }
                        )
                    continue

                exact_unresolved += 1
                jersey_candidates = sorted(jersey_index.get((week, team, jersey_key), set()))
                authorized: list[dict[str, object]] = []
                for gsis in jersey_candidates:
                    signature = _candidate_signature(
                        signatures_by_gsis=signatures_by_gsis,
                        week=week,
                        team=team,
                        gsis_id=gsis,
                    )
                    if signature is None:
                        continue
                    _, first_name, football_name, last_name = signature
                    classification = compat_v3.classify_candidate(
                        display_name,
                        first_name=first_name,
                        football_name=football_name,
                        last_name=last_name,
                    )
                    if not structural_candidate_authorized(classification):
                        continue
                    method = str(classification["compatibility_method"])
                    authorized.append(
                        {
                            "gsis_id": gsis,
                            "method": method,
                            "first_name": first_name,
                            "football_name": football_name,
                            "last_name": last_name,
                        }
                    )

                if len(authorized) == 1:
                    structural_resolved += 1
                    method_counts[str(authorized[0]["method"])] += 1
                    if len(structural_examples) < 200:
                        structural_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": jersey_key,
                                "display_name": display_name,
                                "resolution": authorized[0],
                            }
                        )
                elif len(authorized) > 1:
                    structural_ambiguous += 1
                    if len(ambiguity_examples) < 100:
                        ambiguity_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": jersey_key,
                                "display_name": display_name,
                                "stage": "structural_fallback",
                                "authorized_candidates": authorized,
                            }
                        )
                else:
                    final_unresolved += 1
                    if len(unresolved_examples) < 200:
                        unresolved_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": jersey_key,
                                "display_name": display_name,
                                "same_week_team_jersey_candidate_count": len(jersey_candidates),
                            }
                        )

    if exact_resolved + exact_unresolved + exact_ambiguous != total:
        raise RuntimeError("V1 exact-resolution accounting mismatch")
    if structural_resolved + structural_ambiguous + final_unresolved != exact_unresolved:
        raise RuntimeError("structural fallback accounting mismatch")

    final_resolved = exact_resolved + structural_resolved
    final_ambiguous = exact_ambiguous + structural_ambiguous
    resolution_rate = final_resolved / total if total else 0.0
    replay_pass = bool(
        upstream_passed
        and source_accounting_consistent
        and source_sha == EXPECTED_SOURCE_SHA256[season]
        and exact_source["source_rows_selected"] == EXPECTED_SOURCE_ROWS[season]
        and exact_source["source_identity_conflicts"] == 0
        and exact_source["missing_gsis_rows"] == 0
        and total == EXPECTED_TOTAL[season]
        and exact_resolved == EXPECTED_V1_EXACT[season]
        and exact_unresolved == EXPECTED_V1_MISSES[season]
        and exact_ambiguous == 0
        and structural_ambiguous == 0
    )

    return {
        "audit_version": 4,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_roster_universe_v2_passed": upstream_passed,
        "weekly_identity_source_url": source_url,
        "weekly_identity_source_sha256": source_sha,
        "weekly_identity_source_sha256_matches_frozen": source_sha == EXPECTED_SOURCE_SHA256[season],
        "weekly_identity_source_allowed_fields_only": list(v1.ALLOWED_SOURCE_FIELDS),
        "weekly_roster_status_used": False,
        "source_rows_selected": exact_source["source_rows_selected"],
        "expected_source_rows_selected": EXPECTED_SOURCE_ROWS[season],
        "source_identity_conflicts": exact_source["source_identity_conflicts"],
        "missing_gsis_rows": exact_source["missing_gsis_rows"],
        "source_accounting_consistent": source_accounting_consistent,
        "gamebook_identities_total": total,
        "v1_exact_resolved": exact_resolved,
        "v1_exact_unresolved": exact_unresolved,
        "v1_exact_ambiguous": exact_ambiguous,
        "structural_fallback_resolved": structural_resolved,
        "structural_fallback_ambiguous": structural_ambiguous,
        "final_unresolved": final_unresolved,
        "final_resolved": final_resolved,
        "final_ambiguous": final_ambiguous,
        "final_identity_resolution_rate": resolution_rate,
        "authorized_structural_method_counts": dict(sorted(method_counts.items())),
        "source_and_rule_replay_pass": replay_pass,
        "season_has_identity_qualification_authority": False,
        "legacy_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "structural_resolution_examples": structural_examples,
        "unresolved_examples": unresolved_examples,
        "ambiguity_examples": ambiguity_examples,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=list(SEASONS))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = audit_season(
        args.season,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"structural_resolution_examples", "unresolved_examples", "ambiguity_examples"}
            },
            indent=2,
            sort_keys=True,
        )
    )
    if result["source_and_rule_replay_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Post-V1 diagnostic for unresolved legacy Game Book -> GSIS identities.

This module has no qualification authority. It preserves the exact-match V1 failure and
measures whether V1 misses have zero, one, or multiple GSIS candidates on the narrower
same-season/week/team/jersey source key. Weekly-roster status fields are never selected.
"""

import argparse
import gzip
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as v1
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1
from research import v09b_legacy_gamebook_roster_universe_v2 as roster_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-IDENTITY-DIAGNOSTIC-V2"


def build_same_week_team_jersey_index(*, season: int, frame: pl.DataFrame) -> dict[str, Any]:
    missing = sorted(set(v1.ALLOWED_SOURCE_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing identity fields: {missing}")

    source = frame.select(list(v1.ALLOWED_SOURCE_FIELDS)).filter(
        (pl.col("season").cast(pl.Int64, strict=False) == season)
        & (pl.col("game_type").cast(pl.Utf8, strict=False) == "REG")
    )

    grouped_signatures: dict[tuple[int, str, str], set[tuple[str, str, str, str]]] = defaultdict(set)
    missing_gsis_rows = 0
    for row in source.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = v1.normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            missing_gsis_rows += 1
            continue
        if not team:
            continue
        grouped_signatures[(week, team, gsis)].add(
            (
                v1.normalize_jersey(row.get("jersey_number")),
                str(row.get("first_name") or "").strip(),
                str(row.get("football_name") or "").strip(),
                str(row.get("last_name") or "").strip(),
            )
        )

    conflict_count = 0
    conflict_examples: list[dict[str, object]] = []
    jersey_index: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]] = {}
    for key, signatures in sorted(grouped_signatures.items()):
        week, team, gsis = key
        if len(signatures) != 1:
            conflict_count += 1
            if len(conflict_examples) < 100:
                conflict_examples.append(
                    {
                        "week": week,
                        "team": team,
                        "gsis_id": gsis,
                        "identity_signatures": [list(sig) for sig in sorted(signatures)],
                    }
                )
            continue
        signature = next(iter(signatures))
        signatures_by_gsis[key] = signature
        jersey = signature[0]
        if jersey:
            jersey_index[(week, team, jersey)].add(gsis)

    return {
        "index": jersey_index,
        "signatures_by_gsis": signatures_by_gsis,
        "source_rows_selected": source.height,
        "missing_gsis_rows": missing_gsis_rows,
        "source_identity_conflicts": conflict_count,
        "source_identity_conflict_examples": conflict_examples,
    }


def _candidate_signature(
    *,
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]],
    week: int,
    team: str,
    gsis_id: str,
) -> dict[str, str] | None:
    signature = signatures_by_gsis.get((week, team, gsis_id))
    if signature is None:
        return None
    jersey, first_name, football_name, last_name = signature
    return {
        "jersey_number": jersey,
        "first_name": first_name,
        "football_name": football_name,
        "last_name": last_name,
    }


def audit_season(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 60.0,
    attempts: int = 3,
) -> dict[str, Any]:
    upstream = roster_v2.audit_season_v2(
        season,
        archive_root=archive_root,
        timeout=min(timeout, 30.0),
        attempts=attempts,
    )
    upstream_passed = upstream.get("all_frozen_audit_gates_pass") is True

    raw_roster, source_url = v1.fetch_identity_source(season, timeout=timeout)
    frame = pl.read_parquet(io.BytesIO(raw_roster))
    exact_source = v1.build_identity_index(season=season, frame=frame)
    exact_index: dict[tuple[int, str, str, str], set[str]] = exact_source.pop("index")
    jersey_source = build_same_week_team_jersey_index(season=season, frame=frame)
    jersey_index: dict[tuple[int, str, str], set[str]] = jersey_source.pop("index")
    signatures_by_gsis: dict[tuple[int, str, str], tuple[str, str, str, str]] = jersey_source.pop(
        "signatures_by_gsis"
    )

    if exact_source["source_identity_conflicts"] != jersey_source["source_identity_conflicts"]:
        raise RuntimeError("identity-source conflict accounting mismatch")
    if exact_source["missing_gsis_rows"] != jersey_source["missing_gsis_rows"]:
        raise RuntimeError("missing-GSIS accounting mismatch")

    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    total = 0
    exact_resolved = 0
    exact_unresolved = 0
    exact_ambiguous = 0
    miss_unique_jersey = 0
    miss_zero_jersey = 0
    miss_multiple_jersey = 0
    examples: list[dict[str, object]] = []

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
                    continue

                exact_unresolved += 1
                jersey_candidates = sorted(jersey_index.get((week, team, jersey_key), set()))
                if len(jersey_candidates) == 1:
                    miss_unique_jersey += 1
                    bucket = "unique_same_week_team_jersey"
                elif len(jersey_candidates) == 0:
                    miss_zero_jersey += 1
                    bucket = "zero_same_week_team_jersey"
                else:
                    miss_multiple_jersey += 1
                    bucket = "multiple_same_week_team_jersey"

                if len(examples) < 250:
                    examples.append(
                        {
                            "season": season,
                            "week": week,
                            "game_id": str(source_row["game_id"]),
                            "team": team,
                            "side": side_name,
                            "jersey_number": jersey_key,
                            "gamebook_display_name": display_name,
                            "gamebook_compact_name": v1.compact_name(display_name),
                            "diagnostic_bucket": bucket,
                            "candidate_gsis_ids": jersey_candidates,
                            "candidate_identity_signatures": [
                                {
                                    "gsis_id": gsis,
                                    "identity": _candidate_signature(
                                        signatures_by_gsis=signatures_by_gsis,
                                        week=week,
                                        team=team,
                                        gsis_id=gsis,
                                    ),
                                }
                                for gsis in jersey_candidates
                            ],
                        }
                    )

    if exact_resolved + exact_unresolved + exact_ambiguous != total:
        raise RuntimeError("V1 exact-resolution accounting mismatch")
    if miss_unique_jersey + miss_zero_jersey + miss_multiple_jersey != exact_unresolved:
        raise RuntimeError("post-V1 diagnostic accounting mismatch")

    return {
        "diagnostic_version": 2,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_roster_universe_v2_passed": upstream_passed,
        "weekly_identity_source_url": source_url,
        "weekly_identity_source_sha256": v1._sha256(raw_roster),
        "weekly_identity_source_allowed_fields_only": list(v1.ALLOWED_SOURCE_FIELDS),
        "weekly_roster_status_used": False,
        "source_rows_selected": exact_source["source_rows_selected"],
        "missing_gsis_rows": exact_source["missing_gsis_rows"],
        "source_identity_conflicts": exact_source["source_identity_conflicts"],
        "gamebook_identities_total": total,
        "v1_exact_resolved": exact_resolved,
        "v1_exact_unresolved": exact_unresolved,
        "v1_exact_ambiguous": exact_ambiguous,
        "v1_exact_resolution_rate": exact_resolved / total if total else 0.0,
        "v1_miss_unique_same_week_team_jersey_candidate": miss_unique_jersey,
        "v1_miss_zero_same_week_team_jersey_candidates": miss_zero_jersey,
        "v1_miss_multiple_same_week_team_jersey_candidates": miss_multiple_jersey,
        "unique_jersey_candidate_share_of_v1_misses": (
            miss_unique_jersey / exact_unresolved if exact_unresolved else 0.0
        ),
        "candidate_identity_examples": examples,
        "diagnostic_has_qualification_authority": False,
        "same_week_team_jersey_fallback_authorized": False,
        "legacy_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=[2012, 2013, 2014, 2015, 2016])
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
            {k: v for k, v in result.items() if k != "candidate_identity_examples"},
            indent=2,
            sort_keys=True,
        )
    )
    # Diagnostic-only by contract: observed miss buckets never determine process exit status.


if __name__ == "__main__":
    main()

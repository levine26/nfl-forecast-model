from __future__ import annotations

"""Diagnostic-only name compatibility analysis for legacy Game Book identity misses.

This module does not resolve identities. It replays every V1 exact zero-candidate miss,
enumerates the bounded same-season/week/team/jersey candidate set, and reports explicit
structural name-compatibility evidence for each candidate. Weekly-roster status is never
selected. No compatibility tier has qualification authority.
"""

import argparse
import gzip
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as v1
from research import v09b_legacy_gamebook_identity_diagnostic_v2 as jersey_diag
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1
from research import v09b_legacy_gamebook_roster_universe_v2 as roster_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-IDENTITY-NAME-COMPAT-V3"
SEASONS = (2012, 2013, 2014, 2015, 2016)
EXPECTED_MISSES = {2012: 313, 2013: 298, 2014: 264, 2015: 252, 2016: 705}
EXPECTED_SOURCE_SHA256 = {
    2012: "32a218e187e553abdeacd107ae9c76c321e258809d18578f1b1267882f1c0b29",
    2013: "bb68c0e5dba854c4d0b7dda4331456df701c06a66160b96decdfdc1b71147663",
    2014: "51ae5047bb95297e039ba3d6560cee1ed16407f2e91897f6c9c79aafecdef397",
    2015: "61a57f4484a556d4cad1cf50030a8a8822a345eace783e013f8ba8ae2f721243",
    2016: "70d0ceab697860e946a2acdafcae48809015dcdaf06bd21d26777473cff7db8f",
}
EXPECTED_SOURCE_ROWS = {2012: 30005, 2013: 30437, 2014: 30492, 2015: 30636, 2016: 32944}


def _ascii_upper(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def compact(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", _ascii_upper(value))


def components(value: object) -> tuple[str, ...]:
    return tuple(part for part in re.findall(r"[A-Z0-9]+", _ascii_upper(value)) if part)


def parse_gamebook_display(display_name: object) -> dict[str, object]:
    raw = str(display_name or "").strip()
    if "." in raw:
        given_raw, surname_raw = raw.split(".", 1)
        given = compact(given_raw)
        surname = surname_raw.strip()
    else:
        given = ""
        surname = raw
    return {
        "raw": raw,
        "given_fragment": given,
        "surname_fragment": surname,
        "surname_compact": compact(surname),
        "surname_components": components(surname),
    }


def given_evidence(parsed: dict[str, object], *, first_name: object, football_name: object) -> str:
    given = str(parsed["given_fragment"])
    if not given:
        return "given_absent"
    source_givens = {compact(value) for value in (first_name, football_name) if compact(value)}
    if len(given) >= 2 and any(source.startswith(given) for source in source_givens):
        return "given_full_prefix"
    if any(source.startswith(given[:1]) for source in source_givens):
        return "given_initial_only"
    return "given_incompatible"


def surname_evidence(parsed: dict[str, object], *, last_name: object) -> str:
    gb_compact = str(parsed["surname_compact"])
    gb_parts = tuple(parsed["surname_components"])
    src_compact = compact(last_name)
    src_parts = components(last_name)
    if not gb_compact or not gb_parts:
        return "surname_absent"
    if gb_compact == src_compact:
        return "surname_exact"
    if len(gb_parts) == len(src_parts) and gb_parts and all(
        src.startswith(gb) for gb, src in zip(gb_parts, src_parts)
    ):
        return "compound_component_prefix"
    if len(src_parts) < len(gb_parts) and src_parts and gb_parts[: len(src_parts)] == src_parts:
        return "source_surname_is_gamebook_leading_components"
    if len(gb_parts) < len(src_parts) and gb_parts and src_parts[: len(gb_parts)] == gb_parts:
        return "gamebook_surname_is_source_leading_components"
    return "surname_incompatible"


def classify_candidate(
    display_name: object,
    *,
    first_name: object,
    football_name: object,
    last_name: object,
) -> dict[str, object]:
    parsed = parse_gamebook_display(display_name)
    given = given_evidence(parsed, first_name=first_name, football_name=football_name)
    surname = surname_evidence(parsed, last_name=last_name)
    surname_parts = tuple(parsed["surname_components"])
    nontrivial_surname_component = any(len(part) >= 4 for part in surname_parts)

    strong = bool(
        (given == "given_full_prefix" and surname in {"surname_exact", "compound_component_prefix"})
        or (
            given == "given_initial_only"
            and surname == "compound_component_prefix"
            and nontrivial_surname_component
        )
    )
    extended = bool(
        strong
        or (
            given == "given_full_prefix"
            and surname in {
                "source_surname_is_gamebook_leading_components",
                "gamebook_surname_is_source_leading_components",
            }
        )
        or (
            given == "given_initial_only"
            and surname in {
                "surname_exact",
                "source_surname_is_gamebook_leading_components",
                "gamebook_surname_is_source_leading_components",
            }
        )
        or (given == "given_absent" and surname == "surname_exact")
    )
    method = f"{given}+{surname}"
    insufficient_or_malformed = bool(
        surname == "surname_absent"
        or (given == "given_absent" and surname != "surname_exact")
        or (given == "given_incompatible")
    )
    return {
        "given_evidence": given,
        "surname_evidence": surname,
        "compatibility_method": method,
        "strong_compatible": strong,
        "extended_compatible": extended,
        "insufficient_or_malformed_gamebook_name": insufficient_or_malformed,
        "parsed_gamebook_name": parsed,
    }


def _distribution(counter: Counter[int]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


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

    if exact_source["source_identity_conflicts"] != jersey_source["source_identity_conflicts"]:
        raise RuntimeError("identity-source conflict accounting mismatch")
    if exact_source["missing_gsis_rows"] != jersey_source["missing_gsis_rows"]:
        raise RuntimeError("missing-GSIS accounting mismatch")
    if exact_source["source_rows_selected"] != jersey_source["source_rows_selected"]:
        raise RuntimeError("identity-source row accounting mismatch")

    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    v1_misses = 0
    zero_jersey = 0
    one_jersey = 0
    multiple_jersey = 0
    strong_cardinality: Counter[int] = Counter()
    extended_cardinality: Counter[int] = Counter()
    method_counts: Counter[str] = Counter()
    malformed_count = 0
    candidate_examples: list[dict[str, object]] = []
    malformed_examples: list[dict[str, object]] = []

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
                jersey_key = v1.normalize_jersey(jersey)
                exact_key = (week, team, jersey_key, v1.compact_name(display_name))
                exact_candidates = exact_index.get(exact_key, set())
                if exact_candidates:
                    continue
                v1_misses += 1
                candidate_ids = sorted(jersey_index.get((week, team, jersey_key), set()))
                if not candidate_ids:
                    zero_jersey += 1
                elif len(candidate_ids) == 1:
                    one_jersey += 1
                else:
                    multiple_jersey += 1

                candidate_rows: list[dict[str, object]] = []
                strong_count = 0
                extended_count = 0
                miss_has_malformed = False
                for gsis in candidate_ids:
                    signature = signatures_by_gsis.get((week, team, gsis))
                    if signature is None:
                        raise RuntimeError("same-jersey candidate missing frozen identity signature")
                    source_jersey, first_name, football_name, last_name = signature
                    classification = classify_candidate(
                        display_name,
                        first_name=first_name,
                        football_name=football_name,
                        last_name=last_name,
                    )
                    method_counts[str(classification["compatibility_method"])] += 1
                    if classification["strong_compatible"]:
                        strong_count += 1
                    if classification["extended_compatible"]:
                        extended_count += 1
                    if classification["insufficient_or_malformed_gamebook_name"]:
                        miss_has_malformed = True
                    candidate_rows.append(
                        {
                            "gsis_id": gsis,
                            "source_jersey_number": source_jersey,
                            "first_name": first_name,
                            "football_name": football_name,
                            "last_name": last_name,
                            **classification,
                        }
                    )

                strong_cardinality[strong_count] += 1
                extended_cardinality[extended_count] += 1
                parsed = parse_gamebook_display(display_name)
                if not candidate_ids and (
                    not parsed["surname_compact"] or not parsed["given_fragment"]
                ):
                    miss_has_malformed = True
                if miss_has_malformed:
                    malformed_count += 1
                    if len(malformed_examples) < 200:
                        malformed_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "jersey_number": jersey_key,
                                "gamebook_display_name": display_name,
                                "parsed_gamebook_name": parsed,
                                "candidate_count": len(candidate_ids),
                            }
                        )

                if len(candidate_examples) < 500:
                    candidate_examples.append(
                        {
                            "season": season,
                            "week": week,
                            "game_id": str(source_row["game_id"]),
                            "team": team,
                            "side": side_name,
                            "jersey_number": jersey_key,
                            "gamebook_display_name": display_name,
                            "same_week_team_jersey_candidate_count": len(candidate_ids),
                            "strong_compatible_candidate_count": strong_count,
                            "extended_compatible_candidate_count": extended_count,
                            "candidates": candidate_rows,
                        }
                    )

    integrity_pass = bool(
        upstream_passed
        and source_sha == EXPECTED_SOURCE_SHA256[season]
        and exact_source["source_rows_selected"] == EXPECTED_SOURCE_ROWS[season]
        and exact_source["source_identity_conflicts"] == 0
        and exact_source["missing_gsis_rows"] == 0
        and v1_misses == EXPECTED_MISSES[season]
        and zero_jersey + one_jersey + multiple_jersey == v1_misses
        and sum(strong_cardinality.values()) == v1_misses
        and sum(extended_cardinality.values()) == v1_misses
    )

    return {
        "diagnostic_version": 3,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_roster_universe_v2_passed": upstream_passed,
        "weekly_identity_source_url": source_url,
        "weekly_identity_source_sha256": source_sha,
        "weekly_identity_source_sha256_matches_pinned": source_sha == EXPECTED_SOURCE_SHA256[season],
        "weekly_identity_source_allowed_fields_only": list(v1.ALLOWED_SOURCE_FIELDS),
        "weekly_roster_status_used": False,
        "source_rows_selected": exact_source["source_rows_selected"],
        "source_rows_selected_matches_pinned": exact_source["source_rows_selected"] == EXPECTED_SOURCE_ROWS[season],
        "missing_gsis_rows": exact_source["missing_gsis_rows"],
        "source_identity_conflicts": exact_source["source_identity_conflicts"],
        "v1_exact_misses": v1_misses,
        "expected_v1_exact_misses": EXPECTED_MISSES[season],
        "v1_exact_misses_match_frozen_receipt": v1_misses == EXPECTED_MISSES[season],
        "same_week_team_jersey_zero_candidate_misses": zero_jersey,
        "same_week_team_jersey_one_candidate_misses": one_jersey,
        "same_week_team_jersey_multiple_candidate_misses": multiple_jersey,
        "strong_compatible_candidate_count_distribution": _distribution(strong_cardinality),
        "extended_compatible_candidate_count_distribution": _distribution(extended_cardinality),
        "compatibility_method_counts": dict(sorted(method_counts.items())),
        "malformed_or_insufficient_gamebook_name_miss_count": malformed_count,
        "candidate_level_examples": candidate_examples,
        "malformed_or_insufficient_gamebook_name_examples": malformed_examples,
        "source_integrity_and_population_replay_pass": integrity_pass,
        "diagnostic_has_qualification_authority": False,
        "name_compatibility_resolution_authorized": False,
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
    print(json.dumps({
        k: v for k, v in result.items()
        if k not in {"candidate_level_examples", "malformed_or_insufficient_gamebook_name_examples"}
    }, indent=2, sort_keys=True))
    if result["source_integrity_and_population_replay_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

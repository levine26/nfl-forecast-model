from __future__ import annotations

"""Bounded V2 GSIS identity audit for the 2012-2016 Game Book roster universe.

V1 exact-name matching remains primary. Only exact zero-candidate misses may use the
same-season/week/team/jersey key, and only when that key has exactly one GSIS ID.
Multiple or zero fallback candidates remain unresolved/ambiguous. Qualification is
aggregate across the frozen legacy identity population and never changes membership.
"""

import argparse
import gzip
import io
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as v1
from research import v09b_legacy_gamebook_identity_diagnostic_v2 as diagnostic
from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1
from research import v09b_legacy_gamebook_roster_universe_v2 as roster_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-IDENTITY-V2"
SEASONS = (2012, 2013, 2014, 2015, 2016)
MIN_AGGREGATE_RESOLUTION_RATE = 0.995
EXPECTED_POPULATION = {
    2012: 27108,
    2013: 27122,
    2014: 27119,
    2015: 27112,
    2016: 27111,
}
EXPECTED_V1_EXACT_RESOLVED = {
    2012: 26795,
    2013: 26824,
    2014: 26855,
    2015: 26860,
    2016: 26406,
}
EXPECTED_SOURCE_SHA256 = {
    2012: "32a218e187e553abdeacd107ae9c76c321e258809d18578f1b1267882f1c0b29",
    2013: "bb68c0e5dba854c4d0b7dda4331456df701c06a66160b96decdfdc1b71147663",
    2014: "51ae5047bb95297e039ba3d6560cee1ed16407f2e91897f6c9c79aafecdef397",
    2015: "61a57f4484a556d4cad1cf50030a8a8822a345eace783e013f8ba8ae2f721243",
    2016: "70d0ceab697860e946a2acdafcae48809015dcdaf06bd21d26777473cff7db8f",
}
EXPECTED_SOURCE_ROWS = {
    2012: 30005,
    2013: 30437,
    2014: 30492,
    2015: 30636,
    2016: 32944,
}


def resolve_candidates(
    exact_candidates: Sequence[str] | set[str],
    same_jersey_candidates: Sequence[str] | set[str],
) -> tuple[str, str | None]:
    """Apply the frozen V2 precedence without guessing through ambiguity."""
    exact = sorted(set(exact_candidates))
    jersey = sorted(set(same_jersey_candidates))
    if len(exact) == 1:
        return "exact_v1", exact[0]
    if len(exact) > 1:
        return "ambiguous_exact_v1", None
    if len(jersey) == 1:
        return "unique_same_week_team_jersey", jersey[0]
    if not jersey:
        return "unresolved_zero_same_week_team_jersey", None
    return "ambiguous_multiple_same_week_team_jersey", None


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
    jersey_source = diagnostic.build_same_week_team_jersey_index(season=season, frame=frame)
    jersey_index: dict[tuple[int, str, str], set[str]] = jersey_source.pop("index")
    jersey_source.pop("signatures_by_gsis")

    if exact_source["source_identity_conflicts"] != jersey_source["source_identity_conflicts"]:
        raise RuntimeError("identity-source conflict accounting mismatch")
    if exact_source["missing_gsis_rows"] != jersey_source["missing_gsis_rows"]:
        raise RuntimeError("missing-GSIS accounting mismatch")
    if exact_source["source_rows_selected"] != jersey_source["source_rows_selected"]:
        raise RuntimeError("identity-source row accounting mismatch")

    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    total = 0
    exact_resolved = 0
    fallback_resolved = 0
    ambiguous_exact = 0
    ambiguous_fallback = 0
    unresolved_zero = 0
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
                exact_candidates = exact_index.get(exact_key, set())
                jersey_candidates = jersey_index.get((week, team, jersey_key), set())
                method, gsis_id = resolve_candidates(exact_candidates, jersey_candidates)
                if method == "exact_v1":
                    exact_resolved += 1
                elif method == "unique_same_week_team_jersey":
                    fallback_resolved += 1
                elif method == "ambiguous_exact_v1":
                    ambiguous_exact += 1
                elif method == "ambiguous_multiple_same_week_team_jersey":
                    ambiguous_fallback += 1
                elif method == "unresolved_zero_same_week_team_jersey":
                    unresolved_zero += 1
                else:  # pragma: no cover - defensive invariant
                    raise RuntimeError(f"unknown resolution method: {method}")

                if method != "exact_v1" and len(examples) < 250:
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
                            "resolution_method": method,
                            "resolved_gsis_id": gsis_id,
                            "exact_candidate_gsis_ids": sorted(exact_candidates),
                            "same_week_team_jersey_candidate_gsis_ids": sorted(jersey_candidates),
                        }
                    )

    resolved_total = exact_resolved + fallback_resolved
    unresolved_or_ambiguous = ambiguous_exact + ambiguous_fallback + unresolved_zero
    if resolved_total + unresolved_or_ambiguous != total:
        raise RuntimeError("V2 identity accounting mismatch")

    population_matches = total == EXPECTED_POPULATION[season]
    v1_replay_matches = exact_resolved == EXPECTED_V1_EXACT_RESOLVED[season]
    source_sha_matches = source_sha == EXPECTED_SOURCE_SHA256[season]
    source_rows_match = exact_source["source_rows_selected"] == EXPECTED_SOURCE_ROWS[season]
    source_integrity_pass = bool(
        upstream_passed
        and population_matches
        and v1_replay_matches
        and source_sha_matches
        and source_rows_match
        and exact_source["source_identity_conflicts"] == 0
        and exact_source["missing_gsis_rows"] == 0
    )

    return {
        "audit_version": 2,
        "contract_id": CONTRACT_ID,
        "season": season,
        "season_has_qualification_authority": False,
        "upstream_roster_universe_v2_passed": upstream_passed,
        "weekly_identity_source_url": source_url,
        "weekly_identity_source_sha256": source_sha,
        "expected_weekly_identity_source_sha256": EXPECTED_SOURCE_SHA256[season],
        "weekly_identity_source_sha256_matches": source_sha_matches,
        "weekly_identity_source_allowed_fields_only": list(v1.ALLOWED_SOURCE_FIELDS),
        "weekly_roster_status_used": False,
        "source_rows_selected": exact_source["source_rows_selected"],
        "expected_source_rows_selected": EXPECTED_SOURCE_ROWS[season],
        "source_rows_selected_matches": source_rows_match,
        "missing_gsis_rows": exact_source["missing_gsis_rows"],
        "source_identity_conflicts": exact_source["source_identity_conflicts"],
        "gamebook_identities_total": total,
        "expected_gamebook_identities_total": EXPECTED_POPULATION[season],
        "population_matches_frozen_v1": population_matches,
        "exact_v1_resolved": exact_resolved,
        "expected_exact_v1_resolved": EXPECTED_V1_EXACT_RESOLVED[season],
        "exact_v1_replay_matches": v1_replay_matches,
        "unique_same_week_team_jersey_resolved": fallback_resolved,
        "ambiguous_exact_v1": ambiguous_exact,
        "ambiguous_multiple_same_week_team_jersey": ambiguous_fallback,
        "unresolved_zero_same_week_team_jersey": unresolved_zero,
        "resolved_total": resolved_total,
        "unresolved_or_ambiguous_total": unresolved_or_ambiguous,
        "season_resolution_rate": resolved_total / total if total else 0.0,
        "resolution_examples": examples,
        "source_integrity_gates_pass": source_integrity_pass,
        "legacy_player_team_game_identity_qualified": False,
        "unresolved_identities_silently_dropped": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def aggregate_receipts(receipts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_season: dict[int, dict[str, Any]] = {}
    for receipt in receipts:
        season = int(receipt["season"])
        if season in by_season:
            raise RuntimeError(f"duplicate season receipt: {season}")
        by_season[season] = receipt
    if set(by_season) != set(SEASONS):
        raise RuntimeError(f"aggregate requires exactly seasons {list(SEASONS)}; got {sorted(by_season)}")

    total = sum(int(by_season[s]["gamebook_identities_total"]) for s in SEASONS)
    exact = sum(int(by_season[s]["exact_v1_resolved"]) for s in SEASONS)
    fallback = sum(int(by_season[s]["unique_same_week_team_jersey_resolved"]) for s in SEASONS)
    ambiguous_exact = sum(int(by_season[s]["ambiguous_exact_v1"]) for s in SEASONS)
    ambiguous_fallback = sum(
        int(by_season[s]["ambiguous_multiple_same_week_team_jersey"]) for s in SEASONS
    )
    unresolved_zero = sum(
        int(by_season[s]["unresolved_zero_same_week_team_jersey"]) for s in SEASONS
    )
    resolved = exact + fallback
    unresolved_or_ambiguous = ambiguous_exact + ambiguous_fallback + unresolved_zero
    if resolved + unresolved_or_ambiguous != total:
        raise RuntimeError("aggregate identity accounting mismatch")

    resolution_rate = resolved / total if total else 0.0
    source_integrity_all = all(by_season[s]["source_integrity_gates_pass"] is True for s in SEASONS)
    denominator_matches = total == sum(EXPECTED_POPULATION.values()) == 135572
    no_status = all(by_season[s]["weekly_roster_status_used"] is False for s in SEASONS)
    no_outcomes = all(
        by_season[s]["game_outcomes_used"] == 0
        and by_season[s]["completed_2026_outcomes_used"] == 0
        for s in SEASONS
    )
    qualified = bool(
        source_integrity_all
        and denominator_matches
        and no_status
        and no_outcomes
        and resolution_rate >= MIN_AGGREGATE_RESOLUTION_RATE
    )

    return {
        "aggregate_version": 2,
        "contract_id": CONTRACT_ID,
        "seasons": list(SEASONS),
        "qualification_scope": "aggregate_2012_2016_player_team_game_identity_population",
        "source_integrity_all_seasons_pass": source_integrity_all,
        "legacy_identity_population": total,
        "legacy_identity_population_matches_frozen_denominator": denominator_matches,
        "exact_v1_resolved": exact,
        "unique_same_week_team_jersey_resolved": fallback,
        "resolved_total": resolved,
        "ambiguous_exact_v1": ambiguous_exact,
        "ambiguous_multiple_same_week_team_jersey": ambiguous_fallback,
        "unresolved_zero_same_week_team_jersey": unresolved_zero,
        "unresolved_or_ambiguous_total": unresolved_or_ambiguous,
        "unresolved_identities_silently_dropped": False,
        "aggregate_identity_resolution_rate": resolution_rate,
        "frozen_minimum_identity_resolution_rate": MIN_AGGREGATE_RESOLUTION_RATE,
        "aggregate_identity_resolution_gate_pass": resolution_rate >= MIN_AGGREGATE_RESOLUTION_RATE,
        "weekly_roster_status_used": False,
        "legacy_player_team_game_identity_qualified": qualified,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "season_receipts": {
            str(s): {
                "season_resolution_rate": by_season[s]["season_resolution_rate"],
                "resolved_total": by_season[s]["resolved_total"],
                "unresolved_or_ambiguous_total": by_season[s]["unresolved_or_ambiguous_total"],
                "source_integrity_gates_pass": by_season[s]["source_integrity_gates_pass"],
            }
            for s in SEASONS
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    season_parser = sub.add_parser("season")
    season_parser.add_argument("--season", type=int, required=True, choices=list(SEASONS))
    season_parser.add_argument("--archive-root", type=Path, required=True)
    season_parser.add_argument("--output", type=Path, required=True)
    season_parser.add_argument("--timeout", type=float, default=60.0)
    season_parser.add_argument("--attempts", type=int, default=3)

    aggregate_parser = sub.add_parser("aggregate")
    aggregate_parser.add_argument("--input-root", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "season":
        result = audit_season(
            args.season,
            archive_root=args.archive_root,
            timeout=args.timeout,
            attempts=args.attempts,
        )
        _write_json(args.output, result)
        print(json.dumps({k: v for k, v in result.items() if k != "resolution_examples"}, indent=2, sort_keys=True))
        if result["source_integrity_gates_pass"] is not True:
            raise SystemExit(1)
        return

    paths = sorted(args.input_root.glob("**/receipt.json"))
    if not paths:
        raise RuntimeError(f"no season receipts found under {args.input_root}")
    receipts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    result = aggregate_receipts(receipts)
    _write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["legacy_player_team_game_identity_qualified"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

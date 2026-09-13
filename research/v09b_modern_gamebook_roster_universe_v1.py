from __future__ import annotations

"""Archive-only modern Game Book roster-universe audit for 2017-2021.

No network retrieval and no player-identity resolution occur here. The parser consumes only
the exact aggregate-qualified modern V2 Game Book archive. Game-day membership authority is
the official Game Book partition: Lineups + Substitutions + Did Not Play form the active
candidate set; Not Active forms the inactive set. Era-specific roster counts are sanity
bounds only and never create or remove membership.
"""

import argparse
import gzip
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as legacy_v2

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-ROSTER-UNIVERSE-V1"
UPSTREAM_CONTRACT_ID = "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2"
UPSTREAM_QUALIFICATION_ID = "V09B-MODERN-GAMEBOOK-RAW-ARCHIVE-V2-QUALIFICATION"
EXPECTED_GAMES = {2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272}
EXPECTED_TEAM_PARTITIONS = {season: games * 2 for season, games in EXPECTED_GAMES.items()}
EXPECTED_TOTAL_GAMES = 1296
EXPECTED_TOTAL_TEAM_PARTITIONS = 2592


@dataclass(frozen=True)
class EraBounds:
    active_min: int
    active_max: int
    roster_max: int


@dataclass(frozen=True)
class ModernTeamPartition:
    team: str
    side: str
    lineup_count: int
    substitutions_count: int
    did_not_play_count: int
    not_active_count: int
    active_candidate_count: int
    roster_candidate_count: int
    repeated_within_section_occurrences: int
    repeated_within_section_identities: int
    cross_active_semantic_section_conflicts: int
    active_inactive_overlaps: int
    active_count_sanity_pass: bool
    roster_count_sanity_pass: bool


def era_bounds(season: int) -> EraBounds:
    if season in {2017, 2018, 2019}:
        return EraBounds(active_min=43, active_max=46, roster_max=53)
    if season in {2020, 2021}:
        return EraBounds(active_min=44, active_max=48, roster_max=55)
    raise ValueError(f"unsupported modern season: {season}")


def partition_from_sections(
    sections: dict[str, list[Any]],
    *,
    team: str,
    side: str,
    season: int,
) -> ModernTeamPartition:
    diag = legacy_v2.active_membership_diagnostics(sections)
    active = set(diag["active"])
    inactive = set(diag["inactive"])
    roster = active | inactive
    bounds = era_bounds(season)
    return ModernTeamPartition(
        team=team,
        side=side,
        lineup_count=len(sections["lineup"]),
        substitutions_count=len(sections["substitutions"]),
        did_not_play_count=len(sections["did_not_play"]),
        not_active_count=len(sections["not_active"]),
        active_candidate_count=len(active),
        roster_candidate_count=len(roster),
        repeated_within_section_occurrences=int(diag["repeated_within_section_occurrences"]),
        repeated_within_section_identities=int(diag["repeated_within_section_identities"]),
        cross_active_semantic_section_conflicts=int(diag["cross_semantic_section_conflicts"]),
        active_inactive_overlaps=int(diag["active_inactive_overlaps"]),
        active_count_sanity_pass=bounds.active_min <= len(active) <= bounds.active_max,
        roster_count_sanity_pass=bounds.active_min <= len(roster) <= bounds.roster_max,
    )


def parse_gamebook_roster_partitions(
    text: str,
    *,
    season: int,
    away_team: str,
    home_team: str,
) -> tuple[dict[str, int], ModernTeamPartition, ModernTeamPartition]:
    markers_left, sections_left = legacy_v2._section_entries(text, side=0)
    markers_right, sections_right = legacy_v2._section_entries(text, side=1)
    if markers_left != markers_right:
        raise ValueError("marker counts changed between paired team columns")
    away = partition_from_sections(
        sections_left,
        team=away_team,
        side="visitor_left",
        season=season,
    )
    home = partition_from_sections(
        sections_right,
        team=home_team,
        side="home_right",
        season=season,
    )
    return markers_left, away, home


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_upstream_archive(archive_root: Path, season: int) -> dict[str, bool]:
    aggregate_path = archive_root / "aggregate_qualification.json"
    season_receipt_path = archive_root / "receipts" / f"{season}.json"
    if not aggregate_path.exists() or not season_receipt_path.exists():
        return {"aggregate_qualified": False, "season_source_gate_pass": False, "upstream_passed": False}

    aggregate = _read_json(aggregate_path)
    receipt = _read_json(season_receipt_path)
    aggregate_qualified = bool(
        aggregate.get("qualification_id") == UPSTREAM_QUALIFICATION_ID
        and aggregate.get("canonical_games") == EXPECTED_TOTAL_GAMES
        and aggregate.get("qualified_source_rows") == EXPECTED_TOTAL_GAMES
        and aggregate.get("source_row_errors") == 0
        and aggregate.get("modern_raw_source_bytes_qualified") is True
        and aggregate.get("modern_gamebook_structure_qualified") is True
        and aggregate.get("modern_game_day_roster_universe_qualified") is False
        and aggregate.get("modern_player_team_game_identity_qualified") is False
        and aggregate.get("v09b_model_fit_authorized") is False
        and aggregate.get("completed_2026_outcomes_used") == 0
    )
    season_source_gate_pass = bool(
        receipt.get("contract_id") == UPSTREAM_CONTRACT_ID
        and receipt.get("season") == season
        and receipt.get("expected_games") == EXPECTED_GAMES[season]
        and receipt.get("canonical_games") == EXPECTED_GAMES[season]
        and receipt.get("season_frozen_source_gates_pass") is True
        and receipt.get("snapshot_coverage_rate") == 1.0
        and receipt.get("source_bytes_verified_rate") == 1.0
        and receipt.get("pdf_text_extraction_rate") == 1.0
        and receipt.get("not_active_structure_rate") == 1.0
        and receipt.get("did_not_play_structure_rate") == 1.0
        and receipt.get("source_row_errors") == 0
        and receipt.get("live_game_center_rediscovery_used") is False
        and receipt.get("page_order_tie_break_used") is False
        and receipt.get("completed_2026_outcomes_used") == 0
    )
    return {
        "aggregate_qualified": aggregate_qualified,
        "season_source_gate_pass": season_source_gate_pass,
        "upstream_passed": aggregate_qualified and season_source_gate_pass,
    }


def audit_season(season: int, *, archive_root: Path) -> dict[str, Any]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"season must be one of {sorted(EXPECTED_GAMES)}")

    upstream = validate_upstream_archive(archive_root, season)
    upstream_passed = upstream["upstream_passed"]
    manifest_path = archive_root / "manifests" / f"{season}.jsonl"
    if not manifest_path.exists():
        raise RuntimeError("qualified modern V2 archive manifest is missing")
    manifest = _read_manifest(manifest_path)
    expected = EXPECTED_GAMES[season]

    game_rows: list[dict[str, Any]] = []
    active_distribution: Counter[int] = Counter()
    inactive_distribution: Counter[int] = Counter()
    roster_distribution: Counter[int] = Counter()
    repeated_occurrences = 0
    repeated_identities = 0
    cross_conflicts = 0
    overlaps = 0
    active_sanity_failures = 0
    roster_sanity_failures = 0
    parsed_partitions = 0
    marker_exact_games = 0
    source_errors = 0

    for source_row in manifest:
        error: str | None = None
        marker_counts = {"lineups": 0, "substitutions": 0, "did_not_play": 0, "not_active": 0}
        partitions: list[ModernTeamPartition] = []
        try:
            if source_row.get("source_row_qualified") is not True:
                raise ValueError("upstream V2 source row is not qualified")
            raw_path = archive_root / str(source_row["raw_object_relpath"])
            with gzip.open(raw_path, "rb") as handle:
                raw_pdf = handle.read()
            text = raw_helpers._extract_pdf_text(raw_pdf)
            marker_counts, away, home = parse_gamebook_roster_partitions(
                text,
                season=season,
                away_team=str(source_row["away_team"]),
                home_team=str(source_row["home_team"]),
            )
            partitions = [away, home]
            parsed_partitions += 2
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            source_errors += 1

        marker_exact = all(marker_counts[key] == 1 for key in marker_counts)
        if marker_exact:
            marker_exact_games += 1
        for partition in partitions:
            active_distribution[partition.active_candidate_count] += 1
            inactive_distribution[partition.not_active_count] += 1
            roster_distribution[partition.roster_candidate_count] += 1
            repeated_occurrences += partition.repeated_within_section_occurrences
            repeated_identities += partition.repeated_within_section_identities
            cross_conflicts += partition.cross_active_semantic_section_conflicts
            overlaps += partition.active_inactive_overlaps
            active_sanity_failures += int(not partition.active_count_sanity_pass)
            roster_sanity_failures += int(not partition.roster_count_sanity_pass)

        qualified = bool(
            upstream_passed
            and error is None
            and marker_exact
            and len(partitions) == 2
            and all(p.cross_active_semantic_section_conflicts == 0 for p in partitions)
            and all(p.active_inactive_overlaps == 0 for p in partitions)
            and all(p.active_count_sanity_pass for p in partitions)
            and all(p.roster_count_sanity_pass for p in partitions)
        )
        game_rows.append(
            {
                "season": season,
                "week": int(source_row["week"]),
                "game_id": str(source_row["game_id"]),
                "away_team": str(source_row["away_team"]),
                "home_team": str(source_row["home_team"]),
                "marker_counts": marker_counts,
                "marker_counts_exact": marker_exact,
                "partitions": [asdict(p) for p in partitions],
                "game_partition_qualified": qualified,
                "error": error,
            }
        )

    qualified_games = sum(row["game_partition_qualified"] is True for row in game_rows)
    all_pass = bool(
        upstream_passed
        and len(manifest) == expected
        and len({str(row["game_id"]) for row in manifest}) == expected
        and parsed_partitions == EXPECTED_TEAM_PARTITIONS[season]
        and marker_exact_games == expected
        and qualified_games == expected
        and cross_conflicts == 0
        and overlaps == 0
        and active_sanity_failures == 0
        and roster_sanity_failures == 0
        and source_errors == 0
    )
    return {
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_raw_archive_aggregate_qualified": upstream["aggregate_qualified"],
        "upstream_season_source_gate_pass": upstream["season_source_gate_pass"],
        "upstream_raw_archive_qualified": upstream_passed,
        "canonical_games": len(manifest),
        "expected_games": expected,
        "team_partitions_parsed": parsed_partitions,
        "expected_team_partitions": EXPECTED_TEAM_PARTITIONS[season],
        "team_partition_parse_coverage_rate": parsed_partitions / EXPECTED_TEAM_PARTITIONS[season],
        "marker_exact_games": marker_exact_games,
        "marker_exact_game_rate": marker_exact_games / expected,
        "qualified_games": qualified_games,
        "canonical_game_coverage_rate": qualified_games / expected,
        "active_candidate_count_distribution": {str(k): active_distribution[k] for k in sorted(active_distribution)},
        "not_active_count_distribution": {str(k): inactive_distribution[k] for k in sorted(inactive_distribution)},
        "roster_candidate_count_distribution": {str(k): roster_distribution[k] for k in sorted(roster_distribution)},
        "same_section_repeat_occurrences": repeated_occurrences,
        "same_section_repeat_identities": repeated_identities,
        "cross_active_semantic_section_conflicts": cross_conflicts,
        "active_inactive_overlaps": overlaps,
        "active_count_sanity_failures": active_sanity_failures,
        "roster_count_sanity_failures": roster_sanity_failures,
        "source_errors": source_errors,
        "season_roster_universe_gate_pass": all_pass,
        "season_has_global_qualification_authority": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "game_rows": game_rows,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, archive_root=args.archive_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "game_rows"}, indent=2, sort_keys=True))
    if result["season_roster_universe_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

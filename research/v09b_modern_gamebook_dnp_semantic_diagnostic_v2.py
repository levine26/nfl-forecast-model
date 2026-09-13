from __future__ import annotations

"""Post-failure diagnostic for modern Game Book `Did Not Play` semantics.

The V1 roster audit is preserved as failed evidence. This module does not repair or relax
V1. It replays the exact qualified 2017-2021 Game Book archive and quantifies where adding
`Did Not Play` identities to Lineups + Substitutions creates a mathematical contradiction
with the already-frozen official era active-roster maxima. Results are diagnostic only and
cannot classify any individual DNP player, qualify a roster universe, or authorize fitting.
"""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as legacy_v2
from research import v09b_modern_gamebook_roster_universe_v1 as modern_v1

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-DNP-SEMANTIC-DIAGNOSTIC-V2"
EXPECTED_V1_FAILURE_KEYS = {
    "2018_16_DEN_OAK|OAK",
    "2020_11_PIT_JAX|JAX",
    "2020_13_NO_ATL|NO",
    "2020_15_JAX_BAL|JAX",
    "2021_10_KC_LV|KC",
    "2021_10_TB_WAS|TB",
    "2021_16_PIT_KC|PIT",
}


def _identity_set(entries: list[Any]) -> set[tuple[str, str]]:
    return {entry.parser_identity for entry in entries}


def _display_identities(values: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"jersey_number": jersey, "display_name": display_name}
        for jersey, display_name in sorted(values)
    ]


def diagnose_partition(
    sections: dict[str, list[Any]],
    *,
    season: int,
    game_id: str,
    team: str,
    side: str,
) -> dict[str, Any]:
    lineup = _identity_set(sections["lineup"])
    substitutions = _identity_set(sections["substitutions"])
    dnp = _identity_set(sections["did_not_play"])
    inactive = _identity_set(sections["not_active"])

    lineup_substitutions = lineup | substitutions
    dnp_only = dnp - lineup_substitutions
    v1_active = lineup_substitutions | dnp
    v1_roster = v1_active | inactive
    bounds = modern_v1.era_bounds(season)

    active_contradiction = bool(
        len(lineup_substitutions) <= bounds.active_max < len(v1_active)
    )
    minimum_dnp_non_active = (
        max(0, len(v1_active) - bounds.active_max)
        if len(lineup_substitutions) <= bounds.active_max
        else 0
    )
    total_roster_contradiction = len(v1_roster) > bounds.roster_max
    v1_active_sanity_pass = bounds.active_min <= len(v1_active) <= bounds.active_max
    v1_roster_sanity_pass = bounds.active_min <= len(v1_roster) <= bounds.roster_max

    return {
        "season": season,
        "game_id": game_id,
        "team": team,
        "side": side,
        "lineup_unique_count": len(lineup),
        "substitutions_unique_count": len(substitutions),
        "lineups_plus_substitutions_union_count": len(lineup_substitutions),
        "did_not_play_unique_count": len(dnp),
        "did_not_play_only_count": len(dnp_only),
        "did_not_play_only_identities": _display_identities(dnp_only),
        "not_active_unique_count": len(inactive),
        "v1_active_candidate_count": len(v1_active),
        "v1_roster_candidate_count": len(v1_roster),
        "era_active_min": bounds.active_min,
        "era_active_max": bounds.active_max,
        "era_roster_max": bounds.roster_max,
        "active_max_contradiction": active_contradiction,
        "minimum_dnp_non_active_required_by_active_max": minimum_dnp_non_active,
        "total_roster_max_contradiction": total_roster_contradiction,
        "v1_active_count_sanity_pass": v1_active_sanity_pass,
        "v1_roster_count_sanity_pass": v1_roster_sanity_pass,
        "v1_partition_failed": not (v1_active_sanity_pass and v1_roster_sanity_pass),
        "did_not_play_identity_classification_performed": False,
        "diagnostic_has_membership_authority": False,
    }


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def audit_season(season: int, *, archive_root: Path) -> dict[str, Any]:
    if season not in modern_v1.EXPECTED_GAMES:
        raise ValueError(f"unsupported season: {season}")

    upstream = modern_v1.validate_upstream_archive(archive_root, season)
    manifest = _read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    expected_games = modern_v1.EXPECTED_GAMES[season]
    partition_rows: list[dict[str, Any]] = []
    source_errors: list[dict[str, str]] = []
    exact_marker_games = 0

    for source_row in manifest:
        game_id = str(source_row["game_id"])
        try:
            raw_path = archive_root / str(source_row["raw_object_relpath"])
            with gzip.open(raw_path, "rb") as handle:
                text = raw_helpers._extract_pdf_text(handle.read())
            left_markers, left_sections = legacy_v2._section_entries(text, side=0)
            right_markers, right_sections = legacy_v2._section_entries(text, side=1)
            if left_markers != right_markers:
                raise ValueError("paired-column marker counts differ")
            if not all(left_markers.get(key) == 1 for key in ("lineups", "substitutions", "did_not_play", "not_active")):
                raise ValueError(f"marker count is not exact: {left_markers}")
            exact_marker_games += 1
            partition_rows.append(
                diagnose_partition(
                    left_sections,
                    season=season,
                    game_id=game_id,
                    team=str(source_row["away_team"]),
                    side="visitor_left",
                )
            )
            partition_rows.append(
                diagnose_partition(
                    right_sections,
                    season=season,
                    game_id=game_id,
                    team=str(source_row["home_team"]),
                    side="home_right",
                )
            )
        except Exception as exc:
            source_errors.append({"game_id": game_id, "error": f"{type(exc).__name__}: {exc}"})

    failed_keys = {
        f"{row['game_id']}|{row['team']}"
        for row in partition_rows
        if row["v1_partition_failed"] is True
    }
    expected_failed_keys = {
        key for key in EXPECTED_V1_FAILURE_KEYS if key.startswith(f"{season}_")
    }
    active_contradictions = [row for row in partition_rows if row["active_max_contradiction"] is True]
    total_roster_contradictions = [row for row in partition_rows if row["total_roster_max_contradiction"] is True]
    dnp_partitions = [row for row in partition_rows if row["did_not_play_only_count"] > 0]
    dnp_only_distribution = Counter(row["did_not_play_only_count"] for row in partition_rows)

    replay_ok = failed_keys == expected_failed_keys
    diagnostic_gate_pass = bool(
        upstream["upstream_passed"] is True
        and len(manifest) == expected_games
        and len({str(row["game_id"]) for row in manifest}) == expected_games
        and len(partition_rows) == modern_v1.EXPECTED_TEAM_PARTITIONS[season]
        and exact_marker_games == expected_games
        and not source_errors
        and replay_ok
    )

    return {
        "diagnostic_version": 2,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_raw_archive_qualified": upstream["upstream_passed"],
        "canonical_games": len(manifest),
        "expected_games": expected_games,
        "team_partitions_diagnosed": len(partition_rows),
        "expected_team_partitions": modern_v1.EXPECTED_TEAM_PARTITIONS[season],
        "exact_marker_games": exact_marker_games,
        "source_error_count": len(source_errors),
        "source_errors": source_errors,
        "v1_failed_partition_keys": sorted(failed_keys),
        "expected_v1_failed_partition_keys": sorted(expected_failed_keys),
        "v1_failure_replay_exact": replay_ok,
        "partitions_with_dnp_only_identities": len(dnp_partitions),
        "dnp_only_identity_count_total": sum(row["did_not_play_only_count"] for row in partition_rows),
        "dnp_only_count_distribution": {str(k): dnp_only_distribution[k] for k in sorted(dnp_only_distribution)},
        "active_max_contradiction_partitions": len(active_contradictions),
        "minimum_dnp_non_active_required_total": sum(
            row["minimum_dnp_non_active_required_by_active_max"] for row in active_contradictions
        ),
        "active_max_contradiction_rows": active_contradictions,
        "total_roster_max_contradiction_partitions": len(total_roster_contradictions),
        "total_roster_max_contradiction_rows": total_roster_contradictions,
        "noncontradictory_dnp_examples": dnp_partitions[:100],
        "diagnostic_gate_pass": diagnostic_gate_pass,
        "diagnostic_has_qualification_authority": False,
        "did_not_play_identity_classification_performed": False,
        "lineups_or_substitutions_used_as_training_positive_labels": False,
        "absence_from_not_active_used_as_positive_label": False,
        "weekly_roster_status_used": False,
        "weekly_roster_membership_used": False,
        "player_identity_crosswalk_used": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "partition_rows": partition_rows,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(modern_v1.EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = audit_season(args.season, archive_root=args.archive_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"partition_rows", "noncontradictory_dnp_examples", "active_max_contradiction_rows", "total_roster_max_contradiction_rows", "source_errors"}}, indent=2, sort_keys=True))
    if result["diagnostic_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

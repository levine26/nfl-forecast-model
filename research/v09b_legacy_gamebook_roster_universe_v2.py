from __future__ import annotations

"""Evidence-bounded V2 correction for the 2012-2016 direct Game Book roster universe.

V1 is preserved as a failed duplicate-gate specification. V2 changes only duplicate
occurrence semantics: repeated occurrences of the same player identity inside one semantic
section are diagnostic only, while membership in multiple distinct active semantic sections
still fails closed. Active membership remains the set union of Lineups, Substitutions and
Did Not Play; Not Active remains the negative partition.
"""

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as v1

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-ROSTER-UNIVERSE-V2"


def _section_entries(text: str, *, side: int) -> tuple[dict[str, int], dict[str, list[v1.PlayerEntry]]]:
    lines = text.splitlines()
    lineups_idx = [i for i, line in enumerate(lines) if v1.LINEUPS_LINE_RE.match(line)]
    subs_idx = [i for i, line in enumerate(lines) if v1.SUBSTITUTIONS_LINE_RE.match(line)]
    dnp_idx = [i for i, line in enumerate(lines) if v1.DID_NOT_PLAY_LINE_RE.match(line)]
    inactive_idx = [i for i, line in enumerate(lines) if v1.NOT_ACTIVE_LINE_RE.match(line)]
    field_goals_idx = [i for i, line in enumerate(lines) if v1.FIELD_GOALS_RE.search(line)]

    lineups = v1._one_index(lineups_idx, "Lineups")
    substitutions = v1._one_index(subs_idx, "Substitutions")
    did_not_play = v1._one_index(dnp_idx, "Did Not Play")
    not_active = v1._one_index(inactive_idx, "Not Active")
    if not field_goals_idx:
        raise ValueError("Field Goals boundary not found")
    field_goals = field_goals_idx[0]
    if not (lineups < substitutions < did_not_play < not_active < field_goals):
        raise ValueError("roster section ordering is invalid")

    offense_defense = [
        i
        for i in range(lineups + 1, substitutions)
        if "Offense" in lines[i] and "Defense" in lines[i]
    ]
    od = v1._one_index(offense_defense, "Offense/Defense")

    marker_counts = {
        "lineups": len(lineups_idx),
        "substitutions": len(subs_idx),
        "did_not_play": len(dnp_idx),
        "not_active": len(inactive_idx),
    }
    sections = {
        "lineup": v1._entries(v1._section_text(lines, od + 1, substitutions, side)),
        "substitutions": v1._entries(v1._section_text(lines, substitutions + 1, did_not_play, side)),
        "did_not_play": v1._entries(v1._section_text(lines, did_not_play + 1, not_active, side)),
        "not_active": v1._entries(v1._section_text(lines, not_active + 1, field_goals, side)),
    }
    return marker_counts, sections


def active_membership_diagnostics(
    sections: dict[str, list[v1.PlayerEntry]],
) -> dict[str, Any]:
    active_section_names = ("lineup", "substitutions", "did_not_play")
    section_counts: dict[str, Counter[tuple[str, str]]] = {}
    memberships: dict[tuple[str, str], set[str]] = defaultdict(set)

    for section_name in active_section_names:
        counts = Counter(entry.parser_identity for entry in sections[section_name])
        section_counts[section_name] = counts
        for identity in counts:
            memberships[identity].add(section_name)

    repeated_within_section_occurrences = sum(
        max(0, count - 1)
        for counts in section_counts.values()
        for count in counts.values()
    )
    repeated_within_section_identities = sum(
        1
        for counts in section_counts.values()
        for count in counts.values()
        if count > 1
    )
    cross_section = {
        identity: sorted(section_names)
        for identity, section_names in memberships.items()
        if len(section_names) > 1
    }
    active = set(memberships)
    inactive = {entry.parser_identity for entry in sections["not_active"]}
    return {
        "active": active,
        "inactive": inactive,
        "repeated_within_section_occurrences": repeated_within_section_occurrences,
        "repeated_within_section_identities": repeated_within_section_identities,
        "cross_semantic_section_identities": cross_section,
        "cross_semantic_section_conflicts": len(cross_section),
        "active_inactive_overlaps": len(active & inactive),
    }


def parse_gamebook_roster_partitions_v2(
    text: str,
    *,
    away_team: str,
    home_team: str,
) -> tuple[dict[str, int], v1.TeamPartition, v1.TeamPartition]:
    marker_counts: dict[str, int] | None = None
    partitions: list[v1.TeamPartition] = []
    for side, team, side_name in ((0, away_team, "visitor_left"), (1, home_team, "home_right")):
        side_markers, sections = _section_entries(text, side=side)
        if marker_counts is None:
            marker_counts = side_markers
        elif marker_counts != side_markers:
            raise ValueError("marker counts changed between team partitions")

        diag = active_membership_diagnostics(sections)
        active = diag["active"]
        inactive = diag["inactive"]
        roster = active | inactive
        partitions.append(
            v1.TeamPartition(
                team=team,
                side=side_name,
                lineup_count=len(sections["lineup"]),
                substitutions_count=len(sections["substitutions"]),
                did_not_play_count=len(sections["did_not_play"]),
                not_active_count=len(sections["not_active"]),
                active_candidate_count=len(active),
                roster_candidate_count=len(roster),
                duplicate_active_memberships=int(diag["cross_semantic_section_conflicts"]),
                active_inactive_overlaps=int(diag["active_inactive_overlaps"]),
                active_count_sanity_pass=len(active) in v1.ACCEPTED_ACTIVE_COUNTS,
                roster_count_sanity_pass=(v1.TOTAL_ROSTER_COUNT_MIN <= len(roster) <= v1.TOTAL_ROSTER_COUNT_MAX),
            )
        )
    assert marker_counts is not None
    return marker_counts, partitions[0], partitions[1]


def _diagnose_archive(season: int, *, archive_root: Path) -> dict[str, Any]:
    manifest = v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    repeated_occurrences = 0
    repeated_identities = 0
    cross_conflicts = 0
    cross_examples: list[dict[str, object]] = []
    repeated_examples: list[dict[str, object]] = []

    for source_row in manifest:
        raw_path = archive_root / str(source_row["raw_object_relpath"])
        with gzip.open(raw_path, "rb") as handle:
            text = raw_v1._extract_pdf_text(handle.read())
        for side, team, side_name in (
            (0, str(source_row["away_team"]), "visitor_left"),
            (1, str(source_row["home_team"]), "home_right"),
        ):
            _, sections = _section_entries(text, side=side)
            diag = active_membership_diagnostics(sections)
            repeated_occurrences += int(diag["repeated_within_section_occurrences"])
            repeated_identities += int(diag["repeated_within_section_identities"])
            cross_conflicts += int(diag["cross_semantic_section_conflicts"])

            if diag["repeated_within_section_occurrences"] and len(repeated_examples) < 25:
                for section_name in ("lineup", "substitutions", "did_not_play"):
                    counts = Counter(entry.parser_identity for entry in sections[section_name])
                    for (jersey, name), count in sorted(counts.items()):
                        if count > 1 and len(repeated_examples) < 25:
                            repeated_examples.append(
                                {
                                    "season": season,
                                    "week": int(source_row["week"]),
                                    "game_id": str(source_row["game_id"]),
                                    "team": team,
                                    "side": side_name,
                                    "section": section_name,
                                    "jersey_number": jersey,
                                    "display_name": name,
                                    "occurrences": count,
                                }
                            )
            if diag["cross_semantic_section_conflicts"] and len(cross_examples) < 25:
                for (jersey, name), section_names in sorted(diag["cross_semantic_section_identities"].items()):
                    if len(cross_examples) < 25:
                        cross_examples.append(
                            {
                                "season": season,
                                "week": int(source_row["week"]),
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": jersey,
                                "display_name": name,
                                "active_sections": section_names,
                            }
                        )

    return {
        "repeated_within_section_occurrences": repeated_occurrences,
        "repeated_within_section_identities": repeated_identities,
        "cross_semantic_active_section_conflicts": cross_conflicts,
        "repeated_within_section_examples": repeated_examples,
        "cross_semantic_section_examples": cross_examples,
    }


def audit_season_v2(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    original_parser = v1.parse_gamebook_roster_partitions
    v1.parse_gamebook_roster_partitions = parse_gamebook_roster_partitions_v2
    try:
        result = v1.audit_season(
            season,
            archive_root=archive_root,
            timeout=timeout,
            attempts=attempts,
        )
    finally:
        v1.parse_gamebook_roster_partitions = original_parser

    result = dict(result)
    diagnostics = _diagnose_archive(season, archive_root=archive_root)
    result["audit_version"] = 2
    result["contract_id"] = CONTRACT_ID
    result["v1_failure_preserved"] = True
    result["duplicate_gate_correction_scope"] = "within-section occurrence versus cross-semantic-section membership"
    result["coverage_thresholds_relaxed_from_v1"] = False
    result["label_semantics_changed_from_v1"] = False
    result["cross_semantic_active_section_conflicts"] = result["duplicate_active_section_memberships"]
    result["duplicate_semantics_diagnostics"] = diagnostics
    result["v09b_model_fit_authorized"] = False
    result["model_fit_performed"] = False
    result["game_outcomes_used"] = 0
    result["completed_2026_outcomes_used"] = 0
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(v1.EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = audit_season_v2(
        args.season,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "error_rows"}, indent=2, sort_keys=True))
    if result["all_frozen_audit_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

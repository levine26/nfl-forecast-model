from __future__ import annotations

"""Diagnostic-only probe for duplicated active-section membership in the legacy Game Book roster parser.

The V1 roster-universe audit is preserved unchanged. This probe reuses the same first-party
Game Book bytes and parser boundaries, then emits the exact game/team/player identity and
active sections whenever one parsed (jersey, display_name) key appears in more than one of
Lineups, Substitutions, or Did Not Play. It never changes membership, deduplicates rows,
constructs labels, uses outcomes, or qualifies the source.
"""

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_raw_archive_v2 as raw_v2
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1


def _section_entries(text: str, *, side: int) -> dict[str, list[roster_v1.PlayerEntry]]:
    lines = text.splitlines()
    lineups = roster_v1._one_index(
        [i for i, line in enumerate(lines) if roster_v1.LINEUPS_LINE_RE.match(line)],
        "Lineups",
    )
    substitutions = roster_v1._one_index(
        [i for i, line in enumerate(lines) if roster_v1.SUBSTITUTIONS_LINE_RE.match(line)],
        "Substitutions",
    )
    did_not_play = roster_v1._one_index(
        [i for i, line in enumerate(lines) if roster_v1.DID_NOT_PLAY_LINE_RE.match(line)],
        "Did Not Play",
    )
    not_active = roster_v1._one_index(
        [i for i, line in enumerate(lines) if roster_v1.NOT_ACTIVE_LINE_RE.match(line)],
        "Not Active",
    )
    field_goals_candidates = [
        i for i, line in enumerate(lines) if roster_v1.FIELD_GOALS_RE.search(line)
    ]
    if not field_goals_candidates:
        raise ValueError("Field Goals boundary not found")
    field_goals = field_goals_candidates[0]
    offense_defense = roster_v1._one_index(
        [
            i
            for i in range(lineups + 1, substitutions)
            if "Offense" in lines[i] and "Defense" in lines[i]
        ],
        "Offense/Defense",
    )
    return {
        "lineup": roster_v1._entries(
            roster_v1._section_text(lines, offense_defense + 1, substitutions, side)
        ),
        "substitutions": roster_v1._entries(
            roster_v1._section_text(lines, substitutions + 1, did_not_play, side)
        ),
        "did_not_play": roster_v1._entries(
            roster_v1._section_text(lines, did_not_play + 1, not_active, side)
        ),
        "not_active": roster_v1._entries(
            roster_v1._section_text(lines, not_active + 1, field_goals, side)
        ),
    }


def probe_season(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    source_receipt = raw_v2.archive_season_v2(
        season,
        archive_root=archive_root,
        timeout=timeout,
        attempts=attempts,
    )
    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    duplicate_records: list[dict[str, object]] = []
    parsed_games = 0

    for source_row in manifest:
        raw_path = archive_root / str(source_row["raw_object_relpath"])
        with gzip.open(raw_path, "rb") as handle:
            text = raw_v1._extract_pdf_text(handle.read())
        parsed_games += 1
        for side, team, side_name in (
            (0, str(source_row["away_team"]), "visitor_left"),
            (1, str(source_row["home_team"]), "home_right"),
        ):
            sections = _section_entries(text, side=side)
            memberships: dict[tuple[str, str], list[str]] = defaultdict(list)
            entries_by_identity: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
            for section_name in ("lineup", "substitutions", "did_not_play"):
                for entry in sections[section_name]:
                    memberships[entry.parser_identity].append(section_name)
                    entries_by_identity[entry.parser_identity][section_name] = {
                        "position": entry.position,
                        "jersey_number": entry.jersey_number,
                        "display_name": entry.display_name,
                    }
            inactive = {entry.parser_identity for entry in sections["not_active"]}
            for identity, section_names in memberships.items():
                if len(section_names) <= 1:
                    continue
                duplicate_records.append(
                    {
                        "season": season,
                        "week": int(source_row["week"]),
                        "game_id": str(source_row["game_id"]),
                        "away_team": str(source_row["away_team"]),
                        "home_team": str(source_row["home_team"]),
                        "team": team,
                        "side": side_name,
                        "jersey_number": identity[0],
                        "display_name": identity[1],
                        "active_sections": section_names,
                        "section_entries": entries_by_identity[identity],
                        "also_in_not_active": identity in inactive,
                    }
                )

    return {
        "probe_version": 1,
        "season": season,
        "source_v2_all_frozen_gates_pass": source_receipt.get("all_frozen_gates_pass") is True,
        "canonical_games_parsed": parsed_games,
        "duplicate_active_identity_records": len(duplicate_records),
        "records": duplicate_records,
        "membership_modified": False,
        "deduplication_performed": False,
        "qualification_authority": False,
        "player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2012, choices=[2012])
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = probe_season(
        args.season,
        archive_root=args.archive_root,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

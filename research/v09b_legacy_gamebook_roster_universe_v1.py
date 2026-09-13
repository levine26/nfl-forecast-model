from __future__ import annotations

"""Audit the official Game Book as the direct 2012-2016 game-day roster universe.

This parser never uses weekly roster status, snaps, play-by-play, starters from a later
source, game outcomes, or 2026 outcomes. It operates only on the official Game Summary
layout after the V2 raw-source gate passes.
"""

import argparse
import gzip
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_raw_archive_v2 as raw_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-ROSTER-UNIVERSE-V1"
COLUMN_SPLIT = 80
EXPECTED_GAMES = {2012: 256, 2013: 256, 2014: 256, 2015: 256, 2016: 256}
EXPECTED_TEAM_PARTITIONS = 512
ACCEPTED_ACTIVE_COUNTS = {45, 46}
TOTAL_ROSTER_COUNT_MIN = 45
TOTAL_ROSTER_COUNT_MAX = 53

LINEUPS_LINE_RE = re.compile(r"^\s*Lineups\s*$", re.I)
SUBSTITUTIONS_LINE_RE = re.compile(r"^\s*Substitutions\s+Substitutions\s*$", re.I)
DID_NOT_PLAY_LINE_RE = re.compile(r"^\s*Did\s+Not\s+Play\b", re.I)
NOT_ACTIVE_LINE_RE = re.compile(r"^\s*Not\s+Active\b", re.I)
FIELD_GOALS_RE = re.compile(r"Field\s+Goals", re.I)
ENTRY_RE = re.compile(
    r"(?:(?<=^)|(?<=\s))([A-Z][A-Z/.-]{0,7})\s+(\d{1,2})\s+([A-Za-z][A-Za-z0-9.'’\-]+)"
)


@dataclass(frozen=True)
class PlayerEntry:
    position: str
    jersey_number: str
    display_name: str

    @property
    def parser_identity(self) -> tuple[str, str]:
        return (self.jersey_number, self.display_name)


@dataclass(frozen=True)
class TeamPartition:
    team: str
    side: str
    lineup_count: int
    substitutions_count: int
    did_not_play_count: int
    not_active_count: int
    active_candidate_count: int
    roster_candidate_count: int
    duplicate_active_memberships: int
    active_inactive_overlaps: int
    active_count_sanity_pass: bool
    roster_count_sanity_pass: bool


@dataclass(frozen=True)
class GamePartitionRow:
    season: int
    week: int
    game_id: str
    away_team: str
    home_team: str
    source_v2_gate_passed: bool
    marker_lineups_count: int
    marker_substitutions_count: int
    marker_did_not_play_count: int
    marker_not_active_count: int
    marker_counts_exact: bool
    away: TeamPartition | None
    home: TeamPartition | None
    game_partition_qualified: bool
    error: str | None


def _section_text(lines: list[str], start: int, end: int, side: int) -> str:
    chunks: list[str] = []
    for line in lines[start:end]:
        chunk = line[:COLUMN_SPLIT] if side == 0 else line[COLUMN_SPLIT:]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
    return " ".join(chunks)


def _entries(text: str) -> list[PlayerEntry]:
    return [PlayerEntry(position=p, jersey_number=j, display_name=n) for p, j, n in ENTRY_RE.findall(text)]


def _one_index(indices: list[int], label: str) -> int:
    if len(indices) != 1:
        raise ValueError(f"expected exactly one {label} marker line, found {len(indices)}")
    return indices[0]


def parse_gamebook_roster_partitions(
    text: str,
    *,
    away_team: str,
    home_team: str,
) -> tuple[dict[str, int], TeamPartition, TeamPartition]:
    lines = text.splitlines()
    lineups_idx = [i for i, line in enumerate(lines) if LINEUPS_LINE_RE.match(line)]
    subs_idx = [i for i, line in enumerate(lines) if SUBSTITUTIONS_LINE_RE.match(line)]
    dnp_idx = [i for i, line in enumerate(lines) if DID_NOT_PLAY_LINE_RE.match(line)]
    inactive_idx = [i for i, line in enumerate(lines) if NOT_ACTIVE_LINE_RE.match(line)]
    field_goals_idx = [i for i, line in enumerate(lines) if FIELD_GOALS_RE.search(line)]

    lineups = _one_index(lineups_idx, "Lineups")
    substitutions = _one_index(subs_idx, "Substitutions")
    did_not_play = _one_index(dnp_idx, "Did Not Play")
    not_active = _one_index(inactive_idx, "Not Active")
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
    od = _one_index(offense_defense, "Offense/Defense")

    marker_counts = {
        "lineups": len(lineups_idx),
        "substitutions": len(subs_idx),
        "did_not_play": len(dnp_idx),
        "not_active": len(inactive_idx),
    }

    partitions: list[TeamPartition] = []
    for side, team, side_name in ((0, away_team, "visitor_left"), (1, home_team, "home_right")):
        sections = {
            "lineup": _entries(_section_text(lines, od + 1, substitutions, side)),
            "substitutions": _entries(_section_text(lines, substitutions + 1, did_not_play, side)),
            "did_not_play": _entries(_section_text(lines, did_not_play + 1, not_active, side)),
            "not_active": _entries(_section_text(lines, not_active + 1, field_goals, side)),
        }
        active_occurrences: Counter[tuple[str, str]] = Counter()
        for section_name in ("lineup", "substitutions", "did_not_play"):
            active_occurrences.update(entry.parser_identity for entry in sections[section_name])
        active = set(active_occurrences)
        inactive = {entry.parser_identity for entry in sections["not_active"]}
        duplicate_active = sum(count - 1 for count in active_occurrences.values() if count > 1)
        overlaps = len(active & inactive)
        roster = active | inactive
        partitions.append(
            TeamPartition(
                team=team,
                side=side_name,
                lineup_count=len(sections["lineup"]),
                substitutions_count=len(sections["substitutions"]),
                did_not_play_count=len(sections["did_not_play"]),
                not_active_count=len(sections["not_active"]),
                active_candidate_count=len(active),
                roster_candidate_count=len(roster),
                duplicate_active_memberships=duplicate_active,
                active_inactive_overlaps=overlaps,
                active_count_sanity_pass=len(active) in ACCEPTED_ACTIVE_COUNTS,
                roster_count_sanity_pass=(TOTAL_ROSTER_COUNT_MIN <= len(roster) <= TOTAL_ROSTER_COUNT_MAX),
            )
        )
    return marker_counts, partitions[0], partitions[1]


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def audit_season(
    season: int,
    *,
    archive_root: Path,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"unsupported season: {season}")

    source_receipt = raw_v2.archive_season_v2(
        season,
        archive_root=archive_root,
        timeout=timeout,
        attempts=attempts,
    )
    source_passed = source_receipt.get("all_frozen_gates_pass") is True
    manifest = _read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    rows: list[GamePartitionRow] = []

    for source_row in manifest:
        error: str | None = None
        marker_counts = {"lineups": 0, "substitutions": 0, "did_not_play": 0, "not_active": 0}
        away: TeamPartition | None = None
        home: TeamPartition | None = None
        try:
            raw_path = archive_root / str(source_row["raw_object_relpath"])
            with gzip.open(raw_path, "rb") as handle:
                raw_pdf = handle.read()
            text = raw_v1._extract_pdf_text(raw_pdf)
            marker_counts, away, home = parse_gamebook_roster_partitions(
                text,
                away_team=str(source_row["away_team"]),
                home_team=str(source_row["home_team"]),
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        marker_exact = all(marker_counts[key] == 1 for key in marker_counts)
        partitions = [partition for partition in (away, home) if partition is not None]
        qualified = bool(
            source_passed
            and error is None
            and marker_exact
            and len(partitions) == 2
            and all(partition.duplicate_active_memberships == 0 for partition in partitions)
            and all(partition.active_inactive_overlaps == 0 for partition in partitions)
            and all(partition.active_count_sanity_pass for partition in partitions)
            and all(partition.roster_count_sanity_pass for partition in partitions)
        )
        rows.append(
            GamePartitionRow(
                season=season,
                week=int(source_row["week"]),
                game_id=str(source_row["game_id"]),
                away_team=str(source_row["away_team"]),
                home_team=str(source_row["home_team"]),
                source_v2_gate_passed=source_passed,
                marker_lineups_count=marker_counts["lineups"],
                marker_substitutions_count=marker_counts["substitutions"],
                marker_did_not_play_count=marker_counts["did_not_play"],
                marker_not_active_count=marker_counts["not_active"],
                marker_counts_exact=marker_exact,
                away=away,
                home=home,
                game_partition_qualified=qualified,
                error=error,
            )
        )

    partitions = [p for row in rows for p in (row.away, row.home) if p is not None]
    active_count_distribution = dict(sorted(Counter(p.active_candidate_count for p in partitions).items()))
    inactive_count_distribution = dict(sorted(Counter(p.not_active_count for p in partitions).items()))
    total_count_distribution = dict(sorted(Counter(p.roster_candidate_count for p in partitions).items()))
    game_errors = [row for row in rows if row.error is not None]
    qualified_games = sum(row.game_partition_qualified for row in rows)
    marker_exact_games = sum(row.marker_counts_exact for row in rows)
    duplicate_active = sum(p.duplicate_active_memberships for p in partitions)
    overlaps = sum(p.active_inactive_overlaps for p in partitions)
    active_sanity_failures = sum(not p.active_count_sanity_pass for p in partitions)
    roster_sanity_failures = sum(not p.roster_count_sanity_pass for p in partitions)

    all_pass = bool(
        source_passed
        and len(rows) == EXPECTED_GAMES[season]
        and qualified_games == EXPECTED_GAMES[season]
        and len(partitions) == EXPECTED_TEAM_PARTITIONS
        and marker_exact_games == EXPECTED_GAMES[season]
        and duplicate_active == 0
        and overlaps == 0
        and active_sanity_failures == 0
        and roster_sanity_failures == 0
        and not game_errors
    )
    return {
        "audit_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "canonical_games": len(rows),
        "expected_games": EXPECTED_GAMES[season],
        "source_v2_all_frozen_gates_pass": source_passed,
        "qualified_game_partitions": qualified_games,
        "canonical_game_parse_coverage_rate": qualified_games / EXPECTED_GAMES[season],
        "team_partitions_parsed": len(partitions),
        "expected_team_partitions": EXPECTED_TEAM_PARTITIONS,
        "team_partition_parse_coverage_rate": len(partitions) / EXPECTED_TEAM_PARTITIONS,
        "marker_exact_games": marker_exact_games,
        "required_marker_exact_count_rate": marker_exact_games / EXPECTED_GAMES[season],
        "duplicate_active_section_memberships": duplicate_active,
        "active_inactive_overlaps": overlaps,
        "active_count_sanity_failures": active_sanity_failures,
        "total_roster_count_sanity_failures": roster_sanity_failures,
        "active_candidate_count_distribution": {str(k): v for k, v in active_count_distribution.items()},
        "not_active_count_distribution": {str(k): v for k, v in inactive_count_distribution.items()},
        "roster_candidate_count_distribution": {str(k): v for k, v in total_count_distribution.items()},
        "source_row_errors": len(game_errors),
        "all_frozen_audit_gates_pass": all_pass,
        "legacy_gamebook_roster_partition_qualified": all_pass,
        "legacy_game_day_roster_universe_qualified": all_pass,
        "player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "weekly_roster_status_used_to_define_membership": False,
        "postgame_participation_used_to_define_membership": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "error_rows": [asdict(row) for row in game_errors],
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
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
    print(json.dumps({k: v for k, v in result.items() if k != "error_rows"}, indent=2, sort_keys=True))
    if result["all_frozen_audit_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Exact-match GSIS identity audit for the 2012-2016 official Game Book roster universe.

Membership authority remains the official Game Book. The nflverse weekly-roster parquet is
used only as an identity crosswalk. Generic roster status fields are never selected or read.
No fuzzy, adjacent-week, season-wide or manual fallback is allowed in V1.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl
import requests

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_legacy_gamebook_roster_universe_v1 as roster_v1
from research import v09b_legacy_gamebook_roster_universe_v2 as roster_v2

CONTRACT_ID = "V09B-LEGACY-GAMEBOOK-IDENTITY-V1"
RELEASE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/"
    "roster_weekly_{season}.parquet"
)
ALLOWED_SOURCE_FIELDS = (
    "season",
    "game_type",
    "week",
    "team",
    "gsis_id",
    "jersey_number",
    "first_name",
    "football_name",
    "last_name",
)
TEAM_ALIASES = {
    "JAC": "JAX",
    "SD": "LAC",
    "STL": "LA",
    "LAR": "LA",
    "OAK": "LV",
    "WSH": "WAS",
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "SL": "LA",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_team(value: object) -> str:
    team = str(value or "").strip().upper()
    return TEAM_ALIASES.get(team, team)


def normalize_jersey(value: object) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def compact_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def roster_display_keys(*, first_name: object, football_name: object, last_name: object) -> set[str]:
    last = str(last_name or "").strip()
    keys: set[str] = set()
    for given in (football_name, first_name):
        given_text = str(given or "").strip()
        if given_text and last:
            key = compact_name(given_text[0] + last)
            if key:
                keys.add(key)
    return keys


def fetch_identity_source(season: int, *, timeout: float = 60.0) -> tuple[bytes, str]:
    url = RELEASE_URL.format(season=season)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "LevLine-V09B-research/1.0"},
    )
    response.raise_for_status()
    raw = response.content
    if len(raw) < 8 or raw[:4] != b"PAR1" or raw[-4:] != b"PAR1":
        raise RuntimeError(f"weekly-roster source is not valid parquet for {season}")
    return raw, response.url


def build_identity_index(*, season: int, frame: pl.DataFrame) -> dict[str, Any]:
    missing = sorted(set(ALLOWED_SOURCE_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing identity fields: {missing}")

    # Select the allowlist before converting to Python rows so status fields cannot influence resolution.
    source = frame.select(list(ALLOWED_SOURCE_FIELDS)).filter(
        (pl.col("season").cast(pl.Int64, strict=False) == season)
        & (pl.col("game_type").cast(pl.Utf8, strict=False) == "REG")
    )

    grouped_signatures: dict[tuple[int, str, str], set[tuple[str, str, str, str]]] = defaultdict(set)
    missing_gsis_rows = 0
    usable_rows = 0
    for row in source.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not team or not gsis:
            if not gsis:
                missing_gsis_rows += 1
            continue
        usable_rows += 1
        signature = (
            normalize_jersey(row.get("jersey_number")),
            str(row.get("first_name") or "").strip(),
            str(row.get("football_name") or "").strip(),
            str(row.get("last_name") or "").strip(),
        )
        grouped_signatures[(week, team, gsis)].add(signature)

    conflict_count = 0
    conflict_examples: list[dict[str, object]] = []
    index: dict[tuple[int, str, str, str], set[str]] = defaultdict(set)
    collapsed_identity_keys = 0
    for (week, team, gsis), signatures in sorted(grouped_signatures.items()):
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
        collapsed_identity_keys += 1
        jersey, first_name, football_name, last_name = next(iter(signatures))
        if not jersey:
            continue
        for display_key in roster_display_keys(
            first_name=first_name,
            football_name=football_name,
            last_name=last_name,
        ):
            index[(week, team, jersey, display_key)].add(gsis)

    return {
        "index": index,
        "source_rows_selected": source.height,
        "usable_non_null_gsis_rows": usable_rows,
        "missing_gsis_rows": missing_gsis_rows,
        "collapsed_player_team_week_gsis_keys": collapsed_identity_keys,
        "source_identity_conflicts": conflict_count,
        "source_identity_conflict_examples": conflict_examples,
    }


def _gamebook_identities_for_side(text: str, *, side: int) -> set[tuple[str, str]]:
    _, sections = roster_v2._section_entries(text, side=side)
    diag = roster_v2.active_membership_diagnostics(sections)
    return set(diag["active"]) | set(diag["inactive"])


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

    raw_roster, source_url = fetch_identity_source(season, timeout=timeout)
    frame = pl.read_parquet(io.BytesIO(raw_roster))
    identity_source = build_identity_index(season=season, frame=frame)
    index: dict[tuple[int, str, str, str], set[str]] = identity_source.pop("index")

    manifest = roster_v1._read_manifest(archive_root / "manifests" / f"{season}.jsonl")
    total_identities = 0
    resolved = 0
    exact_unresolved_count = 0
    exact_ambiguous_count = 0
    unresolved_examples: list[dict[str, object]] = []
    ambiguous_examples: list[dict[str, object]] = []

    for source_row in manifest:
        raw_path = archive_root / str(source_row["raw_object_relpath"])
        with gzip.open(raw_path, "rb") as handle:
            text = raw_v1._extract_pdf_text(handle.read())
        week = int(source_row["week"])
        for side, team, side_name in (
            (0, normalize_team(source_row["away_team"]), "visitor_left"),
            (1, normalize_team(source_row["home_team"]), "home_right"),
        ):
            for jersey, display_name in sorted(_gamebook_identities_for_side(text, side=side)):
                total_identities += 1
                key = (week, team, normalize_jersey(jersey), compact_name(display_name))
                candidates = sorted(index.get(key, set()))
                if len(candidates) == 1:
                    resolved += 1
                elif not candidates:
                    exact_unresolved_count += 1
                    if len(unresolved_examples) < 200:
                        unresolved_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": normalize_jersey(jersey),
                                "display_name": display_name,
                                "normalized_name_key": compact_name(display_name),
                            }
                        )
                else:
                    exact_ambiguous_count += 1
                    if len(ambiguous_examples) < 200:
                        ambiguous_examples.append(
                            {
                                "season": season,
                                "week": week,
                                "game_id": str(source_row["game_id"]),
                                "team": team,
                                "side": side_name,
                                "jersey_number": normalize_jersey(jersey),
                                "display_name": display_name,
                                "normalized_name_key": compact_name(display_name),
                                "candidate_gsis_ids": candidates,
                            }
                        )

    if resolved + exact_unresolved_count + exact_ambiguous_count != total_identities:
        raise RuntimeError("identity resolution accounting mismatch")

    resolution_rate = resolved / total_identities if total_identities else 0.0
    all_pass = bool(
        upstream_passed
        and total_identities > 0
        and resolution_rate == 1.0
        and exact_unresolved_count == 0
        and exact_ambiguous_count == 0
        and identity_source["source_identity_conflicts"] == 0
    )
    return {
        "audit_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_roster_universe_v2_passed": upstream_passed,
        "weekly_identity_source_url": source_url,
        "weekly_identity_source_sha256": _sha256(raw_roster),
        "weekly_identity_source_allowed_fields_only": list(ALLOWED_SOURCE_FIELDS),
        "weekly_roster_status_used": False,
        **identity_source,
        "gamebook_identities_total": total_identities,
        "exact_unique_gsis_resolutions": resolved,
        "unresolved_gamebook_identities": exact_unresolved_count,
        "ambiguous_gamebook_identities": exact_ambiguous_count,
        "exact_identity_resolution_rate": resolution_rate,
        "unresolved_examples": unresolved_examples,
        "ambiguous_examples": ambiguous_examples,
        "all_frozen_identity_gates_pass": all_pass,
        "legacy_player_team_game_identity_qualified": all_pass,
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
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_examples")}, indent=2, sort_keys=True))
    if result["all_frozen_identity_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

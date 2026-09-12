from __future__ import annotations

"""V2 diagnostic wrapper for the frozen weekly-roster source audit.

V1 is preserved as the preregistered first execution. V2 corrects only source identifier
normalization for legacy NFL Data Exchange abbreviations observed in the failed receipts
and adds diagnostics describing duplicate player-team-week rows. It does not relax the V1
zero-duplicate gate, infer roster eligibility, interpret status values, construct labels,
use postgame participation, or fit V09B.
"""

import argparse
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_roster_universe_audit_v1 as v1

V2_TEAM_ALIASES = {
    **v1.TEAM_ALIASES,
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "SL": "LA",
}


def normalize_team_v2(value: object) -> str:
    team = str(value or "").strip().upper()
    return V2_TEAM_ALIASES.get(team, team)


def duplicate_shape_diagnostics(*, season: int, frame: pl.DataFrame) -> dict[str, Any]:
    season_frame = frame.filter(
        (pl.col("season").cast(pl.Int64, strict=False) == season)
        & (pl.col("game_type").cast(pl.Utf8, strict=False) == "REG")
    )
    identity_variants: dict[tuple[int, str, str], Counter[tuple[str, str]]] = defaultdict(Counter)
    exact_rows: Counter[tuple[int, str, str, str, str]] = Counter()
    alias_rows: Counter[tuple[str, str]] = Counter()

    for row in season_frame.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        raw_team = str(row.get("team") or "").strip().upper()
        team = normalize_team_v2(raw_team)
        if raw_team and raw_team != team:
            alias_rows[(raw_team, team)] += 1
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            continue
        abbr = str(row.get("status_description_abbr") or "<NULL>")
        short = str(row.get("status_short_description") or "<NULL>")
        identity = (week, team, gsis)
        variant = (abbr, short)
        identity_variants[identity][variant] += 1
        exact_rows[(week, team, gsis, abbr, short)] += 1

    duplicate_identities = {
        key: variants
        for key, variants in identity_variants.items()
        if sum(variants.values()) > 1
    }
    identical_keys = sum(1 for variants in duplicate_identities.values() if len(variants) == 1)
    conflicting_keys = sum(1 for variants in duplicate_identities.values() if len(variants) > 1)
    exact_duplicate_excess_rows = sum(max(0, count - 1) for count in exact_rows.values())

    examples: dict[str, list[dict[str, object]]] = {}
    for (week, team, gsis), variants in sorted(duplicate_identities.items())[:50]:
        examples[f"{season}-W{week}-{team}-{gsis}"] = [
            {
                "status_description_abbr": abbr,
                "status_short_description": short,
                "rows": count,
            }
            for (abbr, short), count in sorted(variants.items())
        ]

    return {
        "legacy_team_alias_row_counts": {
            f"{raw}->{normalized}": count
            for (raw, normalized), count in sorted(alias_rows.items())
        },
        "duplicate_identity_keys_total": len(duplicate_identities),
        "duplicate_identity_keys_single_status_variant": identical_keys,
        "duplicate_identity_keys_conflicting_status_variants": conflicting_keys,
        "exact_duplicate_normalized_excess_rows": exact_duplicate_excess_rows,
        "duplicate_identity_status_variant_examples": examples,
    }


def audit_frame_v2(
    *,
    season: int,
    frame: pl.DataFrame,
    games: list[dict[str, object]],
    raw_sha256: str,
    raw_size_bytes: int,
    parquet_magic_valid: bool,
    source_url: str,
) -> dict[str, Any]:
    original_normalize = v1.normalize_team
    v1.normalize_team = normalize_team_v2
    try:
        result = v1.audit_frame(
            season=season,
            frame=frame,
            games=games,
            raw_sha256=raw_sha256,
            raw_size_bytes=raw_size_bytes,
            parquet_magic_valid=parquet_magic_valid,
            source_url=source_url,
        )
    finally:
        v1.normalize_team = original_normalize

    result = dict(result)
    result["audit_version"] = 2
    result["v1_frozen_zero_duplicate_gate_preserved"] = True
    result["team_alias_repair_scope"] = "identifier normalization only"
    result["duplicate_shape_diagnostics"] = duplicate_shape_diagnostics(
        season=season,
        frame=frame,
    )
    return result


def audit_season(season: int, *, timeout: float = 60.0) -> dict[str, Any]:
    raw, url = v1.fetch_release(season, timeout=timeout)
    parquet_magic = len(raw) >= 8 and raw[:4] == b"PAR1" and raw[-4:] == b"PAR1"
    frame = pl.read_parquet(io.BytesIO(raw))
    games = v1.canonical_games(season)
    return audit_frame_v2(
        season=season,
        frame=frame,
        games=games,
        raw_sha256=v1._sha256(raw),
        raw_size_bytes=len(raw),
        parquet_magic_valid=parquet_magic,
        source_url=url,
    )


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(v1.EXPECTED_GAMES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["all_frozen_gates_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

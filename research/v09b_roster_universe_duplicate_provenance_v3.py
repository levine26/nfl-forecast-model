from __future__ import annotations

"""Diagnostic-only full-row provenance audit for legacy weekly-roster duplicates.

V1/V2 remain the qualification gates and are not relaxed here. V3 answers one narrower
question raised by the failed 2012-2015 source audits: when a normalized
(player, team, week) identity appears more than once, are the underlying source rows
literal repeats or materially different snapshots? No deduplication is performed and this
module has no qualification authority.
"""

import argparse
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_roster_universe_audit_v1 as v1
from research.v09b_roster_universe_audit_v2 import audit_frame_v2, normalize_team_v2

LEGACY_SEASONS = (2012, 2013, 2014, 2015)


def _canonical_source_row(row: dict[str, object], *, season: int, week: int, team: str) -> dict[str, object]:
    normalized = {str(key): v1._jsonable(value) for key, value in row.items()}
    normalized["season"] = season
    normalized["week"] = week
    normalized["team"] = team
    return normalized


def full_row_duplicate_diagnostics(*, season: int, frame: pl.DataFrame) -> dict[str, Any]:
    season_frame = frame.filter(
        (pl.col("season").cast(pl.Int64, strict=False) == season)
        & (pl.col("game_type").cast(pl.Utf8, strict=False) == "REG")
    )

    identity_rows: dict[tuple[int, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in season_frame.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = normalize_team_v2(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not team or not gsis:
            continue
        identity_rows[(week, team, gsis)].append(
            _canonical_source_row(row, season=season, week=week, team=team)
        )

    duplicate_identities = {
        identity: rows for identity, rows in identity_rows.items() if len(rows) > 1
    }
    single_variant = 0
    multi_variant = 0
    literal_repeat_excess_rows = 0
    multi_variant_excess_rows = 0
    differing_column_counts: Counter[str] = Counter()
    examples: dict[str, dict[str, object]] = {}

    for (week, team, gsis), rows in sorted(duplicate_identities.items()):
        encoded = [json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows]
        variants = Counter(encoded)
        if len(variants) == 1:
            single_variant += 1
            literal_repeat_excess_rows += len(rows) - 1
            continue

        multi_variant += 1
        multi_variant_excess_rows += len(rows) - 1
        columns = sorted({key for row in rows for key in row})
        differing = []
        for column in columns:
            values = {
                json.dumps(v1._jsonable(row.get(column)), sort_keys=True, separators=(",", ":"))
                for row in rows
            }
            if len(values) > 1:
                differing.append(column)
                differing_column_counts[column] += 1

        if len(examples) < 50:
            key = f"{season}-W{week}-{team}-{gsis}"
            examples[key] = {
                "rows": len(rows),
                "distinct_full_row_variants": len(variants),
                "differing_columns": differing,
                "variant_counts": sorted(variants.values(), reverse=True),
                "variant_row_samples": [json.loads(value) for value in list(variants)[:3]],
            }

    duplicate_rows_total = sum(len(rows) for rows in duplicate_identities.values())
    duplicate_excess_rows_total = sum(len(rows) - 1 for rows in duplicate_identities.values())
    return {
        "diagnostic_version": 3,
        "season": season,
        "source_columns": sorted(season_frame.columns),
        "duplicate_identity_keys_total": len(duplicate_identities),
        "duplicate_identity_keys_single_full_row_variant": single_variant,
        "duplicate_identity_keys_multiple_full_row_variants": multi_variant,
        "duplicate_rows_total": duplicate_rows_total,
        "duplicate_excess_rows_total": duplicate_excess_rows_total,
        "literal_repeat_excess_rows": literal_repeat_excess_rows,
        "material_variant_excess_rows": multi_variant_excess_rows,
        "differing_column_identity_counts": dict(sorted(differing_column_counts.items())),
        "multiple_full_row_variant_examples": examples,
        "deduplication_performed": False,
        "qualification_authority": False,
        "status_semantics_interpreted": False,
        "game_day_roster_universe_qualified": False,
        "player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def audit_season(season: int, *, timeout: float = 60.0) -> dict[str, Any]:
    if season not in LEGACY_SEASONS:
        raise ValueError(f"season must be one of {LEGACY_SEASONS}")
    raw, url = v1.fetch_release(season, timeout=timeout)
    parquet_magic = len(raw) >= 8 and raw[:4] == b"PAR1" and raw[-4:] == b"PAR1"
    frame = pl.read_parquet(io.BytesIO(raw))
    games = v1.canonical_games(season)
    frozen = audit_frame_v2(
        season=season,
        frame=frame,
        games=games,
        raw_sha256=v1._sha256(raw),
        raw_size_bytes=len(raw),
        parquet_magic_valid=parquet_magic,
        source_url=url,
    )
    return {
        "season": season,
        "source_url": url,
        "raw_parquet_sha256": v1._sha256(raw),
        "v2_frozen_gate_result": {
            "canonical_team_game_week_coverage_rate": frozen.get("canonical_team_game_week_coverage_rate"),
            "duplicate_non_null_gsis_player_team_week_keys": frozen.get("duplicate_non_null_gsis_player_team_week_keys"),
            "all_frozen_gates_pass": frozen.get("all_frozen_gates_pass"),
        },
        "full_row_duplicate_diagnostics": full_row_duplicate_diagnostics(season=season, frame=frame),
        "qualification_authority": False,
        "deduplication_performed": False,
        "completed_2026_outcomes_used": 0,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=LEGACY_SEASONS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

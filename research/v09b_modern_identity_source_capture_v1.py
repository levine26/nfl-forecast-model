from __future__ import annotations

"""Freeze 2017-2021 nflverse weekly-roster bytes for identity-only research.

This module is source-provenance capture only. It never defines game-day membership, never
uses roster status fields for resolution, never resolves Game Book identities, and never
fits a model. Downstream identity audits must consume the persisted status-free projection
rather than the raw weekly-roster source.
"""

import argparse
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl
import requests

CONTRACT_ID = "V09B-MODERN-IDENTITY-SOURCE-CAPTURE-V1"
RELEASE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/"
    "roster_weekly_{season}.parquet"
)
SEASONS = (2017, 2018, 2019, 2020, 2021)
ALLOWED_FIELDS = (
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
FORBIDDEN_STATUS_FIELDS = (
    "status",
    "status_description_abbr",
    "status_short_description",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_parquet_magic(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] == b"PAR1" and data[-4:] == b"PAR1"


def fetch_source(season: int, *, timeout: float = 90.0) -> tuple[bytes, str]:
    if season not in SEASONS:
        raise ValueError(f"unsupported season: {season}")
    response = requests.get(
        RELEASE_URL.format(season=season),
        timeout=timeout,
        headers={"User-Agent": "LevLine-V09B-modern-identity-source/1.0"},
    )
    response.raise_for_status()
    raw = response.content
    if not valid_parquet_magic(raw):
        raise RuntimeError(f"weekly-roster release is not valid parquet for {season}")
    return raw, str(response.url)


def project_identity_source(*, season: int, frame: pl.DataFrame) -> pl.DataFrame:
    missing = sorted(set(ALLOWED_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing required identity fields: {missing}")

    # Select the identity allowlist before any row conversion. Status values are never read.
    projected = frame.select(list(ALLOWED_FIELDS)).with_columns(
        pl.col("season").cast(pl.Int64, strict=False),
        pl.col("week").cast(pl.Int64, strict=False),
        pl.col("game_type").cast(pl.Utf8, strict=False),
        pl.col("team").cast(pl.Utf8, strict=False),
        pl.col("gsis_id").cast(pl.Utf8, strict=False),
        pl.col("jersey_number").cast(pl.Utf8, strict=False),
        pl.col("first_name").cast(pl.Utf8, strict=False),
        pl.col("football_name").cast(pl.Utf8, strict=False),
        pl.col("last_name").cast(pl.Utf8, strict=False),
    )
    projected = projected.filter(
        (pl.col("season") == int(season)) & (pl.col("game_type") == "REG")
    )
    return projected.sort(list(ALLOWED_FIELDS), nulls_last=True)


def diagnose_projection(frame: pl.DataFrame) -> dict[str, Any]:
    if tuple(frame.columns) != ALLOWED_FIELDS:
        raise RuntimeError("identity projection fields do not exactly match the allowlist")
    if any(field in frame.columns for field in FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("identity projection contains forbidden roster status fields")

    missing_gsis_rows = 0
    usable_rows = 0
    signatures: dict[tuple[int, str, str], set[tuple[str, str, str, str]]] = defaultdict(set)
    for row in frame.to_dicts():
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            missing_gsis_rows += 1
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = str(row.get("team") or "").strip().upper()
        if not team:
            continue
        usable_rows += 1
        signatures[(week, team, gsis)].add(
            (
                str(row.get("jersey_number") or "").strip(),
                str(row.get("first_name") or "").strip(),
                str(row.get("football_name") or "").strip(),
                str(row.get("last_name") or "").strip(),
            )
        )

    conflicts = 0
    collapsed = 0
    examples: list[dict[str, Any]] = []
    for (week, team, gsis), values in sorted(signatures.items()):
        if len(values) == 1:
            collapsed += 1
            continue
        conflicts += 1
        if len(examples) < 100:
            examples.append(
                {
                    "week": week,
                    "team": team,
                    "gsis_id": gsis,
                    "identity_signatures": [list(value) for value in sorted(values)],
                }
            )

    return {
        "source_rows_selected": frame.height,
        "usable_non_null_gsis_rows": usable_rows,
        "missing_gsis_rows": missing_gsis_rows,
        "collapsed_player_team_week_gsis_keys": collapsed,
        "source_identity_conflicts": conflicts,
        "source_identity_conflict_examples": examples,
    }


def projection_bytes(frame: pl.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    raw = buffer.getvalue()
    if not valid_parquet_magic(raw):
        raise RuntimeError("persisted identity projection is not valid parquet")
    return raw


def _write_if_missing(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != data:
            raise RuntimeError(f"content-addressed object mismatch at {path}")
        return
    path.write_bytes(data)


def capture_season(
    season: int,
    *,
    output_root: Path,
    timeout: float = 90.0,
) -> dict[str, Any]:
    raw, final_url = fetch_source(season, timeout=timeout)
    raw_sha = sha256_bytes(raw)
    frame = pl.read_parquet(io.BytesIO(raw))
    projected = project_identity_source(season=season, frame=frame)
    diagnostic = diagnose_projection(projected)
    projected_raw = projection_bytes(projected)
    projected_sha = sha256_bytes(projected_raw)

    raw_relpath = Path("raw") / f"{raw_sha}.parquet"
    projection_relpath = Path("projections") / f"{season}-{projected_sha}.parquet"
    _write_if_missing(output_root / raw_relpath, raw)
    _write_if_missing(output_root / projection_relpath, projected_raw)

    projection_fields = list(projected.columns)
    projection_nonempty = projected.height > 0
    gate_pass = bool(
        valid_parquet_magic(raw)
        and valid_parquet_magic(projected_raw)
        and projection_nonempty
        and tuple(projected.columns) == ALLOWED_FIELDS
        and not any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS)
    )

    receipt = {
        "capture_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "source_provider": "nflverse",
        "requested_url": RELEASE_URL.format(season=season),
        "final_source_url": final_url,
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "raw_source_relpath": str(raw_relpath),
        "raw_parquet_magic_valid": valid_parquet_magic(raw),
        "projection_sha256": projected_sha,
        "projection_bytes": len(projected_raw),
        "projection_relpath": str(projection_relpath),
        "projection_parquet_magic_valid": valid_parquet_magic(projected_raw),
        "projection_fields": projection_fields,
        "projection_contains_only_allowlisted_fields": tuple(projected.columns) == ALLOWED_FIELDS,
        "projection_contains_status_fields": any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS),
        "status_fields_selected": False,
        "status_fields_read_for_resolution": False,
        **diagnostic,
        "capture_gate_pass": gate_pass,
        "diagnostic_values_authorize_identity_resolution": False,
        "weekly_roster_defines_game_day_membership": False,
        "modern_game_day_roster_universe_qualified_by_this_capture": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "identity_resolution_performed": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
    }
    receipt_path = output_root / "receipts" / f"{season}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=list(SEASONS))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = capture_season(args.season, output_root=args.output_root, timeout=args.timeout)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_examples")}, indent=2, sort_keys=True))
    if result["capture_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

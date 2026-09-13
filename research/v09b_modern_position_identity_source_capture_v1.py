from __future__ import annotations

"""Create a status-free 2019 weekly-roster position projection for V09B identity V2.

This module is source capture only. It reads the exact raw nflverse weekly-roster bytes
already frozen by the qualified identity-source capture, selects only a narrow allowlist
that includes source-native position, and persists a new projection before any V2 identity
resolver consumes position evidence. It never reads roster status fields, never interprets
game-day membership, and never fits a model.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable

import polars as pl

CAPTURE_CONTRACT_ID = "V09B-MODERN-POSITION-IDENTITY-SOURCE-CAPTURE-V1"
SEASON = 2019
RAW_SOURCE_SHA256 = "08ef64996cecdff2f4631ca26b21ed9a39bf5fba0b3379d902e531facf81e5c4"
EXPECTED_REG_ROWS = 49561
EXPECTED_MISSING_GSIS_ROWS = 2
ALLOWED_FIELDS = (
    "season",
    "game_type",
    "week",
    "team",
    "gsis_id",
    "jersey_number",
    "position",
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


def project_position_source(*, frame: pl.DataFrame) -> pl.DataFrame:
    missing = sorted(set(ALLOWED_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing required position-source fields: {missing}")

    # Select the allowlist before any row conversion. Status columns are never selected/read.
    projected = frame.select(list(ALLOWED_FIELDS)).with_columns(
        pl.col("season").cast(pl.Int64, strict=False),
        pl.col("week").cast(pl.Int64, strict=False),
        pl.col("game_type").cast(pl.Utf8, strict=False),
        pl.col("team").cast(pl.Utf8, strict=False),
        pl.col("gsis_id").cast(pl.Utf8, strict=False),
        pl.col("jersey_number").cast(pl.Utf8, strict=False),
        pl.col("position").cast(pl.Utf8, strict=False),
    )
    projected = projected.filter(
        (pl.col("season") == SEASON) & (pl.col("game_type") == "REG")
    )
    return projected.sort(list(ALLOWED_FIELDS), nulls_last=True)


def projection_bytes(frame: pl.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    raw = buffer.getvalue()
    if not valid_parquet_magic(raw):
        raise RuntimeError("persisted position projection is not valid parquet")
    return raw


def capture_position_source(*, raw_path: Path, output_root: Path) -> dict[str, Any]:
    raw = raw_path.read_bytes()
    raw_sha = sha256_bytes(raw)
    if raw_sha != RAW_SOURCE_SHA256:
        raise RuntimeError("raw weekly-roster bytes do not match the frozen 2019 SHA256")
    if not valid_parquet_magic(raw):
        raise RuntimeError("frozen weekly-roster source is not valid parquet")

    frame = pl.read_parquet(io.BytesIO(raw))
    projected = project_position_source(frame=frame)
    if tuple(projected.columns) != ALLOWED_FIELDS:
        raise RuntimeError("position projection fields do not exactly match the allowlist")
    if any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("status field leaked into the position projection")

    rows = projected.to_dicts()
    missing_gsis_rows = sum(1 for row in rows if not str(row.get("gsis_id") or "").strip())
    blank_position_rows = sum(1 for row in rows if not str(row.get("position") or "").strip())

    projected_raw = projection_bytes(projected)
    projection_sha = sha256_bytes(projected_raw)
    projection_relpath = Path("projections") / f"{SEASON}-{projection_sha}.parquet"
    projection_path = output_root / projection_relpath
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    projection_path.write_bytes(projected_raw)

    capture_gate_pass = bool(
        raw_sha == RAW_SOURCE_SHA256
        and projected.height == EXPECTED_REG_ROWS
        and missing_gsis_rows == EXPECTED_MISSING_GSIS_ROWS
        and tuple(projected.columns) == ALLOWED_FIELDS
        and not any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS)
        and valid_parquet_magic(projected_raw)
    )

    receipt = {
        "capture_version": 1,
        "capture_contract_id": CAPTURE_CONTRACT_ID,
        "season": SEASON,
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "raw_source_path_name": raw_path.name,
        "source_rows_selected": projected.height,
        "expected_source_rows_selected": EXPECTED_REG_ROWS,
        "missing_gsis_rows": missing_gsis_rows,
        "expected_missing_gsis_rows": EXPECTED_MISSING_GSIS_ROWS,
        "blank_position_rows": blank_position_rows,
        "projection_sha256": projection_sha,
        "projection_bytes": len(projected_raw),
        "projection_relpath": str(projection_relpath),
        "projection_fields": list(projected.columns),
        "projection_contains_only_allowlisted_fields": tuple(projected.columns) == ALLOWED_FIELDS,
        "projection_contains_status_fields": any(
            field in projected.columns for field in FORBIDDEN_STATUS_FIELDS
        ),
        "status_fields_selected": False,
        "status_fields_read": False,
        "position_semantics_interpreted_by_capture": False,
        "weekly_roster_defines_game_day_membership": False,
        "capture_gate_pass": capture_gate_pass,
        "modern_player_team_game_identity_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
    }
    receipt_path = output_root / "receipts" / f"{SEASON}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = capture_position_source(raw_path=args.raw_path, output_root=args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["capture_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

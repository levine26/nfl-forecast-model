from __future__ import annotations

"""Capture the preregistered 2026 status-free identity source.

This module freezes source provenance and an identity-only projection. It deliberately has
no roster-membership, availability, player-value, forecasting, or production authority.
Roster status fields are excluded before any row conversion and are never read.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl
import requests

CONTRACT_ID = "LEVLINE-4-2026-STATUS-FREE-IDENTITY-SOURCE-V1"
SEASON = 2026
SOURCE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/"
    "roster_weekly_2026.parquet"
)
SOURCE_ASSET_ID = 567939096
SOURCE_CREATED_AT_UTC = "2026-09-16T12:35:57Z"
EXPECTED_SOURCE_BYTES = 619674
EXPECTED_SOURCE_SHA256 = "71ff033b7a835a73b8489f7c1fac4e26e94e5f0cb2036efe70f22e986de2369e"
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_parquet_magic(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] == b"PAR1" and data[-4:] == b"PAR1"


def fetch_source(*, timeout: float = 90.0) -> tuple[bytes, str]:
    response = requests.get(
        SOURCE_URL,
        timeout=timeout,
        headers={"User-Agent": "LevLine-4-2026-status-free-identity-source/1.0"},
    )
    response.raise_for_status()
    raw = response.content
    if not valid_parquet_magic(raw):
        raise RuntimeError("2026 weekly-roster release is not valid parquet")
    if len(raw) != EXPECTED_SOURCE_BYTES:
        raise RuntimeError(
            f"source byte-size drift: expected {EXPECTED_SOURCE_BYTES}, observed {len(raw)}"
        )
    observed_sha = sha256_bytes(raw)
    if observed_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            f"source SHA drift: expected {EXPECTED_SOURCE_SHA256}, observed {observed_sha}"
        )
    return raw, str(response.url)


def project_identity_source(frame: pl.DataFrame) -> pl.DataFrame:
    missing = sorted(set(ALLOWED_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing required identity fields: {missing}")

    # Critical firewall: select only identity fields before any row conversion.
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
        (pl.col("season") == SEASON) & (pl.col("game_type") == "REG")
    )
    return projected.sort(list(ALLOWED_FIELDS), nulls_last=True)


def diagnose_projection(frame: pl.DataFrame) -> dict[str, Any]:
    if tuple(frame.columns) != ALLOWED_FIELDS:
        raise RuntimeError("projection columns do not exactly equal the frozen allowlist")
    if any(field in frame.columns for field in FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("projection contains forbidden roster-status fields")

    missing_gsis = 0
    usable = 0
    weeks: set[int] = set()
    signatures: dict[tuple[int, str, str], set[tuple[str, str, str, str]]] = defaultdict(set)
    for row in frame.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = str(row.get("team") or "").strip().upper()
        gsis = str(row.get("gsis_id") or "").strip()
        weeks.add(week)
        if not gsis:
            missing_gsis += 1
            continue
        if not team:
            continue
        usable += 1
        signatures[(week, team, gsis)].add(
            (
                str(row.get("jersey_number") or "").strip(),
                str(row.get("first_name") or "").strip(),
                str(row.get("football_name") or "").strip(),
                str(row.get("last_name") or "").strip(),
            )
        )

    conflicts = sum(1 for values in signatures.values() if len(values) > 1)
    examples = []
    for (week, team, gsis), values in sorted(signatures.items()):
        if len(values) <= 1:
            continue
        if len(examples) >= 50:
            break
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
        "weeks_present": sorted(weeks),
        "usable_non_null_gsis_rows": usable,
        "missing_gsis_rows": missing_gsis,
        "source_identity_conflicts": conflicts,
        "source_identity_conflict_examples": examples,
    }


def projection_bytes(frame: pl.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    raw = buffer.getvalue()
    if not valid_parquet_magic(raw):
        raise RuntimeError("identity projection is not valid parquet")
    return raw


def _write_content_addressed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"content-addressed object mismatch: {path}")
    if not path.exists():
        path.write_bytes(data)


def capture(*, output_root: Path, timeout: float = 90.0) -> dict[str, Any]:
    raw, final_url = fetch_source(timeout=timeout)
    raw_sha = sha256_bytes(raw)
    source_frame = pl.read_parquet(io.BytesIO(raw))
    projected = project_identity_source(source_frame)
    diagnostic = diagnose_projection(projected)
    projected_raw = projection_bytes(projected)
    projected_sha = sha256_bytes(projected_raw)

    raw_relpath = Path("raw") / f"{raw_sha}.parquet"
    projection_relpath = Path("projections") / f"2026-{projected_sha}.parquet"
    _write_content_addressed(output_root / raw_relpath, raw)
    _write_content_addressed(output_root / projection_relpath, projected_raw)

    gate_pass = bool(
        raw_sha == EXPECTED_SOURCE_SHA256
        and len(raw) == EXPECTED_SOURCE_BYTES
        and valid_parquet_magic(raw)
        and valid_parquet_magic(projected_raw)
        and projected.height > 0
        and tuple(projected.columns) == ALLOWED_FIELDS
        and not any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS)
    )
    receipt = {
        "capture_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "PASS" if gate_pass else "FAIL",
        "captured_at_utc": _utc_now(),
        "season": SEASON,
        "source_provider": "nflverse",
        "source_asset_id": SOURCE_ASSET_ID,
        "source_asset_created_at_utc": SOURCE_CREATED_AT_UTC,
        "requested_url": SOURCE_URL,
        "final_source_url": final_url,
        "expected_source_sha256": EXPECTED_SOURCE_SHA256,
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "raw_source_relpath": str(raw_relpath),
        "raw_parquet_magic_valid": valid_parquet_magic(raw),
        "projection_sha256": projected_sha,
        "projection_bytes": len(projected_raw),
        "projection_relpath": str(projection_relpath),
        "projection_fields": list(projected.columns),
        "projection_contains_only_allowlisted_fields": tuple(projected.columns) == ALLOWED_FIELDS,
        "projection_contains_status_fields": any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS),
        "status_fields_selected": False,
        "status_fields_read_for_resolution": False,
        **diagnostic,
        "capture_gate_pass": gate_pass,
        "source_capture_qualified_by_this_receipt": gate_pass,
        "player_identity_to_gsis_qualified": False,
        "weekly_roster_defines_game_day_membership": False,
        "availability_state_authorized": False,
        "availability_probability_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "identity_resolution_performed": False,
        "postgame_participation_used": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "f_st_01_frozen_2026_unchanged": True,
    }
    receipt_path = output_root / "receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("research_outputs/levline4_2026_identity_source_v1"),
    )
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    receipt = capture(output_root=args.output_root, timeout=args.timeout)
    print(json.dumps({k: v for k, v in receipt.items() if not k.endswith("_examples")}, indent=2, sort_keys=True))
    if receipt["capture_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

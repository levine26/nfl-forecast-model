from __future__ import annotations

"""Prospective 2026 status-free identity-source capture for LevLine 4 research.

This module is deliberately narrower than an identity resolver. It verifies one exact,
preregistered nflverse weekly-roster byte object and derives a projection containing only
identity fields. It never reads roster status for resolution, never determines game-day
membership, never reconstructs a past state, never joins player value, and never changes a
forecast.
"""

import argparse
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl

CONTRACT_ID = "LEVLINE-2026-STATUS-FREE-IDENTITY-SOURCE-CAPTURE-V1"
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


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract_id")
    if int(contract.get("season", -1)) != 2026:
        raise ValueError("contract season must be 2026")
    projection = contract.get("identity_projection") or {}
    if tuple(projection.get("allowed_fields") or ()) != ALLOWED_FIELDS:
        raise ValueError("contract allowed_fields drifted")
    if tuple(projection.get("forbidden_fields") or ()) != FORBIDDEN_STATUS_FIELDS:
        raise ValueError("contract forbidden_fields drifted")
    return contract


def verify_raw_source(raw: bytes, contract: dict[str, Any]) -> None:
    source = contract["source"]
    if not valid_parquet_magic(raw):
        raise RuntimeError("source is not valid parquet bytes")
    expected_size = int(source["expected_size_bytes"])
    if len(raw) != expected_size:
        raise RuntimeError(f"source byte-size mismatch: {len(raw)} != {expected_size}")
    observed_sha = sha256_bytes(raw)
    if observed_sha != str(source["expected_sha256"]).lower():
        raise RuntimeError(
            f"source sha256 mismatch: {observed_sha} != {source['expected_sha256']}"
        )


def project_status_free_identity(frame: pl.DataFrame) -> pl.DataFrame:
    missing = sorted(set(ALLOWED_FIELDS) - set(frame.columns))
    if missing:
        raise RuntimeError(f"missing required identity fields: {missing}")

    # Critical firewall: select only the allowlist before any row conversion or diagnostics.
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
        (pl.col("season") == 2026) & (pl.col("game_type") == "REG")
    )
    return projected.sort(list(ALLOWED_FIELDS), nulls_last=True)


def diagnose_projection(frame: pl.DataFrame) -> dict[str, Any]:
    if tuple(frame.columns) != ALLOWED_FIELDS:
        raise RuntimeError("projection fields do not exactly match the identity allowlist")
    if any(field in frame.columns for field in FORBIDDEN_STATUS_FIELDS):
        raise RuntimeError("status field leaked into identity projection")

    missing_gsis = 0
    signatures: dict[tuple[int, str, str], set[tuple[str, str, str, str]]] = defaultdict(set)
    for row in frame.to_dicts():
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            missing_gsis += 1
            continue
        team = str(row.get("team") or "").strip().upper()
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        signatures[(week, team, gsis)].add(
            (
                str(row.get("jersey_number") or "").strip(),
                str(row.get("first_name") or "").strip(),
                str(row.get("football_name") or "").strip(),
                str(row.get("last_name") or "").strip(),
            )
        )

    conflicts = sum(1 for values in signatures.values() if len(values) > 1)
    return {
        "source_rows_selected": frame.height,
        "missing_gsis_rows": missing_gsis,
        "collapsed_player_team_week_gsis_keys": len(signatures),
        "source_identity_conflicts": conflicts,
    }


def projection_bytes(frame: pl.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    raw = buffer.getvalue()
    if not valid_parquet_magic(raw):
        raise RuntimeError("projection is not valid parquet")
    return raw


def capture(
    *,
    raw_source_path: Path,
    contract_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    raw = raw_source_path.read_bytes()
    verify_raw_source(raw, contract)

    source_frame = pl.read_parquet(io.BytesIO(raw))
    projected = project_status_free_identity(source_frame)
    if projected.height <= 0:
        raise RuntimeError("status-free identity projection is empty")
    diagnostic = diagnose_projection(projected)
    projected_raw = projection_bytes(projected)
    raw_sha = sha256_bytes(raw)
    projection_sha = sha256_bytes(projected_raw)

    raw_relpath = Path("raw") / f"{raw_sha}.parquet"
    projection_relpath = Path("projections") / f"2026-{projection_sha}.parquet"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / raw_relpath).parent.mkdir(parents=True, exist_ok=True)
    (output_root / projection_relpath).parent.mkdir(parents=True, exist_ok=True)
    (output_root / raw_relpath).write_bytes(raw)
    (output_root / projection_relpath).write_bytes(projected_raw)

    receipt = {
        "schema_version": "levline-2026-status-free-identity-source-v1",
        "contract_id": CONTRACT_ID,
        "status": "PASS",
        "season": 2026,
        "source_provider": "nflverse",
        "source_asset_id": int(contract["source"]["asset_id"]),
        "source_known_by_utc": contract["prospective_time_firewall"]["source_known_by_utc"],
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "raw_source_relpath": str(raw_relpath),
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
        "status_fields_allowed_for_resolution": False,
        **diagnostic,
        "exact_2026_status_free_identity_source_captured": True,
        "player_identity_resolution_qualified": False,
        "week_1_retroactive_identity_join_authorized": False,
        "game_day_membership_qualified": False,
        "availability_state_qualified": False,
        "starter_probability_qualified": False,
        "role_share_qualified": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "identity_resolution_performed": False,
        "completed_2026_outcomes_used": 0,
        "postgame_participation_used": False,
        "postgame_snaps_used": False,
    }
    receipt_path = output_root / "capture_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-source", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    receipt = capture(
        raw_source_path=args.raw_source,
        contract_path=args.contract,
        output_root=args.output_root,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Capture a team/status-free global player identity dictionary for LevLine 4 research."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable

import polars as pl
import requests

CONTRACT_ID = "LEVLINE-4-2026-GLOBAL-PLAYER-IDENTITY-SOURCE-V1"
SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.parquet"
SOURCE_ASSET_ID = 567981040
SOURCE_CREATED_AT_UTC = "2026-09-16T13:00:58Z"
EXPECTED_SOURCE_BYTES = 3386516
EXPECTED_SOURCE_SHA256 = "a6874a809c67a4a0b8749206fe1820fe25f440e460d78394d2ff762b94a3d32b"
ALLOWED_FIELDS = (
    "gsis_id",
    "display_name",
    "common_first_name",
    "first_name",
    "last_name",
    "position_group",
    "position",
)
FORBIDDEN_FIELDS = ("latest_team", "status", "last_season", "jersey_number")


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
        headers={"User-Agent": "LevLine-4-global-player-identity-source/1.0"},
    )
    response.raise_for_status()
    raw = response.content
    if not valid_parquet_magic(raw):
        raise RuntimeError("players release is not valid parquet")
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
        raise RuntimeError(f"missing required player identity fields: {missing}")
    projected = frame.select(list(ALLOWED_FIELDS)).with_columns(
        *(pl.col(field).cast(pl.Utf8, strict=False) for field in ALLOWED_FIELDS)
    )
    return projected.sort(list(ALLOWED_FIELDS), nulls_last=True)


def diagnose_projection(frame: pl.DataFrame) -> dict[str, Any]:
    if tuple(frame.columns) != ALLOWED_FIELDS:
        raise RuntimeError("projection columns do not exactly equal the frozen allowlist")
    if any(field in frame.columns for field in FORBIDDEN_FIELDS):
        raise RuntimeError("projection contains forbidden team/status fields")

    gsis_signatures: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    display_name_ids: dict[str, set[str]] = defaultdict(set)
    blank_gsis = 0
    canonical_gsis_rows = 0
    blank_display_name = 0

    for row in frame.to_dicts():
        gsis = str(row.get("gsis_id") or "").strip()
        display_name = str(row.get("display_name") or "").strip()
        if not gsis:
            blank_gsis += 1
        else:
            if gsis.startswith("00-"):
                canonical_gsis_rows += 1
            signature = tuple(str(row.get(field) or "").strip() for field in ALLOWED_FIELDS[1:])
            gsis_signatures[gsis].add(signature)
            if display_name:
                display_name_ids[display_name].add(gsis)
        if not display_name:
            blank_display_name += 1

    gsis_conflicts = sum(1 for values in gsis_signatures.values() if len(values) > 1)
    exact_display_name_collisions = {
        name: sorted(ids) for name, ids in display_name_ids.items() if len(ids) > 1
    }
    collision_examples = [
        {"display_name": name, "gsis_ids": ids}
        for name, ids in sorted(exact_display_name_collisions.items())[:50]
    ]
    return {
        "source_rows_selected": frame.height,
        "blank_gsis_rows": blank_gsis,
        "canonical_00_gsis_rows": canonical_gsis_rows,
        "noncanonical_or_blank_gsis_rows": frame.height - canonical_gsis_rows,
        "blank_display_name_rows": blank_display_name,
        "duplicate_gsis_identity_conflicts": gsis_conflicts,
        "exact_display_name_collision_count": len(exact_display_name_collisions),
        "exact_display_name_collision_examples": collision_examples,
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
    source_frame = pl.read_parquet(io.BytesIO(raw))
    projected = project_identity_source(source_frame)
    diagnostic = diagnose_projection(projected)
    projection_raw = projection_bytes(projected)
    raw_sha = sha256_bytes(raw)
    projection_sha = sha256_bytes(projection_raw)

    raw_relpath = Path("raw") / f"{raw_sha}.parquet"
    projection_relpath = Path("projections") / f"players-{projection_sha}.parquet"
    _write_content_addressed(output_root / raw_relpath, raw)
    _write_content_addressed(output_root / projection_relpath, projection_raw)

    gate_pass = bool(
        raw_sha == EXPECTED_SOURCE_SHA256
        and len(raw) == EXPECTED_SOURCE_BYTES
        and valid_parquet_magic(raw)
        and valid_parquet_magic(projection_raw)
        and projected.height > 0
        and tuple(projected.columns) == ALLOWED_FIELDS
        and not any(field in projected.columns for field in FORBIDDEN_FIELDS)
    )
    receipt = {
        "capture_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "PASS" if gate_pass else "FAIL",
        "captured_at_utc": _utc_now(),
        "source_provider": "nflverse",
        "source_asset_id": SOURCE_ASSET_ID,
        "source_asset_created_at_utc": SOURCE_CREATED_AT_UTC,
        "requested_url": SOURCE_URL,
        "final_source_url": final_url,
        "expected_source_sha256": EXPECTED_SOURCE_SHA256,
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "raw_parquet_magic_valid": valid_parquet_magic(raw),
        "raw_source_relpath": str(raw_relpath),
        "projection_sha256": projection_sha,
        "projection_bytes": len(projection_raw),
        "projection_relpath": str(projection_relpath),
        "projection_fields": list(projected.columns),
        "projection_contains_only_allowlisted_fields": tuple(projected.columns) == ALLOWED_FIELDS,
        "projection_contains_forbidden_team_or_status_fields": any(
            field in projected.columns for field in FORBIDDEN_FIELDS
        ),
        **diagnostic,
        "capture_gate_pass": gate_pass,
        "source_capture_qualified_by_this_receipt": gate_pass,
        "player_identity_to_gsis_qualified": False,
        "team_membership_authorized": False,
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
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("research_outputs/levline4_2026_global_player_identity_source_v1"),
    )
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    receipt = capture(output_root=args.output_root, timeout=args.timeout)
    print(json.dumps({k: v for k, v in receipt.items() if not k.endswith("_examples")}, indent=2, sort_keys=True))
    if receipt["capture_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

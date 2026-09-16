from __future__ import annotations

import io

import polars as pl
import pytest

from research.levline4_2026_identity_source_capture_v1 import (
    ALLOWED_FIELDS,
    EXPECTED_SOURCE_SHA256,
    diagnose_projection,
    project_identity_source,
    sha256_bytes,
    valid_parquet_magic,
)


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2026, 2026, 2026],
            "game_type": ["REG", "REG", "PRE"],
            "week": [1, 2, 3],
            "team": ["ARI", "LAC", "ARI"],
            "gsis_id": ["00-001", "00-002", "00-003"],
            "jersey_number": ["1", "2", "3"],
            "first_name": ["Alpha", "Beta", "Gamma"],
            "football_name": ["Alpha", "Beta", "Gamma"],
            "last_name": ["One", "Two", "Three"],
            "status": ["INA", "ACT", "ACT"],
            "status_description_abbr": ["INA", "ACT", "ACT"],
            "status_short_description": ["Inactive", "Active", "Active"],
        }
    )


def test_projection_drops_status_before_rows_and_filters_reg_2026() -> None:
    projected = project_identity_source(_frame())
    assert tuple(projected.columns) == ALLOWED_FIELDS
    assert projected.height == 2
    assert "status" not in projected.columns
    assert "status_description_abbr" not in projected.columns
    assert "status_short_description" not in projected.columns
    diagnostic = diagnose_projection(projected)
    assert diagnostic["source_identity_conflicts"] == 0
    assert diagnostic["weeks_present"] == [1, 2]


def test_missing_identity_field_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="missing required identity fields"):
        project_identity_source(_frame().drop("gsis_id"))


def test_duplicate_gsis_with_conflicting_identity_signature_is_reported() -> None:
    frame = pl.DataFrame(
        {
            "season": [2026, 2026],
            "game_type": ["REG", "REG"],
            "week": [2, 2],
            "team": ["ARI", "ARI"],
            "gsis_id": ["00-009", "00-009"],
            "jersey_number": ["9", "9"],
            "first_name": ["A", "A"],
            "football_name": ["A", "A"],
            "last_name": ["One", "Two"],
        }
    )
    projected = project_identity_source(frame)
    assert diagnose_projection(projected)["source_identity_conflicts"] == 1


def test_parquet_magic_and_hash_helpers() -> None:
    buffer = io.BytesIO()
    project_identity_source(_frame()).write_parquet(buffer)
    raw = buffer.getvalue()
    assert valid_parquet_magic(raw) is True
    assert valid_parquet_magic(b"not parquet") is False
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert len(EXPECTED_SOURCE_SHA256) == 64

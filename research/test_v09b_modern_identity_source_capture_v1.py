from __future__ import annotations

import io

import polars as pl

from research.v09b_modern_identity_source_capture_v1 import (
    ALLOWED_FIELDS,
    FORBIDDEN_STATUS_FIELDS,
    diagnose_projection,
    project_identity_source,
    projection_bytes,
    valid_parquet_magic,
)


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2019, 2019, 2019, 2020],
            "game_type": ["REG", "REG", "POST", "REG"],
            "week": [1, 1, 19, 1],
            "team": ["ARI", "ARI", "ARI", "ARI"],
            "gsis_id": ["00-001", "00-002", "00-003", "00-004"],
            "jersey_number": ["1", "2", "3", "4"],
            "first_name": ["Alpha", "Beta", "Gamma", "Delta"],
            "football_name": ["A", "B", "G", "D"],
            "last_name": ["One", "Two", "Three", "Four"],
            "status": ["ACT", "RES", "ACT", "ACT"],
            "status_description_abbr": ["A", "R", "A", "A"],
            "status_short_description": ["Active", "Reserve", "Active", "Active"],
        }
    )


def test_projection_selects_only_identity_allowlist_before_row_use() -> None:
    projected = project_identity_source(season=2019, frame=_frame())
    assert tuple(projected.columns) == ALLOWED_FIELDS
    assert projected.height == 2
    assert projected["season"].to_list() == [2019, 2019]
    assert projected["game_type"].to_list() == ["REG", "REG"]
    assert not any(field in projected.columns for field in FORBIDDEN_STATUS_FIELDS)


def test_diagnostics_are_identity_only_and_account_for_missing_gsis() -> None:
    frame = pl.DataFrame(
        {
            "season": [2019, 2019, 2019],
            "game_type": ["REG", "REG", "REG"],
            "week": [1, 1, 1],
            "team": ["ARI", "ARI", "ARI"],
            "gsis_id": ["00-001", "00-001", None],
            "jersey_number": ["1", "9", "3"],
            "first_name": ["Alpha", "Alpha", "Gamma"],
            "football_name": ["A", "A", "G"],
            "last_name": ["One", "One", "Three"],
        }
    ).select(list(ALLOWED_FIELDS))
    result = diagnose_projection(frame)
    assert result["source_rows_selected"] == 3
    assert result["usable_non_null_gsis_rows"] == 2
    assert result["missing_gsis_rows"] == 1
    assert result["collapsed_player_team_week_gsis_keys"] == 0
    assert result["source_identity_conflicts"] == 1
    assert result["source_identity_conflict_examples"][0]["gsis_id"] == "00-001"


def test_projection_parquet_round_trip_preserves_allowlist() -> None:
    projected = project_identity_source(season=2019, frame=_frame())
    raw = projection_bytes(projected)
    assert valid_parquet_magic(raw)
    restored = pl.read_parquet(io.BytesIO(raw))
    assert tuple(restored.columns) == ALLOWED_FIELDS
    assert restored.height == projected.height


def test_invalid_parquet_magic_is_rejected() -> None:
    assert valid_parquet_magic(b"PAR1abcdPAR1") is True
    assert valid_parquet_magic(b"not parquet") is False

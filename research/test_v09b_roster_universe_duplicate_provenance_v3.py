from __future__ import annotations

import polars as pl

from research.v09b_roster_universe_duplicate_provenance_v3 import (
    full_row_duplicate_diagnostics,
)


def _frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {
        "season": 2012,
        "game_type": "REG",
        "week": 1,
        "team": "ARZ",
        "gsis_id": "00-0000001",
        "status_description_abbr": "A01",
        "status_short_description": None,
        "position": "WR",
        "full_name": "Example Player",
    }
    return pl.DataFrame([{**base, **row} for row in rows])


def test_literal_duplicate_rows_are_distinguished_from_material_variants() -> None:
    frame = _frame([
        {},
        {},
        {"gsis_id": "00-0000002", "position": "RB"},
        {"gsis_id": "00-0000002", "position": "FB"},
    ])
    result = full_row_duplicate_diagnostics(season=2012, frame=frame)
    assert result["duplicate_identity_keys_total"] == 2
    assert result["duplicate_identity_keys_single_full_row_variant"] == 1
    assert result["duplicate_identity_keys_multiple_full_row_variants"] == 1
    assert result["literal_repeat_excess_rows"] == 1
    assert result["material_variant_excess_rows"] == 1
    assert result["differing_column_identity_counts"] == {"position": 1}


def test_team_alias_is_normalized_before_full_row_fingerprint() -> None:
    frame = _frame([
        {},
        {"team": "ARI"},
    ])
    result = full_row_duplicate_diagnostics(season=2012, frame=frame)
    assert result["duplicate_identity_keys_total"] == 1
    assert result["duplicate_identity_keys_single_full_row_variant"] == 1
    assert result["duplicate_identity_keys_multiple_full_row_variants"] == 0


def test_status_consistency_does_not_hide_other_column_differences() -> None:
    frame = _frame([
        {"position": "WR"},
        {"position": "KR"},
    ])
    result = full_row_duplicate_diagnostics(season=2012, frame=frame)
    assert result["duplicate_identity_keys_multiple_full_row_variants"] == 1
    example = next(iter(result["multiple_full_row_variant_examples"].values()))
    assert "position" in example["differing_columns"]
    assert "status_description_abbr" not in example["differing_columns"]


def test_v3_is_diagnostic_only_and_never_deduplicates() -> None:
    result = full_row_duplicate_diagnostics(season=2012, frame=_frame([{}, {}]))
    assert result["deduplication_performed"] is False
    assert result["qualification_authority"] is False
    assert result["status_semantics_interpreted"] is False
    assert result["v09b_model_fit_authorized"] is False
    assert result["completed_2026_outcomes_used"] == 0

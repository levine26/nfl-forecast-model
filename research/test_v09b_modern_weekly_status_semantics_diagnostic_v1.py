from __future__ import annotations

import polars as pl
import pytest

from research import v09b_modern_identity_source_capture_v1 as identity_capture
from research.v09b_modern_weekly_status_semantics_diagnostic_v1 import (
    _projection_index,
    _status_lookup,
    gamebook_name_signature,
    normalize_jersey,
    normalize_last_name,
    resolve_identity,
)


def _identity_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season": 2021,
        "game_type": "REG",
        "week": 1,
        "team": "ARI",
        "gsis_id": "00-0000001",
        "jersey_number": "10",
        "first_name": "DeAndre",
        "football_name": "DeAndre",
        "last_name": "Hopkins",
    }
    row.update(overrides)
    return row


def test_name_signature_is_narrow_and_deterministic() -> None:
    assert gamebook_name_signature("D.Hopkins") == ("D", "HOPKINS")
    assert gamebook_name_signature("A.St. Brown") == ("A", "STBROWN")
    assert gamebook_name_signature("NoDot") is None
    assert normalize_last_name("Smith Jr.") == "SMITH"
    assert normalize_last_name("Rodgers-Cromartie") == "RODGERSCROMARTIE"
    assert normalize_jersey(10.0) == "10"


def test_unique_identity_requires_name_evidence_not_candidate_uniqueness() -> None:
    candidates = [_identity_row()]
    good = resolve_identity(display_name="D.Hopkins", candidates=candidates)
    assert good["resolution"] == "resolved"
    assert good["gsis_id"] == "00-0000001"

    wrong_name = resolve_identity(display_name="A.Green", candidates=candidates)
    assert wrong_name["resolution"] == "unresolved"
    assert wrong_name["gsis_id"] is None


def test_multiple_matching_gsis_ids_remain_ambiguous() -> None:
    candidates = [
        _identity_row(gsis_id="00-0000001"),
        _identity_row(gsis_id="00-0000002"),
    ]
    result = resolve_identity(display_name="D.Hopkins", candidates=candidates)
    assert result["resolution"] == "ambiguous"
    assert result["matching_gsis_ids"] == ["00-0000001", "00-0000002"]


def test_status_fields_are_rejected_from_identity_resolver() -> None:
    for field in ("status", "status_description_abbr", "status_short_description"):
        candidate = _identity_row()
        candidate[field] = "ACT"
        with pytest.raises(ValueError, match="status field leaked"):
            resolve_identity(display_name="D.Hopkins", candidates=[candidate])


def test_projection_index_requires_exact_status_free_allowlist() -> None:
    frame = pl.DataFrame([_identity_row()]).select(list(identity_capture.ALLOWED_FIELDS))
    index = _projection_index(frame, season=2021)
    assert list(index) == [(1, "ARI", "10")]
    assert not {
        "status",
        "status_description_abbr",
        "status_short_description",
    } & set(index[(1, "ARI", "10")][0])

    contaminated = frame.with_columns(pl.lit("ACT").alias("status_description_abbr"))
    with pytest.raises(RuntimeError, match="allowlist"):
        _projection_index(contaminated, season=2021)


def test_status_lookup_is_post_resolution_keyed_by_gsis_and_preserves_both_status_layers() -> None:
    frame = pl.DataFrame(
        [
            {
                "season": 2021,
                "game_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "status": "ACT",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
            },
            {
                "season": 2021,
                "game_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "status": "ACT",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
            },
        ]
    )
    lookup = _status_lookup(frame, season=2021)
    assert lookup[(1, "ARI", "00-0000001")][("ACT", "A01", "Active")] == 2


def test_status_lookup_retains_generic_status_contradictions_separately() -> None:
    frame = pl.DataFrame(
        [
            {
                "season": 2021,
                "game_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "status": "ACT",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
            },
            {
                "season": 2021,
                "game_type": "REG",
                "week": 1,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "status": "INA",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
            },
        ]
    )
    lookup = _status_lookup(frame, season=2021)
    variants = lookup[(1, "ARI", "00-0000001")]
    assert variants[("ACT", "A01", "Active")] == 1
    assert variants[("INA", "A01", "Active")] == 1
    assert len(variants) == 2

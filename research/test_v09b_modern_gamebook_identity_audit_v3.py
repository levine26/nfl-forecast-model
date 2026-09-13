from __future__ import annotations

import polars as pl

from research import v09b_modern_position_identity_source_capture_v2 as position_capture
from research.v09b_modern_gamebook_identity_audit_v3 import (
    classify_position_family,
    wilson_lower_bound,
)


def _raw_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {
        "season": 2019,
        "game_type": "REG",
        "week": 1,
        "team": "WAS",
        "gsis_id": "00-0000001",
        "jersey_number": "46",
        "position": "DB",
        "status": "ACT",
        "status_description_abbr": "A01",
        "status_short_description": "Active",
    }
    return pl.DataFrame([{**base, **row} for row in rows])


def test_position_capture_selects_only_status_free_allowlist() -> None:
    projected = position_capture.project_position_source(season=2019, frame=_raw_frame([{}]))
    assert tuple(projected.columns) == position_capture.ALLOWED_FIELDS
    assert not set(position_capture.FORBIDDEN_STATUS_FIELDS) & set(projected.columns)
    assert projected.height == 1


def test_position_capture_filters_other_seasons_and_game_types() -> None:
    projected = position_capture.project_position_source(
        season=2019,
        frame=_raw_frame([{}, {"game_type": "PRE"}, {"season": 2018}]),
    )
    assert projected.height == 1


def test_secondary_family_accepts_broad_secondary_labels() -> None:
    for values in (["DB"], ["S", "DB"], ["CB"], ["FS/SS"], ["NB"]):
        result = classify_position_family(values)
        assert result["valid"] is True
        assert result["family"] == "secondary"


def test_linebacker_family_accepts_broad_linebacker_labels() -> None:
    for values in (["LB"], ["OLB", "LB"], ["ILB"], ["MLB"], ["SLB/WLB"]):
        result = classify_position_family(values)
        assert result["valid"] is True
        assert result["family"] == "linebacker"


def test_unknown_or_cross_family_evidence_fails_closed() -> None:
    unknown = classify_position_family(["DE"])
    assert unknown["valid"] is False
    assert unknown["reason"] == "unknown_or_other_family"
    mixed = classify_position_family(["DB/LB"])
    assert mixed["valid"] is False
    assert mixed["reason"] == "mixed"
    empty = classify_position_family([])
    assert empty["valid"] is False
    assert empty["reason"] == "empty"


def test_wilson_lower_bound_is_conservative() -> None:
    assert 0.94 < wilson_lower_bound(970, 1000) < 0.97
    assert wilson_lower_bound(0, 0) == 0.0


def test_frozen_source_constants_cover_all_five_seasons() -> None:
    assert set(position_capture.SEASONS) == {2017, 2018, 2019, 2020, 2021}
    assert set(position_capture.RAW_SOURCE_SHA256) == set(position_capture.SEASONS)
    assert set(position_capture.EXPECTED_REG_ROWS) == set(position_capture.SEASONS)
    assert set(position_capture.EXPECTED_MISSING_GSIS_ROWS) == set(position_capture.SEASONS)

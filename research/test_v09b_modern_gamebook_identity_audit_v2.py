from __future__ import annotations

import polars as pl

from research import v09b_modern_position_identity_source_capture_v1 as position_capture
from research.v09b_modern_gamebook_identity_audit_v2 import (
    classify_position_evidence,
    resolve_ambiguity_by_side,
)


def _raw_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {
        "season": 2019,
        "game_type": "REG",
        "week": 1,
        "team": "NYJ",
        "gsis_id": "00-0000001",
        "jersey_number": "33",
        "position": "DB",
        "status": "ACT",
        "status_description_abbr": "A01",
        "status_short_description": "Active",
    }
    return pl.DataFrame([{**base, **row} for row in rows])


def test_position_projection_selects_only_status_free_allowlist() -> None:
    projected = position_capture.project_position_source(frame=_raw_frame([{}]))
    assert tuple(projected.columns) == position_capture.ALLOWED_FIELDS
    assert not set(position_capture.FORBIDDEN_STATUS_FIELDS) & set(projected.columns)
    assert projected.height == 1


def test_position_projection_filters_non_regular_season_rows() -> None:
    projected = position_capture.project_position_source(
        frame=_raw_frame([{}, {"game_type": "PRE"}, {"season": 2018}])
    )
    assert projected.height == 1


def test_side_taxonomy_tolerates_detail_within_same_side() -> None:
    assert classify_position_evidence(["S", "DB"])["side"] == "defense"
    assert classify_position_evidence(["OLB", "LB"])["side"] == "defense"
    assert classify_position_evidence(["RB", "WR"])["side"] == "offense"
    assert classify_position_evidence(["K", "P", "LS"])["side"] == "special_teams"
    assert classify_position_evidence(["S/DB"])["side"] == "defense"


def test_mixed_or_unknown_position_fails_closed() -> None:
    mixed = classify_position_evidence(["WR/KR"])
    assert mixed["valid"] is False
    assert mixed["reason"] == "mixed"
    unknown = classify_position_evidence(["MYSTERY"])
    assert unknown["valid"] is False
    assert unknown["reason"] == "unknown"


def test_unique_same_side_candidate_resolves() -> None:
    result = resolve_ambiguity_by_side(
        gamebook_positions=["S"],
        candidate_positions={
            "00-0000001": ["DB"],
            "00-0000002": ["RB"],
        },
    )
    assert result["resolution"] == "resolved"
    assert result["resolved_gsis_id"] == "00-0000001"
    assert result["reason"] == "unique_same_side_candidate"


def test_multiple_same_side_candidates_remain_ambiguous() -> None:
    result = resolve_ambiguity_by_side(
        gamebook_positions=["OLB"],
        candidate_positions={
            "00-0000001": ["LB"],
            "00-0000002": ["DE"],
        },
    )
    assert result["resolution"] == "ambiguous"
    assert result["resolved_gsis_id"] is None
    assert result["reason"] == "multiple_same_side_candidates"


def test_unknown_candidate_position_prevents_resolution() -> None:
    result = resolve_ambiguity_by_side(
        gamebook_positions=["S"],
        candidate_positions={
            "00-0000001": ["DB"],
            "00-0000002": ["UNKNOWN"],
        },
    )
    assert result["resolution"] == "ambiguous"
    assert result["reason"] == "candidate_position_incomplete"


def test_empty_candidate_position_prevents_resolution() -> None:
    result = resolve_ambiguity_by_side(
        gamebook_positions=["S"],
        candidate_positions={
            "00-0000001": ["DB"],
            "00-0000002": [],
        },
    )
    assert result["resolution"] == "ambiguous"
    assert result["reason"] == "candidate_position_incomplete"

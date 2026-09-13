from __future__ import annotations

import polars as pl

from research import v09b_legacy_gamebook_identity_audit_v1 as identity_v1
from research import v09b_legacy_gamebook_identity_diagnostic_v2 as jersey_diag
from research import v09b_modern_identity_source_capture_v1 as identity_capture
from research.v09b_modern_gamebook_identity_audit_v1 import (
    _authorized_structural_candidates,
    _all_section_identities,
)


def _projection(rows: list[dict[str, object]]) -> pl.DataFrame:
    base = {
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
    return pl.DataFrame([{**base, **row} for row in rows]).select(list(identity_capture.ALLOWED_FIELDS))


def test_status_free_projection_supports_exact_identity_index() -> None:
    frame = _projection([{}])
    result = identity_v1.build_identity_index(season=2021, frame=frame)
    index = result.pop("index")
    assert result["source_identity_conflicts"] == 0
    assert result["missing_gsis_rows"] == 0
    assert index[(1, "ARI", "10", "DHOPKINS")] == {"00-0000001"}


def test_structural_fallback_requires_authorized_name_evidence() -> None:
    frame = _projection([
        {
            "gsis_id": "00-0000001",
            "jersey_number": "23",
            "first_name": "Ronald",
            "football_name": "Ronald",
            "last_name": "Darby",
        }
    ])
    source = jersey_diag.build_same_week_team_jersey_index(season=2021, frame=frame)
    jersey_index = source.pop("index")
    signatures = source.pop("signatures_by_gsis")
    authorized = _authorized_structural_candidates(
        display_name="R.Darby",
        week=1,
        team="ARI",
        jersey="23",
        jersey_index=jersey_index,
        signatures_by_gsis=signatures,
    )
    # Initial + exact surname is deliberately not an authorized stage-2-only rule.
    assert authorized == []


def test_structural_fallback_accepts_prequalified_compound_rule() -> None:
    frame = _projection([
        {
            "gsis_id": "00-0000002",
            "jersey_number": "17",
            "first_name": "Amon-Ra",
            "football_name": "Amon-Ra",
            "last_name": "St. Brown",
        }
    ])
    source = jersey_diag.build_same_week_team_jersey_index(season=2021, frame=frame)
    jersey_index = source.pop("index")
    signatures = source.pop("signatures_by_gsis")
    authorized = _authorized_structural_candidates(
        display_name="A.St.Brown",
        week=1,
        team="ARI",
        jersey="17",
        jersey_index=jersey_index,
        signatures_by_gsis=signatures,
    )
    assert len(authorized) == 1
    assert authorized[0]["gsis_id"] == "00-0000002"
    assert authorized[0]["method"] in {
        "given_initial_only+compound_component_prefix",
        "given_initial_only+gamebook_surname_is_source_leading_components",
        "given_initial_only+source_surname_is_gamebook_leading_components",
    }


def test_gamebook_identity_universe_is_all_four_sections_without_membership_interpretation() -> None:
    text = """
Lineups                                      Lineups
Offense                 Defense              Offense                 Defense
 10 D.Hopkins            3 B.Baker             1 K.Murray             7 I.Simmons
Substitutions                                Substitutions
 13 C.Kirk                                    18 A.Green
Did Not Play                                 Did Not Play
 44 M.Vallejo                                 82 M.Williams
Not Active                                   Not Active
 99 J.Watt                                     2 C.Jones
Field Goals                                  Field Goals
"""
    left, left_markers = _all_section_identities(text, side=0)
    right, right_markers = _all_section_identities(text, side=1)
    assert left_markers is True
    assert right_markers is True
    assert ("10", "D.Hopkins") in left
    assert ("13", "C.Kirk") in left
    assert ("44", "M.Vallejo") in left
    assert ("99", "J.Watt") in left
    assert ("1", "K.Murray") in right
    assert ("18", "A.Green") in right
    assert ("82", "M.Williams") in right
    assert ("2", "C.Jones") in right


def test_identity_projection_allowlist_excludes_all_status_fields() -> None:
    assert not set(identity_capture.FORBIDDEN_STATUS_FIELDS) & set(identity_capture.ALLOWED_FIELDS)

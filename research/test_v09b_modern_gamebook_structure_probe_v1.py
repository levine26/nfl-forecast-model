from __future__ import annotations

from research.v09b_modern_gamebook_structure_probe_v1 import (
    _heading_like,
    _unique_bounded,
    structure_candidates,
)


def test_structure_candidates_report_phrases_without_classifying_them() -> None:
    text = (
        "GAMEBOOK\n"
        "Lineups Lineups\n"
        "Substitutions Substitutions\n"
        "Not Active Not Active\n"
        "Did Not Play Did Not Play\n"
    )
    result = structure_candidates(text)
    assert result["literal_phrase_occurrence_counts"] == {
        "not_active": 2,
        "did_not_play": 2,
        "lineup": 2,
        "substitutions": 2,
    }
    assert "Not Active Not Active" in result["keyword_candidate_lines"]
    assert "Did Not Play Did Not Play" in result["keyword_candidate_lines"]


def test_heading_like_is_diagnostic_only_uppercase_shape() -> None:
    assert _heading_like("NOT ACTIVE") is True
    assert _heading_like("Not Active") is False
    assert _heading_like("12") is False


def test_unique_bounded_preserves_first_occurrence_and_limit() -> None:
    result = _unique_bounded([" A ", "A", " B ", "C"], 2)
    assert result == ["A", "B"]

from __future__ import annotations

from research.v09b_legacy_gamebook_identity_audit_v4 import (
    AUTHORIZED_METHODS,
    structural_candidate_authorized,
)
from research.v09b_legacy_gamebook_identity_name_compat_v3 import classify_candidate


def _classification(display: str, first: str, football: str, last: str) -> dict[str, object]:
    return classify_candidate(
        display,
        first_name=first,
        football_name=football,
        last_name=last,
    )


def test_authorized_method_set_excludes_weak_extended_tiers() -> None:
    assert "given_initial_only+surname_exact" not in AUTHORIZED_METHODS
    assert "given_absent+surname_exact" not in AUTHORIZED_METHODS
    assert "given_incompatible+surname_exact" not in AUTHORIZED_METHODS


def test_full_given_prefix_plus_exact_surname_is_authorized() -> None:
    c = _classification("St.Johnson", "Stevie", "Stevie", "Johnson")
    assert c["compatibility_method"] == "given_full_prefix+surname_exact"
    assert structural_candidate_authorized(c) is True


def test_initial_plus_nontrivial_compound_prefix_is_authorized() -> None:
    c = _classification("D.R-Cromartie", "Dominique", "Dominique", "Rodgers-Cromartie")
    assert c["compatibility_method"] == "given_initial_only+compound_component_prefix"
    assert c["strong_compatible"] is True
    assert structural_candidate_authorized(c) is True


def test_gamebook_truncated_compound_surname_is_authorized() -> None:
    c = _classification("D.Van", "DeMarcus", "DeMarcus", "Van Dyke")
    assert c["compatibility_method"] == "given_initial_only+gamebook_surname_is_source_leading_components"
    assert structural_candidate_authorized(c) is True


def test_source_shorter_surname_after_name_change_is_authorized() -> None:
    c = _classification("N.Robey-Coleman", "Nickell", "Nickell", "Robey")
    assert c["compatibility_method"] == "given_initial_only+source_surname_is_gamebook_leading_components"
    assert structural_candidate_authorized(c) is True


def test_initial_plus_exact_surname_remains_excluded_even_if_extended_compatible() -> None:
    c = _classification("D.Johnson", "David", "David", "Johnson")
    assert c["compatibility_method"] == "given_initial_only+surname_exact"
    assert c["extended_compatible"] is True
    assert structural_candidate_authorized(c) is False


def test_surname_only_match_remains_excluded() -> None:
    c = _classification("Williams", "Trey", "Trey", "Williams")
    assert c["compatibility_method"] == "given_absent+surname_exact"
    assert c["extended_compatible"] is True
    assert structural_candidate_authorized(c) is False


def test_rejected_unique_jersey_false_candidate_remains_excluded() -> None:
    c = _classification("R.Mallett", "Michael", "Michael", "Campanaro")
    assert structural_candidate_authorized(c) is False


def test_method_string_alone_cannot_bypass_v3_evidence_flags() -> None:
    forged = {
        "compatibility_method": "given_initial_only+compound_component_prefix",
        "strong_compatible": False,
        "extended_compatible": True,
    }
    assert structural_candidate_authorized(forged) is False

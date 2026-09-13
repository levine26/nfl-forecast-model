from __future__ import annotations

from research.v09b_legacy_gamebook_identity_name_compat_v3 import (
    classify_candidate,
    components,
    parse_gamebook_display,
)


def test_parse_preserves_compound_surname_components() -> None:
    parsed = parse_gamebook_display("D.R-Cromartie")
    assert parsed["given_fragment"] == "D"
    assert parsed["surname_compact"] == "RCROMARTIE"
    assert parsed["surname_components"] == ("R", "CROMARTIE")
    assert components("Rodgers-Cromartie") == ("RODGERS", "CROMARTIE")


def test_compound_abbreviation_can_supply_strong_structural_evidence() -> None:
    result = classify_candidate(
        "D.R-Cromartie",
        first_name="Dominique",
        football_name="Dominique",
        last_name="Rodgers-Cromartie",
    )
    assert result["given_evidence"] == "given_initial_only"
    assert result["surname_evidence"] == "compound_component_prefix"
    assert result["strong_compatible"] is True
    assert result["extended_compatible"] is True


def test_multi_character_given_prefix_plus_exact_surname_is_strong() -> None:
    result = classify_candidate(
        "St.Johnson",
        first_name="Stevie",
        football_name="Stevie",
        last_name="Johnson",
    )
    assert result["given_evidence"] == "given_full_prefix"
    assert result["surname_evidence"] == "surname_exact"
    assert result["strong_compatible"] is True


def test_initial_plus_exact_surname_is_reported_only_as_extended() -> None:
    result = classify_candidate(
        "D.Johnson",
        first_name="David",
        football_name="David",
        last_name="Johnson",
    )
    assert result["given_evidence"] == "given_initial_only"
    assert result["surname_evidence"] == "surname_exact"
    assert result["strong_compatible"] is False
    assert result["extended_compatible"] is True


def test_rejected_baltimore_mallett_to_campanaro_unique_jersey_candidate_is_incompatible() -> None:
    result = classify_candidate(
        "R.Mallett",
        first_name="Michael",
        football_name="Michael",
        last_name="Campanaro",
    )
    assert result["given_evidence"] == "given_incompatible"
    assert result["surname_evidence"] == "surname_incompatible"
    assert result["strong_compatible"] is False
    assert result["extended_compatible"] is False


def test_rejected_baltimore_wallace_to_hester_unique_jersey_candidate_is_incompatible() -> None:
    result = classify_candidate(
        "M.Wallace",
        first_name="Devin",
        football_name="Devin",
        last_name="Hester",
    )
    assert result["strong_compatible"] is False
    assert result["extended_compatible"] is False


def test_rejected_philadelphia_grugier_hill_candidates_are_incompatible() -> None:
    tulloch = classify_candidate(
        "K.Grugier-Hill",
        first_name="Stephen",
        football_name="Stephen",
        last_name="Tulloch",
    )
    skinner = classify_candidate(
        "K.Grugier-Hill",
        first_name="Deontae",
        football_name="Deontae",
        last_name="Skinner",
    )
    for result in (tulloch, skinner):
        assert result["strong_compatible"] is False
        assert result["extended_compatible"] is False


def test_given_absent_exact_surname_never_counts_as_strong() -> None:
    result = classify_candidate(
        "Johnson",
        first_name="David",
        football_name="David",
        last_name="Johnson",
    )
    assert result["given_evidence"] == "given_absent"
    assert result["surname_evidence"] == "surname_exact"
    assert result["strong_compatible"] is False
    assert result["extended_compatible"] is True


def test_no_fuzzy_or_phonetic_similarity_is_inferred() -> None:
    result = classify_candidate(
        "Jon.Smyth",
        first_name="John",
        football_name="John",
        last_name="Smith",
    )
    assert result["strong_compatible"] is False
    assert result["extended_compatible"] is False

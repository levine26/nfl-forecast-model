from __future__ import annotations

from research.v09b_legacy_gamebook_raw_archive_v2 import source_structure_signals_v2


def test_official_two_column_headings_without_colons_are_recognized() -> None:
    text = (
        "                                  Did Not Play                                                                          Did Not Play\n"
        "                                    Not Active                                                                           Not Active\n"
    )
    signals = source_structure_signals_v2(text)
    assert signals["not_active_heading_occurrences"] == 1
    assert signals["did_not_play_heading_occurrences"] == 1
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is True


def test_colon_layout_remains_recognized() -> None:
    signals = source_structure_signals_v2("Not Active: A. Player\nDid Not Play: B. Player\n")
    assert signals["not_active_structure_valid"] is True
    assert signals["did_not_play_structure_valid"] is True
    assert signals["semantic_headings_distinct"] is True


def test_narrative_mentions_do_not_count_as_heading_lines() -> None:
    text = "Narrative note: the player was Not Active before kickoff.\nAnother player Did Not Play.\n"
    signals = source_structure_signals_v2(text)
    assert signals["not_active_heading_occurrences"] == 0
    assert signals["did_not_play_heading_occurrences"] == 0
    assert signals["semantic_headings_distinct"] is False


def test_each_semantic_structure_is_still_independently_required() -> None:
    only_inactive = source_structure_signals_v2("   Not Active\n")
    assert only_inactive["not_active_structure_valid"] is True
    assert only_inactive["did_not_play_structure_valid"] is False
    assert only_inactive["semantic_headings_distinct"] is False

    only_dnp = source_structure_signals_v2("   Did Not Play\n")
    assert only_dnp["not_active_structure_valid"] is False
    assert only_dnp["did_not_play_structure_valid"] is True
    assert only_dnp["semantic_headings_distinct"] is False

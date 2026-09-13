from __future__ import annotations

from research.v09b_legacy_gamebook_roster_universe_v2 import (
    active_membership_diagnostics,
    parse_gamebook_roster_partitions_v2,
)
from research.v09b_legacy_gamebook_roster_universe_v1 import PlayerEntry


def _fixture() -> str:
    left = lambda text: text.ljust(80)
    return "\n".join(
        [
            " " * 78 + "Lineups",
            left("Arizona Cardinals") + "St. Louis Rams",
            left("Offense                         Defense") + "Offense                         Defense",
            left("QB 3 C.Palmer                  DE 93 C.Campbell") + "QB 8 S.Bradford                 DE 91 C.Long",
            left("                               Substitutions") + "                                        Substitutions",
            left("K 4 J.Feely, WR 12 A.Roberts") + "K 4 G.Zuerlein, WR 11 T.Austin",
            left("                               Did Not Play") + "                                        Did Not Play",
            left("QB 5 D.Stanton") + "QB 10 K.Clemens",
            left("                                 Not Active") + "                                         Not Active",
            left("CB 23 J.Fleming") + "S 20 D.Stewart",
            left("Field Goals (made & missed)") + "",
        ]
    )


def test_repeated_identity_within_one_section_is_diagnostic_only() -> None:
    entry = PlayerEntry(position="CB", jersey_number="31", display_name="A.Cromartie")
    sections = {
        "lineup": [entry, entry],
        "substitutions": [],
        "did_not_play": [],
        "not_active": [],
    }
    diag = active_membership_diagnostics(sections)
    assert diag["repeated_within_section_occurrences"] == 1
    assert diag["repeated_within_section_identities"] == 1
    assert diag["cross_semantic_section_conflicts"] == 0
    assert len(diag["active"]) == 1


def test_identity_in_two_distinct_active_sections_still_fails_duplicate_gate() -> None:
    entry = PlayerEntry(position="QB", jersey_number="3", display_name="C.Palmer")
    sections = {
        "lineup": [entry],
        "substitutions": [entry],
        "did_not_play": [],
        "not_active": [],
    }
    diag = active_membership_diagnostics(sections)
    assert diag["repeated_within_section_occurrences"] == 0
    assert diag["cross_semantic_section_conflicts"] == 1
    assert diag["cross_semantic_section_identities"][("3", "C.Palmer")] == ["lineup", "substitutions"]


def test_v2_preserves_normal_partition_semantics() -> None:
    markers, away, home = parse_gamebook_roster_partitions_v2(
        _fixture(), away_team="ARI", home_team="LA"
    )
    assert markers == {"lineups": 1, "substitutions": 1, "did_not_play": 1, "not_active": 1}
    assert away.active_candidate_count == 5
    assert away.not_active_count == 1
    assert away.duplicate_active_memberships == 0
    assert away.active_inactive_overlaps == 0
    assert home.active_candidate_count == 5
    assert home.not_active_count == 1


def test_v2_cross_section_duplicate_remains_hard_failure_signal() -> None:
    text = _fixture().replace("K 4 J.Feely, WR 12 A.Roberts", "QB 3 C.Palmer, WR 12 A.Roberts")
    _, away, _ = parse_gamebook_roster_partitions_v2(text, away_team="ARI", home_team="LA")
    assert away.duplicate_active_memberships == 1


def test_v2_active_inactive_overlap_remains_hard_failure_signal() -> None:
    text = _fixture().replace("CB 23 J.Fleming", "QB 3 C.Palmer")
    _, away, _ = parse_gamebook_roster_partitions_v2(text, away_team="ARI", home_team="LA")
    assert away.active_inactive_overlaps == 1

from __future__ import annotations

from research.v09b_legacy_gamebook_roster_universe_v1 import parse_gamebook_roster_partitions


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


def test_direct_gamebook_sections_define_disjoint_candidate_partitions() -> None:
    markers, away, home = parse_gamebook_roster_partitions(
        _fixture(), away_team="ARI", home_team="LA"
    )
    assert markers == {"lineups": 1, "substitutions": 1, "did_not_play": 1, "not_active": 1}
    assert away.active_candidate_count == 5
    assert away.not_active_count == 1
    assert away.active_inactive_overlaps == 0
    assert away.duplicate_active_memberships == 0
    assert home.active_candidate_count == 5
    assert home.not_active_count == 1
    assert home.active_inactive_overlaps == 0


def test_did_not_play_is_inside_active_candidate_union_not_inactive() -> None:
    _, away, _ = parse_gamebook_roster_partitions(_fixture(), away_team="ARI", home_team="LA")
    assert away.did_not_play_count == 1
    assert away.active_candidate_count == away.lineup_count + away.substitutions_count + away.did_not_play_count


def test_duplicate_player_across_active_sections_is_detected() -> None:
    text = _fixture().replace("K 4 J.Feely, WR 12 A.Roberts", "QB 3 C.Palmer, WR 12 A.Roberts")
    _, away, _ = parse_gamebook_roster_partitions(text, away_team="ARI", home_team="LA")
    assert away.duplicate_active_memberships == 1


def test_active_inactive_overlap_is_detected() -> None:
    text = _fixture().replace("CB 23 J.Fleming", "QB 3 C.Palmer")
    _, away, _ = parse_gamebook_roster_partitions(text, away_team="ARI", home_team="LA")
    assert away.active_inactive_overlaps == 1

"""Baseline comparator identity tests — no new candidate outcomes."""
from research.post_week4_phase4.reconcile_baselines import KNOWN_TIES, audit


def test_reference_equivalence_and_known_ties():
    report = audit()
    s = report["baseline_definitions"]
    assert report["paired_games"] == 1087
    assert s["season_forward"]["correct"] == 741
    assert s["frozen_final_coefficients"]["correct"] == 740
    assert set(x["game_id"] for x in report["three_known_ties"]) == set(KNOWN_TIES)
    assert all(x["wrongly_credited_as_away_win"] for x in report["three_known_ties"])
    assert s["static_exclude_ties_no_refit"]["fst_prob"]["games"] == 1084
    assert s["static_exclude_ties_no_refit"]["fst_prob"]["correct"] == 738
    assert report["production_changed"] is False
    assert report["outcomes_2026_used"] == 0

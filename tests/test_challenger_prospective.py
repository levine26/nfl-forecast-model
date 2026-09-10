from __future__ import annotations

import pandas as pd

from nfl_forecast.challenger_fst import FROZEN_CANDIDATE_ID
from nfl_forecast.challenger_prospective import evaluate_frozen_fst

FREEZE = "2026-09-10T05:08:04+00:00"


def _history(weeks: int = 16, games_per_week: int = 16) -> pd.DataFrame:
    rows = []
    for week in range(1, weeks + 1):
        for game in range(games_per_week):
            home_win = (game + week) % 2 == 0
            rows.append({
                "challenger_version": FROZEN_CANDIDATE_ID,
                "candidate_freeze_utc": FREEZE,
                "production_lock_timestamp_utc": f"2026-10-{min(week, 28):02d}T20:00:00+00:00",
                "season": 2026,
                "week": week,
                "actual_home_score": 27 if home_win else 17,
                "actual_away_score": 17 if home_win else 27,
                "challenger_final_home_prob": 0.75 if home_win else 0.25,
                "production_final_home_prob": 0.60 if home_win else 0.40,
                "market_home_prob_t120": 0.75 if home_win else 0.25,
                "challenger_pure_home_prob": 0.65 if home_win else 0.35,
            })
    return pd.DataFrame(rows)


def test_prospective_gate_requires_minimum_evidence_even_when_point_metrics_are_good():
    report, weekly = evaluate_frozen_fst(_history(weeks=5), bootstrap_samples=200)
    assert len(weekly) == 5
    assert report["games"] == 80
    assert report["promotion_gate"]["minimum_evidence_met"] is False
    assert report["promotion_gate_passed"] is False
    assert report["promotion_authorized"] is False
    assert report["2026_outcomes_used_for_model_tuning"] == 0


def test_predeclared_gate_passes_coherent_synthetic_evidence_but_never_auto_authorizes():
    report, weekly = evaluate_frozen_fst(_history(), bootstrap_samples=300)
    assert report["games"] == 256
    assert report["weeks"] == 16
    assert report["metrics"]["fst"]["brier"] < report["metrics"]["production"]["brier"]
    assert report["promotion_gate"]["minimum_evidence_met"] is True
    assert report["promotion_gate"]["A_vs_production_pass"] is True
    assert report["promotion_gate"]["B_vs_market_pass"] is True
    assert report["promotion_gate"]["C_week_coherence_pass"] is True
    assert report["promotion_gate_passed"] is True
    assert report["promotion_authorized"] is False
    assert weekly.fst_minus_production_brier.lt(0).all()


def test_games_locked_before_freeze_are_excluded_from_prospective_evidence():
    history = _history(weeks=1, games_per_week=4)
    prefreeze = history.iloc[[0]].copy()
    prefreeze["production_lock_timestamp_utc"] = "2026-09-10T05:00:00+00:00"
    combined = pd.concat([prefreeze, history], ignore_index=True)
    report, _ = evaluate_frozen_fst(combined, bootstrap_samples=100)
    assert report["excluded_prefreeze_rows"] == 1
    assert report["games"] == 4


def test_legacy_pre_fst_shadow_ledger_normalizes_to_awaiting_without_backfill():
    legacy = pd.DataFrame([{
        "game_id": "legacy_game",
        "research_candidate": "Old challenger",
        "challenger_pick": "HOME",
    }])
    report, weekly = evaluate_frozen_fst(legacy, bootstrap_samples=100)
    assert report["status"] == "awaiting_graded_games"
    assert report["games"] == 0
    assert report["weeks"] == 0
    assert report["promotion_gate_passed"] is False
    assert report["promotion_authorized"] is False
    assert weekly.empty

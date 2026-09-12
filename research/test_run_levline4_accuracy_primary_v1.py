from __future__ import annotations

import pandas as pd

from research.levline4_horizon_shadow_v1 import (
    FST_HORIZON_CANDIDATE_ID,
    MARKET_CANDIDATE_ID,
)
from research.run_levline4_accuracy_primary_v1 import build_report


def _row(game_id, horizon, candidate_id, prob, incumbent, home_win, week=1):
    kickoff = pd.Timestamp("2026-09-13T20:00:00Z")
    horizon_minutes = {"T-120m": 120, "T-60m": 60, "T-45m": 45, "T-30m": 30}[horizon]
    target = kickoff - pd.Timedelta(minutes=horizon_minutes)
    return {
        "game_id": game_id,
        "horizon": horizon,
        "candidate_id": candidate_id,
        "final_home_prob": prob,
        "kickoff_timestamp_utc": kickoff.isoformat(),
        "market_timing_error_minutes": -1.0,
        "season": 2026,
        "week": week,
        "target_timestamp_utc": target.isoformat(),
        "market_snapshot_request_timestamp_utc": (target - pd.Timedelta(minutes=1)).isoformat(),
        "incumbent_for_test": incumbent,
        "home_win_for_test": home_win,
    }


def _inputs():
    rows = []
    for game_id, home_win, incumbent in [("g1", 1, 0.52), ("g2", 0, 0.52)]:
        for horizon, market_prob, fst_prob in [
            ("T-120m", 0.51, 0.52),
            ("T-60m", 0.49 if game_id == "g2" else 0.53, 0.48 if game_id == "g2" else 0.54),
            ("T-45m", 0.48 if game_id == "g2" else 0.54, 0.47 if game_id == "g2" else 0.55),
            ("T-30m", 0.47 if game_id == "g2" else 0.55, 0.46 if game_id == "g2" else 0.56),
        ]:
            rows.append(_row(game_id, horizon, MARKET_CANDIDATE_ID, market_prob, incumbent, home_win))
            rows.append(_row(game_id, horizon, FST_HORIZON_CANDIDATE_ID, fst_prob, incumbent, home_win))
    shadows = pd.DataFrame(rows)
    history = pd.DataFrame([
        {
            "game_id": "g1",
            "season": 2026,
            "week": 1,
            "lock_status": "LOCKED",
            "actual_home_score": 24,
            "actual_away_score": 20,
            "final_home_prob": 0.52,
        },
        {
            "game_id": "g2",
            "season": 2026,
            "week": 1,
            "lock_status": "LOCKED",
            "actual_home_score": 17,
            "actual_away_score": 21,
            "final_home_prob": 0.52,
        },
    ])
    return shadows, history


def test_accuracy_report_centers_switches_against_incumbent() -> None:
    shadows, history = _inputs()
    report = build_report(shadows, history)
    assert report["raw_market_all_four_complete_case_games"] == 2
    t45 = report["candidate_vs_incumbent_accuracy"]["raw_market"]["T-45m"]
    assert t45["games"] == 2
    assert t45["candidate_accuracy"] == 1.0
    assert t45["benchmark_accuracy"] == 0.5
    assert t45["candidate_only_correct"] == 1
    assert t45["benchmark_only_correct"] == 0
    assert t45["discordant_games"] == 1
    assert t45["switch_win_rate"] == 1.0
    assert report["production_authorized"] is False
    assert report["promotion_authorized"] is False


def test_post_cutoff_shadow_is_excluded_from_accuracy_report() -> None:
    shadows, history = _inputs()
    mask = (
        shadows["game_id"].eq("g2")
        & shadows["horizon"].eq("T-45m")
    )
    shadows.loc[mask, "market_timing_error_minutes"] = 0.25
    report = build_report(shadows, history)
    assert report["strict_pit_audit"]["excluded_post_cutoff_rows"] == 2
    assert report["raw_market_all_four_complete_case_games"] == 1


def test_pre_contract_game_is_audit_only_not_primary_evidence() -> None:
    shadows, history = _inputs()
    shadows["kickoff_timestamp_utc"] = "2026-09-11T00:00:00+00:00"
    report = build_report(shadows, history)
    assert report["gate_status"] == "awaiting_graded_post_contract_games"
    assert report["prospective_sample"]["eligible_games"] == 0

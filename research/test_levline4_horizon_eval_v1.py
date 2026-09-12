from __future__ import annotations

import pandas as pd
import pytest

import research.levline4_horizon_eval_v1 as evaluator
from research.levline4_horizon_shadow_v1 import (
    FST_HORIZON_CANDIDATE_ID,
    MARKET_CANDIDATE_ID,
)


def _history(game_id: str, *, week: int, home_win: bool, incumbent: float = 0.55) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": week,
        "lock_status": "LOCKED",
        "actual_home_score": 24 if home_win else 17,
        "actual_away_score": 17 if home_win else 24,
        "final_home_prob": incumbent,
    }


def _shadow(game_id: str, candidate: str, horizon: str, probability: float) -> dict:
    return {
        "game_id": game_id,
        "season": None,
        "week": None,
        "candidate_id": candidate,
        "horizon": horizon,
        "final_home_prob": probability,
    }


def test_scores_only_graded_rows_and_uses_brier() -> None:
    shadows = pd.DataFrame(
        [
            _shadow("g1", MARKET_CANDIDATE_ID, "T-45m", 0.70),
            _shadow("g2", MARKET_CANDIDATE_ID, "T-45m", 0.40),
            _shadow("g3", MARKET_CANDIDATE_ID, "T-45m", 0.80),
        ]
    )
    history = pd.DataFrame(
        [
            _history("g1", week=1, home_win=True),
            _history("g2", week=1, home_win=False),
            {**_history("g3", week=1, home_win=True), "actual_home_score": None, "actual_away_score": None},
        ]
    )
    scored = evaluator.score_rows(shadows, history)
    assert scored.excluded_ungraded == 1
    assert scored.excluded_ties == 0
    assert len(scored.frame) == 2
    expected = ((0.70 - 1.0) ** 2 + (0.40 - 0.0) ** 2) / 2
    assert scored.frame["brier_loss"].mean() == pytest.approx(expected)


def test_invalid_probabilities_are_excluded_not_clipped() -> None:
    shadows = pd.DataFrame(
        [
            _shadow("g1", MARKET_CANDIDATE_ID, "T-45m", -0.2),
            _shadow("g2", MARKET_CANDIDATE_ID, "T-45m", 1.2),
            _shadow("g3", MARKET_CANDIDATE_ID, "T-45m", 0.6),
        ]
    )
    history = pd.DataFrame(
        [
            _history("g1", week=1, home_win=True),
            _history("g2", week=1, home_win=True),
            _history("g3", week=1, home_win=True),
        ]
    )
    scored = evaluator.score_rows(shadows, history)
    assert scored.excluded_invalid_probability == 2
    assert list(scored.frame["game_id"]) == ["g3"]
    assert scored.frame.iloc[0]["prob"] == pytest.approx(0.6)


def test_ties_are_excluded_from_binary_grading() -> None:
    shadows = pd.DataFrame([_shadow("tie", MARKET_CANDIDATE_ID, "T-45m", 0.60)])
    tied = _history("tie", week=1, home_win=True)
    tied["actual_home_score"] = 20
    tied["actual_away_score"] = 20
    scored = evaluator.score_rows(shadows, pd.DataFrame([tied]))
    assert scored.excluded_ties == 1
    assert scored.excluded_ungraded == 0
    assert scored.frame.empty


def test_same_horizon_pairing_rejects_unpaired_games() -> None:
    candidate = pd.DataFrame(
        [
            {"game_id": "g1", "horizon": "T-45m", "brier_loss": 0.04, "log_loss": 0.2, "prob": 0.8, "home_win": 1.0, "season_official": 2026, "week_official": 1},
            {"game_id": "g2", "horizon": "T-45m", "brier_loss": 0.09, "log_loss": 0.3, "prob": 0.7, "home_win": 1.0, "season_official": 2026, "week_official": 2},
        ]
    )
    benchmark = pd.DataFrame(
        [
            {"game_id": "g1", "horizon": "T-45m", "brier_loss": 0.09, "log_loss": 0.3, "prob": 0.7, "home_win": 1.0, "season_official": 2026, "week_official": 1},
            {"game_id": "g3", "horizon": "T-45m", "brier_loss": 0.01, "log_loss": 0.1, "prob": 0.9, "home_win": 1.0, "season_official": 2026, "week_official": 2},
        ]
    )
    result = evaluator.paired_comparison(candidate, benchmark, label="market")
    assert result["games"] == 1
    assert result["brier_delta"] == pytest.approx(-0.05)


def test_primary_horizon_comparison_requires_all_four_horizons() -> None:
    rows = []
    histories = []
    for gid in ("complete", "missing_t120"):
        histories.append(_history(gid, week=1, home_win=True))
    for horizon, prob in (
        ("T-120m", 0.58),
        ("T-60m", 0.60),
        ("T-45m", 0.65),
        ("T-30m", 0.70),
    ):
        rows.append(_shadow("complete", MARKET_CANDIDATE_ID, horizon, prob))
    for horizon in ("T-60m", "T-45m", "T-30m"):
        rows.append(_shadow("missing_t120", MARKET_CANDIDATE_ID, horizon, 0.99))

    report = evaluator.evaluate(pd.DataFrame(rows), pd.DataFrame(histories))
    common = report["common_game_horizon_comparison"][MARKET_CANDIDATE_ID]
    assert common["common_games"] == 1
    assert common["required_horizons"] == list(evaluator.PRIMARY_HORIZONS)
    assert common["horizons"]["T-120m"]["games"] == 1
    assert common["horizons"]["T-30m"]["games"] == 1
    assert "T-120m_to_T-30m" in common["contrasts"]
    assert common["selection_authorized"] is False


def test_sample_gate_requires_four_horizon_market_intersection_and_never_selects(monkeypatch) -> None:
    monkeypatch.setattr(evaluator, "MIN_GAMES", 2)
    monkeypatch.setattr(evaluator, "MIN_WEEKS", 2)
    monkeypatch.setattr(evaluator, "BOOTSTRAP_DRAWS", 100)

    shadows = []
    history = []
    for i, (week, home_win) in enumerate(((1, True), (2, False)), start=1):
        gid = f"g{i}"
        history.append(_history(gid, week=week, home_win=home_win, incumbent=0.55))
        market_prob = 0.60 if home_win else 0.40
        fst_prob = 0.70 if home_win else 0.30
        for horizon in evaluator.PRIMARY_HORIZONS:
            shadows.append(_shadow(gid, MARKET_CANDIDATE_ID, horizon, market_prob))
            shadows.append(_shadow(gid, FST_HORIZON_CANDIDATE_ID, horizon, fst_prob))

    report = evaluator.evaluate(pd.DataFrame(shadows), pd.DataFrame(history))
    assert report["gate_status"] == "SAMPLE_GATE_REACHED_FORMAL_FAMILY_INFERENCE_REQUIRED"
    assert report["primary_timing_sample_ready"] is True
    assert report["formal_family_inference_required"] is True
    assert report["promotion_authorized"] is False
    assert report["horizon_selection_authorized"] is False
    for horizon in evaluator.PRIMARY_HORIZONS:
        comparison = report["paired_model_vs_same_horizon_market"][horizon]
        assert comparison["games"] == 2
        assert comparison["brier_delta"] < 0


def test_duplicate_shadow_identity_fails_closed() -> None:
    row = _shadow("g1", MARKET_CANDIDATE_ID, "T-45m", 0.60)
    shadows = pd.DataFrame([row, row])
    with pytest.raises(ValueError, match="duplicate forecast identities"):
        evaluator.evaluate(shadows, pd.DataFrame([_history("g1", week=1, home_win=True)]))


def test_no_outcomes_means_waiting_not_zero_performance() -> None:
    report = evaluator.evaluate(
        pd.DataFrame([_shadow("g1", MARKET_CANDIDATE_ID, "T-45m", 0.60)]),
        pd.DataFrame([{
            **_history("g1", week=1, home_win=True),
            "actual_home_score": None,
            "actual_away_score": None,
        }]),
    )
    assert report["gate_status"] == "WAITING_FOR_GRADED_SHADOWS"
    assert report["graded_shadow_rows"] == 0
    assert report["promotion_authorized"] is False

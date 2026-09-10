from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_fst import (
    FROZEN_CANDIDATE_ID,
    fit_frozen_2026_stack,
    frozen_stack_probability,
)
from nfl_forecast.challenger_shadow import lock_shadow


def _training_frame() -> pd.DataFrame:
    rows = []
    for season in range(2019, 2026):
        for i in range(60):
            market = 0.35 + 0.005 * (i % 40)
            pure = 0.40 + 0.004 * ((i * 7) % 35)
            rows.append({
                "season": season,
                "home_win": int((i + season) % 3 != 0),
                "market_prob": market,
                "pure_prob": pure,
            })
    return pd.DataFrame(rows)


def _production(market: float = 0.64) -> pd.DataFrame:
    return pd.DataFrame([{
        "game_id": "2026_01_AWAY_HOME",
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-10",
        "gametime": "19:30",
        "away_team": "AWAY",
        "home_team": "HOME",
        "market_home_prob": market,
        "final_home_prob": 0.58,
        "snapshot_type": "FINAL",
        "model_version": "production-v1",
        "prediction_timestamp_utc": "2026-09-10T21:58:00+00:00",
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-09-10T22:00:00+00:00",
        "kickoff_utc": "2026-09-10T23:30:00+00:00",
        "minutes_to_kickoff_at_lock": 90.0,
        "actual_home_score": np.nan,
        "actual_away_score": np.nan,
    }])


def _fst_shadow(fit, *, generated: str = "2026-09-10T18:00:00+00:00") -> pd.DataFrame:
    pure = 0.55
    stale_market = 0.51
    stale_preview = frozen_stack_probability(
        [stale_market], [pure],
        intercept=fit.intercept,
        market_logit_coefficient=fit.market_logit_coefficient,
        pure_logit_coefficient=fit.pure_logit_coefficient,
    )[0]
    return pd.DataFrame([{
        "game_id": "2026_01_AWAY_HOME",
        "challenger_pure_home_prob": pure,
        "market_home_prob": stale_market,
        "challenger_final_home_prob": stale_preview,
        "research_candidate": "F-ST-01",
        "research_method": "stack",
        "research_feature_set": "market_plus_v08_pure_logit_stack",
        "challenger_version": FROZEN_CANDIDATE_ID,
        "selected_shadow_candidate": True,
        "effective_pure_weight": np.nan,
        "effective_market_weight": np.nan,
        "shadow_generated_utc": generated,
        "shadow_source_sha": "source123",
        "training_cutoff": "2025",
        "training_games": fit.training_games,
        "training_first_season": fit.training_first_season,
        "training_last_season": fit.training_last_season,
        "training_data_sha256": fit.training_data_sha256,
        "stack_intercept": fit.intercept,
        "stack_market_logit_coefficient": fit.market_logit_coefficient,
        "stack_pure_logit_coefficient": fit.pure_logit_coefficient,
        "candidate_freeze_utc": "2026-09-10T05:08:04Z",
        "candidate_code_sha": "59830d23e406d32c34e74919b31d0dd9f85b16ca",
    }])


def test_frozen_fit_is_deterministic_and_refuses_2026_rows():
    frame = _training_frame()
    first = fit_frozen_2026_stack(frame)
    second = fit_frozen_2026_stack(frame.sample(frac=1.0, random_state=26))
    assert first.training_games == second.training_games
    assert first.training_data_sha256 == second.training_data_sha256
    assert np.isclose(first.intercept, second.intercept)
    assert np.isclose(first.market_logit_coefficient, second.market_logit_coefficient)
    assert np.isclose(first.pure_logit_coefficient, second.pure_logit_coefficient)

    contaminated = pd.concat([
        frame,
        pd.DataFrame([{"season": 2026, "home_win": 1, "market_prob": 0.7, "pure_prob": 0.6}]),
    ], ignore_index=True)
    with pytest.raises(ValueError, match="2026-or-later"):
        fit_frozen_2026_stack(contaminated)


def test_fst_lock_recomputes_with_authoritative_t120_market_and_records_reproducibility():
    fit = fit_frozen_2026_stack(_training_frame())
    history, added, skipped = lock_shadow(
        _production(market=0.64),
        _fst_shadow(fit),
        now_utc=datetime(2026, 9, 10, 22, 1, tzinfo=timezone.utc),
    )
    assert added == 1 and skipped == 0
    row = history.iloc[0]
    expected = frozen_stack_probability(
        [0.64], [0.55],
        intercept=fit.intercept,
        market_logit_coefficient=fit.market_logit_coefficient,
        pure_logit_coefficient=fit.pure_logit_coefficient,
    )[0]
    assert np.isclose(float(row.challenger_final_home_prob), expected)
    assert np.isclose(float(row.market_home_prob_t120), 0.64)
    assert np.isclose(float(row.production_final_home_prob), 0.58)
    assert row.challenger_version == FROZEN_CANDIDATE_ID
    assert row.training_cutoff == "2025"
    assert row.training_data_sha256 == fit.training_data_sha256
    assert np.isclose(float(row.stack_intercept), fit.intercept)
    assert np.isnan(float(row.effective_pure_weight))


def test_fst_generated_after_authoritative_lock_is_not_backfilled():
    fit = fit_frozen_2026_stack(_training_frame())
    history, added, skipped = lock_shadow(
        _production(),
        _fst_shadow(fit, generated="2026-09-10T22:00:01+00:00"),
    )
    assert history.empty
    assert added == 0
    assert skipped == 1


def test_frozen_candidate_spec_is_non_promoting_and_architecture_locked():
    spec = json.loads(Path("research/fst/F-ST-01-FROZEN-2026.json").read_text())
    assert spec["candidate_id"] == FROZEN_CANDIDATE_ID
    assert spec["production_promotion_authorized"] is False
    assert spec["production_behavior_must_remain_unchanged"] is True
    assert spec["architecture"] == {
        "inputs": ["logit(market_home_prob)", "logit(v0.8 PURE home probability)"],
        "meta_model": "logistic_regression",
        "fit_intercept": True,
        "penalty": "l2",
        "C": 1.0,
        "solver": "lbfgs",
        "max_iter": 3000,
        "probability_clip": [0.000001, 0.999999],
    }
    assert spec["training_policy"]["2026_outcomes_allowed"] is False
    assert spec["promotion_evaluation_policy"]["automatic_promotion"] is False


def test_training_cutoff_csv_roundtrip_is_compared_numerically(tmp_path):
    mixed_path = tmp_path / "mixed.csv"
    fst_path = tmp_path / "fst.csv"
    pd.DataFrame({
        "selected_shadow_candidate": [False, True],
        "training_cutoff": [np.nan, "2025"],
    }).to_csv(mixed_path, index=False)
    pd.DataFrame({"training_cutoff": ["2025"]}).to_csv(fst_path, index=False)

    mixed = pd.read_csv(mixed_path)
    selected = mixed.loc[mixed.selected_shadow_candidate, "training_cutoff"].reset_index(drop=True)
    fst = pd.read_csv(fst_path)["training_cutoff"].reset_index(drop=True)

    assert not selected.astype(str).equals(fst.astype(str))
    assert np.allclose(
        pd.to_numeric(selected, errors="raise"),
        pd.to_numeric(fst, errors="raise"),
        equal_nan=False,
    )

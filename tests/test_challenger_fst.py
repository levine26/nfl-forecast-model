from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_fst import (
    FROZEN_CANDIDATE_ID,
    FrozenStackFit,
    fit_frozen_2026_stack,
    frozen_stack_probability,
)
from nfl_forecast.challenger_shadow import lock_shadow
from nfl_forecast.fst_provenance import (
    capture_fst_pre_fit_provenance,
    write_fst_fit_provenance,
)


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


def _provenance_inputs():
    idx = pd.Index([101, 205, 309, 412])
    historical = pd.DataFrame(
        {
            "game_id": ["2019_01_A_B", "2020_02_C_D", "2024_03_E_F", "2025_04_G_H"],
            "season": [2019, 2020, 2024, 2025],
            "home_win": [0, 1, 0, 1],
        },
        index=idx,
    )
    base_oof = pd.DataFrame(
        {
            "logistic": [0.5000000000000001, 0.61, 0.42, 0.77],
            "extra_trees": [0.49, 0.63, 0.40, 0.74],
            "xgboost": [0.47, 0.62, 0.41, 0.76],
            "catboost": [0.51, 0.60, 0.43, 0.75],
            "home_win": [0, 1, 0, 1],
            "season": [2019, 2020, 2024, 2025],
        },
        index=idx,
    )
    training = pd.DataFrame(
        {
            "season": [2020, 2024, 2025],
            "home_win": [1, 0, 1],
            "market_prob": [0.58, 0.44, 0.71],
            "pure_prob": [0.57, 0.46, 0.69],
        },
        index=idx[1:],
    )
    return historical, base_oof, training


def test_fst_provenance_persists_exact_order_and_canonical_keyed_identity(tmp_path):
    historical, base_oof, training = _provenance_inputs()

    first = capture_fst_pre_fit_provenance(
        historical,
        base_oof,
        training,
        tmp_path / "first",
        candidate_id=FROZEN_CANDIDATE_ID,
    )
    second = capture_fst_pre_fit_provenance(
        historical,
        base_oof,
        training,
        tmp_path / "second",
        candidate_id=FROZEN_CANDIDATE_ID,
    )
    assert first == second

    keyed = pd.read_csv(tmp_path / "first" / "base_oof_keyed.csv")
    assert keyed["game_id"].tolist() == historical["game_id"].tolist()
    assert keyed["row_position"].tolist() == list(range(len(base_oof)))
    assert first["base_oof"]["raw_sha256"] == second["base_oof"]["raw_sha256"]

    shuffled = capture_fst_pre_fit_provenance(
        historical,
        base_oof.iloc[::-1],
        training.iloc[::-1],
        tmp_path / "shuffled",
        candidate_id=FROZEN_CANDIDATE_ID,
    )
    assert shuffled["base_oof"]["raw_sha256"] != first["base_oof"]["raw_sha256"]
    assert (
        shuffled["base_oof"]["game_id_sequence_sha256"]
        != first["base_oof"]["game_id_sequence_sha256"]
    )
    assert (
        shuffled["base_oof"]["canonical_game_keyed_sha256"]
        == first["base_oof"]["canonical_game_keyed_sha256"]
    )
    assert (
        shuffled["training_frame"]["canonical_game_keyed_sha256"]
        == first["training_frame"]["canonical_game_keyed_sha256"]
    )


def test_fst_fit_provenance_distinguishes_raw_input_hash_from_model_digest(tmp_path):
    historical, base_oof, training = _provenance_inputs()
    inputs = capture_fst_pre_fit_provenance(
        historical,
        base_oof,
        training,
        tmp_path,
        candidate_id=FROZEN_CANDIDATE_ID,
    )
    fit = FrozenStackFit(
        intercept=-0.1,
        market_logit_coefficient=1.1,
        pure_logit_coefficient=-0.2,
        training_games=len(training),
        training_first_season=2020,
        training_last_season=2025,
        training_data_sha256="f" * 64,
    )
    manifest = write_fst_fit_provenance(tmp_path, inputs, fit)
    assert manifest["model_training_data_sha256"] == "f" * 64
    assert manifest["training_frame_raw_sha256"] == inputs["training_frame"]["raw_sha256"]
    assert manifest["model_training_data_sha256"] != manifest["training_frame_raw_sha256"]
    assert manifest["runtime"]["python_version"]
    assert manifest["runtime"]["numpy_version"]
    assert manifest["runtime"]["scipy_version"]
    assert manifest["runtime"]["scikit_learn_version"]
    assert isinstance(manifest["runtime"]["threadpools"], list)
    assert (tmp_path / "inputs_manifest.json").is_file()
    assert (tmp_path / "fit_manifest.json").is_file()


def test_fst_provenance_fails_closed_on_ambiguous_or_post_cutoff_rows(tmp_path):
    historical, base_oof, training = _provenance_inputs()

    duplicate_ids = historical.copy()
    duplicate_ids.loc[205, "game_id"] = duplicate_ids.loc[101, "game_id"]
    with pytest.raises(ValueError, match="duplicate game_id"):
        capture_fst_pre_fit_provenance(
            duplicate_ids,
            base_oof,
            training,
            tmp_path / "duplicate",
            candidate_id=FROZEN_CANDIDATE_ID,
        )

    contaminated = training.copy()
    contaminated.loc[412, "season"] = 2026
    with pytest.raises(ValueError, match="post-2025"):
        capture_fst_pre_fit_provenance(
            historical,
            base_oof,
            contaminated,
            tmp_path / "contaminated",
            candidate_id=FROZEN_CANDIDATE_ID,
        )

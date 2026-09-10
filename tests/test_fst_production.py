from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import nfl_forecast.fst_production as fst_production
from nfl_forecast.challenger import build_nested_stack_oof as research_nested_oof
from nfl_forecast.fst_nested_pure import (
    BASE_MODEL_NAMES,
    build_nested_stack_oof as production_nested_oof,
)
from nfl_forecast.fst_production import (
    CANDIDATE_ID,
    EXPECTED_FIRST_SEASON,
    EXPECTED_INTERCEPT,
    EXPECTED_LAST_SEASON,
    EXPECTED_MARKET_COEF,
    EXPECTED_PURE_COEF,
    EXPECTED_TRAINING_GAMES,
    EXPECTED_TRAINING_SHA256,
    LEGACY_PRODUCTION_STRATEGY,
    canonical_training_hash,
    frozen_fst_probability,
    legacy_final_home_probability,
    load_fst_artifact,
    score_official_fst,
)
from nfl_forecast.publish import CURRENT_COLUMNS, _load_official
from scripts.run_challenger_fst_evaluation import _attach_production_regime


def test_frozen_artifact_identity_is_exact():
    artifact = load_fst_artifact()
    assert artifact.candidate_id == CANDIDATE_ID == "F-ST-01-FROZEN-2026"
    assert artifact.intercept == EXPECTED_INTERCEPT == -0.06954359363166639
    assert artifact.market_logit_coefficient == EXPECTED_MARKET_COEF == 1.1939087340527093
    assert artifact.pure_logit_coefficient == EXPECTED_PURE_COEF == -0.19342747983803402
    assert artifact.training_games == EXPECTED_TRAINING_GAMES == 1615
    assert artifact.training_first_season == EXPECTED_FIRST_SEASON == 2020
    assert artifact.training_last_season == EXPECTED_LAST_SEASON == 2025
    assert artifact.training_data_sha256 == EXPECTED_TRAINING_SHA256 == "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
    assert artifact.C == 1.0
    assert artifact.penalty == "l2"
    assert artifact.solver == "lbfgs"
    assert artifact.max_iter == 3000
    assert artifact.training_cutoff <= 2025
    assert artifact.outcomes_2026_used == 0


def test_fst_matches_hand_computed_logit_fixture():
    artifact = load_fst_artifact()
    market = np.array([0.60])
    pure = np.array([0.55])
    score = (
        -0.06954359363166639
        + 1.1939087340527093 * math.log(0.60 / 0.40)
        - 0.19342747983803402 * math.log(0.55 / 0.45)
    )
    expected = 1.0 / (1.0 + math.exp(-score))
    actual = frozen_fst_probability(market, pure, artifact)[0]
    assert actual == pytest.approx(expected, abs=1e-15, rel=0.0)


def test_missing_and_nonfinite_market_fall_back_to_legacy_without_crash():
    artifact = load_fst_artifact()
    index = pd.Index(["usable", "missing", "infinite"])
    legacy_pure = pd.Series([0.60, 0.40, 0.70], index=index)
    fst_pure = pd.Series([0.58, 0.42, 0.68], index=index)
    market = pd.Series([0.65, np.nan, np.inf], index=index)
    scored = score_official_fst(legacy_pure, fst_pure, market, artifact)

    expected_usable = frozen_fst_probability(np.array([0.65]), np.array([0.58]), artifact)[0]
    assert scored.final_home_prob.loc["usable"] == pytest.approx(expected_usable, abs=1e-15)
    assert scored.final_home_prob.loc["missing"] == pytest.approx(0.40)
    assert scored.final_home_prob.loc["infinite"] == pytest.approx(0.70)
    assert scored.fst_fallback.to_dict() == {"usable": False, "missing": True, "infinite": True}
    assert scored.fst_fallback_reason.loc["missing"] == "market_missing"
    assert scored.fst_fallback_reason.loc["infinite"] == "market_non_finite"
    assert np.isfinite(scored.final_home_prob.to_numpy()).all()
    assert ((scored.final_home_prob > 0.0) & (scored.final_home_prob < 1.0)).all()


def test_legacy_counterfactual_is_previous_production_expression():
    pure = pd.Series([0.2, 0.5, 0.8, 0.33])
    market = pd.Series([0.4, 0.6, 0.7, np.nan])
    actual = legacy_final_home_probability(pure, market)
    expected = pure.copy()
    mask = market.notna()
    expected.loc[mask] = 0.75 * pure.loc[mask] + 0.25 * market.loc[mask]
    np.testing.assert_array_equal(actual.to_numpy(), expected.to_numpy())


def test_one_line_rollback_switch_restores_exact_legacy_probability(monkeypatch):
    artifact = load_fst_artifact()
    pure = pd.Series([0.2, 0.5, 0.8])
    fst_pure = pd.Series([0.3, 0.6, 0.7])
    market = pd.Series([0.4, np.nan, 0.65])
    expected = legacy_final_home_probability(pure, market)
    monkeypatch.setattr(
        fst_production,
        "ACTIVE_PRODUCTION_STRATEGY",
        LEGACY_PRODUCTION_STRATEGY,
    )
    scored = fst_production.score_official_fst(pure, fst_pure, market, artifact)
    np.testing.assert_array_equal(scored.final_home_prob.to_numpy(), expected.to_numpy())


def test_training_digest_rejects_2026_outcomes():
    frame = pd.DataFrame({
        "season": [2025, 2026],
        "home_win": [1, 0],
        "market_prob": [0.6, 0.4],
        "pure_prob": [0.55, 0.45],
    })
    with pytest.raises(RuntimeError, match="2026-or-later"):
        canonical_training_hash(frame)


def test_unknown_or_modified_artifact_is_rejected(tmp_path: Path):
    source = Path("src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["candidate_id"] = "UNKNOWN"
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="candidate_id"):
        load_fst_artifact(path)

    payload["candidate_id"] = CANDIDATE_ID
    payload["market_logit_coefficient"] = EXPECTED_MARKET_COEF + 1e-12
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="market coefficient"):
        load_fst_artifact(path)


def test_production_nested_meta_matches_research_on_deterministic_fixture():
    rows = []
    idx = []
    for season in range(2018, 2026):
        for game in range(80):
            x = (game + 3 * season) / 97.0
            rows.append({
                "season": season,
                "home_win": (game + season) % 2,
                "logistic": 0.15 + 0.70 * ((x * 1.1) % 1.0),
                "extra_trees": 0.15 + 0.70 * ((x * 1.3 + 0.1) % 1.0),
                "xgboost": 0.15 + 0.70 * ((x * 1.7 + 0.2) % 1.0),
                "catboost": 0.15 + 0.70 * ((x * 1.9 + 0.3) % 1.0),
            })
            idx.append(f"{season}-{game}")
    base_oof = pd.DataFrame(rows, index=idx)
    production = production_nested_oof(base_oof).target_oof
    research = research_nested_oof(base_oof, target_seasons=(2022, 2023, 2024, 2025), seed=26).target_oof
    assert tuple(BASE_MODEL_NAMES) == ("logistic", "extra_trees", "xgboost", "catboost")
    assert production.index.equals(research.index)
    np.testing.assert_array_equal(production["pure_prob"].to_numpy(), research["pure_prob"].to_numpy())


def test_old_locked_rows_keep_official_values_when_new_schema_is_loaded(tmp_path: Path):
    old = pd.DataFrame([{
        "game_id": "old_game",
        "final_home_prob": 0.6042095144550527,
        "pure_home_prob": 0.6043603622926776,
        "market_home_prob": 0.6037569709421778,
        "pick": "SEA",
        "lock_status": "LOCKED",
    }])
    path = tmp_path / "prediction_history.csv"
    old.to_csv(path, index=False)
    loaded = _load_official(path, CURRENT_COLUMNS)
    assert len(loaded) == 1
    assert loaded.loc[0, "game_id"] == "old_game"
    assert loaded.loc[0, "final_home_prob"] == pytest.approx(0.6042095144550527)
    assert loaded.loc[0, "pure_home_prob"] == pytest.approx(0.6043603622926776)
    assert pd.isna(loaded.loc[0, "fst_pure_home_prob"])
    assert pd.isna(loaded.loc[0, "legacy_final_home_prob"])


def test_evaluator_tolerates_predeployment_history_schema(tmp_path: Path):
    history = pd.DataFrame([{
        "game_id": "g1",
        "challenger_final_home_prob": 0.60,
        "production_final_home_prob": 0.55,
    }])
    official = pd.DataFrame([{
        "game_id": "g1",
        "final_home_prob": 0.55,
        "market_home_prob": 0.52,
        "model_version": "0.4.0-accountability",
    }])
    path = tmp_path / "official.csv"
    official.to_csv(path, index=False)
    result = _attach_production_regime(history, path)
    assert result.loc[0, "challenger_final_home_prob"] == pytest.approx(0.60)
    assert result.loc[0, "production_final_home_prob"] == pytest.approx(0.55)


def test_evaluator_uses_locked_legacy_counterfactual_after_promotion(tmp_path: Path):
    history = pd.DataFrame([{
        "game_id": "g1",
        "challenger_final_home_prob": 0.61,
        "production_final_home_prob": 0.61,
        "challenger_pure_home_prob": 0.57,
        "market_home_prob_t120": 0.62,
    }])
    official = pd.DataFrame([{
        "game_id": "g1",
        "final_home_prob": 0.61,
        "legacy_final_home_prob": 0.56,
        "fst_pure_home_prob": 0.57,
        "market_home_prob": 0.62,
        "final_probability_strategy": CANDIDATE_ID,
        "model_version": "0.9.0-fst",
    }])
    path = tmp_path / "official.csv"
    official.to_csv(path, index=False)
    result = _attach_production_regime(history, path)
    assert result.loc[0, "challenger_final_home_prob"] == pytest.approx(0.61)
    assert result.loc[0, "production_final_home_prob"] == pytest.approx(0.56)
    assert result.loc[0, "market_home_prob_t120"] == pytest.approx(0.62)
    assert result.loc[0, "challenger_pure_home_prob"] == pytest.approx(0.57)
    assert result.loc[0, "evaluation_reference"] == "locked_legacy_75_25_counterfactual"


def test_production_path_has_no_research_imports():
    import ast

    for filename in (
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/fst_nested_pure.py",
        "src/nfl_forecast/fst_production.py",
        "src/nfl_forecast/fst_diagnostics.py",
        "src/nfl_forecast/publish.py",
    ):
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any("challenger" in name or "research" in name for name in imports), (filename, imports)

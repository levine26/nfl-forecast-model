from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import nfl_forecast.fst_production as fst_production
from nfl_forecast.fst_nested_pure import (
    BASE_MODEL_NAMES,
    FROZEN_BASE_OOF_ROWS,
    FROZEN_TRAINING_DIGEST,
    FROZEN_TRAINING_ROWS,
    canonical_training_hash,
    load_frozen_base_oof,
    load_frozen_training_frame,
    reconstruct_frozen_coefficients,
)
from nfl_forecast.fst_production import (
    CANDIDATE_ID,
    EXPECTED_INTERCEPT,
    EXPECTED_MARKET_COEF,
    EXPECTED_PURE_COEF,
    EXPECTED_TRAINING_SHA256,
    LEGACY_PRODUCTION_STRATEGY,
    frozen_fst_probability,
    legacy_final_home_probability,
    load_fst_artifact,
    score_official_fst,
)

TOLERANCE = 1e-12


def test_frozen_artifact_identity_is_exact():
    artifact = load_fst_artifact()
    assert artifact.candidate_id == CANDIDATE_ID == "F-ST-01-FROZEN-2026"
    assert artifact.intercept == EXPECTED_INTERCEPT == -0.06954359363166639
    assert artifact.market_logit_coefficient == EXPECTED_MARKET_COEF == 1.1939087340527093
    assert artifact.pure_logit_coefficient == EXPECTED_PURE_COEF == -0.19342747983803402
    assert artifact.training_data_sha256 == EXPECTED_TRAINING_SHA256 == FROZEN_TRAINING_DIGEST
    assert artifact.training_games == FROZEN_TRAINING_ROWS == 1615
    assert artifact.training_first_season == 2020
    assert artifact.training_last_season == 2025
    assert artifact.training_cutoff == 2025
    assert artifact.outcomes_2026_used == 0


def test_immutable_recovered_inputs_load_and_reconstruct_within_gate():
    base = load_frozen_base_oof()
    training = load_frozen_training_frame()
    assert len(base) == FROZEN_BASE_OOF_ROWS == 2127
    assert len(training) == FROZEN_TRAINING_ROWS == 1615
    assert list(base.columns[:2]) == ["game_id", "row_position"]
    assert list(base.columns[2:6]) == list(BASE_MODEL_NAMES)
    assert int(base.season.min()) == 2018 and int(base.season.max()) == 2025
    assert int(training.season.min()) == 2020 and int(training.season.max()) == 2025
    refit = reconstruct_frozen_coefficients(training)
    assert abs(refit["intercept"] - EXPECTED_INTERCEPT) <= TOLERANCE
    assert abs(refit["market_logit_coefficient"] - EXPECTED_MARKET_COEF) <= TOLERANCE
    assert abs(refit["pure_logit_coefficient"] - EXPECTED_PURE_COEF) <= TOLERANCE


def test_fst_matches_hand_computed_logit_fixture():
    artifact = load_fst_artifact()
    score = EXPECTED_INTERCEPT + EXPECTED_MARKET_COEF * math.log(0.60 / 0.40) + EXPECTED_PURE_COEF * math.log(0.55 / 0.45)
    expected = 1.0 / (1.0 + math.exp(-score))
    actual = frozen_fst_probability(np.array([0.60]), np.array([0.55]), artifact)[0]
    assert actual == pytest.approx(expected, abs=1e-15, rel=0.0)


def test_missing_market_falls_back_to_exact_legacy_and_rollback_is_one_switch(monkeypatch):
    artifact = load_fst_artifact()
    idx = pd.Index(["fst", "missing"])
    legacy_pure = pd.Series([0.60, 0.40], index=idx)
    fst_pure = pd.Series([0.58, 0.42], index=idx)
    market = pd.Series([0.65, np.nan], index=idx)
    scored = score_official_fst(legacy_pure, fst_pure, market, artifact)
    expected_fst = frozen_fst_probability(np.array([0.65]), np.array([0.58]), artifact)[0]
    assert scored.final_home_prob.loc["fst"] == pytest.approx(expected_fst, abs=1e-15)
    assert scored.final_home_prob.loc["missing"] == 0.40
    assert scored.fst_fallback.to_dict() == {"fst": False, "missing": True}
    assert scored.fst_fallback_reason.loc["missing"] == "market_missing"

    expected_legacy = legacy_final_home_probability(legacy_pure, market)
    monkeypatch.setattr(fst_production, "ACTIVE_PRODUCTION_STRATEGY", LEGACY_PRODUCTION_STRATEGY)
    rollback = fst_production.score_official_fst(legacy_pure, fst_pure, market, artifact)
    np.testing.assert_array_equal(rollback.final_home_prob.to_numpy(), expected_legacy.to_numpy())


def test_artifact_modification_and_post_2025_training_fail_closed(tmp_path: Path):
    source = Path("src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["market_logit_coefficient"] = EXPECTED_MARKET_COEF + 1e-12
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="market coefficient"):
        load_fst_artifact(path)

    contaminated = load_frozen_training_frame().copy()
    contaminated.loc[contaminated.index[0], "season"] = 2026
    with pytest.raises(RuntimeError, match="2026-or-later"):
        canonical_training_hash(contaminated)


def test_historical_game_identity_alignment_is_fail_closed():
    base = load_frozen_base_oof()
    historical = base[["game_id", "season", "home_win"]].copy()
    historical.index = np.arange(50000, 50000 + len(historical))
    aligned = load_frozen_base_oof(historical=historical)
    assert aligned.index.equals(historical.index)
    changed = historical.copy()
    changed.iloc[0, changed.columns.get_loc("home_win")] = 1 - int(changed.iloc[0].home_win)
    with pytest.raises(RuntimeError, match="target mismatch"):
        load_frozen_base_oof(historical=changed)


def test_production_path_has_no_research_or_challenger_imports():
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


def test_ordinary_workflows_do_not_force_cpu_target():
    for filename in (
        ".github/workflows/weekly.yml",
        ".github/workflows/market_refresh.yml",
        ".github/workflows/fst_deployment.yml",
    ):
        text = Path(filename).read_text(encoding="utf-8")
        assert "OPENBLAS_CORETYPE" not in text
        assert "SKYLAKEX" not in text

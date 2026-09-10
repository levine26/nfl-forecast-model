from __future__ import annotations

from pathlib import Path
import re
import subprocess


def replace(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")


def write(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def git_show(ref: str, path: str) -> str:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)


def patch_pipeline() -> None:
    replace(
        "src/nfl_forecast/pipeline.py",
        "from .fst_nested_pure import build_fst_training_frame, fit_future_nested_stack, load_frozen_base_oof",
        "from .fst_nested_pure import fit_future_nested_stack, load_frozen_base_oof, load_frozen_training_frame",
    )
    replace(
        "src/nfl_forecast/pipeline.py",
        "    fst_training = build_fst_training_frame(fst_historical, fst_base_oof, seed=seed)\n",
        "    fst_training = load_frozen_training_frame(historical=fst_historical)\n",
    )
    old = '''    # The pre-existing confidence machinery was validated around the legacy PURE
    # ensemble. Preserve it as an explicitly legacy diagnostic rather than silently
    # inventing an F-ST confidence model.
    current["model_disagreement"] = base_probs.std(axis=1)
    current["legacy_consistency_flag"] = current.apply(
        lambda r: consistency_flag(r["legacy_final_home_prob"], r["expected_margin"]), axis=1
    )
    current["legacy_confidence"] = current.apply(
        lambda r: confidence_label(r["legacy_final_home_prob"], r["model_disagreement"], r["legacy_consistency_flag"]), axis=1
    )
    current["consistency_flag"] = current["legacy_consistency_flag"]
    current["confidence"] = current["legacy_confidence"]
    current["confidence_diagnostic_scope"] = "legacy_75_25_pure_ensemble"
    # Feed the legacy probability through the legacy confidence-index implementation,
    # then restore the official F-ST probability immediately after diagnostics return.
    official_probability = current["final_home_prob"].copy()
    current["final_home_prob"] = current["legacy_final_home_prob"]
    current = add_confidence_diagnostics(current)
    current["final_home_prob"] = official_probability
'''
    new = '''    # Legacy confidence remains available only as a counterfactual comparator.
    # Official confidence/consistency are driven by the official F-ST probability.
    current["model_disagreement"] = base_probs.std(axis=1)
    current["legacy_consistency_flag"] = current.apply(
        lambda r: consistency_flag(r["legacy_final_home_prob"], r["expected_margin"]), axis=1
    )
    current["legacy_confidence"] = current.apply(
        lambda r: confidence_label(r["legacy_final_home_prob"], r["model_disagreement"], r["legacy_consistency_flag"]), axis=1
    )
    current["consistency_flag"] = current.apply(
        lambda r: consistency_flag(r["final_home_prob"], r["expected_margin"]), axis=1
    )
    current["confidence"] = current.apply(
        lambda r: confidence_label(r["final_home_prob"], r["model_disagreement"], r["consistency_flag"]), axis=1
    )
    current["confidence_diagnostic_scope"] = "official_fst_probability"
    current = add_confidence_diagnostics(current)
'''
    replace("src/nfl_forecast/pipeline.py", old, new)


def patch_canary() -> None:
    replace(
        "scripts/validate_fst_production_canary.py",
        "from nfl_forecast.fst_nested_pure import build_fst_training_frame, load_frozen_base_oof",
        "from nfl_forecast.fst_nested_pure import load_frozen_base_oof, load_frozen_training_frame",
    )
    replace(
        "scripts/validate_fst_production_canary.py",
        "    training_frame = build_fst_training_frame(historical, frozen_oof, seed=seed)\n",
        "    training_frame = load_frozen_training_frame(historical=historical)\n",
    )


def patch_market_refresh() -> None:
    p = Path("scripts/refresh_market.py")
    text = p.read_text(encoding="utf-8")
    start = text.index("def _legacy_diagnostics(")
    end = text.index("\ndef _rescore_winner_probability", start)
    replacement = '''def _winner_diagnostics(p: pd.DataFrame) -> None:
    p["legacy_consistency_flag"] = p.apply(
        lambda r: "NEUTRAL"
        if abs(float(r["legacy_final_home_prob"]) - 0.5) < 0.02
        or abs(float(r["expected_margin"])) < 1.0
        else (
            "ALIGNED"
            if (float(r["legacy_final_home_prob"]) - 0.5) * float(r["expected_margin"]) > 0
            else "WIN-MARGIN SPLIT"
        ),
        axis=1,
    )
    p["legacy_confidence"] = p.apply(
        lambda r: confidence(
            r["legacy_final_home_prob"],
            r.get("model_disagreement", 0.0),
            r["legacy_consistency_flag"],
        ),
        axis=1,
    )
    p["consistency_flag"] = p.apply(
        lambda r: "NEUTRAL"
        if abs(float(r["final_home_prob"]) - 0.5) < 0.02
        or abs(float(r["expected_margin"])) < 1.0
        else (
            "ALIGNED"
            if (float(r["final_home_prob"]) - 0.5) * float(r["expected_margin"]) > 0
            else "WIN-MARGIN SPLIT"
        ),
        axis=1,
    )
    p["confidence"] = p.apply(
        lambda r: confidence(
            r["final_home_prob"],
            r.get("model_disagreement", 0.0),
            r["consistency_flag"],
        ),
        axis=1,
    )
    strategy = p["final_probability_strategy"].astype(str) if "final_probability_strategy" in p else pd.Series("", index=p.index)
    p["confidence_diagnostic_scope"] = np.where(
        strategy.eq(CANDIDATE_ID),
        "official_fst_probability",
        "legacy_75_25_pure_ensemble",
    )
'''
    text = text[:start] + replacement + text[end:]
    if "    _legacy_diagnostics(p)\n" not in text:
        raise RuntimeError("Expected legacy diagnostics call missing")
    text = text.replace("    _legacy_diagnostics(p)\n", "    _winner_diagnostics(p)\n")
    p.write_text(text, encoding="utf-8")


def patch_public_presentation() -> None:
    p = Path("site/src/fst-production-presentation.js")
    text = p.read_text(encoding="utf-8")
    text = text.replace("  replaceExactText(root, 'Confidence', 'Legacy confidence')\n", "")
    text = text.replace(
        "    if (label?.textContent?.trim() === 'Model disagreement') label.textContent = 'Legacy model disagreement'\n",
        "",
    )
    text = re.sub(
        r"\n  for \(const stat of root\.querySelectorAll\('\.vnext-hero-stats \.pub-stat'\)\) \{.*?\n  \}\n",
        "\n",
        text,
        flags=re.S,
    )
    p.write_text(text, encoding="utf-8")


def patch_workflows() -> None:
    for name in ("weekly.yml", "market_refresh.yml"):
        path = f".github/workflows/{name}"
        text = git_show("origin/feat/deploy-fst-production", path)
        text = re.sub(
            r"\n    env:\n      OPENBLAS_CORETYPE: SKYLAKEX\n      OPENBLAS_NUM_THREADS: '4'\n      OMP_NUM_THREADS: '4'\n      MKL_NUM_THREADS: '4'\n      NUMEXPR_NUM_THREADS: '4'\n",
            "\n",
            text,
        )
        write(path, text)


def write_pyproject() -> None:
    write(
        "pyproject.toml",
        '''[project]
name = "nfl-forecast-engine"
version = "0.1.0"
description = "Free, automated Sujar-inspired NFL forecasting ensemble"
requires-python = ">=3.11,<3.12"
dependencies = [
  "nflreadpy==0.1.5",
  "polars==1.44.2",
  "pandas==3.0.5",
  "numpy==2.4.6",
  "scipy==1.17.1",
  "scikit-learn==1.9.0",
  "xgboost==3.2.0",
  "catboost==1.2.10",
  "pyarrow==25.0.1",
  "duckdb==1.5.5",
  "joblib==1.6.0",
  "threadpoolctl==3.6.0",
  "pyyaml>=6.0",
  "requests>=2.32",
  "beautifulsoup4>=4.12",
  "lxml>=5.0",
  "json-repair>=0.63,<1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.8"]

[tool.setuptools.package-data]
nfl_forecast = ["artifacts/*.json", "artifacts/*.csv", "artifacts/*.part*"]

[tool.pytest.ini_options]
pythonpath = ["src", "."]

[tool.ruff]
line-length = 100
''',
    )


def write_tests() -> None:
    write(
        "tests/test_fst_production.py",
        '''from __future__ import annotations

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
''',
    )


def write_deployment_workflow() -> None:
    write(
        ".github/workflows/fst_deployment.yml",
        '''name: F-ST production deployment validation

on:
  pull_request:
    paths:
      - 'src/nfl_forecast/fst_*.py'
      - 'src/nfl_forecast/artifacts/**'
      - 'src/nfl_forecast/pipeline.py'
      - 'src/nfl_forecast/publish.py'
      - 'scripts/refresh_market.py'
      - 'scripts/run_week.py'
      - 'scripts/validate_fst_production_canary.py'
      - 'tests/test_fst_*.py'
      - 'pyproject.toml'
      - 'site/**'
      - '.github/workflows/fst_deployment.yml'
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: fst-production-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-24.04
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11.16'
          cache: pip
      - run: pip install '.[dev]'
      - uses: actions/cache@v4
        with:
          path: .cache/nflreadpy
          key: nfl-fst-deploy-${{ runner.os }}-${{ github.run_id }}
          restore-keys: |
            nflreadpy-${{ runner.os }}-
      - name: Full Python test suite
        run: pytest -q
      - name: Validate immutable frozen artifacts and coefficient parity
        run: |
          python - <<'PY'
          from nfl_forecast.fst_nested_pure import load_frozen_base_oof, load_frozen_training_frame, reconstruct_frozen_coefficients
          from nfl_forecast.fst_production import load_fst_artifact
          a=load_fst_artifact(); b=load_frozen_base_oof(); t=load_frozen_training_frame(); r=reconstruct_frozen_coefficients(t)
          assert len(b)==2127 and len(t)==1615
          assert a.training_data_sha256=='6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0'
          assert max(abs(r['intercept']-a.intercept),abs(r['market_logit_coefficient']-a.market_logit_coefficient),abs(r['pure_logit_coefficient']-a.pure_logit_coefficient)) <= 1e-12
          PY
      - name: Same-snapshot standalone-to-production canary
        env:
          LEVLINE_SOURCE_SHA: ${{ github.sha }}
        run: |
          rm -rf deployment_audits
          PYTHONPATH="$PWD:$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python scripts/validate_fst_production_canary.py
          python - <<'PY'
          import json
          x=json.load(open('deployment_audits/fst_predeploy_canary.json'))
          assert x['parity_passed'] is True
          assert x['fst_max_absolute_difference'] <= 1e-12
          assert x['nested_pure_max_absolute_difference'] <= 1e-12
          assert x['reconstruction_coefficient_max_absolute_difference'] <= 1e-12
          PY
      - name: Regenerate production outputs and preserve old locks
        run: |
          cp outputs/prediction_history.csv /tmp/prediction_history.before.csv
          PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python scripts/run_week.py --season 2026 --snapshot EARLY
          python - <<'PY'
          import numpy as np, pandas as pd
          p=pd.read_csv('outputs/this_week.csv')
          required={'final_home_prob','fst_pure_home_prob','market_home_prob','legacy_final_home_prob','final_probability_strategy','fst_artifact_id','fst_fallback','fst_fallback_reason','confidence','fair_home_moneyline'}
          assert not (required-set(p.columns)), required-set(p.columns)
          assert set(p.final_probability_strategy.astype(str)) == {'F-ST-01-FROZEN-2026'}
          assert set(p.fst_artifact_id.astype(str)) == {'F-ST-01-FROZEN-2026'}
          eligible=~p.fst_fallback.fillna(False).astype(bool)
          if eligible.any():
              m=np.clip(p.loc[eligible,'market_home_prob'].to_numpy(float),1e-6,1-1e-6)
              q=np.clip(p.loc[eligible,'fst_pure_home_prob'].to_numpy(float),1e-6,1-1e-6)
              expected=1/(1+np.exp(-(-0.06954359363166639+1.1939087340527093*np.log(m/(1-m))-0.19342747983803402*np.log(q/(1-q)))))
              assert np.allclose(p.loc[eligible,'final_home_prob'],expected,atol=1e-12,rtol=0)
          assert np.array_equal(p.pick.to_numpy(),np.where(p.final_home_prob>=0.5,p.home_team,p.away_team))
          assert (p.confidence_diagnostic_scope.astype(str)=='official_fst_probability').all()
          assert np.isfinite(p.fair_home_moneyline.to_numpy(float)).all()
          before=pd.read_csv('/tmp/prediction_history.before.csv')
          after=pd.read_csv('outputs/prediction_history.csv')
          old=after[after.game_id.astype(str).isin(before.game_id.astype(str))]
          merged=before.merge(old,on='game_id',suffixes=('_before','_after'))
          for col in ['pure_home_prob','market_home_prob','final_home_prob','pick','model_version','lock_status']:
              assert merged[f'{col}_before'].astype(str).tolist()==merged[f'{col}_after'].astype(str).tolist(), col
          PY
      - name: Validate hourly market refresh path
        run: |
          PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" python scripts/refresh_market.py --season 2026
          python - <<'PY'
          import pandas as pd
          p=pd.read_csv('outputs/this_week.csv')
          assert set(p.final_probability_strategy.astype(str)) == {'F-ST-01-FROZEN-2026'}
          assert (p.confidence_diagnostic_scope.astype(str)=='official_fst_probability').all()
          PY
      - name: Build public site
        working-directory: site
        run: |
          npm install --no-audit --no-fund
          npm run build
      - name: Upload deployment evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: fst-production-evidence-${{ github.run_id }}
          path: deployment_audits/
          if-no-files-found: warn
          retention-days: 90
''',
    )


def document() -> None:
    p = Path("README.md")
    text = p.read_text(encoding="utf-8")
    marker = "## Official winner-probability model — F-ST-01-FROZEN-2026"
    if marker in text:
        return
    text += '''

## Official winner-probability model — F-ST-01-FROZEN-2026

LevLine's official 2026 winner probability is the frozen two-input F-ST logit stack. Its inputs are the current vig-free market home-win probability and the separately materialized frozen nested-PURE probability. The exact registered coefficients are intercept `-0.06954359363166639`, market-logit coefficient `1.1939087340527093`, and nested-PURE-logit coefficient `-0.19342747983803402`. Frozen training identity is 1,615 games from 2020–2025 with canonical SHA-256 `6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`; 2026 outcomes are excluded from fitting and model selection.

The recovered keyed OOF and final training inputs are committed as immutable package artifacts and verified before scoring. Ordinary production does not force a CPU-specific OpenBLAS target. If the current market probability is unavailable for a game, that game falls back to the exact legacy 75% PURE / 25% market rule. The pre-F-ST production probability is retained as `legacy_final_home_prob` for counterfactual grading and rollback; changing `ACTIVE_PRODUCTION_STRATEGY` in `fst_production.py` to `LEGACY_PRODUCTION_STRATEGY` restores the legacy path without rewriting historical locks.
'''
    p.write_text(text, encoding="utf-8")


def main() -> None:
    patch_pipeline()
    patch_canary()
    patch_market_refresh()
    patch_public_presentation()
    patch_workflows()
    write_pyproject()
    write_tests()
    write_deployment_workflow()
    document()


if __name__ == "__main__":
    main()

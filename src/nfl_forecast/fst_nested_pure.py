from __future__ import annotations

"""Production-safe reproduction of the frozen F-ST nested PURE architecture.

This module intentionally contains no challenger/research imports. It preserves the
validated season-forward base OOF construction, four production model templates, nested
meta-model, deterministic seed, and future/live inference semantics used by F-ST-01.

For real production historical frames, the authoritative F-ST base OOF is reconstructed
under the recovered freeze-era numerical runtime and verified against cryptographic
identities captured by the independent forensic matrix. The older package CSV is retained
only as archival v0.8 evidence; it is not the authoritative F-ST fit input.
"""

from dataclasses import dataclass
import hashlib
from importlib.metadata import version as package_version
import os
from pathlib import Path
import platform

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_info

from .features import core_columns
from .models import _win_models

EPS = 1e-6
BASE_MODEL_NAMES = ("logistic", "extra_trees", "xgboost", "catboost")
BASE_OOF_START = 2018
HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)
MIN_META_GAMES = 300

# Archived generic v0.8 OOF from the original successful workflow. It is useful evidence,
# but the F-ST step rebuilt its own OOF later in that workflow and that later numerical
# realization is the one bound by the recovered identities below.
FROZEN_BASE_OOF_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "F-ST-01-FROZEN-2026-base-oof.csv"
)
FROZEN_BASE_OOF_SHA256 = "4e5a72f545982465b2401876dfb60c293403ceb89eac1f87778b85d9f5b988e7"
FROZEN_BASE_OOF_ROWS = 2127
FROZEN_BASE_OOF_FIRST_SEASON = 2018
FROZEN_BASE_OOF_LAST_SEASON = 2025

# Exact identities captured from forensic workflow 34538432305. Both a native SkylakeX
# runner and an independently allocated runner forced to SKYLAKEX reproduced these rows
# and the registered F-ST training digest without using any 2026 outcomes.
RECOVERED_BASE_OOF_SEQUENCE_SHA256 = (
    "5f4eda7d5df86ab13e4d6a6b90653be3160bd857e00eb1d412eae0e78eb2c7b3"
)
RECOVERED_BASE_OOF_GAME_ID_SEQUENCE_SHA256 = (
    "dff495fa86c9c53b1a76213afcb351c01ed691db9c225bdd911717ccd2ce236c"
)
REQUIRED_PYTHON_VERSION = "3.11.16"
REQUIRED_ENVIRONMENT = {
    "OPENBLAS_CORETYPE": "SKYLAKEX",
    "OPENBLAS_NUM_THREADS": "4",
    "OMP_NUM_THREADS": "4",
    "MKL_NUM_THREADS": "4",
    "NUMEXPR_NUM_THREADS": "4",
}
REQUIRED_PACKAGE_VERSIONS = {
    "nflreadpy": "0.1.5",
    "polars": "1.44.2",
    "pandas": "3.0.5",
    "numpy": "2.4.6",
    "scipy": "1.17.1",
    "scikit-learn": "1.9.0",
    "xgboost": "3.2.0",
    "catboost": "1.2.10",
    "pyarrow": "25.0.1",
    "duckdb": "1.5.5",
    "joblib": "1.6.0",
    "threadpoolctl": "3.6.0",
}


@dataclass(frozen=True)
class NestedStackResult:
    base_oof: pd.DataFrame
    target_oof: pd.DataFrame


def _clip(values) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _meta_template(seed: int) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", LogisticRegression(C=0.5, max_iter=3000, random_state=seed)),
    ])


def _assert_historical_cutoff(frame: pd.DataFrame, season_col: str = "season") -> None:
    if season_col not in frame.columns:
        raise ValueError(f"F-ST historical frame missing {season_col!r}")
    season = pd.to_numeric(frame[season_col], errors="coerce")
    if season.dropna().gt(HISTORICAL_END).any():
        raise ValueError("F-ST nested PURE fitting may not use outcomes after 2025")


def require_fst_reconstruction_runtime() -> dict:
    """Fail closed unless the recovered F-ST numerical runtime is active."""
    failures: list[str] = []
    actual_python = platform.python_version()
    if actual_python != REQUIRED_PYTHON_VERSION:
        failures.append(f"python={actual_python} (required {REQUIRED_PYTHON_VERSION})")

    packages: dict[str, str] = {}
    for package, expected in REQUIRED_PACKAGE_VERSIONS.items():
        try:
            actual = package_version(package)
        except Exception as exc:  # pragma: no cover - diagnostic fail-closed path
            actual = f"unavailable:{exc!r}"
        packages[package] = actual
        if actual != expected:
            failures.append(f"{package}={actual} (required {expected})")

    environment = {key: os.environ.get(key) for key in REQUIRED_ENVIRONMENT}
    for key, expected in REQUIRED_ENVIRONMENT.items():
        if environment[key] != expected:
            failures.append(f"{key}={environment[key]!r} (required {expected!r})")

    pools = threadpool_info()
    blas_pools = [p for p in pools if p.get("internal_api") == "openblas"]
    if not blas_pools:
        failures.append("no OpenBLAS runtime detected")
    for pool in blas_pools:
        if str(pool.get("architecture") or "").lower() != "skylakex":
            failures.append(
                f"BLAS architecture={pool.get('architecture')!r} (required 'SkylakeX')"
            )
        if int(pool.get("num_threads") or 0) != 4:
            failures.append(f"BLAS num_threads={pool.get('num_threads')!r} (required 4)")

    report = {
        "python_version": actual_python,
        "package_versions": packages,
        "environment": environment,
        "threadpools": pools,
        "matches": not failures,
        "failures": failures,
    }
    if failures:
        raise RuntimeError("F-ST reconstruction runtime mismatch: " + "; ".join(failures))
    return report


def validate_reconstructed_base_oof(
    base_oof: pd.DataFrame,
    historical: pd.DataFrame,
) -> dict:
    """Bind reconstructed OOF rows to the recovered game/row sequence exactly."""
    _assert_historical_cutoff(historical)
    if "game_id" not in historical.columns:
        raise ValueError("F-ST OOF identity validation requires historical game_id")
    if not historical.index.is_unique or not base_oof.index.is_unique:
        raise RuntimeError("F-ST OOF identity requires unique historical/base indexes")
    if len(base_oof) != FROZEN_BASE_OOF_ROWS:
        raise RuntimeError(
            f"Recovered F-ST base OOF row count changed: {len(base_oof)} != {FROZEN_BASE_OOF_ROWS}"
        )
    missing = base_oof.index.difference(historical.index)
    if len(missing):
        raise RuntimeError(f"Recovered F-ST base OOF has {len(missing)} unknown historical rows")

    ordered = base_oof.sort_index().copy()
    required = [*BASE_MODEL_NAMES, "home_win", "season"]
    missing_cols = set(required) - set(ordered.columns)
    if missing_cols:
        raise RuntimeError(f"Recovered F-ST base OOF missing fields: {sorted(missing_cols)}")
    season = pd.to_numeric(ordered["season"], errors="coerce")
    target = pd.to_numeric(ordered["home_win"], errors="coerce")
    if season.isna().any() or int(season.min()) != 2018 or int(season.max()) != 2025:
        raise RuntimeError("Recovered F-ST base OOF season identity changed")
    if not target.isin([0, 1]).all():
        raise RuntimeError("Recovered F-ST base OOF target is not binary")
    probs = ordered[list(BASE_MODEL_NAMES)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(probs.to_numpy(dtype=float)).all():
        raise RuntimeError("Recovered F-ST base OOF contains non-finite probabilities")
    if ((probs <= 0.0) | (probs >= 1.0)).any().any():
        raise RuntimeError("Recovered F-ST base OOF probability outside (0, 1)")

    keyed = ordered[required].copy()
    keyed.insert(0, "row_position", np.arange(len(keyed), dtype=int))
    keyed.insert(0, "game_id", historical.loc[ordered.index, "game_id"].astype(str).to_numpy())
    if keyed["game_id"].duplicated().any():
        raise RuntimeError("Recovered F-ST base OOF game_id is not unique")

    text = keyed.to_csv(index=False, float_format="%.17g", lineterminator="\n")
    sequence_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    game_ids = keyed["game_id"].astype(str).tolist()
    game_sequence_sha = hashlib.sha256(("\n".join(game_ids) + "\n").encode("utf-8")).hexdigest()
    if sequence_sha != RECOVERED_BASE_OOF_SEQUENCE_SHA256:
        raise RuntimeError(
            "Recovered F-ST base OOF sequence digest changed: "
            f"{sequence_sha} != {RECOVERED_BASE_OOF_SEQUENCE_SHA256}"
        )
    if game_sequence_sha != RECOVERED_BASE_OOF_GAME_ID_SEQUENCE_SHA256:
        raise RuntimeError(
            "Recovered F-ST game sequence digest changed: "
            f"{game_sequence_sha} != {RECOVERED_BASE_OOF_GAME_ID_SEQUENCE_SHA256}"
        )
    return {
        "rows": len(keyed),
        "first_season": int(season.min()),
        "last_season": int(season.max()),
        "sequence_sha256": sequence_sha,
        "game_id_sequence_sha256": game_sequence_sha,
    }


def _load_archived_generic_base_oof(path: str | Path = FROZEN_BASE_OOF_PATH) -> pd.DataFrame:
    """Load the older generic v0.8 OOF artifact for archival evidence/tests only."""
    artifact_path = Path(path)
    raw = artifact_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_BASE_OOF_SHA256:
        raise RuntimeError(
            f"Frozen F-ST base OOF digest changed: {digest} != {FROZEN_BASE_OOF_SHA256}"
        )
    frame = pd.read_csv(artifact_path)
    required = [*BASE_MODEL_NAMES, "home_win", "season"]
    if list(frame.columns) != required:
        raise RuntimeError(
            f"Frozen F-ST base OOF columns changed: {list(frame.columns)!r} != {required!r}"
        )
    if len(frame) != FROZEN_BASE_OOF_ROWS:
        raise RuntimeError(
            f"Frozen F-ST base OOF row count changed: {len(frame)} != {FROZEN_BASE_OOF_ROWS}"
        )
    season = pd.to_numeric(frame["season"], errors="coerce")
    if season.isna().any():
        raise RuntimeError("Frozen F-ST base OOF contains invalid season values")
    if int(season.min()) != FROZEN_BASE_OOF_FIRST_SEASON:
        raise RuntimeError("Frozen F-ST base OOF first season changed")
    if int(season.max()) != FROZEN_BASE_OOF_LAST_SEASON:
        raise RuntimeError("Frozen F-ST base OOF last season changed")
    numeric = frame[[*BASE_MODEL_NAMES, "home_win"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise RuntimeError("Frozen F-ST base OOF contains non-finite values")
    if not numeric["home_win"].isin([0, 1]).all():
        raise RuntimeError("Frozen F-ST base OOF target is not binary")
    for name in BASE_MODEL_NAMES:
        if ((numeric[name] <= 0.0) | (numeric[name] >= 1.0)).any():
            raise RuntimeError(f"Frozen F-ST base OOF {name} probability outside (0, 1)")
    return frame.copy()


def _align_archived_base_oof(frame: pd.DataFrame, historical: pd.DataFrame) -> pd.DataFrame:
    """Compatibility alignment for the non-authoritative archived generic OOF."""
    _assert_historical_cutoff(historical)
    if "home_win" not in historical.columns:
        raise ValueError("F-ST historical frame missing 'home_win'")
    historical_season = pd.to_numeric(historical["season"], errors="coerce")
    historical_target = pd.to_numeric(historical["home_win"], errors="coerce")
    mask = (
        historical_season.between(FROZEN_BASE_OOF_FIRST_SEASON, FROZEN_BASE_OOF_LAST_SEASON)
        & historical_target.notna()
    )
    reference = historical.loc[mask, ["season", "home_win"]].sort_index().copy()
    if not reference.index.is_unique:
        raise RuntimeError("Frozen F-ST historical alignment index is not unique")
    if len(reference) != len(frame):
        raise RuntimeError(
            f"Frozen F-ST historical alignment row count changed: {len(reference)} != {len(frame)}"
        )
    expected_season = pd.to_numeric(frame["season"], errors="raise").astype(int).to_numpy()
    actual_season = pd.to_numeric(reference["season"], errors="raise").astype(int).to_numpy()
    if not np.array_equal(actual_season, expected_season):
        raise RuntimeError("Frozen F-ST historical season sequence changed")
    expected_target = pd.to_numeric(frame["home_win"], errors="raise").astype(int).to_numpy()
    actual_target = pd.to_numeric(reference["home_win"], errors="raise").astype(int).to_numpy()
    if not np.array_equal(actual_target, expected_target):
        raise RuntimeError("Frozen F-ST historical target sequence changed")
    aligned = frame.copy()
    aligned.index = reference.index
    return aligned


def load_frozen_base_oof(
    path: str | Path = FROZEN_BASE_OOF_PATH,
    *,
    historical: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return authoritative F-ST OOF for production; archive-only OOF otherwise.

    Real historical game frames contain ``game_id``. For those frames, reconstruct the
    F-ST step under the recovered numerical runtime and require exact recovered row/game
    hashes. Minimal fixture frames without game identity retain the legacy archive loader
    solely for deterministic compatibility tests.
    """
    if historical is not None and "game_id" in historical.columns:
        require_fst_reconstruction_runtime()
        features = core_columns(historical)
        if len(features) < 4:
            raise RuntimeError(f"F-ST production feature build incomplete: {features}")
        rebuilt = build_base_oof_predictions(
            historical,
            features,
            seed=26,
            validation_start=BASE_OOF_START,
            validation_end=HISTORICAL_END,
        )
        validate_reconstructed_base_oof(rebuilt, historical)
        return rebuilt

    frame = _load_archived_generic_base_oof(path)
    if historical is not None:
        frame = _align_archived_base_oof(frame, historical)
    return frame.copy()


def build_base_oof_predictions(
    df: pd.DataFrame,
    feature_cols: list[str],
    *,
    target: str = "home_win",
    season_col: str = "season",
    seed: int = 26,
    validation_start: int = BASE_OOF_START,
    validation_end: int = HISTORICAL_END,
) -> pd.DataFrame:
    """Generate season-forward base-model OOF predictions using only seasons < S."""
    _assert_historical_cutoff(df, season_col)
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    templates = _win_models(seed)
    if tuple(templates) != BASE_MODEL_NAMES:
        raise RuntimeError(f"F-ST base-model template identity changed: {tuple(templates)!r}")
    parts: list[pd.DataFrame] = []
    for test_season in seasons:
        if test_season < validation_start or test_season > validation_end:
            continue
        tr = train[train[season_col] < test_season]
        va = train[train[season_col] == test_season]
        if len(tr) < 100 or va.empty:
            continue
        part = pd.DataFrame(index=va.index)
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target].astype(int))
            part[name] = model.predict_proba(va[feature_cols])[:, 1]
        part[target] = va[target].astype(int)
        part[season_col] = test_season
        parts.append(part)
    if not parts:
        raise ValueError("No valid F-ST base-model OOF seasons were generated")
    return pd.concat(parts).sort_index()


def build_nested_stack_oof(
    base_oof: pd.DataFrame,
    *,
    target_seasons: tuple[int, ...] = TARGET_SEASONS,
    target: str = "home_win",
    season_col: str = "season",
    seed: int = 26,
    min_meta_games: int = MIN_META_GAMES,
) -> NestedStackResult:
    """Create fully nested PURE probabilities for held-out target seasons."""
    season = pd.to_numeric(base_oof[season_col], errors="coerce")
    if season.dropna().gt(HISTORICAL_END).any():
        raise ValueError("F-ST nested meta-model may not load post-2025 OOF rows")
    parts: list[pd.DataFrame] = []
    for test_season in [int(x) for x in target_seasons]:
        meta_train = base_oof[base_oof[season_col] < test_season]
        test = base_oof[base_oof[season_col] == test_season]
        if test.empty:
            continue
        if len(meta_train) < min_meta_games or meta_train[target].nunique() < 2:
            raise ValueError(
                f"Insufficient pre-{test_season} F-ST meta training sample: {len(meta_train)}"
            )
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train[target].astype(int))
        part = test[[target, season_col]].copy()
        part["pure_prob"] = meta.predict_proba(test[list(BASE_MODEL_NAMES)])[:, 1]
        parts.append(part)
    if not parts:
        raise ValueError("No nested F-ST target seasons were generated")
    target_oof = pd.concat(parts).sort_index()
    missing = set(target_seasons) - set(target_oof[season_col].astype(int).unique())
    if missing:
        raise RuntimeError(f"F-ST nested PURE missing target seasons: {sorted(missing)}")
    return NestedStackResult(base_oof=base_oof, target_oof=target_oof)


def build_fst_training_frame(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    *,
    seed: int = 26,
    target: str = "home_win",
    season_col: str = "season",
    market_col: str = "market_home_prob",
) -> pd.DataFrame:
    """Reproduce the exact leakage-safe OOF frame used to freeze F-ST coefficients."""
    _assert_historical_cutoff(historical, season_col)
    nested = build_nested_stack_oof(base_oof, target_seasons=TARGET_SEASONS, seed=seed)
    research = base_oof[[target, season_col]].copy()
    research["market_prob"] = pd.to_numeric(
        historical.loc[research.index, market_col], errors="coerce"
    )
    research["pure_prob"] = np.nan
    research.loc[nested.target_oof.index, "pure_prob"] = nested.target_oof["pure_prob"]

    for season in sorted(
        int(s) for s in base_oof[season_col].unique() if int(s) < min(TARGET_SEASONS)
    ):
        meta_train = base_oof[base_oof[season_col] < season]
        test = base_oof[base_oof[season_col] == season]
        if len(meta_train) < MIN_META_GAMES or test.empty:
            continue
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train[target].astype(int))
        research.loc[test.index, "pure_prob"] = meta.predict_proba(
            test[list(BASE_MODEL_NAMES)]
        )[:, 1]

    research = research[research["pure_prob"].notna()].copy()
    research = research.rename(columns={target: "home_win", season_col: "season"})
    missing = set(TARGET_SEASONS) - set(research["season"].astype(int).unique())
    if missing:
        raise RuntimeError(f"F-ST training frame missing target seasons: {sorted(missing)}")
    return research[["season", "home_win", "market_prob", "pure_prob"]].copy()


def fit_future_nested_stack(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: list[str],
    *,
    target: str = "home_win",
    seed: int = 26,
) -> np.ndarray:
    """Fit frozen-architecture nested PURE for a future/live slate.

    Base models see all completed games through 2025. The meta-model sees only the
    season-forward base OOF predictions and never in-sample base predictions.
    """
    _assert_historical_cutoff(historical)
    if base_oof[target].nunique() < 2:
        raise ValueError("F-ST meta training target has fewer than two classes")
    meta = _meta_template(seed)
    meta.fit(base_oof[list(BASE_MODEL_NAMES)], base_oof[target].astype(int))

    base_current = pd.DataFrame(index=current.index)
    templates = _win_models(seed)
    if tuple(templates) != BASE_MODEL_NAMES:
        raise RuntimeError(f"F-ST base-model template identity changed: {tuple(templates)!r}")
    for name, template in templates.items():
        model = clone(template)
        model.fit(historical[feature_cols], historical[target].astype(int))
        base_current[name] = model.predict_proba(current[feature_cols])[:, 1]
    return _clip(meta.predict_proba(base_current[list(BASE_MODEL_NAMES)])[:, 1])

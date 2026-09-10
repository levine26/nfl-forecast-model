from __future__ import annotations

"""Production-safe reproduction of the frozen F-ST nested PURE architecture.

This module intentionally contains no challenger/research imports.  It preserves the
validated season-forward base OOF construction, four production model templates, nested
meta-model, deterministic seed, and future/live inference semantics used by F-ST-01.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .models import _win_models

EPS = 1e-6
BASE_MODEL_NAMES = ("logistic", "extra_trees", "xgboost", "catboost")
BASE_OOF_START = 2018
HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)
MIN_META_GAMES = 300


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

    Base models see all completed games through 2025.  The meta-model sees only
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

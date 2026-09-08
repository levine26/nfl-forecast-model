from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, ElasticNet
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier, XGBRegressor
from catboost import CatBoostClassifier, CatBoostRegressor


@dataclass
class FittedWinEnsemble:
    feature_cols: list[str]
    base_models: dict
    meta_model: Pipeline
    model_names: list[str]

    def base_predict(self, X: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({name: model.predict_proba(X[self.feature_cols])[:, 1] for name, model in self.base_models.items()}, index=X.index)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        base = self.base_predict(X)
        p = self.meta_model.predict_proba(base[self.model_names])[:, 1]
        return np.column_stack([1 - p, p])


def _win_models(seed: int = 26) -> dict:
    linear = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.5, max_iter=4000, random_state=seed)),
    ])
    extra = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(n_estimators=500, min_samples_leaf=6, max_features=0.75, random_state=seed, n_jobs=-1)),
    ])
    xgb = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", XGBClassifier(n_estimators=450, max_depth=3, learning_rate=0.035, subsample=0.85, colsample_bytree=0.8, reg_lambda=4.0, reg_alpha=0.2, eval_metric="logloss", random_state=seed, n_jobs=2)),
    ])
    cat = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", CatBoostClassifier(iterations=450, depth=5, learning_rate=0.035, l2_leaf_reg=5.0, verbose=False, random_seed=seed, thread_count=2)),
    ])
    return {"logistic": linear, "extra_trees": extra, "xgboost": xgb, "catboost": cat}


def fit_season_stacked_classifier(df: pd.DataFrame, feature_cols: list[str], target="home_win", season_col="season", seed=26) -> FittedWinEnsemble:
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    if len(seasons) < 3:
        raise ValueError("Need at least three seasons for walk-forward stacking.")

    templates = _win_models(seed)
    oof_parts = []
    for test_season in seasons[1:]:
        tr = train[train[season_col] < test_season]
        va = train[train[season_col] == test_season]
        if len(tr) < 100 or len(va) == 0:
            continue
        part = pd.DataFrame(index=va.index)
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target].astype(int))
            part[name] = model.predict_proba(va[feature_cols])[:, 1]
        part[target] = va[target].astype(int)
        oof_parts.append(part)
    if not oof_parts:
        raise ValueError("No valid out-of-fold seasons available.")

    oof = pd.concat(oof_parts).sort_index()
    names = list(templates)
    meta = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", LogisticRegression(C=0.5, max_iter=3000, random_state=seed)),
    ])
    meta.fit(oof[names], oof[target])

    fitted = {}
    for name, template in templates.items():
        model = clone(template)
        model.fit(train[feature_cols], train[target].astype(int))
        fitted[name] = model
    return FittedWinEnsemble(feature_cols=feature_cols, base_models=fitted, meta_model=meta, model_names=names)


@dataclass
class RegressionEnsemble:
    feature_cols: list[str]
    models: dict
    weights: dict[str, float]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        total = np.zeros(len(X), dtype=float)
        for name, model in self.models.items():
            total += self.weights[name] * model.predict(X[self.feature_cols])
        return total


def _reg_models(seed=26) -> dict:
    linear = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", ElasticNet(alpha=0.08, l1_ratio=0.2, random_state=seed, max_iter=5000)),
    ])
    extra = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", ExtraTreesRegressor(n_estimators=500, min_samples_leaf=6, max_features=0.75, random_state=seed, n_jobs=-1)),
    ])
    xgb = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", XGBRegressor(n_estimators=450, max_depth=3, learning_rate=0.035, subsample=0.85, colsample_bytree=0.8, reg_lambda=4.0, reg_alpha=0.2, objective="reg:squarederror", random_state=seed, n_jobs=2)),
    ])
    cat = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", CatBoostRegressor(iterations=450, depth=5, learning_rate=0.035, l2_leaf_reg=5.0, loss_function="MAE", verbose=False, random_seed=seed, thread_count=2)),
    ])
    return {"elastic_net": linear, "extra_trees": extra, "xgboost": xgb, "catboost": cat}


def fit_weighted_regression(df: pd.DataFrame, feature_cols: list[str], target: str, season_col="season", seed=26) -> RegressionEnsemble:
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    templates = _reg_models(seed)
    errors = {name: [] for name in templates}
    for test_season in seasons[1:]:
        tr = train[train[season_col] < test_season]
        va = train[train[season_col] == test_season]
        if len(tr) < 100 or len(va) == 0:
            continue
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target])
            pred = model.predict(va[feature_cols])
            errors[name].append(mean_absolute_error(va[target], pred))

    scores = {n: np.mean(e) if e else 99.0 for n, e in errors.items()}
    inv = {n: 1.0 / max(v, 1e-6) for n, v in scores.items()}
    denom = sum(inv.values())
    weights = {n: v / denom for n, v in inv.items()}

    fitted = {}
    for name, template in templates.items():
        model = clone(template)
        model.fit(train[feature_cols], train[target])
        fitted[name] = model
    return RegressionEnsemble(feature_cols, fitted, weights)


def classification_metrics(y, p) -> dict:
    y = np.asarray(y).astype(int)
    p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    pick = (p >= 0.5).astype(int)
    return {
        "games": int(len(y)),
        "winner_pct": float((pick == y).mean()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p)),
    }

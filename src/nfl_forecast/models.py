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
    oof_predictions: pd.DataFrame

    def base_predict(self, X: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {name: model.predict_proba(X[self.feature_cols])[:, 1] for name, model in self.base_models.items()},
            index=X.index,
        )

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


def fit_season_stacked_classifier(
    df: pd.DataFrame,
    feature_cols: list[str],
    target="home_win",
    season_col="season",
    seed=26,
    validation_start: int | None = None,
    validation_end: int | None = None,
) -> FittedWinEnsemble:
    """Expanding-window, season-level OOF stacking; no random-CV leakage."""
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    if len(seasons) < 3:
        raise ValueError("Need at least three seasons for walk-forward stacking.")

    templates = _win_models(seed)
    oof_parts = []
    validation_seasons = [
        s for s in seasons[1:]
        if (validation_start is None or s >= validation_start)
        and (validation_end is None or s <= validation_end)
    ]
    for test_season in validation_seasons:
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
        part[season_col] = va[season_col].astype(int)
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
    oof["stack"] = meta.predict_proba(oof[names])[:, 1]

    fitted = {}
    for name, template in templates.items():
        model = clone(template)
        model.fit(train[feature_cols], train[target].astype(int))
        fitted[name] = model
    return FittedWinEnsemble(
        feature_cols=feature_cols,
        base_models=fitted,
        meta_model=meta,
        model_names=names,
        oof_predictions=oof,
    )


@dataclass
class RegressionEnsemble:
    feature_cols: list[str]
    models: dict
    weights: dict[str, float]
    residual_std: float
    validation_mae: float

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


def fit_weighted_regression(
    df: pd.DataFrame,
    feature_cols: list[str],
    target: str,
    season_col="season",
    seed=26,
    validation_start: int | None = None,
    validation_end: int | None = None,
) -> RegressionEnsemble:
    train = df[df[target].notna()].copy()
    seasons = sorted(int(x) for x in train[season_col].dropna().unique())
    templates = _reg_models(seed)
    errors = {name: [] for name in templates}
    oof_parts: list[pd.DataFrame] = []
    validation_seasons = [
        s for s in seasons[1:]
        if (validation_start is None or s >= validation_start)
        and (validation_end is None or s <= validation_end)
    ]
    for test_season in validation_seasons:
        tr = train[train[season_col] < test_season]
        va = train[train[season_col] == test_season]
        if len(tr) < 100 or len(va) == 0:
            continue
        part = pd.DataFrame(index=va.index)
        part["actual"] = va[target].astype(float)
        for name, template in templates.items():
            model = clone(template)
            model.fit(tr[feature_cols], tr[target])
            pred = model.predict(va[feature_cols])
            part[name] = pred
            errors[name].append(mean_absolute_error(va[target], pred))
        oof_parts.append(part)

    scores = {n: np.mean(e) if e else 99.0 for n, e in errors.items()}
    inv = {n: 1.0 / max(v, 1e-6) for n, v in scores.items()}
    denom = sum(inv.values())
    weights = {n: v / denom for n, v in inv.items()}

    if oof_parts:
        oof = pd.concat(oof_parts).sort_index()
        ensemble_oof = np.zeros(len(oof), dtype=float)
        for name in templates:
            ensemble_oof += weights[name] * oof[name].to_numpy(dtype=float)
        residuals = oof["actual"].to_numpy(dtype=float) - ensemble_oof
        residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else float(train[target].std())
        validation_mae = float(mean_absolute_error(oof["actual"], ensemble_oof))
    else:
        residual_std = float(train[target].std())
        validation_mae = float("nan")
    if not np.isfinite(residual_std) or residual_std <= 0:
        residual_std = 1.0

    fitted = {}
    for name, template in templates.items():
        model = clone(template)
        model.fit(train[feature_cols], train[target])
        fitted[name] = model
    return RegressionEnsemble(feature_cols, fitted, weights, residual_std, validation_mae)


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

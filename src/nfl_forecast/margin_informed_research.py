from __future__ import annotations

"""Research-only expected-margin challenger with chronological probability mapping."""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RIDGE_ALPHA = 20.0
MAPPER_C = 1000.0
MIN_MARGIN_TRAIN_SEASONS = 4
EPS = 1e-6


def _margin_pipeline(alpha: float = RIDGE_ALPHA) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def _valid_rows(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    required = ["season", "margin", "home_win", *features]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Margin research frame missing columns: {missing}")
    return frame[frame["margin"].notna() & frame["home_win"].notna()].copy()


@dataclass(frozen=True)
class MarginSeasonResult:
    predictions: pd.DataFrame
    diagnostics: pd.DataFrame
    calibration_oof: pd.DataFrame


def build_margin_oof_history(
    frame: pd.DataFrame,
    features: list[str],
    *,
    before_season: int,
    alpha: float = RIDGE_ALPHA,
    minimum_training_seasons: int = MIN_MARGIN_TRAIN_SEASONS,
) -> pd.DataFrame:
    """Generate prior-season margin predictions where every row is season-out-of-fold."""
    usable = _valid_rows(frame, features)
    seasons = sorted(int(value) for value in usable["season"].dropna().unique() if int(value) < before_season)
    rows: list[pd.DataFrame] = []
    for season in seasons:
        prior_seasons = [value for value in seasons if value < season]
        if len(prior_seasons) < minimum_training_seasons:
            continue
        train = usable[usable["season"].isin(prior_seasons)]
        test = usable[usable["season"].eq(season)]
        if train.empty or test.empty:
            continue
        model = _margin_pipeline(alpha)
        model.fit(train[features], train["margin"].astype(float))
        part = test[["season", "week", "home_win", "margin"]].copy()
        part["predicted_margin"] = model.predict(test[features])
        part["margin_training_max_season"] = int(max(prior_seasons))
        rows.append(part)
    if not rows:
        raise ValueError(f"No chronological OOF margin history available before {before_season}")
    result = pd.concat(rows).sort_index()
    if int(result["season"].max()) >= before_season:
        raise RuntimeError("Margin calibration history crossed target-season boundary")
    if (result["margin_training_max_season"] >= result["season"]).any():
        raise RuntimeError("OOF margin history contains same/future-season fit")
    return result


def _fit_probability_mapper(oof: pd.DataFrame) -> LogisticRegression:
    if len(oof) < 500:
        raise ValueError(f"Need at least 500 chronological OOF calibration games; found {len(oof)}")
    y = oof["home_win"].astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        raise ValueError("Probability mapper needs both binary outcome classes")
    mapper = LogisticRegression(C=MAPPER_C, max_iter=3000, solver="lbfgs")
    mapper.fit(oof[["predicted_margin"]], y)
    return mapper


def season_forward_margin_informed(
    frame: pd.DataFrame,
    features: list[str],
    *,
    target_seasons: Iterable[int] = (2022, 2023, 2024, 2025),
    alpha: float = RIDGE_ALPHA,
) -> MarginSeasonResult:
    """Predict target seasons with prior-only margin fits and prior-OOF calibration."""
    usable = _valid_rows(frame, features)
    prediction_parts: list[pd.DataFrame] = []
    diagnostics: list[dict] = []
    calibration_parts: list[pd.DataFrame] = []

    for target_season in [int(value) for value in target_seasons]:
        train = usable[usable["season"].lt(target_season)]
        test = usable[usable["season"].eq(target_season)]
        if train.empty or test.empty:
            continue
        training_seasons = sorted(int(value) for value in train["season"].unique())
        if max(training_seasons) >= target_season:
            raise RuntimeError("Target margin model used non-prior season")

        oof = build_margin_oof_history(
            usable,
            features,
            before_season=target_season,
            alpha=alpha,
        )
        mapper = _fit_probability_mapper(oof)
        margin_model = _margin_pipeline(alpha)
        margin_model.fit(train[features], train["margin"].astype(float))
        expected_margin = margin_model.predict(test[features])
        probability = mapper.predict_proba(pd.DataFrame({"predicted_margin": expected_margin}))[:, 1]
        probability = np.clip(probability, EPS, 1.0 - EPS)

        part = test[["season", "week", "home_win", "margin"]].copy()
        part["predicted_margin"] = expected_margin
        part["probability"] = probability
        part["margin_training_max_season"] = int(max(training_seasons))
        part["calibration_max_season"] = int(oof["season"].max())
        prediction_parts.append(part)

        calibration_piece = oof.copy()
        calibration_piece["target_season"] = target_season
        calibration_parts.append(calibration_piece)
        diagnostics.append(
            {
                "target_season": target_season,
                "training_games": int(len(train)),
                "target_games": int(len(test)),
                "training_min_season": int(min(training_seasons)),
                "training_max_season": int(max(training_seasons)),
                "calibration_games": int(len(oof)),
                "calibration_min_season": int(oof["season"].min()),
                "calibration_max_season": int(oof["season"].max()),
                "ridge_alpha": float(alpha),
                "mapper_c": float(MAPPER_C),
                "mapper_intercept": float(mapper.intercept_[0]),
                "mapper_margin_coefficient": float(mapper.coef_[0, 0]),
                "target_margin_mae": float(np.mean(np.abs(test["margin"].to_numpy(dtype=float) - expected_margin))),
            }
        )

    if not prediction_parts:
        raise ValueError("No target-season margin predictions generated")
    predictions = pd.concat(prediction_parts).sort_index()
    if (predictions["margin_training_max_season"] >= predictions["season"]).any():
        raise RuntimeError("Margin model leaked same/future-season outcomes")
    if (predictions["calibration_max_season"] >= predictions["season"]).any():
        raise RuntimeError("Margin probability mapper leaked target/future outcomes")
    return MarginSeasonResult(
        predictions=predictions,
        diagnostics=pd.DataFrame(diagnostics),
        calibration_oof=pd.concat(calibration_parts).sort_index(),
    )

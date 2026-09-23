from __future__ import annotations

"""Frozen Stage-A Q1 quantile market-residual model.

Research only. This module implements ``ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1``
without changing production forecasting. It consumes only the Phase-2 gate frame,
uses expanding-season chronology, and never accesses completed 2026 outcomes.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor
from sklearn.metrics import mean_pinball_loss
from sklearn.preprocessing import StandardScaler

from nfl_forecast.challenger_ats_nextgen_gate import (
    FOOTBALL_FEATURE_LINEAGE,
    OUTER_TARGET_SEASONS,
    chronology_plan,
    validate_gate_frame,
)

CANDIDATE_ID = "ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1"
M2_ID = "ATS-Q1-M2-MARKET-ONLY-V1"
M0_ID = "ATS-Q1-M0-RAW-LINE"
QUANTILES = (10.0 / 21.0, 0.5, 11.0 / 21.0)
QUANTILE_LABELS = ("low", "med", "high")
ALPHA_GRID = (0.001, 0.01, 0.1, 1.0)
TIE_TOLERANCE = 1e-12
MIN_INNER_TRAIN_ROWS = 100

MANDATORY_MARKET_FEATURES = (
    "home_spread",
    "market_home_margin_center",
    "favorite_size",
)
OPTIONAL_MARKET_FEATURES = (
    "market_total",
    "no_vig_home_moneyline_prob",
)
FOOTBALL_FEATURES = tuple(FOOTBALL_FEATURE_LINEAGE.keys())
INTERACTION_FEATURES = (
    "market_center_x_centered_total",
    "favorite_size_x_centered_total",
)


@dataclass(frozen=True)
class Q1Preprocessor:
    feature_set: str
    optional_features: tuple[str, ...]
    medians: dict[str, float]
    design_columns: tuple[str, ...]
    scaler_mean: tuple[float, ...]
    scaler_scale: tuple[float, ...]

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        design = _build_unscaled_design(
            frame,
            feature_set=self.feature_set,
            medians=self.medians,
            optional_features=self.optional_features,
        )
        if tuple(design.columns) != self.design_columns:
            raise RuntimeError("Q1 design columns changed after preprocessing fit")
        values = design.to_numpy(dtype=float)
        mean = np.asarray(self.scaler_mean, dtype=float)
        scale = np.asarray(self.scaler_scale, dtype=float)
        return (values - mean) / scale


@dataclass(frozen=True)
class AlphaSelection:
    outer_target_season: int
    arm: str
    quantile: float
    selected_alpha: float
    mean_pinball_loss: float
    inner_rows: int
    inner_targets_used: tuple[int, ...]
    inner_targets_omitted: tuple[int, ...]
    alpha_losses: dict[float, float]


def _feature_contract(feature_set: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if feature_set == "market":
        return MANDATORY_MARKET_FEATURES + OPTIONAL_MARKET_FEATURES, OPTIONAL_MARKET_FEATURES
    if feature_set == "full":
        return (
            MANDATORY_MARKET_FEATURES + OPTIONAL_MARKET_FEATURES + FOOTBALL_FEATURES,
            OPTIONAL_MARKET_FEATURES + FOOTBALL_FEATURES,
        )
    raise ValueError("Q1 feature_set must be 'market' or 'full'")


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise ValueError(f"Q1 frame missing frozen feature: {column}")
    return pd.to_numeric(frame[column], errors="coerce")


def _training_medians(
    frame: pd.DataFrame,
    optional_features: tuple[str, ...],
) -> dict[str, float]:
    medians: dict[str, float] = {}
    for column in optional_features:
        values = _numeric(frame, column)
        value = float(values.median(skipna=True))
        if not np.isfinite(value):
            raise ValueError(f"Q1 training fold has no finite median for {column}")
        medians[column] = value
    return medians


def _build_unscaled_design(
    frame: pd.DataFrame,
    *,
    feature_set: str,
    medians: dict[str, float],
    optional_features: tuple[str, ...],
) -> pd.DataFrame:
    raw_features, expected_optional = _feature_contract(feature_set)
    if tuple(optional_features) != tuple(expected_optional):
        raise ValueError("Q1 optional-feature contract changed")

    design = pd.DataFrame(index=frame.index)
    for column in MANDATORY_MARKET_FEATURES:
        values = _numeric(frame, column)
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"Q1 mandatory feature {column} contains non-finite values")
        design[column] = values.astype(float)

    for column in optional_features:
        values = _numeric(frame, column)
        missing = ~np.isfinite(values.to_numpy(dtype=float))
        design[column] = values.where(~missing, medians[column]).astype(float)
        design[f"{column}__missing"] = missing.astype(float)

    if "market_total" not in design.columns:
        raise RuntimeError("Q1 frozen interactions require market_total")
    centered_total = design["market_total"] - float(medians["market_total"])
    design[INTERACTION_FEATURES[0]] = design["market_home_margin_center"] * centered_total
    design[INTERACTION_FEATURES[1]] = design["favorite_size"] * centered_total

    ordered: list[str] = []
    for column in raw_features:
        ordered.append(column)
        if column in optional_features:
            ordered.append(f"{column}__missing")
    ordered.extend(INTERACTION_FEATURES)
    design = design[ordered]
    if not np.isfinite(design.to_numpy(dtype=float)).all():
        raise ValueError("Q1 design contains non-finite values after fold-local imputation")
    return design


def fit_preprocessor(frame: pd.DataFrame, feature_set: str) -> Q1Preprocessor:
    _, optional = _feature_contract(feature_set)
    medians = _training_medians(frame, optional)
    design = _build_unscaled_design(
        frame,
        feature_set=feature_set,
        medians=medians,
        optional_features=optional,
    )
    scaler = StandardScaler(with_mean=True, with_std=True)
    scaler.fit(design.to_numpy(dtype=float))
    scale = np.asarray(scaler.scale_, dtype=float)
    scale[~np.isfinite(scale) | np.isclose(scale, 0.0)] = 1.0
    return Q1Preprocessor(
        feature_set=feature_set,
        optional_features=tuple(optional),
        medians=medians,
        design_columns=tuple(design.columns),
        scaler_mean=tuple(float(x) for x in scaler.mean_),
        scaler_scale=tuple(float(x) for x in scale),
    )


def _eligible(frame: pd.DataFrame, seasons: tuple[int, ...] | list[int]) -> pd.DataFrame:
    season = pd.to_numeric(frame["season"], errors="coerce")
    eligible = frame["ats_eligible"].astype(bool)
    residual = pd.to_numeric(frame["ats_residual"], errors="coerce")
    mask = season.isin(list(seasons)) & eligible & np.isfinite(residual.to_numpy(dtype=float))
    return frame.loc[mask].copy()


def _fit_quantile_model(
    train: pd.DataFrame,
    target: pd.DataFrame,
    *,
    feature_set: str,
    quantile: float,
    alpha: float,
) -> np.ndarray:
    prep = fit_preprocessor(train, feature_set)
    x_train = prep.transform(train)
    x_target = prep.transform(target)
    y_train = pd.to_numeric(train["ats_residual"], errors="raise").to_numpy(dtype=float)
    model = QuantileRegressor(
        quantile=float(quantile),
        alpha=float(alpha),
        fit_intercept=True,
        solver="highs",
    )
    model.fit(x_train, y_train)
    prediction = np.asarray(model.predict(x_target), dtype=float)
    if not np.isfinite(prediction).all():
        raise RuntimeError("Q1 produced non-finite quantile predictions")
    return prediction


def choose_alpha(alpha_losses: dict[float, float]) -> tuple[float, float]:
    """Choose minimum loss; exact/numerical ties prefer the smaller alpha."""
    if set(float(a) for a in alpha_losses) != set(ALPHA_GRID):
        raise ValueError("Q1 alpha search must use the complete frozen alpha grid")
    finite = {float(a): float(loss) for a, loss in alpha_losses.items() if np.isfinite(loss)}
    if len(finite) != len(ALPHA_GRID):
        raise ValueError("Q1 alpha search produced a non-finite loss")
    best_loss = min(finite.values())
    tied = [a for a, loss in finite.items() if abs(loss - best_loss) <= TIE_TOLERANCE]
    selected = min(tied)
    return float(selected), float(finite[selected])


def select_alpha(
    frame: pd.DataFrame,
    *,
    outer_target_season: int,
    feature_set: str,
    quantile: float,
) -> AlphaSelection:
    validate_gate_frame(frame)
    if float(quantile) not in QUANTILES:
        raise ValueError("Q1 quantile is outside the frozen quantile set")
    plan = chronology_plan(int(outer_target_season))
    alpha_targets: dict[float, list[np.ndarray]] = {a: [] for a in ALPHA_GRID}
    alpha_predictions: dict[float, list[np.ndarray]] = {a: [] for a in ALPHA_GRID}
    targets_used: list[int] = []
    targets_omitted: list[int] = []

    for inner_target in plan.inner_target_seasons:
        train = _eligible(frame, plan.inner_training_seasons[int(inner_target)])
        valid = _eligible(frame, (int(inner_target),))
        if len(train) < MIN_INNER_TRAIN_ROWS or valid.empty:
            targets_omitted.append(int(inner_target))
            continue
        targets_used.append(int(inner_target))
        y_valid = pd.to_numeric(valid["ats_residual"], errors="raise").to_numpy(dtype=float)
        for alpha in ALPHA_GRID:
            pred = _fit_quantile_model(
                train,
                valid,
                feature_set=feature_set,
                quantile=float(quantile),
                alpha=float(alpha),
            )
            alpha_targets[alpha].append(y_valid)
            alpha_predictions[alpha].append(pred)

    if not targets_used:
        raise RuntimeError(
            "Q1 has no usable inner rolling-origin fold after the frozen 100-row minimum"
        )

    losses: dict[float, float] = {}
    total_rows = 0
    for alpha in ALPHA_GRID:
        if not alpha_targets[alpha]:
            raise RuntimeError(f"Q1 alpha {alpha} has no inner OOF rows")
        y = np.concatenate(alpha_targets[alpha])
        pred = np.concatenate(alpha_predictions[alpha])
        total_rows = len(y)
        losses[float(alpha)] = float(mean_pinball_loss(y, pred, alpha=float(quantile)))

    selected, selected_loss = choose_alpha(losses)
    arm = M2_ID if feature_set == "market" else CANDIDATE_ID
    return AlphaSelection(
        outer_target_season=int(outer_target_season),
        arm=arm,
        quantile=float(quantile),
        selected_alpha=selected,
        mean_pinball_loss=selected_loss,
        inner_rows=int(total_rows),
        inner_targets_used=tuple(targets_used),
        inner_targets_omitted=tuple(targets_omitted),
        alpha_losses=losses,
    )


def generate_q1_outer_oof(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate frozen Q1/M2/M0 2022-2025 season-held-out predictions."""
    validate_gate_frame(frame)
    outputs: list[pd.DataFrame] = []
    tuning_rows: list[dict] = []

    for outer in OUTER_TARGET_SEASONS:
        plan = chronology_plan(int(outer))
        train = _eligible(frame, plan.outer_training_seasons)
        target = _eligible(frame, (int(outer),))
        if train.empty or target.empty:
            raise RuntimeError(f"Q1 outer season {outer} lacks eligible train/target rows")

        result_cols = [
            c for c in (
                "game_id", "season", "week", "gameday", "home_team", "away_team",
                "home_spread", "market_home_margin_center", "favorite_size", "market_total",
                "ats_residual", "ats_outcome", "market_evidence_class",
            ) if c in target.columns
        ]
        result = target[result_cols].copy()

        for label, quantile in zip(QUANTILE_LABELS, QUANTILES, strict=True):
            result[f"m0_q_{label}"] = 0.0
            for feature_set, prefix in (("market", "m2"), ("full", "q1")):
                selection = select_alpha(
                    frame,
                    outer_target_season=int(outer),
                    feature_set=feature_set,
                    quantile=float(quantile),
                )
                prediction = _fit_quantile_model(
                    train,
                    target,
                    feature_set=feature_set,
                    quantile=float(quantile),
                    alpha=selection.selected_alpha,
                )
                result[f"{prefix}_q_{label}"] = prediction
                result[f"{prefix}_alpha_{label}"] = selection.selected_alpha
                tuning_rows.append(
                    {
                        "outer_target_season": int(outer),
                        "arm": selection.arm,
                        "feature_set": feature_set,
                        "quantile_label": label,
                        "quantile": float(quantile),
                        "selected_alpha": selection.selected_alpha,
                        "selected_mean_pinball_loss": selection.mean_pinball_loss,
                        "inner_rows": selection.inner_rows,
                        "inner_targets_used": ",".join(map(str, selection.inner_targets_used)),
                        "inner_targets_omitted": ",".join(
                            map(str, selection.inner_targets_omitted)
                        ),
                        **{
                            f"alpha_{alpha:g}_loss": selection.alpha_losses[float(alpha)]
                            for alpha in ALPHA_GRID
                        },
                    }
                )
        outputs.append(result)

    oof = pd.concat(outputs, ignore_index=True)
    if oof["game_id"].astype(str).duplicated().any():
        raise RuntimeError("Q1 OOF contains duplicate game_id")
    oof = oof.sort_values(["season", "game_id"], kind="mergesort").reset_index(drop=True)
    tuning = pd.DataFrame(tuning_rows).sort_values(
        ["outer_target_season", "arm", "quantile"], kind="mergesort"
    ).reset_index(drop=True)
    return oof, tuning


def q1_metric_table(oof: pd.DataFrame) -> pd.DataFrame:
    """Return preregistered Q1 quantile/location metrics by arm and season/overall."""
    required = {"season", "ats_residual", "market_home_margin_center"}
    missing = required - set(oof.columns)
    if missing:
        raise ValueError(f"Q1 OOF missing metric fields: {sorted(missing)}")
    rows: list[dict] = []
    groups: list[tuple[str, pd.DataFrame]] = [("ALL", oof)]
    groups.extend((str(int(s)), part) for s, part in oof.groupby("season", sort=True))
    arms = (("M0", "m0"), ("M2", "m2"), ("Q1", "q1"))

    for season_label, part in groups:
        y = pd.to_numeric(part["ats_residual"], errors="raise").to_numpy(dtype=float)
        center = pd.to_numeric(
            part["market_home_margin_center"], errors="raise"
        ).to_numpy(dtype=float)
        actual_margin = center + y
        for arm, prefix in arms:
            med = pd.to_numeric(part[f"{prefix}_q_med"], errors="raise").to_numpy(dtype=float)
            margin_pred = center + med
            for label, quantile in zip(QUANTILE_LABELS, QUANTILES, strict=True):
                pred = pd.to_numeric(
                    part[f"{prefix}_q_{label}"], errors="raise"
                ).to_numpy(dtype=float)
                rows.append(
                    {
                        "season": season_label,
                        "arm": arm,
                        "quantile_label": label,
                        "quantile": float(quantile),
                        "n": int(len(part)),
                        "pinball_loss": float(mean_pinball_loss(y, pred, alpha=float(quantile))),
                        "empirical_coverage": float(np.mean(y <= pred)),
                        "coverage_error": float(np.mean(y <= pred) - float(quantile)),
                        "median_abs_residual_error": float(np.median(np.abs(y - med))),
                        "residual_mae": float(np.mean(np.abs(y - med))),
                        "residual_rmse": float(np.sqrt(np.mean(np.square(y - med)))),
                        "margin_mae": float(np.mean(np.abs(actual_margin - margin_pred))),
                        "margin_rmse": float(np.sqrt(np.mean(np.square(actual_margin - margin_pred)))),
                    }
                )
    return pd.DataFrame(rows)


def quantile_crossing_table(oof: pd.DataFrame) -> pd.DataFrame:
    """Diagnose, but do not repair, independently fitted Q1/M2 quantile crossings."""
    rows: list[dict] = []
    for arm, prefix in (("M2", "m2"), ("Q1", "q1")):
        low = pd.to_numeric(oof[f"{prefix}_q_low"], errors="raise").to_numpy(dtype=float)
        med = pd.to_numeric(oof[f"{prefix}_q_med"], errors="raise").to_numpy(dtype=float)
        high = pd.to_numeric(oof[f"{prefix}_q_high"], errors="raise").to_numpy(dtype=float)
        crossing = (low > med) | (med > high)
        rows.append(
            {
                "arm": arm,
                "n": int(len(oof)),
                "crossing_rows": int(crossing.sum()),
                "crossing_rate": float(crossing.mean()) if len(oof) else 0.0,
                "posthoc_repair_applied": False,
            }
        )
    return pd.DataFrame(rows)

from __future__ import annotations

"""Rolling-origin Next Gen Stats efficiency challenger for LevLine Props 2.0.

This module evaluates whether strictly lagged NGS context predicts next-game player
efficiency better than the player's own lagged NGS efficiency. It is a gate before
any NGS signal is allowed to modify a LevLine Props Fair Line.

No completed 2026 outcome is accepted. Hyperparameters and feature sets are fixed.
Historical 2023-2025 results are development evidence only.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

from research.props.v2.props_ngs_efficiency_state import build_lagged_ngs_state

ENGINE_VERSION = "levline-props-ngs-efficiency-model-v0.1.0"
RESEARCH_LABEL = "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE"
RIDGE_ALPHA = 25.0
MIN_TRAINING_ROWS = 100
EPS = 1e-9

METRICS = {
    "completion_rate": {
        "channel": "pass",
        "target": "completion_percentage",
        "baseline": "ngs_pass_completion_percentage",
        "features": (
            "ngs_pass_completion_percentage",
            "ngs_pass_expected_completion_percentage",
            "ngs_pass_completion_percentage_above_expectation",
            "ngs_pass_avg_intended_air_yards",
            "ngs_pass_avg_completed_air_yards",
            "ngs_pass_avg_time_to_throw",
            "ngs_pass_aggressiveness",
        ),
        "probability": True,
    },
    "catch_rate": {
        "channel": "rec",
        "target": "catch_percentage",
        "baseline": "ngs_rec_catch_percentage",
        "features": (
            "ngs_rec_catch_percentage",
            "ngs_rec_avg_separation",
            "ngs_rec_avg_cushion",
            "ngs_rec_avg_air_distance",
            "ngs_rec_avg_yac",
            "ngs_rec_avg_expected_yac",
            "ngs_rec_avg_yac_above_expectation",
        ),
        "probability": True,
    },
    "rushing_ypc": {
        "channel": "rush",
        "target": "avg_rush_yards",
        "baseline": "ngs_rush_avg_rush_yards",
        "features": (
            "ngs_rush_avg_rush_yards",
            "ngs_rush_rush_yards_over_expected_per_att",
            "ngs_rush_rush_pct_over_expected",
            "ngs_rush_percent_attempts_gte_eight_defenders",
            "ngs_rush_avg_time_to_los",
            "ngs_rush_efficiency",
        ),
        "probability": False,
    },
}

CHANNEL_FRAME_KEY = {"pass": "passing", "rec": "receiving", "rush": "rushing"}


class NGSEfficiencyModelError(ValueError):
    pass


@dataclass(frozen=True)
class RidgeState:
    metric: str
    feature_names: tuple[str, ...]
    impute_values: tuple[float, ...]
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    intercept: float
    coefficients: tuple[float, ...]
    alpha: float
    training_rows: int
    training_players: int
    training_season_min: int
    training_season_max: int
    probability_target: bool
    engine_version: str = ENGINE_VERSION
    research_label: str = RESEARCH_LABEL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_probability(values: pd.Series) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    finite = x[np.isfinite(x)]
    if not finite.empty and float(finite.quantile(0.95)) > 1.5:
        x = x / 100.0
    return x.clip(lower=0.0, upper=1.0)


def _normalize_current(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    required = {"season", "week", "player_gsis_id"}
    missing = required - set(frame.columns)
    if missing:
        raise NGSEfficiencyModelError(f"NGS current frame missing: {sorted(missing)}")
    out = frame.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out["player_gsis_id"] = out["player_gsis_id"].astype("string").fillna("").str.strip()
    out = out[
        out["season"].notna()
        & out["week"].notna()
        & out["week"].gt(0)
        & out["player_gsis_id"].ne("")
        & out["player_gsis_id"].str.lower().ne("nan")
    ].copy()
    if "season_type" in out.columns:
        out = out[out["season_type"].astype(str).str.upper().eq("REG")].copy()
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    if (out["season"] >= 2026).any():
        # Feature publication may exist in 2026, but completed 2026 outcomes cannot
        # enter this retrospective model-fitting/evaluation helper.
        out = out[out["season"].lt(2026)].copy()
    return out


def build_efficiency_learning_table(
    *,
    passing: pd.DataFrame | None,
    receiving: pd.DataFrame | None,
    rushing: pd.DataFrame | None,
    season_start: int = 2020,
    season_end: int = 2025,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build player-week rows using only state from weeks before each target week."""

    frames = {
        "passing": _normalize_current(passing),
        "receiving": _normalize_current(receiving),
        "rushing": _normalize_current(rushing),
    }
    all_periods: set[tuple[int, int]] = set()
    for frame in frames.values():
        if frame.empty:
            continue
        period = frame[
            frame["season"].between(int(season_start), int(season_end))
        ][["season", "week"]].drop_duplicates()
        all_periods.update((int(r.season), int(r.week)) for r in period.itertuples(index=False))

    rows: list[dict[str, Any]] = []
    state_calls = 0
    for season, week in sorted(all_periods):
        player_ids: set[str] = set()
        current_by_channel: dict[str, pd.DataFrame] = {}
        for channel, frame_key in CHANNEL_FRAME_KEY.items():
            frame = frames[frame_key]
            current = frame[(frame["season"].eq(season)) & (frame["week"].eq(week))].copy()
            current_by_channel[channel] = current
            if not current.empty:
                player_ids.update(current["player_gsis_id"].astype(str))

        if not player_ids:
            continue
        state, _audit = build_lagged_ngs_state(
            passing=frames["passing"],
            receiving=frames["receiving"],
            rushing=frames["rushing"],
            season=season,
            week=week,
            player_ids=player_ids,
        )
        state_calls += 1
        if state.empty:
            continue
        state = state.rename(columns={"player_id": "player_gsis_id"})

        for metric, config in METRICS.items():
            current = current_by_channel[config["channel"]]
            target_col = str(config["target"])
            if current.empty or target_col not in current.columns:
                continue
            target = current[
                ["player_gsis_id", "season", "week", target_col]
            ].copy()
            target[target_col] = pd.to_numeric(target[target_col], errors="coerce")
            target = target[target[target_col].notna()].copy()
            if target.empty:
                continue

            merged = target.merge(
                state,
                on="player_gsis_id",
                how="inner",
                validate="many_to_one",
            )
            if merged.empty:
                continue
            baseline_col = str(config["baseline"])
            if baseline_col not in merged.columns:
                continue
            if config["probability"]:
                merged["_target"] = _normalize_probability(merged[target_col])
                merged["_baseline"] = _normalize_probability(merged[baseline_col])
            else:
                merged["_target"] = pd.to_numeric(merged[target_col], errors="coerce")
                merged["_baseline"] = pd.to_numeric(merged[baseline_col], errors="coerce")

            feature_cols = list(config["features"])
            valid = merged["_target"].notna() & merged["_baseline"].notna()
            merged = merged[valid].copy()
            for feature in feature_cols:
                if feature not in merged.columns:
                    merged[feature] = np.nan
            # Avoid itertuples here: pandas renames underscore-prefixed
            # columns such as _target/_baseline, which can silently break
            # attribute-based access. Dictionary records preserve exact column names.
            for record in merged.to_dict("records"):
                item = {
                    "metric": metric,
                    "player_id": str(record["player_gsis_id"]),
                    "season": int(record["season"]),
                    "week": int(record["week"]),
                    "target": float(record["_target"]),
                    "baseline": float(record["_baseline"]),
                }
                for feature in feature_cols:
                    value = record.get(feature)
                    item[feature] = (
                        float(value)
                        if pd.notna(value) and math.isfinite(float(value))
                        else np.nan
                    )
                rows.append(item)

    table = pd.DataFrame(rows)
    return table, {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "season_start": int(season_start),
        "season_end": int(season_end),
        "state_build_periods": int(state_calls),
        "rows": int(len(table)),
        "metrics": (
            {} if table.empty else {
                str(metric): int(len(group))
                for metric, group in table.groupby("metric", sort=True)
            }
        ),
        "completed_2026_outcomes_used": 0,
        "target_week_state_rows_used": 0,
    }


def _design_matrix(
    frame: pd.DataFrame,
    features: tuple[str, ...],
    *,
    impute: np.ndarray | None = None,
    means: np.ndarray | None = None,
    scales: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x = frame.loc[:, list(features)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if impute is None:
        impute = np.nanmedian(x, axis=0)
        impute = np.where(np.isfinite(impute), impute, 0.0)
    missing = ~np.isfinite(x)
    if missing.any():
        x[missing] = np.take(impute, np.where(missing)[1])
    if means is None:
        means = np.mean(x, axis=0)
    if scales is None:
        scales = np.std(x, axis=0)
        scales = np.where(scales > EPS, scales, 1.0)
    z = (x - means) / scales
    return z, impute, means, scales


def fit_metric_model(
    frame: pd.DataFrame,
    metric: str,
    *,
    alpha: float = RIDGE_ALPHA,
) -> RidgeState:
    if metric not in METRICS:
        raise NGSEfficiencyModelError(f"unsupported metric: {metric}")
    work = frame[frame["metric"].eq(metric)].copy()
    if len(work) < MIN_TRAINING_ROWS:
        raise NGSEfficiencyModelError(
            f"{metric} requires at least {MIN_TRAINING_ROWS} training rows; got {len(work)}"
        )
    features = tuple(METRICS[metric]["features"])
    z, impute, means, scales = _design_matrix(work, features)
    y = pd.to_numeric(work["target"], errors="coerce").to_numpy(float)
    if not np.isfinite(y).all():
        raise NGSEfficiencyModelError(f"{metric} has non-finite target")

    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1], dtype=float) * float(alpha)
    penalty[0, 0] = 0.0
    lhs = design.T @ design + penalty
    rhs = design.T @ y
    beta = np.linalg.solve(lhs, rhs)

    seasons = pd.to_numeric(work["season"], errors="raise").astype(int)
    return RidgeState(
        metric=metric,
        feature_names=features,
        impute_values=tuple(float(v) for v in impute),
        feature_means=tuple(float(v) for v in means),
        feature_scales=tuple(float(v) for v in scales),
        intercept=float(beta[0]),
        coefficients=tuple(float(v) for v in beta[1:]),
        alpha=float(alpha),
        training_rows=int(len(work)),
        training_players=int(work["player_id"].astype(str).nunique()),
        training_season_min=int(seasons.min()),
        training_season_max=int(seasons.max()),
        probability_target=bool(METRICS[metric]["probability"]),
    )


def predict_metric(frame: pd.DataFrame, model: RidgeState) -> np.ndarray:
    features = tuple(model.feature_names)
    z, _, _, _ = _design_matrix(
        frame,
        features,
        impute=np.asarray(model.impute_values, float),
        means=np.asarray(model.feature_means, float),
        scales=np.asarray(model.feature_scales, float),
    )
    pred = float(model.intercept) + z @ np.asarray(model.coefficients, float)
    if model.probability_target:
        pred = np.clip(pred, 0.01, 0.99)
    else:
        pred = np.clip(pred, 0.25, 15.0)
    return np.asarray(pred, float)


def _metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    target = frame["target"].to_numpy(float)
    baseline = frame["baseline"].to_numpy(float)
    pred = frame["prediction"].to_numpy(float)
    baseline_abs = np.abs(baseline - target)
    pred_abs = np.abs(pred - target)
    return {
        "n": int(len(frame)),
        "players": int(frame["player_id"].astype(str).nunique()),
        "baseline_mae": float(np.mean(baseline_abs)),
        "challenger_mae": float(np.mean(pred_abs)),
        "mae_improvement": float(np.mean(baseline_abs - pred_abs)),
        "baseline_rmse": float(np.sqrt(np.mean((baseline - target) ** 2))),
        "challenger_rmse": float(np.sqrt(np.mean((pred - target) ** 2))),
        "challenger_better_row_rate": float(np.mean(pred_abs < baseline_abs)),
    }


def player_clustered_mae_improvement_ci(
    frame: pd.DataFrame,
    *,
    replicates: int = 2000,
    seed: int = 20260918,
) -> list[float | None]:
    players = np.asarray(sorted(frame["player_id"].astype(str).unique()))
    if len(players) < 2:
        return [None, None]
    grouped = {
        player: frame[frame["player_id"].astype(str).eq(player)]
        for player in players
    }
    rng = np.random.default_rng(seed)
    diffs = np.empty(int(replicates), dtype=float)
    for i in range(int(replicates)):
        sampled = rng.choice(players, size=len(players), replace=True)
        boot = pd.concat([grouped[player] for player in sampled], ignore_index=True)
        diffs[i] = float(
            np.mean(
                np.abs(boot["baseline"] - boot["target"])
                - np.abs(boot["prediction"] - boot["target"])
            )
        )
    return [
        float(np.quantile(diffs, 0.025)),
        float(np.quantile(diffs, 0.975)),
    ]


def evaluate_rolling_origin(
    learning_table: pd.DataFrame,
    *,
    evaluation_seasons: tuple[int, ...] = (2024, 2025),
    alpha: float = RIDGE_ALPHA,
) -> dict[str, Any]:
    if learning_table.empty:
        raise NGSEfficiencyModelError("learning table is empty")

    results: dict[str, Any] = {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "ridge_alpha_fixed": float(alpha),
        "hyperparameter_tuning_performed": False,
        "completed_2026_outcomes_used": 0,
        "evaluation": {},
    }

    for season in evaluation_seasons:
        season_result: dict[str, Any] = {}
        for metric in METRICS:
            train = learning_table[
                learning_table["metric"].eq(metric)
                & learning_table["season"].lt(int(season))
            ].copy()
            test = learning_table[
                learning_table["metric"].eq(metric)
                & learning_table["season"].eq(int(season))
            ].copy()
            if len(train) < MIN_TRAINING_ROWS or test.empty:
                season_result[metric] = {
                    "status": "insufficient_data",
                    "training_rows": int(len(train)),
                    "evaluation_rows": int(len(test)),
                }
                continue
            model = fit_metric_model(train, metric, alpha=alpha)
            test["prediction"] = predict_metric(test, model)
            metrics = _metrics(test)
            metrics["mae_improvement_player_clustered_ci95"] = (
                player_clustered_mae_improvement_ci(test)
            )
            season_result[metric] = {
                "status": "evaluated",
                "model": model.to_dict(),
                "metrics": metrics,
            }
        results["evaluation"][str(int(season))] = season_result
    return results

from __future__ import annotations

"""Research-only market-reliance and forecast-horizon diagnostics for LevLine.

Nothing in this module is imported by the production forecast path.  Historical studies
refuse post-2025 outcomes; prospective 2026 outcomes are evaluation-only.  Snapshot
selection is strictly at-or-before the requested pre-kickoff horizon.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .challenger_evaluation import calibration_diagnostics, forecast_metrics, paired_bootstrap

EPS = 1e-6
DEFAULT_HORIZONS_MINUTES = (120, 90, 60, 45, 30, 25, 15)
DEFAULT_MARKET_WEIGHTS = (0.0, 0.25, 0.50, 0.75, 0.90, 1.0)
TARGET_SEASONS = (2022, 2023, 2024, 2025)
DISAGREEMENT_EDGES = (0.0, 0.03, 0.05, 0.10, float("inf"))
DISAGREEMENT_LABELS = ("<3pp", "3-5pp", "5-10pp", "10pp+")


def kickoff_utc(gameday: object, gametime: object) -> datetime:
    text = f"{str(gameday)[:10]} {str(gametime)[:5]}"
    local = datetime.strptime(text, "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo("America/New_York")
    )
    return local.astimezone(timezone.utc)


def _clip(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values: Iterable[float]) -> np.ndarray:
    p = _clip(values)
    return np.log(p / (1.0 - p))


def linear_pool(pure: Iterable[float], market: Iterable[float], market_weight: float) -> np.ndarray:
    w = float(market_weight)
    if not 0.0 <= w <= 1.0:
        raise ValueError("market_weight must be within [0, 1]")
    return _clip((1.0 - w) * np.asarray(pure, dtype=float) + w * np.asarray(market, dtype=float))


def logit_pool(pure: Iterable[float], market: Iterable[float], market_weight: float) -> np.ndarray:
    w = float(market_weight)
    if not 0.0 <= w <= 1.0:
        raise ValueError("market_weight must be within [0, 1]")
    z = (1.0 - w) * _logit(pure) + w * _logit(market)
    return _clip(1.0 / (1.0 + np.exp(-z)))


def _week_from_game_id(value: object) -> float:
    parts = str(value).split("_")
    if len(parts) < 2:
        return np.nan
    try:
        return float(int(parts[1]))
    except Exception:
        return np.nan


def prepare_frozen_historical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the immutable F-ST training frame for research-only historical scoring."""
    required = {"game_id", "season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"market-reliance frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    if work["season"].dropna().ge(2026).any():
        raise ValueError("Historical market-reliance research refuses 2026-or-later outcomes")
    for column in ("home_win", "market_prob", "pure_prob"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=["season", "home_win", "market_prob", "pure_prob"]).copy()
    if work.empty:
        raise ValueError("No usable historical market-reliance rows")
    if not work["home_win"].isin([0, 1]).all():
        raise ValueError("home_win must be binary")
    for column in ("market_prob", "pure_prob"):
        if ((work[column] <= 0.0) | (work[column] >= 1.0)).any():
            raise ValueError(f"{column} must be inside (0, 1)")
    work["week"] = work["game_id"].map(_week_from_game_id)
    return work


def walk_forward_weight_backtest(
    frame: pd.DataFrame,
    *,
    pooling: str = "linear",
    market_weights: Sequence[float] = DEFAULT_MARKET_WEIGHTS,
    target_seasons: Sequence[int] = TARGET_SEASONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose a fixed market weight only on seasons preceding each test season."""
    work = prepare_frozen_historical_frame(frame)
    pool = linear_pool if pooling == "linear" else logit_pool if pooling == "logit" else None
    if pool is None:
        raise ValueError("pooling must be linear or logit")
    weights = tuple(float(x) for x in market_weights)
    if not weights or any(x < 0.0 or x > 1.0 for x in weights):
        raise ValueError("market_weights must be non-empty values within [0, 1]")

    scored_parts: list[pd.DataFrame] = []
    selections: list[dict] = []
    for season in [int(x) for x in target_seasons]:
        tune = work[work.season < season].copy()
        test = work[work.season == season].copy()
        if test.empty:
            continue
        if len(tune) < 300:
            raise ValueError(f"Insufficient pre-{season} history for market-weight selection")
        candidates = []
        for weight in weights:
            probability = pool(tune.pure_prob, tune.market_prob, weight)
            metrics = forecast_metrics(tune.assign(_p=probability), "_p")
            candidates.append((metrics["brier"], weight, metrics))
        _, selected_weight, tune_metrics = min(candidates, key=lambda item: (item[0], -item[1]))
        probability = pool(test.pure_prob, test.market_prob, selected_weight)
        part = test[["game_id", "season", "week", "home_win", "pure_prob", "market_prob"]].copy()
        part["probability"] = probability
        part["pooling"] = pooling
        part["selected_market_weight"] = selected_weight
        scored_parts.append(part)
        test_metrics = forecast_metrics(part, "probability")
        selections.append(
            {
                "season": season,
                "pooling": pooling,
                "tuning_games": int(len(tune)),
                "selected_market_weight": selected_weight,
                "tuning_brier": tune_metrics["brier"],
                "test_games": int(len(test)),
                "test_brier": test_metrics["brier"],
                "test_log_loss": test_metrics["log_loss"],
                "test_winner_pct": test_metrics["winner_pct"],
            }
        )
    if not scored_parts:
        raise ValueError("No target seasons available for market-weight backtest")
    return pd.concat(scored_parts).sort_index(), pd.DataFrame(selections)


def disagreement_buckets(frame: pd.DataFrame, probability_cols: Sequence[str]) -> pd.DataFrame:
    """Score forecasts conditional on football-vs-market disagreement magnitude."""
    required = {"home_win", "pure_prob", "market_prob", *probability_cols}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"disagreement research missing fields: {sorted(missing)}")
    work = frame.copy()
    work["abs_pure_market_gap"] = (
        pd.to_numeric(work.pure_prob, errors="coerce")
        - pd.to_numeric(work.market_prob, errors="coerce")
    ).abs()
    work["bucket"] = pd.cut(
        work.abs_pure_market_gap,
        bins=list(DISAGREEMENT_EDGES),
        labels=list(DISAGREEMENT_LABELS),
        right=False,
        include_lowest=True,
    )
    rows: list[dict] = []
    for bucket in DISAGREEMENT_LABELS:
        part = work[work.bucket.astype("string").eq(bucket)].copy()
        if part.empty:
            continue
        market_pick = pd.to_numeric(part.market_prob, errors="coerce") >= 0.5
        pure_pick = pd.to_numeric(part.pure_prob, errors="coerce") >= 0.5
        base = {
            "bucket": bucket,
            "games": int(len(part)),
            "mean_abs_pure_market_gap": float(part.abs_pure_market_gap.mean()),
            "pick_disagreement_rate": float((market_pick != pure_pick).mean()),
        }
        for column in probability_cols:
            metrics = forecast_metrics(part, column)
            rows.append({"forecast": column, **base, **metrics})
    return pd.DataFrame(rows)


def historical_candidate_table(frame: pd.DataFrame, candidate_probability: pd.Series) -> pd.DataFrame:
    """Score market, football and one supplied chronology-preserving candidate."""
    work = prepare_frozen_historical_frame(frame)
    aligned = pd.to_numeric(candidate_probability.reindex(work.index), errors="coerce")
    work = work.assign(candidate_prob=aligned).dropna(subset=["candidate_prob"])
    rows = []
    for label, column in (
        ("Football only", "pure_prob"),
        ("Market only", "market_prob"),
        ("Candidate", "candidate_prob"),
    ):
        metrics = forecast_metrics(work, column)
        calibration, _ = calibration_diagnostics(work, column)
        rows.append({"forecast": label, **metrics, **calibration})
    return pd.DataFrame(rows)


def compare_candidate_to_market(
    frame: pd.DataFrame,
    candidate_probability: pd.Series,
    *,
    bootstrap_samples: int = 5000,
    seed: int = 26,
) -> pd.DataFrame:
    work = prepare_frozen_historical_frame(frame)
    work["candidate_prob"] = pd.to_numeric(candidate_probability.reindex(work.index), errors="coerce")
    work = work.dropna(subset=["candidate_prob"])
    rows = []
    for metric in ("brier", "log_loss", "accuracy"):
        result = paired_bootstrap(
            work,
            "candidate_prob",
            "market_prob",
            metric=metric,
            block_cols=("season", "week"),
            samples=bootstrap_samples,
            seed=seed + len(rows),
        )
        rows.append(asdict(result))
    return pd.DataFrame(rows)


def select_forecast_horizons(
    run_history: pd.DataFrame,
    prediction_history: pd.DataFrame | None = None,
    *,
    horizons_minutes: Sequence[int] = DEFAULT_HORIZONS_MINUTES,
    include_preweek: bool = True,
) -> pd.DataFrame:
    """Select the latest valid snapshot at or before each requested pre-kickoff horizon.

    The PREWEEK row is the earliest valid pre-kickoff forecast observed for the game.  It
    is an accountability baseline, not a fixed-horizon substitute.  Horizon rows never
    use a snapshot after their target timestamp.
    """
    required = {
        "game_id", "gameday", "gametime", "prediction_timestamp_utc",
        "final_home_prob", "market_home_prob",
    }
    missing = required - set(run_history.columns)
    if missing:
        raise ValueError(f"run history missing forecast-horizon fields: {sorted(missing)}")
    horizons = tuple(sorted({int(x) for x in horizons_minutes}, reverse=True))
    if not horizons or any(x <= 0 for x in horizons):
        raise ValueError("horizons_minutes must contain positive integers")

    history = run_history.copy()
    history["_observed"] = pd.to_datetime(history.prediction_timestamp_utc, utc=True, errors="coerce")
    history["final_home_prob"] = pd.to_numeric(history.final_home_prob, errors="coerce")
    history["market_home_prob"] = pd.to_numeric(history.market_home_prob, errors="coerce")
    if "fst_pure_home_prob" in history.columns:
        history["football_home_prob"] = pd.to_numeric(history.fst_pure_home_prob, errors="coerce")
    elif "pure_home_prob" in history.columns:
        history["football_home_prob"] = pd.to_numeric(history.pure_home_prob, errors="coerce")
    else:
        history["football_home_prob"] = np.nan
    history = history[
        history._observed.notna()
        & history.final_home_prob.notna()
        & history.market_home_prob.notna()
    ].copy()
    rows: list[dict] = []
    metadata = [
        "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
        "snapshot_type", "prediction_id", "final_probability_strategy", "model_version",
    ]
    for game_id, group in history.groupby("game_id", sort=True):
        group = group.sort_values("_observed", kind="stable")
        schedule_row = group.iloc[-1]
        try:
            kickoff = pd.Timestamp(kickoff_utc(schedule_row.gameday, schedule_row.gametime))
        except Exception:
            continue
        pregame = group[group._observed < kickoff].copy()
        if pregame.empty:
            continue

        def emit(chosen: pd.Series, label: str, target: pd.Timestamp | None, minutes: int | None) -> None:
            observed = chosen._observed
            minute_to_kickoff = (kickoff - observed).total_seconds() / 60.0
            staleness = (
                (target - observed).total_seconds() / 60.0 if target is not None else np.nan
            )
            row = {key: chosen.get(key, np.nan) for key in metadata}
            row.update(
                {
                    "horizon": label,
                    "target_minutes_to_kickoff": minutes,
                    "kickoff_utc": kickoff.isoformat(),
                    "target_timestamp_utc": target.isoformat() if target is not None else None,
                    "snapshot_timestamp_utc": observed.isoformat(),
                    "minutes_to_kickoff_at_snapshot": float(minute_to_kickoff),
                    "staleness_minutes_vs_target": float(staleness) if np.isfinite(staleness) else np.nan,
                    "no_lookahead": bool(target is None or observed <= target),
                    "levline_home_prob": float(chosen.final_home_prob),
                    "market_home_prob": float(chosen.market_home_prob),
                    "football_home_prob": (
                        float(chosen.football_home_prob)
                        if pd.notna(chosen.football_home_prob) else np.nan
                    ),
                    "actual_home_score": np.nan,
                    "actual_away_score": np.nan,
                    "home_win": pd.NA,
                    "graded": False,
                }
            )
            rows.append(row)

        if include_preweek:
            emit(pregame.iloc[0], "PREWEEK", None, None)
        for minutes in horizons:
            target = kickoff - pd.Timedelta(minutes=minutes)
            eligible = pregame[pregame._observed <= target]
            if eligible.empty:
                continue
            emit(eligible.iloc[-1], f"T-{minutes}", target, minutes)

    selected = pd.DataFrame(rows)
    if selected.empty:
        return selected

    if prediction_history is not None and not prediction_history.empty and "game_id" in prediction_history:
        grade_cols = [c for c in ("game_id", "actual_home_score", "actual_away_score") if c in prediction_history]
        if len(grade_cols) == 3:
            grades = prediction_history[grade_cols].drop_duplicates("game_id", keep="last")
            selected = selected.drop(columns=["actual_home_score", "actual_away_score"]).merge(
                grades, on="game_id", how="left"
            )
            hs = pd.to_numeric(selected.actual_home_score, errors="coerce")
            aw = pd.to_numeric(selected.actual_away_score, errors="coerce")
            graded = hs.notna() & aw.notna() & hs.ne(aw)
            selected["graded"] = graded
            selected["home_win"] = pd.array(np.where(graded, hs > aw, pd.NA), dtype="boolean")
    return selected.sort_values(["season", "week", "game_id", "minutes_to_kickoff_at_snapshot"], ascending=[True, True, True, False], kind="stable").reset_index(drop=True)


def score_forecast_horizons(selected: pd.DataFrame) -> pd.DataFrame:
    """Report accuracy, calibration and snapshot staleness at every observed horizon."""
    if selected.empty:
        return pd.DataFrame()
    required = {"horizon", "graded", "home_win", "levline_home_prob", "market_home_prob"}
    missing = required - set(selected.columns)
    if missing:
        raise ValueError(f"selected horizons missing fields: {sorted(missing)}")
    rows: list[dict] = []
    for horizon, part in selected.groupby("horizon", sort=False):
        graded = part[part.graded.astype(bool)].copy()
        if graded.empty:
            continue
        for label, column in (
            ("LevLine", "levline_home_prob"),
            ("Market", "market_home_prob"),
            ("Football", "football_home_prob"),
        ):
            usable = graded[pd.to_numeric(graded[column], errors="coerce").notna()].copy()
            if usable.empty:
                continue
            metrics = forecast_metrics(usable, column)
            calibration, _ = calibration_diagnostics(usable, column)
            staleness = pd.to_numeric(usable.staleness_minutes_vs_target, errors="coerce")
            rows.append(
                {
                    "horizon": horizon,
                    "forecast": label,
                    **metrics,
                    **calibration,
                    "median_staleness_minutes": float(staleness.median()) if staleness.notna().any() else np.nan,
                    "p90_staleness_minutes": float(staleness.quantile(0.90)) if staleness.notna().any() else np.nan,
                }
            )
    return pd.DataFrame(rows)


def compare_horizons(
    selected: pd.DataFrame,
    *,
    candidate_horizon: str = "T-25",
    reference_horizon: str = "T-120",
    forecast: str = "levline_home_prob",
    bootstrap_samples: int = 5000,
    seed: int = 26,
) -> pd.DataFrame:
    """Paired week-block comparison of a later horizon against an earlier horizon."""
    if selected.empty:
        return pd.DataFrame()
    data = selected[selected.graded.astype(bool)].copy()
    left = data[data.horizon.eq(candidate_horizon)][["game_id", "season", "week", "home_win", forecast]].rename(columns={forecast: "candidate_prob"})
    right = data[data.horizon.eq(reference_horizon)][["game_id", forecast]].rename(columns={forecast: "reference_prob"})
    paired = left.merge(right, on="game_id", how="inner", validate="one_to_one")
    if paired.empty:
        return pd.DataFrame()
    rows = []
    for metric in ("brier", "log_loss", "accuracy"):
        result = paired_bootstrap(
            paired,
            "candidate_prob",
            "reference_prob",
            metric=metric,
            block_cols=("season", "week"),
            samples=bootstrap_samples,
            seed=seed + len(rows),
        )
        rows.append(asdict(result))
    return pd.DataFrame(rows)

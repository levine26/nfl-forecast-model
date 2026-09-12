from __future__ import annotations

"""Prospective scoring for frozen LevLine 4 horizon forecasts.

This evaluator is descriptive until the preregistered evidence gate is met. It never
fits or changes a candidate. Comparisons are paired on identical games and horizon
comparisons use only the common-game intersection required by the research contract.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from research.levline4_horizon_shadow_v1 import (
    FST_HORIZON_CANDIDATE_ID,
    MARKET_CANDIDATE_ID,
)

MIN_GAMES = 200
MIN_WEEKS = 14
BOOTSTRAP_DRAWS = 10000
BOOTSTRAP_SEED = 20260912
EPS = 1e-6
FINAL_HORIZONS = ("T-60m", "T-45m", "T-30m")


@dataclass(frozen=True)
class ScoredRows:
    frame: pd.DataFrame
    excluded_ungraded: int
    excluded_invalid_probability: int


def _clip_probability(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").clip(EPS, 1.0 - EPS)


def _home_outcome(history: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "actual_home_score", "actual_away_score"}
    if history.empty or not required.issubset(history.columns):
        return pd.DataFrame(
            columns=["game_id", "season", "week", "home_win", "incumbent_home_prob"]
        )

    work = history.copy()
    if "lock_status" in work.columns:
        work = work[work["lock_status"].astype(str).eq("LOCKED")].copy()
    hs = pd.to_numeric(work["actual_home_score"], errors="coerce")
    aw = pd.to_numeric(work["actual_away_score"], errors="coerce")
    graded = hs.notna() & aw.notna()
    work = work.loc[graded].copy()
    hs = hs.loc[graded]
    aw = aw.loc[graded]
    if work.empty:
        return pd.DataFrame(
            columns=["game_id", "season", "week", "home_win", "incumbent_home_prob"]
        )
    if work["game_id"].astype(str).duplicated().any():
        raise ValueError("official graded history contains duplicate game_id rows")

    work["home_win"] = (hs > aw).astype(float).to_numpy()
    if "final_home_prob" in work.columns:
        work["incumbent_home_prob"] = pd.to_numeric(
            work["final_home_prob"], errors="coerce"
        )
    else:
        work["incumbent_home_prob"] = np.nan
    columns = ["game_id", "home_win", "incumbent_home_prob"]
    for optional in ("season", "week"):
        if optional in work.columns:
            columns.append(optional)
    return work[columns].copy()


def score_rows(shadows: pd.DataFrame, history: pd.DataFrame) -> ScoredRows:
    if shadows.empty:
        return ScoredRows(pd.DataFrame(), 0, 0)
    required = {"game_id", "horizon", "candidate_id", "final_home_prob"}
    missing = required - set(shadows.columns)
    if missing:
        raise ValueError(f"shadow ledger missing fields: {sorted(missing)}")
    if shadows.duplicated(["game_id", "horizon", "candidate_id"]).any():
        raise ValueError("shadow ledger contains duplicate forecast identities")

    outcomes = _home_outcome(history)
    merged = shadows.merge(
        outcomes,
        on="game_id",
        how="left",
        suffixes=("", "_official"),
    )
    ungraded = int(merged["home_win"].isna().sum())
    merged = merged[merged["home_win"].notna()].copy()
    if merged.empty:
        return ScoredRows(merged, ungraded, 0)

    merged["prob"] = _clip_probability(merged["final_home_prob"])
    invalid = int(merged["prob"].isna().sum())
    merged = merged[merged["prob"].notna()].copy()
    if merged.empty:
        return ScoredRows(merged, ungraded, invalid)

    y = merged["home_win"].astype(float)
    p = merged["prob"].astype(float)
    merged["brier_loss"] = (p - y) ** 2
    merged["log_loss"] = -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    merged["winner_correct_eval"] = ((p >= 0.5).astype(float) == y).astype(float)
    merged["sharpness"] = (p - 0.5).abs()
    merged["incumbent_prob"] = _clip_probability(merged["incumbent_home_prob"])
    merged["incumbent_brier_loss"] = (merged["incumbent_prob"] - y) ** 2
    return ScoredRows(merged.reset_index(drop=True), ungraded, invalid)


def _metadata_series(frame: pd.DataFrame, name: str) -> pd.Series:
    official_name = f"{name}_official"
    base = (
        pd.to_numeric(frame[name], errors="coerce")
        if name in frame.columns
        else pd.Series(np.nan, index=frame.index, dtype=float)
    )
    if official_name not in frame.columns:
        return base
    official = pd.to_numeric(frame[official_name], errors="coerce")
    return official.where(official.notna(), base)


def _week_key(frame: pd.DataFrame) -> pd.Series:
    season = _metadata_series(frame, "season")
    week = _metadata_series(frame, "week")
    valid = season.notna() & week.notna()
    result = pd.Series("unknown", index=frame.index, dtype=object)
    result.loc[valid] = (
        season.loc[valid].astype(int).astype(str)
        + "-W"
        + week.loc[valid].astype(int).astype(str)
    )
    return result


def _calibration_fit(
    probability: np.ndarray,
    outcome: np.ndarray,
) -> tuple[float | None, float | None]:
    """Two-parameter logistic recalibration via deterministic Newton iterations."""
    if len(probability) < 20 or np.unique(outcome).size < 2:
        return None, None
    p = np.clip(probability.astype(float), EPS, 1.0 - EPS)
    x = np.log(p / (1.0 - p))
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.asarray([0.0, 1.0], dtype=float)
    for _ in range(100):
        eta = np.clip(design @ beta, -35.0, 35.0)
        mu = 1.0 / (1.0 + np.exp(-eta))
        weights = np.clip(mu * (1.0 - mu), 1e-8, None)
        score = design.T @ (outcome - mu)
        information = design.T @ (weights[:, None] * design)
        try:
            step = np.linalg.solve(information, score)
        except np.linalg.LinAlgError:
            return None, None
        next_beta = beta + step
        if not np.isfinite(next_beta).all():
            return None, None
        beta = next_beta
        if float(np.max(np.abs(step))) < 1e-10:
            break
    return float(beta[0]), float(beta[1])


def metric_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "games": 0,
            "weeks": 0,
            "brier": None,
            "log_loss": None,
            "winner_accuracy": None,
            "sharpness": None,
            "calibration_intercept": None,
            "calibration_slope": None,
        }
    p = frame["prob"].to_numpy(dtype=float)
    y = frame["home_win"].to_numpy(dtype=float)
    intercept, slope = _calibration_fit(p, y)
    week_keys = _week_key(frame)
    known_weeks = week_keys[week_keys.ne("unknown")]
    return {
        "games": int(len(frame)),
        "weeks": int(known_weeks.nunique()),
        "brier": float(frame["brier_loss"].mean()),
        "log_loss": float(frame["log_loss"].mean()),
        "winner_accuracy": float(frame["winner_correct_eval"].mean()),
        "sharpness": float(frame["sharpness"].mean()),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }


def _block_bootstrap_mean_delta(
    frame: pd.DataFrame,
    delta_column: str,
    *,
    draws: int | None = None,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if frame.empty:
        return {"mean_delta": None, "ci95_low": None, "ci95_high": None, "draws": 0}
    draws = int(BOOTSTRAP_DRAWS if draws is None else draws)
    work = frame.copy()
    work["week_key"] = _week_key(work)
    work = work[work["week_key"].ne("unknown")].copy()
    observed = float(frame[delta_column].mean())
    if work.empty:
        return {
            "mean_delta": observed,
            "ci95_low": None,
            "ci95_high": None,
            "draws": 0,
            "reason": "missing_week_metadata",
        }
    blocks = [
        group[delta_column].to_numpy(dtype=float)
        for _, group in work.groupby("week_key", sort=True)
    ]
    if len(blocks) < 2:
        return {
            "mean_delta": observed,
            "ci95_low": None,
            "ci95_high": None,
            "draws": 0,
            "reason": "fewer_than_two_week_blocks",
        }
    rng = np.random.default_rng(seed)
    sampled_means = np.empty(draws, dtype=float)
    n_blocks = len(blocks)
    for i in range(draws):
        choices = rng.integers(0, n_blocks, size=n_blocks)
        values = np.concatenate([blocks[int(j)] for j in choices])
        sampled_means[i] = float(values.mean())
    low, high = np.quantile(sampled_means, [0.025, 0.975])
    return {
        "mean_delta": observed,
        "ci95_low": float(low),
        "ci95_high": float(high),
        "draws": draws,
        "week_blocks": int(n_blocks),
        "seed": int(seed),
    }


def _leave_one_week_out(frame: pd.DataFrame, delta_column: str) -> dict[str, Any]:
    if frame.empty:
        return {
            "weeks": 0,
            "deltas": {},
            "all_remaining_negative": None,
            "max_remaining_delta": None,
        }
    work = frame.copy()
    work["week_key"] = _week_key(work)
    work = work[work["week_key"].ne("unknown")].copy()
    keys = sorted(work["week_key"].unique())
    deltas: dict[str, float] = {}
    for key in keys:
        remaining = work[work["week_key"].ne(key)]
        if remaining.empty:
            continue
        deltas[str(key)] = float(remaining[delta_column].mean())
    values = list(deltas.values())
    return {
        "weeks": int(len(keys)),
        "deltas": deltas,
        "all_remaining_negative": bool(all(value < 0 for value in values)) if values else None,
        "max_remaining_delta": float(max(values)) if values else None,
    }


def paired_comparison(
    candidate: pd.DataFrame,
    benchmark: pd.DataFrame,
    *,
    label: str,
) -> dict[str, Any]:
    left_columns = [
        "game_id",
        "horizon",
        "brier_loss",
        "log_loss",
        "prob",
        "home_win",
    ]
    right_columns = ["game_id", "horizon", "brier_loss", "log_loss", "prob"]
    left = candidate[left_columns].copy()
    right = benchmark[right_columns].copy()
    paired = left.merge(
        right,
        on=["game_id", "horizon"],
        suffixes=("_candidate", "_benchmark"),
    )
    if paired.empty:
        return {
            "benchmark": label,
            "games": 0,
            "brier_delta": None,
            "log_loss_delta": None,
        }

    meta_columns = [
        column
        for column in (
            "game_id",
            "season_official",
            "week_official",
            "season",
            "week",
        )
        if column in candidate.columns
    ]
    if len(meta_columns) > 1:
        meta = candidate[meta_columns].drop_duplicates("game_id")
        paired = paired.merge(meta, on="game_id", how="left")
    paired["brier_delta"] = (
        paired["brier_loss_candidate"] - paired["brier_loss_benchmark"]
    )
    paired["log_loss_delta"] = (
        paired["log_loss_candidate"] - paired["log_loss_benchmark"]
    )
    return {
        "benchmark": label,
        "games": int(len(paired)),
        "brier_delta": float(paired["brier_delta"].mean()),
        "log_loss_delta": float(paired["log_loss_delta"].mean()),
        "brier_week_block_bootstrap": _block_bootstrap_mean_delta(
            paired, "brier_delta"
        ),
        "leave_one_week_out_brier": _leave_one_week_out(paired, "brier_delta"),
    }


def incumbent_comparison(candidate: pd.DataFrame) -> dict[str, Any]:
    paired = candidate[candidate["incumbent_prob"].notna()].copy()
    if paired.empty:
        return {"benchmark": "official_T-120_F-ST", "games": 0, "brier_delta": None}
    paired["brier_delta"] = paired["brier_loss"] - paired["incumbent_brier_loss"]
    return {
        "benchmark": "official_T-120_F-ST",
        "games": int(len(paired)),
        "brier_delta": float(paired["brier_delta"].mean()),
        "brier_week_block_bootstrap": _block_bootstrap_mean_delta(
            paired, "brier_delta"
        ),
        "leave_one_week_out_brier": _leave_one_week_out(paired, "brier_delta"),
    }


def _common_horizon_metrics(scored: pd.DataFrame, candidate_id: str) -> dict[str, Any]:
    subset = scored[
        scored["candidate_id"].astype(str).eq(candidate_id)
        & scored["horizon"].astype(str).isin(FINAL_HORIZONS)
    ].copy()
    if subset.empty:
        return {
            "candidate_id": candidate_id,
            "common_games": 0,
            "required_horizons": list(FINAL_HORIZONS),
            "horizons": {},
            "selection_authorized": False,
        }
    presence = subset.groupby("game_id")["horizon"].agg(lambda s: set(map(str, s)))
    eligible_games = presence[
        presence.map(lambda values: set(FINAL_HORIZONS).issubset(values))
    ].index
    common = subset[subset["game_id"].isin(eligible_games)].copy()
    metrics = {
        horizon: metric_summary(common[common["horizon"].astype(str).eq(horizon)])
        for horizon in FINAL_HORIZONS
    }
    return {
        "candidate_id": candidate_id,
        "common_games": int(len(eligible_games)),
        "required_horizons": list(FINAL_HORIZONS),
        "horizons": metrics,
        "selection_authorized": False,
        "note": (
            "Descriptive only; no preferred horizon may be selected before the "
            "prospective evidence gate is satisfied."
        ),
    }


def evaluate(shadows: pd.DataFrame, history: pd.DataFrame) -> dict[str, Any]:
    scored_result = score_rows(shadows, history)
    scored = scored_result.frame
    report: dict[str, Any] = {
        "program": "LEVLINE-4-RESEARCH-V1",
        "evaluation_version": "LEVLINE4-HORIZON-EVAL-V1",
        "primary_metric": "brier",
        "graded_shadow_rows": int(len(scored)),
        "excluded_ungraded_rows": int(scored_result.excluded_ungraded),
        "excluded_invalid_probability_rows": int(
            scored_result.excluded_invalid_probability
        ),
        "minimum_games": MIN_GAMES,
        "minimum_weeks": MIN_WEEKS,
        "automatic_promotion": False,
        "horizon_selection_authorized": False,
        "promotion_authorized": False,
        "production_authorized": False,
        "candidate_horizon_metrics": {},
        "paired_model_vs_same_horizon_market": {},
        "candidate_vs_incumbent": {},
        "common_game_horizon_comparison": {},
    }
    if scored.empty:
        report["gate_status"] = "WAITING_FOR_GRADED_SHADOWS"
        return report

    for (candidate_id, horizon), group in scored.groupby(
        ["candidate_id", "horizon"], sort=True
    ):
        key = f"{candidate_id}__{horizon}"
        metrics = metric_summary(group)
        metrics["gate_sample_ready"] = bool(
            metrics["games"] >= MIN_GAMES and metrics["weeks"] >= MIN_WEEKS
        )
        report["candidate_horizon_metrics"][key] = metrics
        report["candidate_vs_incumbent"][key] = incumbent_comparison(group)

    for horizon in sorted(set(scored["horizon"].astype(str))):
        candidate = scored[
            scored["candidate_id"].astype(str).eq(FST_HORIZON_CANDIDATE_ID)
            & scored["horizon"].astype(str).eq(horizon)
        ]
        market = scored[
            scored["candidate_id"].astype(str).eq(MARKET_CANDIDATE_ID)
            & scored["horizon"].astype(str).eq(horizon)
        ]
        if not candidate.empty and not market.empty:
            report["paired_model_vs_same_horizon_market"][horizon] = paired_comparison(
                candidate,
                market,
                label=MARKET_CANDIDATE_ID,
            )

    for candidate_id in (MARKET_CANDIDATE_ID, FST_HORIZON_CANDIDATE_ID):
        report["common_game_horizon_comparison"][candidate_id] = (
            _common_horizon_metrics(scored, candidate_id)
        )

    eligible = [
        metrics
        for metrics in report["candidate_horizon_metrics"].values()
        if metrics.get("gate_sample_ready")
    ]
    report["gate_status"] = (
        "SAMPLE_GATE_REACHED_EVALUATION_ONLY"
        if eligible
        else "ACCUMULATING_PROSPECTIVE_EVIDENCE"
    )
    return report

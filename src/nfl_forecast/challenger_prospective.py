from __future__ import annotations

"""Pre-registered prospective evaluation for frozen F-ST-01 shadow locks."""

import numpy as np
import pandas as pd

from .challenger_evaluation import calibration_diagnostics, forecast_metrics, paired_bootstrap
from .challenger_fst import FROZEN_CANDIDATE_ID
from .challenger_shadow import normalize_history

MIN_GAMES = 200
MIN_WEEKS = 14
MARKET_BRIER_NONINFERIORITY_MARGIN = 0.0025
BOOTSTRAP_SEED = 26
BOOTSTRAP_SAMPLES = 10000


def _prepare(history: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    # Existing v0.8 shadow ledgers predate the frozen F-ST columns. Normalize them
    # before enforcing the new evaluator schema so a legitimate pre-first-FST-lock
    # ledger returns awaiting_graded_games instead of failing CI. This normalization
    # adds schema only; it never invents an F-ST candidate or backfills a forecast.
    history = normalize_history(history)
    required = {
        "challenger_version", "candidate_freeze_utc", "production_lock_timestamp_utc",
        "season", "week", "actual_home_score", "actual_away_score",
        "challenger_final_home_prob", "production_final_home_prob", "market_home_prob_t120",
        "challenger_pure_home_prob",
    }
    missing = required - set(history.columns)
    if missing:
        raise ValueError(f"F-ST evaluation history missing fields: {sorted(missing)}")
    work = history[history.challenger_version.astype(str).eq(FROZEN_CANDIDATE_ID)].copy()
    if work.empty:
        return work, 0
    lock_time = pd.to_datetime(work.production_lock_timestamp_utc, utc=True, errors="coerce")
    freeze_time = pd.to_datetime(work.candidate_freeze_utc, utc=True, errors="coerce")
    if lock_time.isna().any() or freeze_time.isna().any():
        raise ValueError("F-ST evaluation requires parseable freeze and lock timestamps")
    prefreeze = lock_time < freeze_time
    excluded = int(prefreeze.sum())
    work = work.loc[~prefreeze].copy()
    numeric = [
        "actual_home_score", "actual_away_score", "challenger_final_home_prob",
        "production_final_home_prob", "market_home_prob_t120", "challenger_pure_home_prob",
    ]
    for column in numeric:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=numeric).copy()
    if not work.empty:
        work["home_win"] = (work.actual_home_score > work.actual_away_score).astype(int)
    return work, excluded


def _weekly(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (season, week), part in frame.groupby(["season", "week"], sort=True):
        fst = forecast_metrics(part, "challenger_final_home_prob")
        production = forecast_metrics(part, "production_final_home_prob")
        market = forecast_metrics(part, "market_home_prob_t120")
        pure = forecast_metrics(part, "challenger_pure_home_prob")
        rows.append({
            "season": int(season), "week": int(week), "games": int(len(part)),
            "fst_brier": fst["brier"], "production_brier": production["brier"],
            "market_brier": market["brier"], "pure_brier": pure["brier"],
            "fst_minus_production_brier": fst["brier"] - production["brier"],
            "fst_minus_market_brier": fst["brier"] - market["brier"],
        })
    return pd.DataFrame(rows)


def _loo_coherent(frame: pd.DataFrame) -> bool:
    keys = frame.season.astype(str) + "-W" + frame.week.astype(str)
    unique = sorted(keys.unique())
    if len(unique) < 2:
        return False
    for key in unique:
        part = frame.loc[~keys.eq(key)]
        fst = forecast_metrics(part, "challenger_final_home_prob")["brier"]
        production = forecast_metrics(part, "production_final_home_prob")["brier"]
        if fst - production >= 0.0:
            return False
    return True


def _slice(frame: pd.DataFrame, mask: np.ndarray) -> dict:
    part = frame.loc[mask]
    if part.empty:
        return {"games": 0}
    return forecast_metrics(part, "challenger_final_home_prob")


def evaluate_frozen_fst(
    history: pd.DataFrame,
    *,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> tuple[dict, pd.DataFrame]:
    """Score frozen post-freeze locks; outcomes are evaluation-only and never tune F-ST."""
    work, excluded_prefreeze = _prepare(history)
    if work.empty:
        return ({
            "candidate_id": FROZEN_CANDIDATE_ID,
            "status": "awaiting_graded_games",
            "games": 0,
            "weeks": 0,
            "excluded_prefreeze_rows": excluded_prefreeze,
            "promotion_gate_passed": False,
            "promotion_authorized": False,
            "2026_outcomes_used_for_model_tuning": 0,
        }, pd.DataFrame())

    metrics = {}
    calibration = {}
    for label, column in {
        "fst": "challenger_final_home_prob",
        "production": "production_final_home_prob",
        "market": "market_home_prob_t120",
        "pure": "challenger_pure_home_prob",
    }.items():
        metrics[label] = forecast_metrics(work, column)
        calibration[label], _ = calibration_diagnostics(work, column)

    prod_boot = paired_bootstrap(
        work, "challenger_final_home_prob", "production_final_home_prob",
        metric="brier", block_cols=("season", "week"), samples=bootstrap_samples,
        seed=bootstrap_seed,
    )
    market_boot = paired_bootstrap(
        work, "challenger_final_home_prob", "market_home_prob_t120",
        metric="brier", block_cols=("season", "week"), samples=bootstrap_samples,
        seed=bootstrap_seed + 1,
    )
    weekly = _weekly(work)
    games, weeks = int(len(work)), int(len(weekly))
    minimum_evidence = games >= MIN_GAMES and weeks >= MIN_WEEKS
    fst_minus_production = metrics["fst"]["brier"] - metrics["production"]["brier"]
    fst_minus_market = metrics["fst"]["brier"] - metrics["market"]["brier"]
    median_weekly_delta = float(weekly.fst_minus_production_brier.median())
    loo = _loo_coherent(work)
    gate_a = fst_minus_production < 0.0 and prod_boot.ci_upper < 0.0
    gate_b = market_boot.ci_upper <= MARKET_BRIER_NONINFERIORITY_MARGIN
    gate_c = median_weekly_delta < 0.0 and loo
    passed = bool(minimum_evidence and gate_a and gate_b and gate_c)

    fst = work.challenger_final_home_prob.to_numpy(dtype=float)
    market = work.market_home_prob_t120.to_numpy(dtype=float)
    production = work.production_final_home_prob.to_numpy(dtype=float)
    report = {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "status": "evaluation_ready" if minimum_evidence else "accumulating_prospective_evidence",
        "primary_metric": "brier",
        "games": games,
        "weeks": weeks,
        "excluded_prefreeze_rows": excluded_prefreeze,
        "metrics": metrics,
        "calibration": calibration,
        "paired": {
            "fst_minus_production_brier": fst_minus_production,
            "fst_minus_market_brier": fst_minus_market,
            "production_week_block_bootstrap": prod_boot.__dict__,
            "market_week_block_bootstrap": market_boot.__dict__,
        },
        "diagnostic_slices": {
            "fst_market_pick_disagreement": _slice(work, (fst >= 0.5) != (market >= 0.5)),
            "fst_production_pick_disagreement": _slice(work, (fst >= 0.5) != (production >= 0.5)),
            "fst_high_confidence": _slice(work, np.abs(fst - 0.5) >= 0.20),
            "mean_abs_probability_disagreement_vs_market": float(np.mean(np.abs(fst - market))),
            "mean_abs_probability_disagreement_vs_production": float(np.mean(np.abs(fst - production))),
        },
        "promotion_gate": {
            "minimum_games": MIN_GAMES,
            "minimum_weeks": MIN_WEEKS,
            "minimum_evidence_met": bool(minimum_evidence),
            "A_vs_production_pass": bool(gate_a),
            "B_market_noninferiority_margin": MARKET_BRIER_NONINFERIORITY_MARGIN,
            "B_vs_market_pass": bool(gate_b),
            "C_median_weekly_delta": median_weekly_delta,
            "C_leave_one_week_out_all_negative": bool(loo),
            "C_week_coherence_pass": bool(gate_c),
        },
        "promotion_gate_passed": passed,
        "promotion_authorized": False,
        "secondary_metrics_can_rescue_primary_failure": False,
        "2026_outcomes_used_for_model_tuning": 0,
    }
    return report, weekly

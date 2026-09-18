from __future__ import annotations

"""Evaluate the preregistered Props 2.0 market-prior residual challenger.

Historical 2023-2025 outputs are research-development evidence only. This script
never promotes a model or chooses a selective betting threshold.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_market_residual import (  # noqa: E402
    RESEARCH_LABEL,
    apply_market_prior_residual,
    fit_market_prior_residual,
    grade_directional_rows,
)

CONTRACT_VERSION = "levline-props-v2-market-prior-development-v0.1.0"
BOOTSTRAP_SEED = 20260918
DEFAULT_BOOTSTRAP_REPLICATES = 5000


def _fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _binary_log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(np.asarray(p, float), 1e-8, 1.0 - 1e-8)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.square(np.asarray(p, float) - np.asarray(y, float))))


def _cluster_bootstrap(
    frame: pd.DataFrame,
    *,
    challenger_col: str,
    baseline_col: str,
    replicates: int,
    seed: int,
) -> dict:
    work = frame[["game_id", challenger_col, baseline_col]].dropna().copy()
    games = np.asarray(sorted(work["game_id"].astype(str).unique()))
    if len(games) < 2:
        return {"challenger_accuracy_ci95": None, "paired_difference_ci95": None}
    grouped = {g: work[work["game_id"].astype(str).eq(g)] for g in games}
    rng = np.random.default_rng(seed)
    challenger_acc = np.empty(replicates)
    paired_diff = np.empty(replicates)
    for i in range(replicates):
        sampled = rng.choice(games, size=len(games), replace=True)
        rows = pd.concat([grouped[g] for g in sampled], ignore_index=True)
        challenger_acc[i] = float(rows[challenger_col].mean())
        paired_diff[i] = float((rows[challenger_col] - rows[baseline_col]).mean())
    return {
        "challenger_accuracy_ci95": [
            float(np.quantile(challenger_acc, 0.025)),
            float(np.quantile(challenger_acc, 0.975)),
        ],
        "paired_difference_ci95": [
            float(np.quantile(paired_diff, 0.025)),
            float(np.quantile(paired_diff, 0.975)),
        ],
    }


def _evaluate(scored: pd.DataFrame, *, replicates: int, seed: int) -> dict:
    decided = scored[
        scored["market_outcome_recomputed"].ne("PUSH")
        & scored["model_side"].isin(["OVER", "UNDER"])
    ].copy()
    if decided.empty:
        raise ValueError("evaluation sample has no paired decided rows")

    y_over = decided["market_outcome_recomputed"].eq("OVER").astype(float).to_numpy()
    v1 = decided["v1_correct"].astype(float)
    market = decided["market_price_correct"].astype(float)
    challenger = decided["challenger_correct"].astype(float)

    result = {
        "rows": int(len(decided)),
        "unique_games": int(decided["game_id"].astype(str).nunique()),
        "unique_players": int(decided["player_id"].astype(str).nunique()),
        "v1_accuracy": float(v1.mean()),
        "market_price_direction_accuracy": float(market.mean()),
        "challenger_accuracy": float(challenger.mean()),
        "challenger_minus_v1_accuracy": float((challenger - v1).mean()),
        "challenger_minus_market_accuracy": float((challenger - market).mean()),
        "market_brier": _brier(y_over, decided["market_no_vig_p_over"].to_numpy(float)),
        "challenger_brier": _brier(y_over, decided["challenger_p_over"].to_numpy(float)),
        "v1_brier": _brier(y_over, decided["p_over"].to_numpy(float)),
        "market_log_loss": _binary_log_loss(
            y_over, decided["market_no_vig_p_over"].to_numpy(float)
        ),
        "challenger_log_loss": _binary_log_loss(
            y_over, decided["challenger_p_over"].to_numpy(float)
        ),
        "v1_log_loss": _binary_log_loss(y_over, decided["p_over"].to_numpy(float)),
        "challenger_over_call_rate": float(decided["challenger_side"].eq("OVER").mean()),
        "market_over_call_rate": float(decided["market_price_side"].eq("OVER").mean()),
    }
    result["clustered_vs_v1"] = _cluster_bootstrap(
        decided,
        challenger_col="challenger_correct",
        baseline_col="v1_correct",
        replicates=replicates,
        seed=seed,
    )
    result["clustered_vs_market"] = _cluster_bootstrap(
        decided,
        challenger_col="challenger_correct",
        baseline_col="market_price_correct",
        replicates=replicates,
        seed=seed + 1,
    )

    by_prop = {}
    for prop, group in decided.groupby("prop_type", sort=True):
        by_prop[str(prop)] = {
            "rows": int(len(group)),
            "v1_accuracy": float(group["v1_correct"].mean()),
            "market_accuracy": float(group["market_price_correct"].mean()),
            "challenger_accuracy": float(group["challenger_correct"].mean()),
        }
    result["by_prop_type"] = by_prop
    return result


def _score(frame: pd.DataFrame, model) -> pd.DataFrame:
    return grade_directional_rows(apply_market_prior_residual(frame, model))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=DEFAULT_BOOTSTRAP_REPLICATES)
    args = parser.parse_args()
    if args.bootstrap_replicates <= 0:
        raise ValueError("--bootstrap-replicates must be positive")

    frames = [pd.read_csv(path) for path in args.input]
    data = pd.concat(frames, ignore_index=True)
    required = {
        "season", "week", "game_id", "player_id", "prop_type", "market_line",
        "over_odds", "under_odds", "p_over", "model_side", "actual_result",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"input forecast ledger missing fields: {sorted(missing)}")

    data["season"] = pd.to_numeric(data["season"], errors="raise").astype(int)
    data["week"] = pd.to_numeric(data["week"], errors="raise").astype(int)

    # Fixed-anchor stability test: fit once on 2023 Weeks 1-9 and never refit.
    fixed_train = data[(data["season"].eq(2023)) & (data["week"].le(9))].copy()
    fixed_eval = data[
        ((data["season"].eq(2023)) & (data["week"].ge(10)))
        | data["season"].isin([2024, 2025])
    ].copy()
    fixed_model = fit_market_prior_residual(fixed_train)
    fixed_scored = _score(fixed_eval, fixed_model)
    fixed_summary = _evaluate(
        fixed_scored, replicates=args.bootstrap_replicates, seed=BOOTSTRAP_SEED
    )

    # Rolling-origin annual retraining. Each evaluated season can use only earlier seasons.
    rolling_parts = []
    rolling_models = {}
    for season in (2024, 2025):
        train = data[data["season"].lt(season) & data["season"].ge(2023)].copy()
        evaluate = data[data["season"].eq(season)].copy()
        if train.empty or evaluate.empty:
            continue
        model = fit_market_prior_residual(train)
        rolling_models[str(season)] = model.to_dict()
        scored = _score(evaluate, model)
        scored["rolling_evaluation_season"] = season
        rolling_parts.append(scored)
    if not rolling_parts:
        raise ValueError("no rolling-origin evaluation seasons were available")
    rolling_scored = pd.concat(rolling_parts, ignore_index=True)
    rolling_summary = _evaluate(
        rolling_scored, replicates=args.bootstrap_replicates, seed=BOOTSTRAP_SEED + 20
    )
    rolling_by_season = {}
    for season, group in rolling_scored.groupby("rolling_evaluation_season", sort=True):
        rolling_by_season[str(int(season))] = _evaluate(
            group, replicates=args.bootstrap_replicates, seed=BOOTSTRAP_SEED + int(season)
        )
    rolling_summary["by_evaluation_season"] = rolling_by_season

    summary = {
        "contract_version": CONTRACT_VERSION,
        "research_label": RESEARCH_LABEL,
        "promotion_authorized": False,
        "historical_2023_2025_is_pristine_promotion_holdout": False,
        "selective_betting_threshold_used": False,
        "input_provenance": [_fingerprint(path) for path in args.input],
        "fixed_anchor": {
            "training_rule": "2023 Weeks 1-9 only; model fixed thereafter",
            "model": fixed_model.to_dict(),
            "evaluation": fixed_summary,
        },
        "rolling_origin": {
            "training_rule": "for each target season, use seasons >=2023 and strictly earlier",
            "models": rolling_models,
            "evaluation": rolling_summary,
        },
        "interpretation": (
            "Retrospective challenger-development evidence only. Positive results cannot promote "
            "Props 2.0 because 2023-2025 baseline outcomes informed the research program."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fixed_scored.to_csv(args.output_dir / "fixed_anchor_rows.csv", index=False)
    rolling_scored.to_csv(args.output_dir / "rolling_origin_rows.csv", index=False)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

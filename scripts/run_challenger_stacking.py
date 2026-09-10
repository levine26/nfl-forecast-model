from __future__ import annotations

"""Run the single pre-registered F-ST-01 market + v0.8 chronological logit stack."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
import sklearn

from nfl_forecast.challenger import blend_probabilities, score_probabilities
from nfl_forecast.challenger_evaluation import compare_forecasts, confidence_set_approximation
from nfl_forecast.challenger_v07 import (
    build_opponent_adjusted_matchup_features,
    opponent_adjusted_feature_columns,
)
from nfl_forecast.challenger_v08 import build_qb_matchup_features, qb_feature_columns
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import (
    add_game_results,
    aggregate_team_games,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.stacking_research import (
    STACK_C,
    TARGET_SEASONS,
    build_chronological_logit_stack,
)
from run_challenger_v08 import build_nested_research, nested_linear_hybrid

HISTORICAL_END = 2025
CANDIDATE_VERSION = "F-ST-01-market-v08-logit-stack"
BOOTSTRAP_SAMPLES = 2000


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def _metric_row(label: str, target: pd.Series, probability) -> dict:
    return {"candidate": label, **score_probabilities(target, probability)}


def _historical_frame(config_path: str):
    """Build only 2012-2025 history; F-ST-01 never loads 2026."""
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(
        bundle.pbp,
        cfg["data"]["neutral_wp_lower"],
        cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, bundle.schedules)
    base_games = build_matchup_features(team_games, bundle.schedules, elo)
    opponent_games = build_opponent_adjusted_matchup_features(team_games, bundle.schedules, base_games)
    games = build_qb_matchup_features(bundle.pbp, bundle.schedules, opponent_games)
    games = add_vig_free_market_prob(games)

    season = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season.le(HISTORICAL_END)].copy()
    if historical.empty or pd.to_numeric(historical["season"], errors="coerce").gt(2025).any():
        raise RuntimeError("F-ST-01 historical horizon was violated")

    opponent = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    core = core_columns(historical)
    blocked = set(opponent) | set(qb)
    production = [column for column in core if column not in blocked]
    v08 = sorted(set(production + opponent + qb))
    if not production or len(opponent) != 32 or not qb:
        raise RuntimeError("F-ST-01 v0.8 feature construction is incomplete")
    return cfg, historical, sorted(production), v08


def _write_comparison(out: Path, label: str, result: dict[str, object]) -> dict[str, object]:
    bootstrap = result["bootstrap"]
    paired_tests = result["paired_tests"]
    slices = result["slices"]
    calibration_bins = result["calibration_bins"]
    assert isinstance(bootstrap, pd.DataFrame)
    assert isinstance(paired_tests, pd.DataFrame)
    assert isinstance(slices, pd.DataFrame)
    assert isinstance(calibration_bins, pd.DataFrame)
    bootstrap.to_csv(out / f"{label}_bootstrap.csv", index=False)
    paired_tests.to_csv(out / f"{label}_paired_tests.csv", index=False)
    slices.to_csv(out / f"{label}_slices.csv", index=False)
    calibration_bins.to_csv(out / f"{label}_calibration_bins.csv", index=False)
    key = bootstrap[
        bootstrap["block"].isin(["season+week", "season"])
        & bootstrap["metric"].isin(["accuracy", "brier", "log_loss"])
    ]
    return {
        "candidate": result["candidate"],
        "reference": result["reference"],
        "metric_deltas": result["metric_deltas"],
        "candidate_calibration": result["candidate_calibration"],
        "block_bootstrap": json.loads(key.to_json(orient="records")),
        "paired_tests": json.loads(paired_tests.to_json(orient="records")),
    }


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "challenger_outputs/f_st_01",
) -> dict[str, object]:
    cfg, historical, production_features, v08_features = _historical_frame(config_path)
    seed = int(cfg["model"]["random_state"])

    _, production = build_nested_research(historical, production_features, seed)
    _, v08 = build_nested_research(historical, v08_features, seed)
    v08_adaptive = nested_linear_hybrid(v08, objective="brier")
    stack = build_chronological_logit_stack(v08)

    production_target = production[production["season"].isin(TARGET_SEASONS)]
    v08_target = v08[v08["season"].isin(TARGET_SEASONS)]
    stack_target = stack.predictions[stack.predictions["season"].isin(TARGET_SEASONS)]
    common = production_target.index.intersection(v08_target.index)
    common = common.intersection(v08_adaptive.predictions.index)
    common = common.intersection(stack_target.index)
    if len(common) < 1000:
        raise RuntimeError(f"F-ST-01 paired target sample unexpectedly small: {len(common)}")

    paired = historical.loc[common, ["game_id", "season", "week", "home_win"]].copy()
    paired["market"] = pd.to_numeric(v08_target.loc[common, "market_prob"], errors="coerce")
    paired["production_75_25"] = blend_probabilities(
        production_target.loc[common, "pure_prob"],
        production_target.loc[common, "market_prob"],
        0.75,
    )
    paired["v08_pure"] = pd.to_numeric(v08_target.loc[common, "pure_prob"], errors="coerce")
    paired["v08_adaptive_brier"] = pd.to_numeric(
        v08_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )
    paired["stack"] = pd.to_numeric(stack_target.loc[common, "stack_probability"], errors="coerce")

    candidates = ["market", "production_75_25", "v08_pure", "v08_adaptive_brier", "stack"]
    if paired[candidates].isna().any().any():
        bad = paired[candidates].isna().sum()
        raise RuntimeError(f"F-ST-01 paired predictions contain missing values: {bad[bad.gt(0)].to_dict()}")

    overall = pd.DataFrame([_metric_row(column, paired.home_win, paired[column]) for column in candidates])
    season_rows: list[dict] = []
    for season in TARGET_SEASONS:
        piece = paired[paired.season.eq(season)]
        for column in candidates:
            season_rows.append({"season": int(season), **_metric_row(column, piece.home_win, piece[column])})
    season_metrics = pd.DataFrame(season_rows)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comparisons = {
        "stack_vs_market": _write_comparison(
            out,
            "stack_vs_market",
            compare_forecasts(
                paired,
                "stack",
                "market",
                bootstrap_samples=BOOTSTRAP_SAMPLES,
                seed=seed,
            ),
        ),
        "stack_vs_v08_adaptive": _write_comparison(
            out,
            "stack_vs_v08_adaptive",
            compare_forecasts(
                paired,
                "stack",
                "v08_adaptive_brier",
                bootstrap_samples=BOOTSTRAP_SAMPLES,
                seed=seed,
            ),
        ),
    }
    confidence_set = confidence_set_approximation(
        paired,
        ["market", "v08_adaptive_brier", "stack"],
        primary_metric="brier",
        block_cols=("season", "week"),
        bootstrap_samples=BOOTSTRAP_SAMPLES,
        seed=seed,
    )

    metrics = overall.set_index("candidate")
    increments = {
        "stack_over_market": {
            "winner_pp": float(100.0 * (metrics.loc["stack", "winner_pct"] - metrics.loc["market", "winner_pct"])),
            "brier_delta": float(metrics.loc["stack", "brier"] - metrics.loc["market", "brier"]),
            "log_loss_delta": float(metrics.loc["stack", "log_loss"] - metrics.loc["market", "log_loss"]),
        },
        "stack_over_v08_adaptive": {
            "winner_pp": float(100.0 * (metrics.loc["stack", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["stack", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["stack", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
    }

    report: dict[str, object] = {
        "status": "healthy",
        "mode": "research_only",
        "experiment_id": "F-ST-01",
        "candidate_version": CANDIDATE_VERSION,
        "architecture": "logistic regression on exactly [logit(market), logit(v0.8 PURE)]",
        "stack_C": STACK_C,
        "hyperparameter_search_performed": False,
        "paired_target_games": int(len(paired)),
        "target_seasons": list(TARGET_SEASONS),
        "2026_data_loaded": False,
        "2026_outcomes_used": 0,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "increments": increments,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "coefficients": json.loads(stack.coefficients.to_json(orient="records")),
        "comparisons": comparisons,
        "brier_confidence_set": json.loads(confidence_set.to_json(orient="records")),
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "v08_feature_hash": _feature_hash(v08_features),
            "production_feature_hash": _feature_hash(production_features),
            "package_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__,
            },
        },
    }

    paired.to_csv(out / "paired_predictions_2022_2025.csv", index=False)
    overall.to_csv(out / "overall_metrics.csv", index=False)
    season_metrics.to_csv(out / "season_metrics.csv", index=False)
    stack.coefficients.to_csv(out / "stack_coefficients.csv", index=False)
    confidence_set.to_csv(out / "brier_confidence_set.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== F-ST-01 CHRONOLOGICAL LOGIT STACK: 2022-25 OOS ===")
    print(overall.to_string(index=False))
    print("\nStack coefficients by target season:")
    print(stack.coefficients.to_string(index=False))
    print("\nIncremental deltas (negative Brier/log-loss delta is better):")
    print(json.dumps(increments, indent=2))
    print("\nBrier confidence-set approximation:")
    print(confidence_set.to_string(index=False))
    print("2026 data loaded: 0")
    print("2026 outcomes used: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs/f_st_01")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()

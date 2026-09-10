from __future__ import annotations

"""Run pre-registered V09D-EWMA-INTERACTIONS-002 without loading 2026 data."""

import argparse
from datetime import datetime, timezone
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
from nfl_forecast.challenger_v09d import (
    add_predeclared_matchup_interactions,
    matchup_interaction_columns,
)
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
from run_challenger_v08 import build_nested_research, nested_linear_hybrid

HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)
EXPERIMENT_ID = "V09D-EWMA-INTERACTIONS-002"
CANDIDATE_VERSION = "0.9D-fixed-ewma-matchup-interactions"
BOOTSTRAP_SAMPLES = 2000


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _metric_row(label: str, target: pd.Series, probability) -> dict:
    return {"candidate": label, **score_probabilities(target, probability)}


def _historical_frame(config_path: str):
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
    qb_games = build_qb_matchup_features(bundle.pbp, bundle.schedules, opponent_games)
    games = add_predeclared_matchup_interactions(qb_games)
    games = add_vig_free_market_prob(games)

    season = pd.to_numeric(games["season"], errors="coerce")
    historical = games[games["home_win"].notna() & season.le(HISTORICAL_END)].copy()
    if historical.empty or pd.to_numeric(historical["season"], errors="coerce").gt(2025).any():
        raise RuntimeError("v0.9D historical horizon violated")

    opponent = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    interactions = matchup_interaction_columns(historical)
    all_core = core_columns(historical)
    blocked = set(opponent) | set(qb) | set(interactions)
    production = sorted(column for column in all_core if column not in blocked)
    v08 = sorted(set(production + opponent + qb))
    v09d = sorted(set(v08 + interactions))
    if not production or len(opponent) != 32 or not qb or len(interactions) != 4:
        raise RuntimeError("v0.9D feature construction incomplete")
    return cfg, historical, production, v08, v09d, interactions


def _comparison_summary(result: dict[str, object]) -> dict[str, object]:
    bootstrap = result["bootstrap"]
    paired_tests = result["paired_tests"]
    assert isinstance(bootstrap, pd.DataFrame)
    assert isinstance(paired_tests, pd.DataFrame)
    key = bootstrap[
        bootstrap["block"].isin(["season+week", "season"])
        & bootstrap["metric"].isin(["accuracy", "brier", "log_loss"])
    ]
    return {
        "candidate": result["candidate"],
        "reference": result["reference"],
        "metric_deltas": result["metric_deltas"],
        "block_bootstrap": json.loads(key.to_json(orient="records")),
        "paired_tests": json.loads(paired_tests.to_json(orient="records")),
        "candidate_calibration": result["candidate_calibration"],
    }


def _write_comparison(out: Path, label: str, result: dict[str, object]) -> dict[str, object]:
    for key, suffix in [
        ("bootstrap", "bootstrap"),
        ("paired_tests", "paired_tests"),
        ("slices", "slices"),
        ("calibration_bins", "calibration_bins"),
    ]:
        frame = result[key]
        assert isinstance(frame, pd.DataFrame)
        frame.to_csv(out / f"{label}_{suffix}.csv", index=False)
    return _comparison_summary(result)


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs/v09d") -> dict:
    cfg, historical, production_features, v08_features, v09d_features, interactions = _historical_frame(
        config_path
    )
    seed = int(cfg["model"]["random_state"])

    _, production = build_nested_research(historical, production_features, seed)
    _, v08 = build_nested_research(historical, v08_features, seed)
    _, v09d = build_nested_research(historical, v09d_features, seed)
    v08_adaptive = nested_linear_hybrid(v08, objective="brier")
    v09d_adaptive = nested_linear_hybrid(v09d, objective="brier")

    production_target = production[production.season.isin(TARGET_SEASONS)]
    v08_target = v08[v08.season.isin(TARGET_SEASONS)]
    v09d_target = v09d[v09d.season.isin(TARGET_SEASONS)]
    common = production_target.index.intersection(v08_target.index).intersection(v09d_target.index)
    common = common.intersection(v08_adaptive.predictions.index).intersection(v09d_adaptive.predictions.index)
    if len(common) < 1000:
        raise RuntimeError(f"v0.9D paired target sample unexpectedly small: {len(common)}")

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
    paired["v09d_pure"] = pd.to_numeric(v09d_target.loc[common, "pure_prob"], errors="coerce")
    paired["v09d_adaptive_brier"] = pd.to_numeric(
        v09d_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )
    candidate_columns = [
        "market",
        "production_75_25",
        "v08_pure",
        "v08_adaptive_brier",
        "v09d_pure",
        "v09d_adaptive_brier",
    ]
    if paired[candidate_columns].isna().any().any():
        bad = paired[candidate_columns].isna().sum()
        raise RuntimeError(f"v0.9D paired predictions missing: {bad[bad.gt(0)].to_dict()}")

    overall = pd.DataFrame(
        [_metric_row(column, paired.home_win, paired[column]) for column in candidate_columns]
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    comparisons = {
        "adaptive_vs_v08": _write_comparison(
            out,
            "adaptive_vs_v08",
            compare_forecasts(
                paired,
                "v09d_adaptive_brier",
                "v08_adaptive_brier",
                bootstrap_samples=BOOTSTRAP_SAMPLES,
                seed=seed,
            ),
        ),
        "adaptive_vs_market": _write_comparison(
            out,
            "adaptive_vs_market",
            compare_forecasts(
                paired,
                "v09d_adaptive_brier",
                "market",
                bootstrap_samples=BOOTSTRAP_SAMPLES,
                seed=seed,
            ),
        ),
        "pure_vs_v08_pure": _write_comparison(
            out,
            "pure_vs_v08_pure",
            compare_forecasts(
                paired,
                "v09d_pure",
                "v08_pure",
                bootstrap_samples=BOOTSTRAP_SAMPLES,
                seed=seed,
            ),
        ),
    }
    confidence_set = confidence_set_approximation(
        paired,
        ["market", "v08_adaptive_brier", "v09d_adaptive_brier"],
        primary_metric="brier",
        block_cols=("season", "week"),
        bootstrap_samples=BOOTSTRAP_SAMPLES,
        seed=seed,
    )

    metrics = overall.set_index("candidate")
    increments = {
        "adaptive_over_v08": {
            "winner_pp": float(100 * (metrics.loc["v09d_adaptive_brier", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09d_adaptive_brier", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["v09d_adaptive_brier", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
        "pure_over_v08_pure": {
            "winner_pp": float(100 * (metrics.loc["v09d_pure", "winner_pct"] - metrics.loc["v08_pure", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09d_pure", "brier"] - metrics.loc["v08_pure", "brier"]),
            "log_loss_delta": float(metrics.loc["v09d_pure", "log_loss"] - metrics.loc["v08_pure", "log_loss"]),
        },
    }

    report = {
        "status": "healthy",
        "mode": "research_only",
        "experiment_id": EXPERIMENT_ID,
        "candidate_version": CANDIDATE_VERSION,
        "interaction_features": interactions,
        "interaction_count": len(interactions),
        "feature_subset_search_performed": False,
        "hyperparameter_search_performed": False,
        "paired_target_games": int(len(paired)),
        "target_seasons": list(TARGET_SEASONS),
        "2026_data_loaded": False,
        "2026_outcomes_used": 0,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "increments": increments,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "comparisons": comparisons,
        "brier_confidence_set": json.loads(confidence_set.to_json(orient="records")),
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
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
    confidence_set.to_csv(out / "brier_confidence_set.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== V09D-EWMA-INTERACTIONS-002 FIXED INTERACTIONS: 2022-25 OOS ===")
    print(overall.to_string(index=False))
    print("\nIncremental deltas (negative Brier/log-loss is better):")
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
    parser.add_argument("--output-dir", default="challenger_outputs/v09d")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()

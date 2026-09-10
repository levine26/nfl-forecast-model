from __future__ import annotations

"""Run paired uncertainty diagnostics on the existing v0.8 historical candidates.

This is diagnostic research only. It does not select a new production model, does not use
2026 outcomes, and writes only to research_outputs/.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import blend_probabilities
from nfl_forecast.challenger_evaluation import compare_forecasts, confidence_set_approximation
from nfl_forecast.challenger_v06 import nested_logit_hybrid_backtest
from nfl_forecast.experiment_registry import reproducibility_metadata
from scripts.run_challenger_v08 import (
    TARGET_SEASONS,
    build_nested_research,
    build_research_frame,
    nested_linear_hybrid,
)


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.replace({np.nan: None}).to_json(orient="records"))


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "research_outputs/statistical_validation",
    bootstrap_samples: int = 2000,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg, historical, _, feature_sets, _, _ = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])

    _, base = build_nested_research(historical, feature_sets["production_compatible"], seed)
    _, combined = build_nested_research(historical, feature_sets["opponent_adjusted_qb"], seed)
    base = base[base.season.isin(TARGET_SEASONS)].copy()
    combined = combined[combined.season.isin(TARGET_SEASONS)].copy()
    common = base.index.intersection(combined.index)
    if len(common) < 1000:
        raise RuntimeError(f"Expected the paired 2022-25 sample; found only {len(common)} games")

    frame = historical.loc[common, [
        "game_id",
        "season",
        "week",
        "home_win",
        "market_home_prob",
        "home_qb_starter_changed",
        "away_qb_starter_changed",
    ]].copy()
    frame["market_prob"] = pd.to_numeric(base.loc[common, "market_prob"], errors="coerce")
    frame["production_75_25"] = blend_probabilities(
        base.loc[common, "pure_prob"], frame.market_prob, 0.75
    )

    combined_linear = nested_linear_hybrid(combined, objective="brier").predictions
    combined_logit = nested_logit_hybrid_backtest(
        combined,
        objective="brier",
        calibrator="none",
    ).predictions
    frame["v08_combined_adaptive_brier"] = pd.to_numeric(
        combined_linear.loc[common, "probability"], errors="coerce"
    )
    frame["v08_combined_logit_brier"] = pd.to_numeric(
        combined_logit.loc[common, "probability"], errors="coerce"
    )

    required = [
        "market_prob",
        "production_75_25",
        "v08_combined_adaptive_brier",
        "v08_combined_logit_brier",
    ]
    if frame[required].isna().any().any():
        raise RuntimeError("Paired uncertainty frame contains missing candidate probabilities")

    vs_production = compare_forecasts(
        frame,
        "v08_combined_adaptive_brier",
        "production_75_25",
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    vs_market = compare_forecasts(
        frame,
        "v08_combined_adaptive_brier",
        "market_prob",
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    confidence_set = confidence_set_approximation(
        frame,
        required,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )

    frame.to_csv(out / "v08_paired_predictions_2022_2025.csv", index=False)
    vs_production["bootstrap"].to_csv(out / "v08_vs_production_bootstrap.csv", index=False)
    vs_production["paired_tests"].to_csv(out / "v08_vs_production_paired_tests.csv", index=False)
    vs_production["slices"].to_csv(out / "v08_vs_production_slices.csv", index=False)
    vs_production["calibration_bins"].to_csv(out / "v08_candidate_calibration_bins.csv", index=False)
    vs_market["bootstrap"].to_csv(out / "v08_vs_market_bootstrap.csv", index=False)
    vs_market["paired_tests"].to_csv(out / "v08_vs_market_paired_tests.csv", index=False)
    vs_market["slices"].to_csv(out / "v08_vs_market_slices.csv", index=False)
    confidence_set.to_csv(out / "v08_model_confidence_set.csv", index=False)

    metadata = reproducibility_metadata(
        candidate_version="0.8-qb-starter-statistical-audit",
        features=feature_sets["opponent_adjusted_qb"],
        data_seasons=range(2012, 2026),
        max_pbp_season=2025,
        random_seed=seed,
        games=len(frame),
        player_observations=0,
        play_observations=0,
        exclusions={"2026_outcomes": 0},
        missing_data_rates={column: float(frame[column].isna().mean()) for column in required},
    )
    report = {
        "status": "healthy",
        "mode": "research_only",
        "historical_selection_seasons": list(TARGET_SEASONS),
        "2026_outcomes_used": 0,
        "promotion_authorized": False,
        "candidate": "Opponent-adjusted + QB-aware Hybrid adaptive Brier",
        "reference_production_like": "Nested 75% PURE / 25% MARKET",
        "reference_market": "Market only benchmark",
        "vs_production": {
            "candidate": vs_production["candidate"],
            "reference": vs_production["reference"],
            "metric_deltas": vs_production["metric_deltas"],
            "candidate_calibration": vs_production["candidate_calibration"],
            "bootstrap": _records(vs_production["bootstrap"]),
            "paired_tests": _records(vs_production["paired_tests"]),
        },
        "vs_market": {
            "candidate": vs_market["candidate"],
            "reference": vs_market["reference"],
            "metric_deltas": vs_market["metric_deltas"],
            "bootstrap": _records(vs_market["bootstrap"]),
            "paired_tests": _records(vs_market["paired_tests"]),
        },
        "confidence_set_approximation": _records(confidence_set),
        "reproducibility": metadata,
    }
    (out / "v08_uncertainty_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="research_outputs/statistical_validation")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()
    run(args.config, args.output_dir, args.bootstrap_samples)


if __name__ == "__main__":
    main()

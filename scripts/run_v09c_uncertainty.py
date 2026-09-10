from __future__ import annotations

"""Paired uncertainty audit for the already-executed v0.9C1 unit-continuity ablation.

This script does not fit, tune, or alter the candidate. It consumes the fixed paired
2022-2025 predictions emitted by ``run_challenger_v09c.py`` and applies the shared
research-only statistical evaluator.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_evaluation import (
    compare_forecasts,
    confidence_set_approximation,
)

BOOTSTRAP_SAMPLES = 2000
SEED = 26

COMPARISONS = (
    ("adaptive_vs_v08_adaptive", "v09c_unit_adaptive_brier", "v08_adaptive_brier"),
    ("adaptive_vs_market", "v09c_unit_adaptive_brier", "market"),
    ("pure_vs_v08_pure", "v09c_unit_pure", "v08_pure"),
)


def _comparison_summary(result: dict[str, object]) -> dict[str, object]:
    bootstrap = result["bootstrap"]
    paired_tests = result["paired_tests"]
    assert isinstance(bootstrap, pd.DataFrame)
    assert isinstance(paired_tests, pd.DataFrame)
    key_bootstrap = bootstrap[
        bootstrap["block"].isin(["season+week", "season"])
        & bootstrap["metric"].isin(["brier", "log_loss", "accuracy"])
    ].copy()
    return {
        "candidate": result["candidate"],
        "reference": result["reference"],
        "metric_deltas": result["metric_deltas"],
        "candidate_calibration": result["candidate_calibration"],
        "block_bootstrap": json.loads(key_bootstrap.to_json(orient="records")),
        "paired_tests": json.loads(paired_tests.to_json(orient="records")),
    }


def run(
    paired_path: str = "challenger_outputs/v09c/paired_predictions_2022_2025.csv",
    output_dir: str = "challenger_outputs/v09c/uncertainty",
) -> dict[str, object]:
    paired = pd.read_csv(paired_path)
    required = {
        "home_win",
        "season",
        "week",
        "market",
        "v08_pure",
        "v08_adaptive_brier",
        "v09c_unit_pure",
        "v09c_unit_adaptive_brier",
    }
    missing = required - set(paired.columns)
    if missing:
        raise ValueError(f"v0.9C1 paired file missing uncertainty fields: {sorted(missing)}")
    if len(paired) < 1000:
        raise RuntimeError(f"v0.9C1 uncertainty sample unexpectedly small: {len(paired)}")
    if pd.to_numeric(paired["season"], errors="coerce").gt(2025).any():
        raise RuntimeError("v0.9C1 uncertainty audit may not use outcomes after 2025")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, object] = {}

    for label, candidate, reference in COMPARISONS:
        result = compare_forecasts(
            paired,
            candidate,
            reference,
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        )
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
        summaries[label] = _comparison_summary(result)

    confidence_set = confidence_set_approximation(
        paired,
        ["market", "v08_adaptive_brier", "v09c_unit_adaptive_brier"],
        target_col="home_win",
        primary_metric="brier",
        block_cols=("season", "week"),
        bootstrap_samples=BOOTSTRAP_SAMPLES,
        seed=SEED,
    )
    confidence_set.to_csv(out / "brier_confidence_set.csv", index=False)

    report: dict[str, object] = {
        "status": "healthy",
        "mode": "research_only",
        "candidate_version": "0.9C-unit-continuity",
        "paired_games": int(len(paired)),
        "target_seasons": sorted(int(s) for s in paired["season"].unique()),
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "seed": SEED,
        "2026_outcomes_used": 0,
        "candidate_refit_or_tuning_performed": False,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "comparisons": summaries,
        "brier_confidence_set": json.loads(confidence_set.to_json(orient="records")),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== v0.9C1 PAIRED UNCERTAINTY AUDIT ===")
    for label, summary in summaries.items():
        print(label)
        print(json.dumps(summary["metric_deltas"], indent=2))
    print("\nBrier confidence-set approximation:")
    print(confidence_set.to_string(index=False))
    print("2026 outcomes used: 0")
    print("candidate refit/tuning performed: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paired",
        default="challenger_outputs/v09c/paired_predictions_2022_2025.csv",
    )
    parser.add_argument("--output-dir", default="challenger_outputs/v09c/uncertainty")
    args = parser.parse_args()
    run(args.paired, args.output_dir)


if __name__ == "__main__":
    main()

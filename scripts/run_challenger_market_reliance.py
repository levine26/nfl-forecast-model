from __future__ import annotations

"""Run Phase 2 LevLine market-reliance research without touching production outputs."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_evaluation import calibration_diagnostics, forecast_metrics
from nfl_forecast.challenger_market_reliance import (
    DEFAULT_MARKET_WEIGHTS,
    TARGET_SEASONS,
    compare_candidate_to_market,
    compare_horizons,
    disagreement_buckets,
    linear_pool,
    logit_pool,
    prepare_frozen_historical_frame,
    score_forecast_horizons,
    select_forecast_horizons,
    walk_forward_weight_backtest,
)
from nfl_forecast.fst_nested_pure import load_frozen_training_frame


def _json_records(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    return json.loads(frame.replace({np.nan: None}).to_json(orient="records"))


def _fixed_grid(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = prepare_frozen_historical_frame(frame)
    target = target[target.season.isin(TARGET_SEASONS)].copy()
    rows: list[dict] = []
    predictions = target[["game_id", "season", "week", "home_win", "pure_prob", "market_prob"]].copy()
    for pooling, pool in (("linear", linear_pool), ("logit", logit_pool)):
        for market_weight in DEFAULT_MARKET_WEIGHTS:
            name = f"{pooling}_market_{int(round(100 * market_weight))}"
            predictions[name] = pool(target.pure_prob, target.market_prob, market_weight)
            metrics = forecast_metrics(predictions, name)
            calibration, _ = calibration_diagnostics(predictions, name)
            rows.append(
                {
                    "candidate": name,
                    "pooling": pooling,
                    "market_weight": float(market_weight),
                    "pure_weight": float(1.0 - market_weight),
                    **metrics,
                    **calibration,
                }
            )
    return predictions, pd.DataFrame(rows).sort_values(["brier", "log_loss", "candidate"])


def run(output_dir: str, bootstrap_samples: int = 2000) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    frozen = load_frozen_training_frame()
    historical = prepare_frozen_historical_frame(frozen)
    if historical.season.max() >= 2026:
        raise RuntimeError("Phase 2 historical study loaded 2026 outcomes")

    fixed_predictions, fixed_metrics = _fixed_grid(historical)
    fixed_predictions.to_csv(out / "fixed_candidate_predictions_2022_2025.csv", index=False)
    fixed_metrics.to_csv(out / "fixed_candidate_metrics.csv", index=False)

    wf_predictions: dict[str, pd.DataFrame] = {}
    wf_selections: list[pd.DataFrame] = []
    wf_metrics: list[dict] = []
    uncertainty: list[pd.DataFrame] = []
    bucket_tables: list[pd.DataFrame] = []
    for pooling in ("linear", "logit"):
        pred, selections = walk_forward_weight_backtest(historical, pooling=pooling)
        pred.to_csv(out / f"walk_forward_{pooling}_predictions.csv", index=False)
        selections.to_csv(out / f"walk_forward_{pooling}_selections.csv", index=False)
        wf_predictions[pooling] = pred
        wf_selections.append(selections)
        metrics = forecast_metrics(pred, "probability")
        calibration, _ = calibration_diagnostics(pred, "probability")
        wf_metrics.append({"candidate": f"walk_forward_{pooling}", **metrics, **calibration})
        comparison = compare_candidate_to_market(
            historical,
            pred.probability,
            bootstrap_samples=bootstrap_samples,
            seed=26 if pooling == "linear" else 126,
        )
        comparison.insert(0, "candidate", f"walk_forward_{pooling}")
        uncertainty.append(comparison)
        bucket_input = pred.rename(columns={"probability": "candidate_prob"})
        buckets = disagreement_buckets(
            bucket_input,
            ["pure_prob", "market_prob", "candidate_prob"],
        )
        buckets.insert(0, "candidate", f"walk_forward_{pooling}")
        bucket_tables.append(buckets)

    pd.concat(wf_selections, ignore_index=True).to_csv(out / "walk_forward_weight_selections.csv", index=False)
    pd.DataFrame(wf_metrics).sort_values("brier").to_csv(out / "walk_forward_metrics.csv", index=False)
    pd.concat(uncertainty, ignore_index=True).to_csv(out / "walk_forward_vs_market_uncertainty.csv", index=False)
    pd.concat(bucket_tables, ignore_index=True).to_csv(out / "disagreement_buckets.csv", index=False)

    run_history_path = Path("outputs/run_history.csv")
    lock_history_path = Path("outputs/prediction_history.csv")
    horizon_selected = pd.DataFrame()
    horizon_metrics = pd.DataFrame()
    t25_vs_t120 = pd.DataFrame()
    if run_history_path.exists():
        run_history = pd.read_csv(run_history_path)
        locks = pd.read_csv(lock_history_path) if lock_history_path.exists() else None
        horizon_selected = select_forecast_horizons(run_history, locks)
        horizon_selected.to_csv(out / "prospective_forecast_horizons.csv", index=False)
        horizon_metrics = score_forecast_horizons(horizon_selected)
        horizon_metrics.to_csv(out / "prospective_horizon_metrics.csv", index=False)
        if not horizon_selected.empty and {"T-25", "T-120"}.issubset(set(horizon_selected.horizon.astype(str))):
            t25_vs_t120 = compare_horizons(
                horizon_selected,
                candidate_horizon="T-25",
                reference_horizon="T-120",
                bootstrap_samples=bootstrap_samples,
            )
            t25_vs_t120.to_csv(out / "t25_vs_t120_uncertainty.csv", index=False)

    report = {
        "status": "research_only",
        "phase": 2,
        "production_changed": False,
        "promotion_authorized": False,
        "2026_outcomes_used_for_historical_model_selection": 0,
        "historical_market_timing_caveat": (
            "Frozen historical market probabilities are a closing-market benchmark, not a matched T-minus horizon."
        ),
        "historical_games": int(len(historical)),
        "target_seasons": list(TARGET_SEASONS),
        "fixed_candidates": _json_records(fixed_metrics),
        "walk_forward_candidates": wf_metrics,
        "walk_forward_weight_selections": _json_records(pd.concat(wf_selections, ignore_index=True)),
        "forecast_horizon_research": {
            "tracked_horizons_minutes": [120, 90, 60, 45, 30, 25, 15],
            "preserve_preweek_pick": True,
            "prospective_rows": int(len(horizon_selected)),
            "graded_horizon_rows": int(horizon_selected.graded.fillna(False).astype(bool).sum()) if not horizon_selected.empty and "graded" in horizon_selected else 0,
            "metrics": _json_records(horizon_metrics),
            "t25_vs_t120": _json_records(t25_vs_t120),
            "lock_policy_changed": False,
        },
        "decision_rule": (
            "Do not change F-ST or the official lock horizon from 120 minutes unless chronology-preserving historical evidence and prospective matched-horizon evidence show a material, uncertainty-supported accuracy improvement without unacceptable missing/stale data risk."
        ),
    }
    (out / "phase2_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/phase2_market_reliance")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()
    run(args.output_dir, args.bootstrap_samples)


if __name__ == "__main__":
    main()

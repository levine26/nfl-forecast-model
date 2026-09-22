from __future__ import annotations

"""Descriptive diagnosis of the frozen Props 2.1 Week 2 miss.

No parameter fitting, threshold search, calibration transform, or model mutation occurs
here. The script consumes forecast_level.csv from the preregistered evaluator and emits
grouped descriptive evidence only.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

GROUPINGS = (
    "prop_type",
    "position",
    "role_state",
    "availability_state",
    "workload_state",
    "market_liquidity_bucket",
    "forecast_horizon_bin",
)

REQUIRED = {
    "forecast_id",
    "graded",
    "actual_result",
    "model_mean",
    "market_line",
    "model_p_over",
    "market_p_over",
    *GROUPINGS,
}


def prepare_matched(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        raise ValueError(f"forecast-level input missing required columns: {missing}")

    projection = frame[
        frame["graded"].eq(True)
        & frame["actual_result"].notna()
        & frame["model_mean"].notna()
        & frame["market_line"].notna()
        & frame["model_p_over"].notna()
        & frame["market_p_over"].notna()
    ].copy()
    if projection.empty:
        raise ValueError("no graded like-for-like market-matched forecasts")

    projection["model_abs_error"] = (
        projection["actual_result"].astype(float) - projection["model_mean"].astype(float)
    ).abs()
    projection["market_abs_error"] = (
        projection["actual_result"].astype(float) - projection["market_line"].astype(float)
    ).abs()
    projection["mae_delta"] = projection["model_abs_error"] - projection["market_abs_error"]
    projection["push"] = projection["actual_result"].astype(float).eq(
        projection["market_line"].astype(float)
    )

    probability = projection[~projection["push"]].copy()
    if probability.empty:
        raise ValueError("all matched observations are pushes")

    probability["actual_over"] = (
        probability["actual_result"].astype(float)
        > probability["market_line"].astype(float)
    ).astype(float)
    for prefix in ("model", "market"):
        p = probability[f"{prefix}_p_over"].astype(float).clip(1e-12, 1 - 1e-12)
        y = probability["actual_over"]
        probability[f"{prefix}_brier"] = (p - y) ** 2
        probability[f"{prefix}_log_loss"] = -(
            y * np.log(p) + (1.0 - y) * np.log(1.0 - p)
        )
        probability[f"{prefix}_confidence"] = np.maximum(p, 1.0 - p)
        selected_over = p >= 0.5
        probability[f"{prefix}_correct"] = (
            selected_over.eq(y.eq(1.0))
        ).astype(float)

    probability["brier_delta"] = (
        probability["model_brier"] - probability["market_brier"]
    )
    probability["log_loss_delta"] = (
        probability["model_log_loss"] - probability["market_log_loss"]
    )
    return projection, probability


def summarize_group(
    projection: pd.DataFrame,
    probability: pd.DataFrame,
    grouping: str,
    *,
    min_n: int = 10,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    values = sorted(
        set(projection[grouping].dropna().astype(str))
        | set(probability[grouping].dropna().astype(str))
    )
    for value in values:
        p1 = projection[projection[grouping].astype(str).eq(value)]
        p2 = probability[probability[grouping].astype(str).eq(value)]
        if len(p1) < min_n and len(p2) < min_n:
            continue

        row: dict[str, Any] = {
            "grouping": grouping,
            "group": value,
            "projection_n": int(len(p1)),
            "probability_n": int(len(p2)),
        }
        if len(p1) >= min_n:
            row.update(
                {
                    "model_mae": float(p1["model_abs_error"].mean()),
                    "market_mae": float(p1["market_abs_error"].mean()),
                    "mae_delta": float(p1["mae_delta"].mean()),
                }
            )
        if len(p2) >= min_n:
            model_conf = float(p2["model_confidence"].mean())
            model_acc = float(p2["model_correct"].mean())
            market_conf = float(p2["market_confidence"].mean())
            market_acc = float(p2["market_correct"].mean())
            row.update(
                {
                    "model_brier": float(p2["model_brier"].mean()),
                    "market_brier": float(p2["market_brier"].mean()),
                    "brier_delta": float(p2["brier_delta"].mean()),
                    "model_log_loss": float(p2["model_log_loss"].mean()),
                    "market_log_loss": float(p2["market_log_loss"].mean()),
                    "log_loss_delta": float(p2["log_loss_delta"].mean()),
                    "model_direction_confidence": model_conf,
                    "model_direction_accuracy": model_acc,
                    "model_confidence_gap": model_conf - model_acc,
                    "market_direction_confidence": market_conf,
                    "market_direction_accuracy": market_acc,
                    "market_confidence_gap": market_conf - market_acc,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def run(input_csv: Path, output_dir: Path, *, min_n: int = 10) -> dict[str, Any]:
    frame = pd.read_csv(input_csv)
    projection, probability = prepare_matched(frame)

    tables = [
        summarize_group(projection, probability, grouping, min_n=min_n)
        for grouping in GROUPINGS
    ]
    diagnostics = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()

    overall_model_conf = float(probability["model_confidence"].mean())
    overall_model_acc = float(probability["model_correct"].mean())
    overall_market_conf = float(probability["market_confidence"].mean())
    overall_market_acc = float(probability["market_correct"].mean())
    summary = {
        "contract": "props21-week2-error-diagnostics-v1",
        "diagnostic_only": True,
        "parameter_fitting_authorized": False,
        "automatic_promotion_authorized": False,
        "projection_n": int(len(projection)),
        "probability_n": int(len(probability)),
        "overall": {
            "model_mae": float(projection["model_abs_error"].mean()),
            "market_mae": float(projection["market_abs_error"].mean()),
            "mae_delta": float(projection["mae_delta"].mean()),
            "model_brier": float(probability["model_brier"].mean()),
            "market_brier": float(probability["market_brier"].mean()),
            "brier_delta": float(probability["brier_delta"].mean()),
            "model_log_loss": float(probability["model_log_loss"].mean()),
            "market_log_loss": float(probability["market_log_loss"].mean()),
            "log_loss_delta": float(probability["log_loss_delta"].mean()),
            "model_direction_confidence": overall_model_conf,
            "model_direction_accuracy": overall_model_acc,
            "model_confidence_gap": overall_model_conf - overall_model_acc,
            "market_direction_confidence": overall_market_conf,
            "market_direction_accuracy": overall_market_acc,
            "market_confidence_gap": overall_market_conf - overall_market_acc,
        },
        "groupings": list(GROUPINGS),
        "min_group_n": int(min_n),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics.to_csv(output_dir / "group_diagnostics.csv", index=False)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast-level", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-n", type=int, default=10)
    args = parser.parse_args()
    if args.min_n < 1:
        raise ValueError("--min-n must be positive")
    summary = run(args.forecast_level, args.output_dir, min_n=args.min_n)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

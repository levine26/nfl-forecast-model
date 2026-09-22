from __future__ import annotations

"""Paired scientific evaluation for LevLine adaptive weekly challengers.

Primary metric is straight-up accuracy.  Probability metrics and calibration remain
mandatory guardrails.  Week-block bootstrap is reused from the established challenger
framework, while exact McNemar and disagreement accounting make winner changes explicit.
"""

import argparse
import json
from math import comb
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_evaluation import compare_forecasts


def exact_mcnemar_two_sided(candidate_only: int, reference_only: int) -> float | None:
    n = int(candidate_only) + int(reference_only)
    if n == 0:
        return None
    k = min(int(candidate_only), int(reference_only))
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def switch_accounting(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    target_col: str = "home_win",
) -> dict:
    required = {candidate_col, reference_col, target_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"switch accounting missing fields: {sorted(missing)}")

    candidate = pd.to_numeric(frame[candidate_col], errors="raise")
    reference = pd.to_numeric(frame[reference_col], errors="raise")
    y = pd.to_numeric(frame[target_col], errors="raise").astype(int)
    candidate_side = candidate.ge(0.5).astype(int)
    reference_side = reference.ge(0.5).astype(int)
    candidate_correct = candidate_side.eq(y)
    reference_correct = reference_side.eq(y)
    disagreement = candidate_side.ne(reference_side)

    candidate_only = int((disagreement & candidate_correct & ~reference_correct).sum())
    reference_only = int((disagreement & reference_correct & ~candidate_correct).sum())
    switches = int(disagreement.sum())

    return {
        "games": int(len(frame)),
        "candidate_correct": int(candidate_correct.sum()),
        "reference_correct": int(reference_correct.sum()),
        "candidate_accuracy": float(candidate_correct.mean()),
        "reference_accuracy": float(reference_correct.mean()),
        "accuracy_delta_pp": float(100.0 * (candidate_correct.mean() - reference_correct.mean())),
        "disagreements": switches,
        "disagreement_rate": float(disagreement.mean()),
        "candidate_only_correct": candidate_only,
        "reference_only_correct": reference_only,
        "switch_win_rate": float(candidate_only / switches) if switches else None,
        "net_correct_from_switches": int(candidate_only - reference_only),
        "mcnemar_exact_two_sided_p": exact_mcnemar_two_sided(candidate_only, reference_only),
    }


def season_stability(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    target_col: str = "home_win",
) -> list[dict]:
    if "season" not in frame.columns:
        return []
    rows = []
    for season, part in frame.groupby("season", sort=True):
        row = switch_accounting(part, candidate_col, reference_col, target_col=target_col)
        row["season"] = int(season)
        rows.append(row)
    return rows


def evaluate(
    frame: pd.DataFrame,
    candidate_col: str,
    reference_col: str,
    *,
    target_col: str = "home_win",
    bootstrap_samples: int = 10000,
) -> tuple[dict, dict]:
    paired = compare_forecasts(
        frame,
        candidate_col,
        reference_col,
        target_col=target_col,
        bootstrap_samples=bootstrap_samples,
    )
    switch = switch_accounting(frame, candidate_col, reference_col, target_col=target_col)
    report = {
        "evaluation_id": "LEVLINE-ADAPTIVE-WEEKLY-EVALUATION-V1",
        "primary_metric": "straight_up_winner_accuracy",
        "switch_accounting": switch,
        "metric_deltas": paired["metric_deltas"],
        "candidate": paired["candidate"],
        "reference": paired["reference"],
        "candidate_calibration": paired["candidate_calibration"],
        "season_stability": season_stability(
            frame,
            candidate_col,
            reference_col,
            target_col=target_col,
        ),
        "governance": {
            "paired_games_required": True,
            "week_block_uncertainty_required": True,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }
    tables = {
        "bootstrap": paired["bootstrap"],
        "paired_tests": paired["paired_tests"],
        "slices": paired["slices"],
        "calibration_bins": paired["calibration_bins"],
    }
    return report, tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--candidate-col", required=True)
    parser.add_argument("--reference-col", required=True)
    parser.add_argument("--target-col", default="home_win")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--output-dir", default="research_outputs/adaptive_weekly_evaluation_v1")
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    report, tables = evaluate(
        frame,
        args.candidate_col,
        args.reference_col,
        target_col=args.target_col,
        bootstrap_samples=args.bootstrap_samples,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evaluation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, table in tables.items():
        table.to_csv(out / f"{name}.csv", index=False)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()

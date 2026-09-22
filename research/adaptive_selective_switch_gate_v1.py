from __future__ import annotations

"""Selective winner-switch gate for LevLine adaptive challengers.

This module never invents an adaptive probability.  It consumes an incumbent F-ST
probability and a separately generated adaptive probability, then allows a winner
change only near the incumbent decision boundary and only after a material adaptive
shift.  Thresholds are predeclared here and must not be rescued after target results.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EPS = 1e-6
CANDIDATE_ID = "ADAPTIVE-SELECTIVE-SWITCH-GATE-V1"
INCUMBENT_BOUNDARY = 0.075
MIN_ADAPTIVE_SHIFT = 0.035


def apply_selective_gate(
    frame: pd.DataFrame,
    *,
    incumbent_col: str = "fst_prob",
    adaptive_col: str = "adaptive_prob",
    boundary: float = INCUMBENT_BOUNDARY,
    min_shift: float = MIN_ADAPTIVE_SHIFT,
) -> pd.DataFrame:
    required = {incumbent_col, adaptive_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"selective gate missing fields: {sorted(missing)}")
    if not (0.0 < boundary < 0.5):
        raise ValueError("boundary must be in (0, .5)")
    if not (0.0 < min_shift < 0.5):
        raise ValueError("min_shift must be in (0, .5)")

    out = frame.copy()
    incumbent = pd.to_numeric(out[incumbent_col], errors="raise").clip(EPS, 1.0 - EPS)
    adaptive = pd.to_numeric(out[adaptive_col], errors="raise").clip(EPS, 1.0 - EPS)
    opposite_side = incumbent.ge(0.5).ne(adaptive.ge(0.5))
    near_boundary = (incumbent - 0.5).abs().le(boundary)
    material_shift = (adaptive - incumbent).abs().ge(min_shift)
    eligible = opposite_side & near_boundary & material_shift

    out["gate_opposite_side"] = opposite_side
    out["gate_near_boundary"] = near_boundary
    out["gate_material_shift"] = material_shift
    out["gate_eligible"] = eligible
    out["gate_prob"] = incumbent.where(~eligible, adaptive)
    out["gate_reason"] = np.select(
        [
            eligible,
            ~opposite_side,
            opposite_side & ~near_boundary,
            opposite_side & near_boundary & ~material_shift,
        ],
        [
            "adaptive_switch_authorized",
            "same_winner_side",
            "incumbent_too_far_from_boundary",
            "adaptive_shift_too_small",
        ],
        default="ineligible",
    )
    return out


def evaluate_gate(
    frame: pd.DataFrame,
    *,
    incumbent_col: str = "fst_prob",
    gated_col: str = "gate_prob",
    outcome_col: str = "home_win",
) -> dict:
    required = {incumbent_col, gated_col, outcome_col, "gate_eligible"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"gate evaluation missing fields: {sorted(missing)}")

    y = pd.to_numeric(frame[outcome_col], errors="raise").astype(int)
    incumbent = pd.to_numeric(frame[incumbent_col], errors="raise")
    gated = pd.to_numeric(frame[gated_col], errors="raise")
    inc_correct = incumbent.ge(0.5).astype(int).eq(y)
    gate_correct = gated.ge(0.5).astype(int).eq(y)
    switched = frame["gate_eligible"].astype(bool)
    adaptive_only = int((switched & gate_correct & ~inc_correct).sum())
    incumbent_only = int((switched & inc_correct & ~gate_correct).sum())
    n_switch = int(switched.sum())

    return {
        "candidate_id": CANDIDATE_ID,
        "thresholds": {
            "incumbent_boundary_probability_distance": INCUMBENT_BOUNDARY,
            "minimum_adaptive_probability_shift": MIN_ADAPTIVE_SHIFT,
        },
        "games": int(len(frame)),
        "incumbent_correct": int(inc_correct.sum()),
        "candidate_correct": int(gate_correct.sum()),
        "incumbent_accuracy": float(inc_correct.mean()),
        "candidate_accuracy": float(gate_correct.mean()),
        "accuracy_delta_pp": float(100.0 * (gate_correct.mean() - inc_correct.mean())),
        "authorized_switches": n_switch,
        "candidate_only_correct": adaptive_only,
        "incumbent_only_correct": incumbent_only,
        "switch_win_rate": float(adaptive_only / n_switch) if n_switch else None,
        "production_changed": False,
        "promotion_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV containing F-ST and adaptive probabilities")
    parser.add_argument("--output-dir", default="research_outputs/adaptive_selective_switch_gate_v1")
    parser.add_argument("--incumbent-col", default="fst_prob")
    parser.add_argument("--adaptive-col", default="adaptive_prob")
    parser.add_argument("--outcome-col", default="home_win")
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    gated = apply_selective_gate(
        frame,
        incumbent_col=args.incumbent_col,
        adaptive_col=args.adaptive_col,
    )
    report = evaluate_gate(
        gated,
        incumbent_col=args.incumbent_col,
        outcome_col=args.outcome_col,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    gated.to_csv(out / "scored_games.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

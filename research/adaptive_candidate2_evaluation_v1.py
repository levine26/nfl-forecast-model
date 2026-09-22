from __future__ import annotations

"""Paired evaluation for ADAPTIVE-REGIME-SHOCK-GATE-V1.

All comparisons use the exact Candidate 2 paired sample. The primary estimand is
straight-up winner accuracy versus frozen F-ST. Probability metrics are mandatory
secondary diagnostics. This module never fits or retunes Candidate 2.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.adaptive_weekly_evaluation_v1 import evaluate as paired_evaluate

EPS = 1e-6
CANDIDATE_ID = "ADAPTIVE-REGIME-SHOCK-GATE-V1"

COMPARATORS = {
    "frozen_fst": "fst_prob",
    "market": "market_prob",
    "candidate1_residual_state": "candidate1_prob",
    "weekly_refit_control": "weekly_refit_prob",
    "component_resolved": "component_only_prob",
    "boundary_component_no_shock": "boundary_component_prob",
    "candidate2_regime_shock": "candidate_prob",
}


def _log_loss(p: pd.Series, y: pd.Series) -> float:
    prob = np.clip(pd.to_numeric(p, errors="raise").to_numpy(float), EPS, 1.0 - EPS)
    target = pd.to_numeric(y, errors="raise").to_numpy(float)
    return float(np.mean(-(target * np.log(prob) + (1 - target) * np.log(1 - prob))))


def _score(frame: pd.DataFrame, probability_col: str) -> dict:
    y = pd.to_numeric(frame["home_win"], errors="raise").astype(int)
    p = pd.to_numeric(frame[probability_col], errors="raise")
    pick = p.ge(0.5).astype(int)
    correct = pick.eq(y)
    return {
        "games": int(len(frame)),
        "correct": int(correct.sum()),
        "accuracy": float(correct.mean()),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": _log_loss(p, y),
    }


def _week_table(frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for week, part in frame.groupby("week", sort=True):
        fst = _score(part, "fst_prob")
        candidate = _score(part, "candidate_prob")
        switches = part["candidate_switch"].fillna(False).astype(bool)
        y = part["home_win"].astype(int)
        c_ok = part["candidate_prob"].ge(0.5).astype(int).eq(y)
        f_ok = part["fst_prob"].ge(0.5).astype(int).eq(y)
        rows.append({
            "week": int(week),
            "games": int(len(part)),
            "fst_correct": fst["correct"],
            "candidate_correct": candidate["correct"],
            "net_correct": int(candidate["correct"] - fst["correct"]),
            "switches": int(switches.sum()),
            "candidate_only_correct": int((switches & c_ok & ~f_ok).sum()),
            "fst_only_correct": int((switches & f_ok & ~c_ok).sum()),
        })
    return rows


def _shock_attribution(frame: pd.DataFrame) -> list[dict]:
    switched = frame[frame["candidate_switch"].fillna(False).astype(bool)].copy()
    if switched.empty:
        return []
    y = switched["home_win"].astype(int)
    switched["candidate_correct"] = switched["candidate_prob"].ge(0.5).astype(int).eq(y)
    switched["fst_correct"] = switched["fst_prob"].ge(0.5).astype(int).eq(y)
    rows = []
    for reason, part in switched.groupby("shock_reason", sort=True):
        candidate_only = int((part["candidate_correct"] & ~part["fst_correct"]).sum())
        fst_only = int((part["fst_correct"] & ~part["candidate_correct"]).sum())
        rows.append({
            "shock_reason": str(reason),
            "switches": int(len(part)),
            "candidate_only_correct": candidate_only,
            "fst_only_correct": fst_only,
            "net_correct": int(candidate_only - fst_only),
            "switch_win_rate": float(candidate_only / len(part)) if len(part) else None,
        })
    return rows


def _coverage(frame: pd.DataFrame) -> dict:
    return {
        "paired_games": int(len(frame)),
        "seasons": sorted(pd.to_numeric(frame["season"], errors="raise").astype(int).unique().tolist()),
        "weeks": int(frame[["season", "week"]].drop_duplicates().shape[0]),
        "strong_shock_games": int(frame["strong_regime_shock"].fillna(False).astype(bool).sum()),
        "boundary_games": int(frame["boundary_eligible"].fillna(False).astype(bool).sum()),
        "component_disagreement_games": int(frame["component_disagrees"].fillna(False).astype(bool).sum()),
        "candidate2_switches": int(frame["candidate_switch"].fillna(False).astype(bool).sum()),
        "qualified_qb_practice_join_games": int(
            (
                frame["home_qb_practice_qualified"].fillna(False).astype(bool)
                | frame["away_qb_practice_qualified"].fillna(False).astype(bool)
            ).sum()
        ),
    }


def run(
    input_path: str,
    output_dir: str = "research_outputs/adaptive_candidate2_v1/evaluation",
) -> dict:
    frame = pd.read_csv(input_path)
    required = {
        "game_id", "season", "week", "home_win", "fst_prob", "market_prob",
        "candidate1_prob", "weekly_refit_prob", "component_only_prob",
        "boundary_component_prob", "candidate_prob", "candidate_switch",
        "strong_regime_shock", "boundary_eligible", "component_disagrees",
        "shock_reason", "home_qb_practice_qualified", "away_qb_practice_qualified",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Candidate 2 evaluation missing fields: {sorted(missing)}")
    if sorted(frame["season"].astype(int).unique().tolist()) != [2025]:
        raise RuntimeError("Candidate 2 V1 evaluation must remain on the preregistered 2025 target sample")
    if frame["game_id"].astype(str).duplicated().any():
        raise ValueError("Candidate 2 evaluation contains duplicate game IDs")
    if frame[list(COMPARATORS.values())].isna().any().any():
        raise RuntimeError("Candidate 2 exact paired comparator sample is incomplete")

    scoreboard = {name: _score(frame, col) for name, col in COMPARATORS.items()}
    fst = scoreboard["frozen_fst"]
    candidate = scoreboard["candidate2_regime_shock"]

    paired_report, paired_tables = paired_evaluate(
        frame,
        "candidate_prob",
        "fst_prob",
        target_col="home_win",
        bootstrap_samples=10000,
    )

    controls_vs_fst = {}
    for name, col in COMPARATORS.items():
        if name == "frozen_fst":
            continue
        report, _ = paired_evaluate(
            frame,
            col,
            "fst_prob",
            target_col="home_win",
            bootstrap_samples=10000,
        )
        controls_vs_fst[name] = {
            "switch_accounting": report["switch_accounting"],
            "metric_deltas": report["metric_deltas"],
        }

    result = {
        "evaluation_id": "LEVLINE-ADAPTIVE-CANDIDATE2-EVALUATION-V1",
        "candidate_id": CANDIDATE_ID,
        "status": "historical_preregistered_2025_paired_evaluation",
        "primary_metric": "straight_up_winner_accuracy",
        "sample": {
            **_coverage(frame),
            "historical_scope_limitation": (
                "Qualified equivalent personnel-regime state exists only for 2025; "
                "season stability is therefore not estimable for Candidate 2 V1."
            ),
        },
        "scoreboard_same_rows": scoreboard,
        "primary_vs_fst": paired_report,
        "controls_vs_fst": controls_vs_fst,
        "week_results": _week_table(frame),
        "shock_attribution": _shock_attribution(frame),
        "summary": {
            "fst_correct": fst["correct"],
            "fst_accuracy": fst["accuracy"],
            "candidate_correct": candidate["correct"],
            "candidate_accuracy": candidate["accuracy"],
            "accuracy_delta_pp": float(100.0 * (candidate["accuracy"] - fst["accuracy"])),
            "brier_delta": float(candidate["brier"] - fst["brier"]),
            "log_loss_delta": float(candidate["log_loss"] - fst["log_loss"]),
            "switches": int(paired_report["switch_accounting"]["disagreements"]),
            "switch_win_rate": paired_report["switch_accounting"]["switch_win_rate"],
            "candidate_only_correct": paired_report["switch_accounting"]["candidate_only_correct"],
            "fst_only_correct": paired_report["switch_accounting"]["reference_only_correct"],
            "net_correct": paired_report["switch_accounting"]["net_correct_from_switches"],
            "mcnemar_exact_two_sided_p": paired_report["switch_accounting"]["mcnemar_exact_two_sided_p"],
        },
        "governance": {
            "same_sample_comparison_required": True,
            "completed_2026_outcomes_used": 0,
            "candidate_parameters_changed_after_results": False,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evaluation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, table in paired_tables.items():
        table.to_csv(out / f"primary_{name}.csv", index=False)
    pd.DataFrame(result["week_results"]).to_csv(out / "week_results.csv", index=False)
    pd.DataFrame(result["shock_attribution"]).to_csv(out / "shock_attribution.csv", index=False)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_v1/evaluation")
    args = parser.parse_args()
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()

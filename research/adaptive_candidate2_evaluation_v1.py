from __future__ import annotations

"""Candidate 2 paired evaluation on the exact historical Candidate 2 sample."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_evaluation import forecast_metrics
from research.adaptive_naive_weekly_refit_control_v1 import (
    attach_frozen_fst,
    load_frame as load_weekly_frame,
    weekly_refit_predictions,
)
from research.adaptive_residual_state_v1 import load_fst_replay, run_state_filter
from research.adaptive_weekly_evaluation_v1 import evaluate as paired_evaluate
from research.adaptive_weekly_evaluation_v1 import switch_accounting

CANDIDATE_ID = "ADAPTIVE-REGIME-SHOCK-GATE-V1"
TARGET_SEASON = 2025


def attach_controls(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()

    residual = run_state_filter(load_fst_replay())
    residual = residual[residual["season"].eq(TARGET_SEASON)][
        ["game_id", "adaptive_prob"]
    ].rename(columns={"adaptive_prob": "candidate1_prob"})
    work = work.merge(residual, on="game_id", how="left", validate="one_to_one")

    weekly = weekly_refit_predictions(load_weekly_frame())
    weekly = attach_frozen_fst(weekly)
    weekly = weekly[weekly["season"].eq(TARGET_SEASON)][
        ["game_id", "weekly_refit_prob"]
    ]
    work = work.merge(weekly, on="game_id", how="left", validate="one_to_one")

    fst_side = work["fst_prob"].ge(0.5)
    component_side = work["component_prob"].ge(0.5)
    boundary_disagree = (
        work["fst_prob"].sub(0.5).abs().le(0.075)
        & fst_side.ne(component_side)
    )
    work["boundary_component_prob"] = np.where(
        boundary_disagree, work["component_prob"], work["fst_prob"]
    )
    work["boundary_component_switch"] = boundary_disagree
    return work


def _comparison(frame: pd.DataFrame, col: str) -> dict:
    metrics = forecast_metrics(frame, col)
    fst = forecast_metrics(frame, "fst_prob")
    switch = switch_accounting(frame, col, "fst_prob")
    return {
        "probability_column": col,
        "correct": int(round(metrics["winner_pct"] * metrics["games"])),
        "accuracy": metrics["winner_pct"],
        "accuracy_delta_pp": 100.0 * (metrics["winner_pct"] - fst["winner_pct"]),
        "brier": metrics["brier"],
        "brier_delta": metrics["brier"] - fst["brier"],
        "log_loss": metrics["log_loss"],
        "log_loss_delta": metrics["log_loss"] - fst["log_loss"],
        **switch,
    }


def _slice_metrics(part: pd.DataFrame) -> dict:
    c = forecast_metrics(part, "candidate_prob")
    f = forecast_metrics(part, "fst_prob")
    s = switch_accounting(part, "candidate_prob", "fst_prob")
    return {
        "games": int(len(part)),
        "candidate_correct": int(round(c["winner_pct"] * len(part))),
        "fst_correct": int(round(f["winner_pct"] * len(part))),
        "candidate_accuracy": c["winner_pct"],
        "fst_accuracy": f["winner_pct"],
        "accuracy_delta_pp": 100.0 * (c["winner_pct"] - f["winner_pct"]),
        "candidate_brier": c["brier"],
        "fst_brier": f["brier"],
        "brier_delta": c["brier"] - f["brier"],
        "candidate_log_loss": c["log_loss"],
        "fst_log_loss": f["log_loss"],
        "log_loss_delta": c["log_loss"] - f["log_loss"],
        "switches": s["disagreements"],
        "candidate_only_correct": s["candidate_only_correct"],
        "fst_only_correct": s["reference_only_correct"],
        "switch_win_rate": s["switch_win_rate"],
        "net_correct_from_switches": s["net_correct_from_switches"],
    }


def _group_records(frame: pd.DataFrame, family: str, values: pd.Series) -> list[dict]:
    rows = []
    for value in pd.Series(values, index=frame.index).dropna().unique().tolist():
        part = frame.loc[pd.Series(values, index=frame.index).eq(value)]
        if part.empty:
            continue
        rows.append({"slice_family": family, "slice_value": str(value), **_slice_metrics(part)})
    return rows


def mechanism_slices(frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    rows.extend(_group_records(frame, "week", frame["week"].astype(int)))

    week = pd.to_numeric(frame["week"], errors="coerce")
    phase = np.select([week <= 6, week <= 12], ["early", "mid"], default="late")
    rows.extend(_group_records(frame, "season_phase", pd.Series(phase, index=frame.index)))

    fst_strength = frame["fst_prob"].sub(0.5).abs()
    fst_bucket = pd.cut(
        fst_strength,
        [-np.inf, 0.025, 0.05, 0.075, 0.10, np.inf],
        labels=["0-2.5pp", "2.5-5pp", "5-7.5pp", "7.5-10pp", ">10pp"],
    )
    rows.extend(_group_records(frame, "fst_boundary_distance", fst_bucket.astype("string")))

    market_strength = frame["market_prob"].sub(0.5).abs()
    market_bucket = pd.cut(
        market_strength,
        [-np.inf, 0.025, 0.05, 0.10, 0.15, np.inf],
        labels=["0-2.5pp", "2.5-5pp", "5-10pp", "10-15pp", ">15pp"],
    )
    rows.extend(_group_records(frame, "market_boundary_distance", market_bucket.astype("string")))

    market_side = np.where(frame["market_prob"].ge(0.5), "home_market_favorite", "away_market_favorite")
    rows.extend(_group_records(frame, "market_side", pd.Series(market_side, index=frame.index)))

    shock_flags = {
        "qb_change": frame["shock_qb_change"].astype(bool),
        "ol_churn": frame["shock_ol_churn"].astype(bool),
        "qb_practice": frame["shock_qb_practice"].astype(bool),
        "any_strong_shock": frame["strong_regime_shock"].astype(bool),
    }
    for name, flag in shock_flags.items():
        for state in (True, False):
            part = frame.loc[flag.eq(state)]
            if not part.empty:
                rows.append({
                    "slice_family": f"shock_{name}",
                    "slice_value": str(state).lower(),
                    **_slice_metrics(part),
                })

    switch_reason = frame["switch_reason"].astype("string").fillna("unknown")
    rows.extend(_group_records(frame, "switch_reason", switch_reason))
    return rows


def evaluate(input_path: str | Path, bootstrap_samples: int = 10000) -> tuple[dict, dict[str, pd.DataFrame]]:
    frame = pd.read_csv(input_path)
    if not pd.to_numeric(frame["season"], errors="raise").astype(int).eq(TARGET_SEASON).all():
        raise RuntimeError("Candidate 2 evaluation is frozen to the 2025 target sample")
    frame = attach_controls(frame)

    required_controls = {
        "fst_prob",
        "market_prob",
        "candidate1_prob",
        "weekly_refit_prob",
        "component_prob",
        "boundary_component_prob",
        "candidate_prob",
    }
    missing = required_controls - set(frame.columns)
    if missing:
        raise RuntimeError(f"Candidate 2 controls missing: {sorted(missing)}")
    if frame[list(required_controls)].isna().any().any():
        bad = frame.loc[frame[list(required_controls)].isna().any(axis=1), "game_id"].tolist()
        raise RuntimeError(f"Candidate 2 exact paired control sample incomplete: {bad[:5]}")

    primary_report, primary_tables = paired_evaluate(
        frame,
        "candidate_prob",
        "fst_prob",
        bootstrap_samples=bootstrap_samples,
    )

    comparisons = {}
    for name, col in [
        ("frozen_fst", "fst_prob"),
        ("market", "market_prob"),
        ("candidate1_residual", "candidate1_prob"),
        ("weekly_refit_control", "weekly_refit_prob"),
        ("component_resolved", "component_prob"),
        ("boundary_component_no_shock", "boundary_component_prob"),
        ("candidate2", "candidate_prob"),
    ]:
        comparisons[name] = _comparison(frame, col)

    switches = frame[frame["candidate_switch"].astype(bool)].copy()
    switch_rows = []
    for reason, part in switches.groupby("switch_reason", sort=True):
        y = part["home_win"].astype(int)
        candidate_correct = part["candidate_prob"].ge(0.5).astype(int).eq(y)
        fst_correct = part["fst_prob"].ge(0.5).astype(int).eq(y)
        switch_rows.append({
            "switch_reason": str(reason),
            "switches": int(len(part)),
            "candidate_only_correct": int((candidate_correct & ~fst_correct).sum()),
            "fst_only_correct": int((fst_correct & ~candidate_correct).sum()),
            "switch_win_rate": float(candidate_correct.mean()) if len(part) else None,
            "net_correct": int(candidate_correct.sum() - fst_correct.sum()),
        })

    report = {
        "evaluation_id": "ADAPTIVE-CANDIDATE2-EVALUATION-V1",
        "candidate_id": CANDIDATE_ID,
        "status": "historical_2025_paired_evaluation",
        "sample": {
            "season": TARGET_SEASON,
            "games": int(len(frame)),
            "one_season_regime_feature_limit": True,
        },
        "primary_vs_fst": primary_report,
        "comparisons_same_rows": comparisons,
        "coverage": {
            "strong_shock_games": int(frame["strong_regime_shock"].astype(bool).sum()),
            "boundary_component_disagreement_games": int(
                (
                    frame["boundary_eligible"].astype(bool)
                    & frame["component_disagrees"].astype(bool)
                ).sum()
            ),
            "candidate2_switches": int(frame["candidate_switch"].astype(bool).sum()),
            "qb_change_shock_games": int(frame["shock_qb_change"].astype(bool).sum()),
            "ol_churn_shock_games": int(frame["shock_ol_churn"].astype(bool).sum()),
            "qb_practice_shock_games": int(frame["shock_qb_practice"].astype(bool).sum()),
        },
        "switch_reason_summary": switch_rows,
        "governance": {
            "completed_2026_outcomes_used_for_candidate_design": 0,
            "target_outcomes_used_to_change_candidate": 0,
            "same_row_comparison_required": True,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }

    tables = {
        "scored_with_controls": frame,
        "bootstrap": primary_tables["bootstrap"],
        "paired_tests": primary_tables["paired_tests"],
        "calibration_bins": primary_tables["calibration_bins"],
        "standard_slices": primary_tables["slices"],
        "mechanism_slices": pd.DataFrame(mechanism_slices(frame)),
        "switch_reason_summary": pd.DataFrame(switch_rows),
    }
    return report, tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_evaluation_v1")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()

    report, tables = evaluate(args.input, bootstrap_samples=args.bootstrap_samples)
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

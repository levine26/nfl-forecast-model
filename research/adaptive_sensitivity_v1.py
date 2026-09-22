from __future__ import annotations

"""Pre-registered robustness analysis for adaptive weekly learning.

The grid is frozen in research/ADAPTIVE_WEEKLY_LEARNING_RESEARCH_PLAN.md before
the first integrated historical result. Full-sample best configurations are
descriptive only; they are never auto-promoted.
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.adaptive_residual_state_v1 import (
    DEFAULT_CONFIG,
    StateConfig,
    evaluate,
    load_fst_replay,
    run_state_filter,
)
from research.adaptive_selective_switch_gate_v1 import apply_selective_gate, evaluate_gate

PROCESS_VARIANCE = (0.01, 0.03, 0.06)
WEEKLY_REVERSION = (0.90, 0.97, 1.00)
OFFSEASON_REVERSION = (0.25, 0.50, 0.75)
GATE_BOUNDARY = (0.05, 0.075, 0.10)
GATE_MIN_SHIFT = (0.02, 0.035, 0.05)


def config_id(config: StateConfig) -> str:
    return (
        f"q{config.process_variance_per_week:.3f}"
        f"_wr{config.weekly_mean_reversion:.2f}"
        f"_or{config.offseason_mean_reversion:.2f}"
    )


def residual_grid(base: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    rows = []
    scored_by_config: dict[str, pd.DataFrame] = {}
    for q, wr, orev in itertools.product(PROCESS_VARIANCE, WEEKLY_REVERSION, OFFSEASON_REVERSION):
        cfg = StateConfig(
            initial_variance=DEFAULT_CONFIG.initial_variance,
            process_variance_per_week=q,
            weekly_mean_reversion=wr,
            offseason_mean_reversion=orev,
            max_abs_state_logit=DEFAULT_CONFIG.max_abs_state_logit,
        )
        scored = run_state_filter(base, cfg)
        report = evaluate(scored, cfg)
        cid = config_id(cfg)
        scored_by_config[cid] = scored
        rows.append({
            "config_id": cid,
            "process_variance_per_week": q,
            "weekly_mean_reversion": wr,
            "offseason_mean_reversion": orev,
            **report["results"],
        })
    return pd.DataFrame(rows), scored_by_config


def nested_prior_season_selection(
    summaries: pd.DataFrame,
    scored_by_config: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select only from earlier target seasons, then score the untouched later season."""
    target_seasons = (2023, 2024, 2025)
    choices = []
    predictions = []

    for target in target_seasons:
        candidates = []
        for cid, scored in scored_by_config.items():
            prior = scored[scored["season"] < target].copy()
            prior = prior[prior["season"] >= 2022]
            if prior.empty:
                continue
            y = prior["home_win"].astype(int)
            fst_correct = prior["fst_prob"].ge(0.5).astype(int).eq(y)
            adaptive_correct = prior["adaptive_prob"].ge(0.5).astype(int).eq(y)
            brier = float(np.mean((prior["adaptive_prob"] - y) ** 2))
            candidates.append({
                "config_id": cid,
                "prior_games": int(len(prior)),
                "prior_accuracy_delta": float(adaptive_correct.mean() - fst_correct.mean()),
                "prior_brier": brier,
            })
        ranked = pd.DataFrame(candidates).sort_values(
            ["prior_accuracy_delta", "prior_brier", "config_id"],
            ascending=[False, True, True],
            kind="stable",
        )
        if ranked.empty:
            continue
        chosen = ranked.iloc[0].to_dict()
        cid = str(chosen["config_id"])
        target_rows = scored_by_config[cid]
        target_rows = target_rows[target_rows["season"] == target].copy()
        target_rows["selected_config_id"] = cid
        predictions.append(target_rows)
        choices.append({
            "target_season": int(target),
            **chosen,
            "target_outcomes_used_for_selection": 0,
        })

    return pd.DataFrame(choices), pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()


def gate_grid(v1_scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for boundary, shift in itertools.product(GATE_BOUNDARY, GATE_MIN_SHIFT):
        gated = apply_selective_gate(
            v1_scored,
            boundary=boundary,
            min_shift=shift,
        )
        report = evaluate_gate(gated)
        rows.append({
            "boundary": boundary,
            "min_shift": shift,
            **{k: v for k, v in report.items() if k not in {"thresholds", "candidate_id"}},
        })
    return pd.DataFrame(rows)


def run(output_dir: str = "research_outputs/adaptive_sensitivity_v1") -> dict:
    base = load_fst_replay()
    summaries, scored_by_config = residual_grid(base)
    choices, nested = nested_prior_season_selection(summaries, scored_by_config)

    v1_id = config_id(DEFAULT_CONFIG)
    if v1_id not in scored_by_config:
        raise RuntimeError(f"predeclared V1 config missing from sensitivity grid: {v1_id}")
    gates = gate_grid(scored_by_config[v1_id])

    nested_report = None
    if not nested.empty:
        nested_report = evaluate(nested)
        nested_report["status"] = "nested_prior_season_parameter_selection_diagnostic"

    report = {
        "audit_id": "LEVLINE-ADAPTIVE-SENSITIVITY-V1",
        "status": "pre_registered_robustness_not_parameter_rescue",
        "residual_grid_size": int(len(summaries)),
        "gate_grid_size": int(len(gates)),
        "v1_config_id": v1_id,
        "nested_selection": nested_report,
        "governance": {
            "grid_preregistered_before_first_integrated_result": True,
            "full_sample_best_may_be_promoted": False,
            "target_season_outcomes_used_for_own_selection": 0,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summaries.to_csv(out / "residual_grid.csv", index=False)
    gates.to_csv(out / "gate_grid.csv", index=False)
    choices.to_csv(out / "nested_selection_choices.csv", index=False)
    if not nested.empty:
        nested.to_csv(out / "nested_selection_scored_games.csv", index=False)
    (out / "audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/adaptive_sensitivity_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()

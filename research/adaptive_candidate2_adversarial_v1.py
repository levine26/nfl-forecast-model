from __future__ import annotations

"""Preregistered adversarial validation for Candidate 2."""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_evaluation import forecast_metrics
from research.adaptive_regime_shock_gate_v1 import GateConfig, apply_gate
from research.adaptive_weekly_evaluation_v1 import switch_accounting

BOUNDARIES = (0.05, 0.075, 0.10)
OL_THRESHOLDS = (1, 2, 3)
PRACTICE_DEFINITIONS = ("DNP_only", "DNP_or_limited")


def _metrics(frame: pd.DataFrame, col: str) -> dict:
    c = forecast_metrics(frame, col)
    f = forecast_metrics(frame, "fst_prob")
    s = switch_accounting(frame, col, "fst_prob")
    return {
        "games": int(len(frame)),
        "correct": int(round(c["winner_pct"] * len(frame))),
        "accuracy": c["winner_pct"],
        "accuracy_delta_pp": 100.0 * (c["winner_pct"] - f["winner_pct"]),
        "brier": c["brier"],
        "brier_delta": c["brier"] - f["brier"],
        "log_loss": c["log_loss"],
        "log_loss_delta": c["log_loss"] - f["log_loss"],
        "switches": s["disagreements"],
        "candidate_only_correct": s["candidate_only_correct"],
        "fst_only_correct": s["reference_only_correct"],
        "net_correct": s["net_correct_from_switches"],
        "switch_win_rate": s["switch_win_rate"],
        "mcnemar_exact_two_sided_p": s["mcnemar_exact_two_sided_p"],
    }


def _variant_probability(
    frame: pd.DataFrame,
    *,
    use_qb_change: bool = True,
    use_ol: bool = True,
    use_practice: bool = True,
) -> pd.Series:
    shock = pd.Series(False, index=frame.index)
    if use_qb_change:
        shock |= frame["shock_qb_change"].astype(bool)
    if use_ol:
        shock |= frame["shock_ol_churn"].astype(bool)
    if use_practice:
        shock |= frame["shock_qb_practice"].astype(bool)
    switch = (
        frame["boundary_eligible"].astype(bool)
        & frame["component_disagrees"].astype(bool)
        & shock
    )
    return pd.Series(
        np.where(switch, frame["component_prob"], frame["fst_prob"]),
        index=frame.index,
    )


def run(input_path: str | Path, output_dir: str | Path) -> dict:
    source = pd.read_csv(input_path)
    primary = apply_gate(
        source,
        GateConfig(boundary=0.075, ol_new_threshold=2, practice_definition="DNP_only"),
    )
    primary_metrics = _metrics(primary, "candidate_prob")

    grid_rows = []
    for boundary, ol_threshold, practice in itertools.product(
        BOUNDARIES, OL_THRESHOLDS, PRACTICE_DEFINITIONS
    ):
        scored = apply_gate(
            source,
            GateConfig(
                boundary=boundary,
                ol_new_threshold=ol_threshold,
                practice_definition=practice,
            ),
        )
        row = {
            "boundary": boundary,
            "ol_new_threshold": ol_threshold,
            "practice_definition": practice,
            "is_primary_v1": (
                boundary == 0.075
                and ol_threshold == 2
                and practice == "DNP_only"
            ),
            **_metrics(scored, "candidate_prob"),
        }
        grid_rows.append(row)
    grid = pd.DataFrame(grid_rows)

    ablations = []
    for name, kwargs in [
        ("primary_all_channels", {}),
        ("remove_qb_change", {"use_qb_change": False}),
        ("remove_ol_churn", {"use_ol": False}),
        ("remove_qb_practice", {"use_practice": False}),
        ("qb_change_only", {"use_ol": False, "use_practice": False}),
        ("ol_churn_only", {"use_qb_change": False, "use_practice": False}),
        ("qb_practice_only", {"use_qb_change": False, "use_ol": False}),
    ]:
        scored = primary.copy()
        scored[f"prob_{name}"] = _variant_probability(scored, **kwargs)
        ablations.append({"ablation": name, **_metrics(scored, f"prob_{name}")})
    ablations_df = pd.DataFrame(ablations)

    switch = primary["candidate_switch"].astype(bool)
    primary["candidate_correct"] = (
        primary["candidate_prob"].ge(0.5).astype(int) == primary["home_win"].astype(int)
    )
    primary["fst_correct"] = (
        primary["fst_prob"].ge(0.5).astype(int) == primary["home_win"].astype(int)
    )
    primary["switch_net"] = np.where(
        switch,
        primary["candidate_correct"].astype(int) - primary["fst_correct"].astype(int),
        0,
    )

    weekly = (
        primary.groupby(["season", "week"], sort=True)
        .agg(
            games=("game_id", "size"),
            switches=("candidate_switch", "sum"),
            net_correct=("switch_net", "sum"),
        )
        .reset_index()
    )
    max_week_share = None
    positive_net = int(max(0, primary["switch_net"].sum()))
    if positive_net > 0 and not weekly.empty:
        max_week_positive = int(weekly["net_correct"].clip(lower=0).max())
        max_week_share = float(max_week_positive / positive_net)

    team_rows = []
    for team in sorted(set(primary["home_team"].astype(str)) | set(primary["away_team"].astype(str))):
        part = primary[
            primary["home_team"].astype(str).eq(team)
            | primary["away_team"].astype(str).eq(team)
        ]
        team_rows.append(
            {
                "team": team,
                "games": int(len(part)),
                "switches": int(part["candidate_switch"].sum()),
                "net_correct": int(part["switch_net"].sum()),
            }
        )
    teams = pd.DataFrame(team_rows).sort_values(
        ["net_correct", "switches", "team"], ascending=[False, False, True]
    )

    leave_week = []
    for (season, week), part in primary.groupby(["season", "week"], sort=True):
        rest = primary.drop(index=part.index)
        if rest.empty:
            continue
        leave_week.append(
            {
                "left_out_season": int(season),
                "left_out_week": int(week),
                **_metrics(rest, "candidate_prob"),
            }
        )
    leave_week_df = pd.DataFrame(leave_week)

    leave_team = []
    for team in sorted(set(primary["home_team"].astype(str)) | set(primary["away_team"].astype(str))):
        rest = primary[
            ~primary["home_team"].astype(str).eq(team)
            & ~primary["away_team"].astype(str).eq(team)
        ]
        if rest.empty:
            continue
        leave_team.append({"left_out_team": team, **_metrics(rest, "candidate_prob")})
    leave_team_df = pd.DataFrame(leave_team)

    # Primary positive result is considered fragility-sensitive when a majority
    # of the preregistered grid has non-positive accuracy delta, or when the
    # primary net gain is concentrated >50% in one week.
    positive_grid_fraction = float((grid["accuracy_delta_pp"] > 0).mean())
    nonnegative_grid_fraction = float((grid["accuracy_delta_pp"] >= 0).mean())
    primary_positive = primary_metrics["accuracy_delta_pp"] > 0
    fragility = bool(
        primary_positive
        and (
            positive_grid_fraction < 0.5
            or (max_week_share is not None and max_week_share > 0.5)
        )
    )

    report = {
        "audit_id": "ADAPTIVE-CANDIDATE2-ADVERSARIAL-V1",
        "candidate_id": "ADAPTIVE-REGIME-SHOCK-GATE-V1",
        "status": "preregistered_adversarial_validation",
        "primary": primary_metrics,
        "grid": {
            "configurations": int(len(grid)),
            "positive_accuracy_fraction": positive_grid_fraction,
            "nonnegative_accuracy_fraction": nonnegative_grid_fraction,
            "best_accuracy_delta_pp": float(grid["accuracy_delta_pp"].max()),
            "worst_accuracy_delta_pp": float(grid["accuracy_delta_pp"].min()),
            "primary_rank_by_accuracy_delta": int(
                grid["accuracy_delta_pp"].rank(method="min", ascending=False)[
                    grid["is_primary_v1"]
                ].iloc[0]
            ),
            "best_cell_is_descriptive_only": True,
        },
        "concentration": {
            "positive_net_winners_primary": positive_net,
            "max_single_week_positive_gain_share": max_week_share,
            "top_team_rows": teams.head(8).to_dict("records"),
        },
        "ablation_summary": ablations,
        "robustness": {
            "threshold_fragility_flag": fragility,
            "one_season_regime_feature_limit": True,
            "season_stability_estimable": False,
        },
        "governance": {
            "grid_preregistered_before_target_results": True,
            "best_grid_cell_may_replace_primary_v1": False,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "promotion_authorized": False,
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    grid.to_csv(out / "robustness_grid.csv", index=False)
    ablations_df.to_csv(out / "channel_ablations.csv", index=False)
    weekly.to_csv(out / "week_concentration.csv", index=False)
    teams.to_csv(out / "team_concentration.csv", index=False)
    leave_week_df.to_csv(out / "leave_one_week_out.csv", index=False)
    leave_team_df.to_csv(out / "leave_one_team_out.csv", index=False)
    (out / "adversarial.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_adversarial_v1")
    args = parser.parse_args()
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()

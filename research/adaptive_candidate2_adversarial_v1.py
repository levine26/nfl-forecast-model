from __future__ import annotations

"""Preregistered adversarial validation for ADAPTIVE-REGIME-SHOCK-GATE-V1.

The primary V1 configuration remains fixed. Grid cells and channel ablations are
falsification evidence only and may not replace V1 after target outcomes are observed.
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.adaptive_regime_shock_gate_v1 import GateConfig, apply_gate
from research.adaptive_weekly_evaluation_v1 import switch_accounting

BOUNDARIES = (0.05, 0.075, 0.10)
OL_THRESHOLDS = (1, 2, 3)
PRACTICE_MODES = ("dnp_only", "dnp_or_limited")
EPS = 1e-6


def _log_loss(p: pd.Series, y: pd.Series) -> float:
    prob = np.clip(pd.to_numeric(p, errors="raise").to_numpy(float), EPS, 1.0 - EPS)
    target = pd.to_numeric(y, errors="raise").to_numpy(float)
    return float(np.mean(-(target * np.log(prob) + (1 - target) * np.log(1 - prob))))


def _metrics(frame: pd.DataFrame, col: str) -> dict:
    y = pd.to_numeric(frame["home_win"], errors="raise").astype(int)
    p = pd.to_numeric(frame[col], errors="raise")
    fst = pd.to_numeric(frame["fst_prob"], errors="raise")
    correct = p.ge(0.5).astype(int).eq(y)
    fst_correct = fst.ge(0.5).astype(int).eq(y)
    switches = switch_accounting(frame, col, "fst_prob")
    return {
        "games": int(len(frame)),
        "correct": int(correct.sum()),
        "accuracy": float(correct.mean()),
        "fst_correct": int(fst_correct.sum()),
        "fst_accuracy": float(fst_correct.mean()),
        "accuracy_delta_pp": float(100.0 * (correct.mean() - fst_correct.mean())),
        "brier": float(np.mean((p - y) ** 2)),
        "brier_delta": float(np.mean((p - y) ** 2) - np.mean((fst - y) ** 2)),
        "log_loss": _log_loss(p, y),
        "log_loss_delta": float(_log_loss(p, y) - _log_loss(fst, y)),
        "switches": switches["disagreements"],
        "candidate_only_correct": switches["candidate_only_correct"],
        "fst_only_correct": switches["reference_only_correct"],
        "net_correct": switches["net_correct_from_switches"],
        "switch_win_rate": switches["switch_win_rate"],
        "mcnemar_exact_two_sided_p": switches["mcnemar_exact_two_sided_p"],
    }


def _rescore(source: pd.DataFrame, config: GateConfig) -> pd.DataFrame:
    """Reapply a preregistered gate with the target column removed."""
    if "home_win" not in source.columns:
        raise ValueError("adversarial source requires target outcomes for grading")
    outcomes = source[["game_id", "home_win"]].copy()
    prediction = source.drop(columns=["home_win"]).copy()
    rescored = apply_gate(prediction, config)
    return rescored.merge(outcomes, on="game_id", how="left", validate="one_to_one")


def _phase(week: pd.Series) -> pd.Series:
    w = pd.to_numeric(week, errors="coerce")
    return pd.Series(
        np.select([w <= 6, w <= 12], ["early", "mid"], default="late"),
        index=week.index,
    )


def run(input_path: str | Path, output_dir: str | Path) -> dict:
    source = pd.read_csv(input_path)
    if sorted(source["season"].astype(int).unique().tolist()) != [2025]:
        raise RuntimeError("Candidate 2 adversarial audit is frozen to 2025")
    if source["game_id"].astype(str).duplicated().any():
        raise ValueError("Candidate 2 adversarial source has duplicate game IDs")

    primary_config = GateConfig(
        boundary=0.075,
        ol_new_threshold=2,
        practice_mode="dnp_only",
    )
    primary = _rescore(source, primary_config)
    primary_metrics = _metrics(primary, "candidate_prob")

    grid_rows = []
    for boundary, ol_threshold, practice_mode in itertools.product(
        BOUNDARIES, OL_THRESHOLDS, PRACTICE_MODES
    ):
        config = GateConfig(
            boundary=boundary,
            ol_new_threshold=ol_threshold,
            practice_mode=practice_mode,
        )
        scored = _rescore(source, config)
        grid_rows.append({
            "boundary": boundary,
            "ol_new_threshold": ol_threshold,
            "practice_mode": practice_mode,
            "is_primary_v1": (
                boundary == 0.075
                and ol_threshold == 2
                and practice_mode == "dnp_only"
            ),
            **_metrics(scored, "candidate_prob"),
        })
    grid = pd.DataFrame(grid_rows)

    ablation_rows = []
    ablation_specs = [
        ("primary_all_channels", {}),
        ("remove_qb_change", {"include_qb_change": False}),
        ("remove_ol_churn", {"include_ol_churn": False}),
        ("remove_qb_practice", {"include_qb_practice": False}),
        (
            "qb_change_only",
            {"include_ol_churn": False, "include_qb_practice": False},
        ),
        (
            "ol_churn_only",
            {"include_qb_change": False, "include_qb_practice": False},
        ),
        (
            "qb_practice_only",
            {"include_qb_change": False, "include_ol_churn": False},
        ),
    ]
    for name, overrides in ablation_specs:
        config = GateConfig(
            boundary=0.075,
            ol_new_threshold=2,
            practice_mode="dnp_only",
            **overrides,
        )
        rescored = _rescore(source, config)
        ablation_rows.append({"ablation": name, **_metrics(rescored, "candidate_prob")})
    ablations = pd.DataFrame(ablation_rows)

    primary["candidate_correct"] = (
        primary["candidate_prob"].ge(0.5).astype(int) == primary["home_win"].astype(int)
    )
    primary["fst_correct"] = (
        primary["fst_prob"].ge(0.5).astype(int) == primary["home_win"].astype(int)
    )
    primary["switch_net"] = np.where(
        primary["candidate_switch"].astype(bool),
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
    positive_net = int(max(0, primary["switch_net"].sum()))
    max_week_share = None
    if positive_net > 0 and not weekly.empty:
        max_week_positive = int(weekly["net_correct"].clip(lower=0).max())
        max_week_share = float(max_week_positive / positive_net)

    teams_present = sorted(
        set(primary["home_team"].astype(str)) | set(primary["away_team"].astype(str))
    )
    team_rows = []
    for team in teams_present:
        part = primary[
            primary["home_team"].astype(str).eq(team)
            | primary["away_team"].astype(str).eq(team)
        ]
        team_rows.append({
            "team": team,
            "games": int(len(part)),
            "switches": int(part["candidate_switch"].sum()),
            "net_correct": int(part["switch_net"].sum()),
        })
    teams = pd.DataFrame(team_rows).sort_values(
        ["net_correct", "switches", "team"],
        ascending=[False, False, True],
    )

    leave_week_rows = []
    for (season, week), part in primary.groupby(["season", "week"], sort=True):
        rest = primary.drop(index=part.index)
        if not rest.empty:
            leave_week_rows.append({
                "left_out_season": int(season),
                "left_out_week": int(week),
                **_metrics(rest, "candidate_prob"),
            })
    leave_week = pd.DataFrame(leave_week_rows)

    leave_team_rows = []
    for team in teams_present:
        rest = primary[
            ~primary["home_team"].astype(str).eq(team)
            & ~primary["away_team"].astype(str).eq(team)
        ]
        if not rest.empty:
            leave_team_rows.append({
                "left_out_team": team,
                **_metrics(rest, "candidate_prob"),
            })
    leave_team = pd.DataFrame(leave_team_rows)

    subgroup_rows = []
    primary["season_phase"] = _phase(primary["week"])
    primary["fst_pick_favorite_side"] = np.where(
        primary["fst_prob"].ge(0.5), "home", "away"
    )
    primary["fst_boundary_bucket"] = pd.cut(
        primary["fst_prob"].sub(0.5).abs(),
        [-np.inf, 0.025, 0.05, 0.075, 0.10, np.inf],
        labels=["0-2.5pp", "2.5-5pp", "5-7.5pp", "7.5-10pp", ">10pp"],
    ).astype("string")
    primary["market_boundary_bucket"] = pd.cut(
        primary["market_prob"].sub(0.5).abs(),
        [-np.inf, 0.025, 0.05, 0.10, 0.15, np.inf],
        labels=["0-2.5pp", "2.5-5pp", "5-10pp", "10-15pp", ">15pp"],
    ).astype("string")

    for family in (
        "season_phase",
        "fst_pick_favorite_side",
        "fst_boundary_bucket",
        "market_boundary_bucket",
    ):
        for value, part in primary.groupby(family, dropna=False, sort=True):
            subgroup_rows.append({
                "slice_family": family,
                "slice_value": str(value),
                **_metrics(part, "candidate_prob"),
            })
    subgroups = pd.DataFrame(subgroup_rows)

    positive_grid_fraction = float((grid["accuracy_delta_pp"] > 0).mean())
    nonnegative_grid_fraction = float((grid["accuracy_delta_pp"] >= 0).mean())
    primary_positive = primary_metrics["accuracy_delta_pp"] > 0
    primary_rank = int(
        grid["accuracy_delta_pp"].rank(method="min", ascending=False)[
            grid["is_primary_v1"]
        ].iloc[0]
    )
    leave_week_nonpositive = (
        int((leave_week["accuracy_delta_pp"] <= 0).sum()) if not leave_week.empty else None
    )
    leave_team_nonpositive = (
        int((leave_team["accuracy_delta_pp"] <= 0).sum()) if not leave_team.empty else None
    )
    channel_removal_nonpositive = int(
        (
            ablations.loc[
                ablations["ablation"].isin(
                    ["remove_qb_change", "remove_ol_churn", "remove_qb_practice"]
                ),
                "accuracy_delta_pp",
            ]
            <= 0
        ).sum()
    )

    fragility = bool(
        primary_positive
        and (
            positive_grid_fraction < 0.5
            or (max_week_share is not None and max_week_share > 0.5)
        )
    )

    report = {
        "audit_id": "LEVLINE-ADAPTIVE-CANDIDATE2-ADVERSARIAL-V1",
        "candidate_id": "ADAPTIVE-REGIME-SHOCK-GATE-V1",
        "status": "preregistered_adversarial_validation",
        "primary": primary_metrics,
        "grid": {
            "configurations": int(len(grid)),
            "positive_accuracy_fraction": positive_grid_fraction,
            "nonnegative_accuracy_fraction": nonnegative_grid_fraction,
            "best_accuracy_delta_pp": float(grid["accuracy_delta_pp"].max()),
            "worst_accuracy_delta_pp": float(grid["accuracy_delta_pp"].min()),
            "primary_rank_by_accuracy_delta": primary_rank,
            "best_cell_is_descriptive_only": True,
        },
        "concentration": {
            "positive_net_winners_primary": positive_net,
            "max_single_week_positive_gain_share": max_week_share,
            "top_team_rows": teams.head(8).to_dict("records"),
        },
        "ablation": {
            "channel_removal_nonpositive_count": channel_removal_nonpositive,
            "rows": ablations.to_dict("records"),
        },
        "leave_one_out": {
            "weeks_with_nonpositive_delta_after_removal": leave_week_nonpositive,
            "teams_with_nonpositive_delta_after_removal": leave_team_nonpositive,
        },
        "robustness": {
            "threshold_fragility_flag": fragility,
            "one_season_regime_feature_limit": True,
            "season_stability_estimable": False,
            "market_path_dependence_testable_historically": False,
            "reason_market_path_not_tested": (
                "strict equivalent historical multi-book PIT path is unavailable; "
                "Candidate 2 V1 contains no market-shock feature"
            ),
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
    ablations.to_csv(out / "channel_ablations.csv", index=False)
    weekly.to_csv(out / "week_concentration.csv", index=False)
    teams.to_csv(out / "team_concentration.csv", index=False)
    leave_week.to_csv(out / "leave_one_week_out.csv", index=False)
    leave_team.to_csv(out / "leave_one_team_out.csv", index=False)
    subgroups.to_csv(out / "subgroup_slices.csv", index=False)
    (out / "adversarial.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="research_outputs/adaptive_candidate2_v1/adversarial")
    args = parser.parse_args()
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()

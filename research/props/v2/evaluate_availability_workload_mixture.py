from __future__ import annotations

"""Run the preregistered season-forward availability/workload evaluation."""

import argparse
import json
import math
from pathlib import Path
import sys

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids  # noqa: E402
from availability_workload_mixture import (  # noqa: E402
    CONTRACT_VERSION,
    SUPPORTED_DESIGNATIONS,
    SUPPORTED_POSITIONS,
    build_workload_examples,
    evaluate_season_forward,
    normalize_injury_designations,
    normalize_snap_history,
)

EVALUATION_SEASONS = (2023, 2024, 2025)
ACTIVE_BRIER_MAX_DEGRADATION = 0.005


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _pooled_summary(frame: pd.DataFrame) -> dict:
    if frame.empty:
        raise ValueError("cannot summarize empty availability/workload evaluation")
    mixture_rmse = float(math.sqrt(frame["mixture_sq_error"].mean()))
    active_rmse = float(math.sqrt(frame["active_only_sq_error"].mean()))
    return {
        "n": int(len(frame)),
        "unique_players": int(frame["player_id"].nunique()),
        "mixture_workload_mae": float(frame["mixture_abs_error"].mean()),
        "active_only_workload_mae": float(frame["active_only_abs_error"].mean()),
        "mixture_minus_active_only_mae": float(
            (frame["mixture_abs_error"] - frame["active_only_abs_error"]).mean()
        ),
        "mixture_workload_rmse": mixture_rmse,
        "active_only_workload_rmse": active_rmse,
        "mixture_minus_active_only_rmse": float(mixture_rmse - active_rmse),
        "mixture_active_brier": float(frame["mixture_active_brier"].mean()),
        "active_only_brier": float(frame["active_only_brier"].mean()),
        "mixture_minus_active_only_brier": float(
            (frame["mixture_active_brier"] - frame["active_only_brier"]).mean()
        ),
        "mixture_state_brier": float(frame["mixture_state_brier"].mean()),
        "mixture_state_log_loss": float(frame["mixture_state_log_loss"].mean()),
        "state_counts": frame["workload_state"].value_counts().to_dict(),
        "designation_counts": frame["designation"].value_counts().to_dict(),
        "position_counts": frame["position"].value_counts().to_dict(),
    }


def _subgroups(frame: pd.DataFrame) -> dict[str, dict]:
    result = {}
    for (designation, position), group in frame.groupby(
        ["designation", "position"], sort=True
    ):
        result[f"{designation}:{position}"] = _pooled_summary(group)
    return result


def run(output_dir: Path) -> dict:
    load_seasons = list(range(2012, max(EVALUATION_SEASONS) + 1))
    injuries_raw = _pandas(nfl.load_injuries(load_seasons))
    snaps_raw = _pandas(nfl.load_snap_counts(load_seasons))
    players = _pandas(nfl.load_players())
    snaps_with_ids, identity_audit = normalize_snap_counts_player_ids(snaps_raw, players)
    if snaps_with_ids is None or snaps_with_ids.empty:
        raise RuntimeError(f"snap identity normalization failed: {identity_audit}")

    injuries, injury_audit = normalize_injury_designations(
        injuries_raw, max_season=max(EVALUATION_SEASONS)
    )
    snaps, snap_audit = normalize_snap_history(
        snaps_with_ids, max_season=max(EVALUATION_SEASONS)
    )
    examples, examples_audit = build_workload_examples(injuries, snaps)
    if examples.empty:
        raise RuntimeError("no availability/workload examples survived source gates")

    output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    per_season = {}
    for season in EVALUATION_SEASONS:
        scored, summary = evaluate_season_forward(
            examples, evaluation_season=season
        )
        scored["evaluation_season"] = season
        frames.append(scored)
        per_season[str(season)] = summary
        scored.to_csv(output_dir / f"{season}_forecast_level.csv", index=False)
        (output_dir / f"{season}_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    pooled = pd.concat(frames, ignore_index=True)
    aggregate = _pooled_summary(pooled)
    subgroup = _subgroups(pooled)
    improving_seasons = sum(
        float(per_season[str(season)]["mixture_minus_active_only_mae"]) < 0.0
        for season in EVALUATION_SEASONS
    )
    active_brier_delta = float(aggregate["mixture_minus_active_only_brier"])
    development_gate = {
        "aggregate_workload_mae_improved": bool(
            aggregate["mixture_minus_active_only_mae"] < 0.0
        ),
        "at_least_two_of_three_seasons_improved": bool(improving_seasons >= 2),
        "active_brier_not_materially_degraded": bool(
            active_brier_delta <= ACTIVE_BRIER_MAX_DEGRADATION
        ),
        "active_brier_max_allowed_degradation": ACTIVE_BRIER_MAX_DEGRADATION,
        "improving_season_count": int(improving_seasons),
    }
    development_gate["passed"] = bool(all([
        development_gate["aggregate_workload_mae_improved"],
        development_gate["at_least_two_of_three_seasons_improved"],
        development_gate["active_brier_not_materially_degraded"],
    ]))

    result = {
        "contract_version": CONTRACT_VERSION,
        "evaluation_seasons": list(EVALUATION_SEASONS),
        "source_audit": {
            "injuries": injury_audit,
            "snaps": snap_audit,
            "snap_identity": identity_audit,
            "examples": examples_audit,
        },
        "aggregate": aggregate,
        "by_season": per_season,
        "by_designation_position": subgroup,
        "development_gate": development_gate,
        "prop_outcomes_used_for_fit_or_evaluation": 0,
        "sportsbook_results_used_for_fit_or_evaluation": 0,
        "completed_2026_outcomes_used": 0,
        "research_only": True,
        "production_authorized": False,
    }
    (output_dir / "aggregate_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pooled.to_csv(output_dir / "all_forecast_level.csv", index=False)

    report = [
        "# LevLine Props 2.0 — Availability / Workload Mixture",
        "",
        "Retrospective football-state development evidence only. No prop outcomes were used.",
        "",
        f"- N: **{aggregate['n']:,}**",
        f"- mixture workload MAE: **{aggregate['mixture_workload_mae']:.4f}**",
        f"- active-only workload MAE: **{aggregate['active_only_workload_mae']:.4f}**",
        f"- mixture minus active-only MAE: **{aggregate['mixture_minus_active_only_mae']:+.4f}**",
        f"- mixture workload RMSE: **{aggregate['mixture_workload_rmse']:.4f}**",
        f"- active-only workload RMSE: **{aggregate['active_only_workload_rmse']:.4f}**",
        f"- mixture active Brier: **{aggregate['mixture_active_brier']:.5f}**",
        f"- active-only Brier: **{aggregate['active_only_brier']:.5f}**",
        f"- gate passed: **{development_gate['passed']}**",
        "",
        "## Season-forward",
    ]
    for season in EVALUATION_SEASONS:
        item = per_season[str(season)]
        report.extend([
            "",
            f"### {season}",
            f"- N: {item['n']:,}",
            f"- mixture MAE: {item['mixture_workload_mae']:.4f}",
            f"- active-only MAE: {item['active_only_workload_mae']:.4f}",
            f"- delta: {item['mixture_minus_active_only_mae']:+.4f}",
            f"- mixture active Brier: {item['mixture_active_brier']:.5f}",
            f"- active-only Brier: {item['active_only_brier']:.5f}",
        ])
    (output_dir / "report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

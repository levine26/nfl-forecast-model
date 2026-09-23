from __future__ import annotations

"""Execute frozen ATS NextGen Stage-B Q2 historical development.

Research only. Before any Q2 fit, this runner regenerates the Phase-2 gate and
complete frozen Stage-A Q1 OOF interface, verifies their preregistered SHA-256
identities, and directly proves that the Stage-B Q1 center helper reproduces the
frozen Stage-A 2022-2025 median predictions. It fails closed on any drift.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import (
    HISTORICAL_END,
    TRAINING_FLOOR,
    build_historical_ats_gate,
    validate_gate_frame,
)
from nfl_forecast.challenger_ats_nextgen_q1 import generate_q1_outer_oof
from nfl_forecast.challenger_ats_nextgen_q2 import CANDIDATE_ID, q1_median_center_for_target
from nfl_forecast.challenger_ats_nextgen_q2_experiment import generate_q2_outer_oof
from nfl_forecast.challenger_ats_nextgen_q2_reporting import (
    q2_cover_reliability,
    q2_fixed_slice_metrics,
    q2_metric_table,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features

OPENING_REGISTRY = Path("research/ats-nextgen/phase2_opening_registry.json")
Q1_RESULT_REGISTRY = Path("research/ats-nextgen/phase2_q1_result_registry.json")
Q2_OPENING_REGISTRY = Path("research/ats-nextgen/phase2_q2_opening_registry.json")
REPEATED_USE_DISCLOSURE = (
    "2022-2025 is chronology-clean development evidence for this candidate execution "
    "but is not pristine independent confirmation because those seasons have informed "
    "prior LevLine research."
)


def _csv_sha256(frame: pd.DataFrame) -> str:
    raw = frame.to_csv(index=False, float_format="%.17g").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canonical_gate_sha256(frame: pd.DataFrame) -> str:
    canonical = frame.sort_values("game_id", kind="mergesort").reset_index(drop=True)
    raw = canonical.to_csv(
        index=False,
        float_format="%.17g",
        lineterminator="\n",
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build_gate(config_path: str) -> pd.DataFrame:
    cfg = load_config(config_path)
    seasons = list(range(TRAINING_FLOOR, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    schedules = bundle.schedules.copy()
    schedule_season = pd.to_numeric(schedules["season"], errors="coerce")
    if schedule_season.isna().any() or schedule_season.gt(HISTORICAL_END).any():
        raise RuntimeError("Q2 runner received post-2025 schedule rows")
    schedules = schedules[schedule_season.ge(TRAINING_FLOOR)].copy()

    elo = build_pregame_elo(
        schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(
        bundle.pbp,
        cfg["data"]["neutral_wp_lower"],
        cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, schedules)
    games = build_matchup_features(team_games, schedules, elo)
    game_season = pd.to_numeric(games["season"], errors="coerce")
    if game_season.isna().any() or game_season.gt(HISTORICAL_END).any():
        raise RuntimeError("Q2 matchup frame crossed the completed-2025 boundary")
    gate = build_historical_ats_gate(games[game_season.ge(TRAINING_FLOOR)].copy())
    validate_gate_frame(gate)
    return gate


def _assert_q1_median_interface(gate: pd.DataFrame, q1_oof: pd.DataFrame) -> None:
    """Prove the generic Stage-B Q1 helper reproduces frozen outer median predictions."""
    for season in (2022, 2023, 2024, 2025):
        upstream = q1_median_center_for_target(gate, season)
        expected = q1_oof.loc[
            pd.to_numeric(q1_oof["season"], errors="coerce").eq(season),
            ["game_id", "q1_q_med"],
        ].copy()
        actual = pd.DataFrame(
            {
                "game_id": upstream.target_game_ids,
                "stage_b_q1_q_med": upstream.target_residual_prediction,
            }
        )
        merged = expected.merge(
            actual,
            on="game_id",
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        if not merged["_merge"].eq("both").all():
            raise RuntimeError(
                f"Q2 Q1-center game identity differs from frozen Stage-A OOF for {season}"
            )
        frozen = pd.to_numeric(merged["q1_q_med"], errors="raise").to_numpy(dtype=float)
        regenerated = pd.to_numeric(
            merged["stage_b_q1_q_med"], errors="raise"
        ).to_numpy(dtype=float)
        if not np.allclose(frozen, regenerated, atol=1e-10, rtol=0.0):
            maximum = float(np.max(np.abs(frozen - regenerated)))
            raise RuntimeError(
                f"Q2 upstream Q1 median reproduction failed for {season}; "
                f"max_abs_diff={maximum}"
            )


def run(
    output_dir: str = "research_outputs/ats_nextgen/q2",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    opening_registry = json.loads(OPENING_REGISTRY.read_text(encoding="utf-8"))
    q1_registry = json.loads(Q1_RESULT_REGISTRY.read_text(encoding="utf-8"))
    q2_registry = json.loads(Q2_OPENING_REGISTRY.read_text(encoding="utf-8"))

    if opening_registry.get("completed_2026_outcomes_authorized") is not False:
        raise RuntimeError("Phase-2 opening registry no longer preserves the 2026 firewall")
    if int(q1_registry.get("completed_2026_outcomes_used", -1)) != 0:
        raise RuntimeError("Q2 handoff registry no longer preserves the completed-2026 firewall")
    if q2_registry.get("candidate_fitting_performed") is not False:
        raise RuntimeError("Q2 opening registry no longer represents an untrained boundary")
    if q2_registry.get("candidate_performance_generated") is not False:
        raise RuntimeError("Q2 opening registry no longer represents a pre-result boundary")
    if q2_registry.get("historical_execution_allowed_before_contract_tests") is not False:
        raise RuntimeError("Q2 opening registry no longer preserves tests-before-results")

    gate = _build_gate(config_path)
    expected_gate_sha = opening_registry["opening_artifact"][
        "gate_canonical_game_keyed_sha256"
    ]
    actual_gate_sha = _canonical_gate_sha256(gate)
    if actual_gate_sha != expected_gate_sha:
        raise RuntimeError(
            "Q2 refused to fit because regenerated Phase-2 gate identity drifted: "
            f"expected={expected_gate_sha} actual={actual_gate_sha}"
        )

    q1_oof, _ = generate_q1_outer_oof(gate)
    expected_q1_sha = q1_registry["evidence_sha256"]["q1_outer_oof_2022_2025.csv"]
    actual_q1_sha = _csv_sha256(q1_oof)
    if actual_q1_sha != expected_q1_sha:
        raise RuntimeError(
            "Q2 refused to fit because regenerated frozen Q1 OOF identity drifted: "
            f"expected={expected_q1_sha} actual={actual_q1_sha}"
        )
    if q2_registry["q1_result"]["outer_oof_sha256"] != expected_q1_sha:
        raise RuntimeError("Q2 opening registry disagrees with frozen Q1 result registry")
    _assert_q1_median_interface(gate, q1_oof)

    # This is the first line that may fit/score Q2. Every frozen upstream identity
    # and chronology boundary above must succeed before execution reaches here.
    metadata, arms, tuning = generate_q2_outer_oof(gate)
    metrics = q2_metric_table(metadata, arms)
    fixed_slices = q2_fixed_slice_metrics(metadata, arms)
    reliability = q2_cover_reliability(metadata, arms)

    metadata_path = out / "q2_outer_oof_metadata_2022_2025.csv"
    tuning_path = out / "q2_inner_selections.csv"
    metrics_path = out / "q2_distribution_metrics.csv"
    slices_path = out / "q2_fixed_slice_metrics.csv"
    reliability_path = out / "q2_cover_reliability.csv"
    pmf_path = out / "q2_outer_oof_pmfs.npz"

    metadata.to_csv(metadata_path, index=False, float_format="%.17g")
    tuning.to_csv(tuning_path, index=False, float_format="%.17g")
    metrics.to_csv(metrics_path, index=False, float_format="%.17g")
    fixed_slices.to_csv(slices_path, index=False, float_format="%.17g")
    reliability.to_csv(reliability_path, index=False, float_format="%.17g")
    np.savez_compressed(
        pmf_path,
        support=np.arange(-75, 76, dtype=int),
        **{name: np.asarray(pmf, dtype=float) for name, pmf in sorted(arms.items())},
    )

    overall = metrics[metrics["season"].eq("ALL")].set_index("arm")
    required_primary = {"M1_GN_FULL", "Q2_GN_FULL"}
    if not required_primary.issubset(set(overall.index)):
        raise RuntimeError("Q2 primary paired arms missing from metric table")
    m1 = overall.loc["M1_GN_FULL"]
    q2 = overall.loc["Q2_GN_FULL"]

    summary = {
        "status": "COMPLETE_UNINTERPRETED",
        "program": "LEVLINE_ATS_NEXTGEN",
        "phase": 2,
        "stage": "B_Q2",
        "candidate_id": CANDIDATE_ID,
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
        "historical_evidence_class": "development_non_pristine",
        "repeated_use_disclosure": REPEATED_USE_DISCLOSURE,
        "gate_canonical_game_keyed_sha256": actual_gate_sha,
        "frozen_q1_outer_oof_sha256": actual_q1_sha,
        "q1_median_interface_reproduced": True,
        "outer_target_seasons": sorted(
            pd.to_numeric(metadata["season"], errors="raise").astype(int).unique().tolist()
        ),
        "outer_oof_rows": int(len(metadata)),
        "arms": sorted(arms),
        "q2_repair_or_rescue_performed": False,
        "ats_hit_rate_used_for_selection": False,
        "roi_used_for_selection": False,
        "primary_paired_snapshot": {
            "M1_GN_FULL_mean_discrete_crps": float(m1["mean_discrete_crps"]),
            "Q2_GN_FULL_mean_discrete_crps": float(q2["mean_discrete_crps"]),
            "Q2_minus_M1_mean_discrete_crps": float(
                q2["mean_discrete_crps"] - m1["mean_discrete_crps"]
            ),
            "M1_GN_FULL_cpl_logloss": float(m1["multinomial_cpl_logloss"]),
            "Q2_GN_FULL_cpl_logloss": float(q2["multinomial_cpl_logloss"]),
            "M1_GN_FULL_cover_brier_nonpush": float(m1["cover_brier_nonpush"]),
            "Q2_GN_FULL_cover_brier_nonpush": float(q2["cover_brier_nonpush"]),
        },
        "outputs": {
            "metadata": str(metadata_path),
            "pmfs": str(pmf_path),
            "inner_selections": str(tuning_path),
            "distribution_metrics": str(metrics_path),
            "fixed_slice_metrics": str(slices_path),
            "cover_reliability": str(reliability_path),
        },
    }
    summary_path = out / "q2_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/ats_nextgen/q2")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()

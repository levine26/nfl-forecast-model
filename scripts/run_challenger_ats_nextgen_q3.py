from __future__ import annotations

"""Execute frozen ATS NextGen Stage-C Q3 historical development.

Research only.  Before the first Q3 fit this runner regenerates the Phase-2
historical gate and verifies the frozen gate identity plus the upstream Q2
structural-invalidation record.  Q2 is not reconstructed or blended.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import (
    HISTORICAL_END,
    TRAINING_FLOOR,
    build_historical_ats_gate,
    validate_gate_frame,
)
from nfl_forecast.challenger_ats_nextgen_q3 import CANDIDATE_ID, generate_q3_outer_oof
from nfl_forecast.challenger_ats_nextgen_q3_reporting import (
    q3_cover_reliability,
    q3_fixed_slice_metrics,
    q3_metric_table,
    q3_push_calibration,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features

PHASE2_OPENING_REGISTRY = Path("research/ats-nextgen/phase2_opening_registry.json")
Q2_RESULT_REGISTRY = Path("research/ats-nextgen/phase2_q2_result_registry.json")
Q3_OPENING_REGISTRY = Path("research/ats-nextgen/phase2_q3_opening_registry.json")
REPEATED_USE_DISCLOSURE = (
    "2022-2025 is chronology-clean development evidence for this candidate execution "
    "but is not pristine independent confirmation because those seasons have informed "
    "prior LevLine research."
)


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
        raise RuntimeError("Q3 runner received post-2025 schedule rows")
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
        raise RuntimeError("Q3 matchup frame crossed the completed-2025 boundary")
    gate = build_historical_ats_gate(games[game_season.ge(TRAINING_FLOOR)].copy())
    validate_gate_frame(gate)
    return gate


def run(
    output_dir: str = "research_outputs/ats_nextgen/q3",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase2 = json.loads(PHASE2_OPENING_REGISTRY.read_text(encoding="utf-8"))
    q2 = json.loads(Q2_RESULT_REGISTRY.read_text(encoding="utf-8"))
    q3 = json.loads(Q3_OPENING_REGISTRY.read_text(encoding="utf-8"))

    if phase2.get("completed_2026_outcomes_authorized") is not False:
        raise RuntimeError("Q3 refused to run because Phase-2 2026 firewall drifted")
    if q2.get("classification") != "STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT":
        raise RuntimeError("Q3 refused to run because frozen Q2 classification drifted")
    if q2.get("accepted_q2_outer_oof_artifact") is not None:
        raise RuntimeError("Q3 refused to run because Q2 registry unexpectedly exposes OOF")
    if q2.get("accepted_q2_primary_performance") is not None:
        raise RuntimeError("Q3 refused to run because Q2 registry unexpectedly exposes performance")
    if q3.get("candidate_fitting_performed") is not False:
        raise RuntimeError("Q3 opening registry no longer represents an untrained boundary")
    if q3.get("candidate_performance_generated") is not False:
        raise RuntimeError("Q3 opening registry no longer represents a pre-result boundary")
    if q3.get("historical_execution_allowed_before_contract_tests") is not False:
        raise RuntimeError("Q3 opening registry no longer preserves tests-before-results")
    if q3["upstream"].get("q2_valid_oof_available") is not False:
        raise RuntimeError("Q3 opening registry silently reopened Q2")
    if q3["upstream"].get("q2_q3_blend_available") is not False:
        raise RuntimeError("Q3 opening registry silently authorized unavailable Q2 blend")

    gate = _build_gate(config_path)
    expected_gate_sha = phase2["opening_artifact"]["gate_canonical_game_keyed_sha256"]
    actual_gate_sha = _canonical_gate_sha256(gate)
    if actual_gate_sha != expected_gate_sha:
        raise RuntimeError(
            "Q3 refused to fit because regenerated Phase-2 gate identity drifted: "
            f"expected={expected_gate_sha} actual={actual_gate_sha}"
        )

    # First line permitted to fit/score Q3. All upstream identities above must pass.
    oof, tuning = generate_q3_outer_oof(gate)
    metrics = q3_metric_table(oof)
    reliability = q3_cover_reliability(oof)
    push_calibration = q3_push_calibration(oof)
    fixed_slices = q3_fixed_slice_metrics(oof)

    oof_path = out / "q3_outer_oof_2022_2025.csv"
    tuning_path = out / "q3_inner_c_pair_selections.csv"
    metrics_path = out / "q3_probability_metrics.csv"
    reliability_path = out / "q3_cover_reliability.csv"
    push_path = out / "q3_push_calibration.csv"
    slices_path = out / "q3_fixed_slice_metrics.csv"

    oof.to_csv(oof_path, index=False, float_format="%.17g")
    tuning.to_csv(tuning_path, index=False, float_format="%.17g")
    metrics.to_csv(metrics_path, index=False, float_format="%.17g")
    reliability.to_csv(reliability_path, index=False, float_format="%.17g")
    push_calibration.to_csv(push_path, index=False, float_format="%.17g")
    fixed_slices.to_csv(slices_path, index=False, float_format="%.17g")

    overall = metrics[metrics["season"].eq("ALL")].set_index("arm")
    if not {"Q3_M2", "Q3"}.issubset(set(overall.index)):
        raise RuntimeError("Q3 primary exact-row arms are missing from metric table")
    m2 = overall.loc["Q3_M2"]
    q3_row = overall.loc["Q3"]

    summary = {
        "status": "COMPLETE_UNINTERPRETED",
        "program": "LEVLINE_ATS_NEXTGEN",
        "phase": 2,
        "stage": "C_Q3",
        "candidate_id": CANDIDATE_ID,
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
        "historical_evidence_class": "development_non_pristine",
        "repeated_use_disclosure": REPEATED_USE_DISCLOSURE,
        "gate_canonical_game_keyed_sha256": actual_gate_sha,
        "q2_complementarity_available": False,
        "q2_q3_blend_available": False,
        "q2_unavailability_reason": "Q2 V1 structurally invalid; no valid Q2 OOF distribution",
        "outer_target_seasons": sorted(
            pd.to_numeric(oof["season"], errors="raise").astype(int).unique().tolist()
        ),
        "outer_oof_rows": int(len(oof)),
        "q3_repair_or_rescue_performed": False,
        "posthoc_calibration_applied": False,
        "class_weighting_used": False,
        "ats_hit_rate_used_for_selection": False,
        "roi_used_for_selection": False,
        "primary_paired_snapshot": {
            "Q3_M2_multinomial_cpl_logloss": float(m2["multinomial_cpl_logloss"]),
            "Q3_multinomial_cpl_logloss": float(q3_row["multinomial_cpl_logloss"]),
            "Q3_minus_Q3_M2_multinomial_cpl_logloss": float(
                q3_row["multinomial_cpl_logloss"] - m2["multinomial_cpl_logloss"]
            ),
            "Q3_M2_cover_brier_nonpush": float(m2["cover_brier_nonpush"]),
            "Q3_cover_brier_nonpush": float(q3_row["cover_brier_nonpush"]),
            "Q3_M2_mean_predicted_push": float(m2["mean_predicted_push"]),
            "Q3_mean_predicted_push": float(q3_row["mean_predicted_push"]),
            "empirical_push_rate": float(q3_row["empirical_push_rate"]),
        },
        "outputs": {
            "outer_oof": str(oof_path),
            "inner_c_pair_selections": str(tuning_path),
            "probability_metrics": str(metrics_path),
            "cover_reliability": str(reliability_path),
            "push_calibration": str(push_path),
            "fixed_slice_metrics": str(slices_path),
        },
    }
    summary_path = out / "q3_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/ats_nextgen/q3")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()

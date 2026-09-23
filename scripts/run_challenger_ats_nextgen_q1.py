from __future__ import annotations

"""Execute frozen ATS NextGen Stage-A Q1 historical development.

This runner is intentionally isolated from production. It first regenerates the
2015-2025 Phase-2 gate and refuses to fit Q1 unless that gate exactly matches the
canonical game-keyed SHA-256 frozen before candidate fitting.
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
from nfl_forecast.challenger_ats_nextgen_q1 import (
    CANDIDATE_ID,
    generate_q1_outer_oof,
    q1_metric_table,
    quantile_crossing_table,
)
from nfl_forecast.challenger_ats_nextgen_q1_reporting import q1_fixed_slice_metrics
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features

REGISTRY_PATH = Path("research/ats-nextgen/phase2_opening_registry.json")
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
        raise RuntimeError("Q1 runner received post-2025 schedule rows")
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
        raise RuntimeError("Q1 matchup frame crossed the completed-2025 boundary")
    gate = build_historical_ats_gate(games[game_season.ge(TRAINING_FLOOR)].copy())
    validate_gate_frame(gate)
    return gate


def run(
    output_dir: str = "research_outputs/ats_nextgen/q1",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    expected_gate_sha = registry["opening_artifact"]["gate_canonical_game_keyed_sha256"]
    if registry.get("completed_2026_outcomes_authorized") is not False:
        raise RuntimeError("Opening registry no longer preserves the completed-2026 firewall")

    gate = _build_gate(config_path)
    actual_gate_sha = _canonical_gate_sha256(gate)
    if actual_gate_sha != expected_gate_sha:
        raise RuntimeError(
            "Q1 refused to fit because regenerated Phase-2 gate hash differs from frozen opening gate: "
            f"expected={expected_gate_sha} actual={actual_gate_sha}"
        )

    oof, tuning = generate_q1_outer_oof(gate)
    metrics = q1_metric_table(oof)
    crossings = quantile_crossing_table(oof)
    fixed_slices = q1_fixed_slice_metrics(oof)

    oof_path = out / "q1_outer_oof_2022_2025.csv"
    tuning_path = out / "q1_inner_alpha_selections.csv"
    metric_path = out / "q1_quantile_metrics.csv"
    crossing_path = out / "q1_quantile_crossings.csv"
    slice_path = out / "q1_fixed_slice_metrics.csv"
    oof.to_csv(oof_path, index=False, float_format="%.17g")
    tuning.to_csv(tuning_path, index=False, float_format="%.17g")
    metrics.to_csv(metric_path, index=False, float_format="%.17g")
    crossings.to_csv(crossing_path, index=False, float_format="%.17g")
    fixed_slices.to_csv(slice_path, index=False, float_format="%.17g")

    seasons = sorted(pd.to_numeric(oof["season"], errors="raise").astype(int).unique().tolist())
    summary = {
        "status": "COMPLETE",
        "program": "LEVLINE_ATS_NEXTGEN",
        "phase": 2,
        "stage": "A_Q1",
        "candidate_id": CANDIDATE_ID,
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
        "historical_evidence_class": "development_non_pristine",
        "repeated_use_disclosure": REPEATED_USE_DISCLOSURE,
        "gate_canonical_game_keyed_sha256": actual_gate_sha,
        "outer_target_seasons": seasons,
        "outer_oof_rows": int(len(oof)),
        "q1_repair_or_rescue_performed": False,
        "ats_hit_rate_used_for_selection": False,
        "roi_used_for_selection": False,
        "fixed_slice_definitions_frozen_pre_result": True,
        "outputs": {
            "outer_oof": str(oof_path),
            "inner_alpha_selections": str(tuning_path),
            "quantile_metrics": str(metric_path),
            "quantile_crossings": str(crossing_path),
            "fixed_slice_metrics": str(slice_path),
        },
    }
    summary_path = out / "q1_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/ats_nextgen/q1")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()

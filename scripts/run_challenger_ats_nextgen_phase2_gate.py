from __future__ import annotations

"""Materialize the ATS NextGen Phase-2 pre-result gate on 2015-2025 data.

This runner is deliberately pre-fit. It builds the frozen chronology-safe matchup
state, applies the Phase-2 grading/provenance gate, and writes only gate evidence.
It must not fit Q1/Q2/Q3 or inspect completed 2026 outcomes.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import (
    HISTORICAL_END,
    TRAINING_FLOOR,
    build_historical_ats_gate,
    validate_gate_frame,
    write_phase2_gate_artifacts,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features


def run(
    output_dir: str = "research_outputs/ats_nextgen/phase2_opening_gate",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(config_path)

    # The research contract, not the production config, defines the V1 training
    # floor and historical outcome ceiling. Never request 2026 in this runner.
    seasons = list(range(TRAINING_FLOOR, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    advanced_start = max(TRAINING_FLOOR, int(cfg["data"]["advanced_start_season"]))
    bundle = load_advanced_data(bundle, range(advanced_start, HISTORICAL_END + 1))

    schedules = bundle.schedules.copy()
    schedule_season = pd.to_numeric(schedules["season"], errors="coerce")
    if schedule_season.isna().any() or schedule_season.gt(HISTORICAL_END).any():
        raise RuntimeError("Phase-2 opening runner received post-2025 schedule rows")
    if schedule_season.lt(TRAINING_FLOOR).any():
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
        raise RuntimeError("Phase-2 opening matchup frame crossed the 2025 outcome boundary")
    games = games[game_season.ge(TRAINING_FLOOR)].copy()

    gate = build_historical_ats_gate(games)
    validate_gate_frame(gate)
    manifest = write_phase2_gate_artifacts(
        gate,
        out,
        source_description=(
            "2015-2025 nflverse core/advanced data loaded through repository data functions; "
            "pregame Elo and shifted alpha-0.15 matchup features built through existing "
            "chronology-safe feature pipeline; historical schedule market fields retain "
            "exact-horizon-opaque evidence semantics"
        ),
    )

    summary = {
        "status": "PASS",
        "program": "LEVLINE_ATS_NEXTGEN",
        "phase": 2,
        "stage": "pre_result_pre_fit_gate",
        "candidate_fitting_performed": False,
        "candidate_performance_generated": False,
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "requested_seasons": seasons,
        "gate_rows": manifest["artifact"]["rows"],
        "eligible_rows": manifest["eligibility"]["ats_eligible_rows"],
        "push_rows": manifest["eligibility"]["push_rows"],
        "gate_raw_sha256": manifest["artifact"]["raw_sha256"],
        "gate_canonical_game_keyed_sha256": manifest["artifact"][
            "canonical_game_keyed_sha256"
        ],
        "market_evidence_class": manifest["market_evidence_class"],
    }
    (out / "phase2_opening_gate_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="research_outputs/ats_nextgen/phase2_opening_gate",
    )
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()

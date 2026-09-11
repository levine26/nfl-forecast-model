from __future__ import annotations

"""Execute FTN-PROCESS-01 exactly as preregistered through the 2025 season.

The runner is research-only. It never loads completed 2026 outcomes, never writes a
production artifact, and writes all evidence beneath research_outputs/ftn_process_v1.
"""

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import numpy as np
import pandas as pd

from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.market import add_vig_free_market_prob
from research.ftn_process_v1 import (
    EXPERIMENT_ID,
    aggregate_ftn_team_games,
    build_matchup_features,
    join_ftn_to_pbp,
    run_preregistered_evaluation,
)

SEASONS = (2022, 2023, 2024, 2025)
GAME_TYPES = ("REG", "POST")
PREREG_PATH = Path("research/ftn_process_prereg_v1.json")
DEFAULT_OUTPUT = Path("research_outputs/ftn_process_v1")


def _pandas(frame: Any) -> pd.DataFrame:
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _runtime_versions() -> dict[str, str]:
    packages = (
        "nflreadpy",
        "pandas",
        "numpy",
        "scikit-learn",
        "pyarrow",
        "polars",
    )
    return {name: metadata.version(name) for name in packages}


def prepare_schedule_frames(schedules: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate chronology identity from market-benchmark eligibility.

    The preregistration allows any prior REG/POST FTN team-game whose timing and
    ``date_pulled`` constraints pass to contribute lagged state. Historical market
    probability is only required for target games entering the benchmark/evaluation
    sample. Conflating those domains can orphan legitimate source-history games merely
    because their schedule moneyline is missing.
    """

    required = {
        "game_id",
        "season",
        "week",
        "game_type",
        "gameday",
        "gametime",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "home_moneyline",
        "away_moneyline",
    }
    missing = required - set(schedules.columns)
    if missing:
        raise RuntimeError(f"FTN-PROCESS-01 schedule missing required fields: {sorted(missing)}")

    season = pd.to_numeric(schedules["season"], errors="coerce")
    schedule_scope = schedules[
        season.isin(SEASONS) & schedules["game_type"].isin(GAME_TYPES)
    ].copy()
    if schedule_scope.empty:
        raise RuntimeError("FTN-PROCESS-01 has no 2022-2025 REG/POST schedule identity rows")
    if schedule_scope["game_id"].astype(str).duplicated().any():
        raise RuntimeError("FTN-PROCESS-01 schedule scope contains duplicate game_id")

    benchmark = add_vig_free_market_prob(schedule_scope.copy())
    games = benchmark[
        benchmark["home_score"].notna()
        & benchmark["away_score"].notna()
        & benchmark["market_home_prob"].notna()
    ].copy()
    if games.empty:
        raise RuntimeError("FTN-PROCESS-01 has no completed 2022-2025 market benchmark games")
    if pd.to_numeric(games["season"], errors="coerce").ge(2026).any():
        raise RuntimeError("FTN-PROCESS-01 historical game frame contains 2026 rows")
    return schedule_scope, games


def _load_inputs(
    config_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = load_config(config_path)
    bundle = load_core_data(SEASONS, cfg["data"]["cache_dir"])
    ftn = _pandas(nfl.load_ftn_charting(SEASONS))
    if not isinstance(ftn, pd.DataFrame) or ftn.empty:
        raise RuntimeError("FTN-PROCESS-01 received no FTN charting rows")

    pbp_season = pd.to_numeric(bundle.pbp.get("season"), errors="coerce")
    if pbp_season.dropna().ge(2026).any():
        raise RuntimeError("FTN-PROCESS-01 core PBP unexpectedly contains 2026 rows")

    schedule_scope, games = prepare_schedule_frames(bundle.schedules.copy())
    return ftn, bundle.pbp.copy(), schedule_scope, games


def run(
    config_path: str = "config/model.yaml",
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    bootstrap_replicates: int = 5000,
) -> dict[str, Any]:
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("FTN-PROCESS-01 preregistration identity mismatch")
    if prereg.get("status") != "PREREGISTERED_NOT_RUN":
        raise RuntimeError("FTN-PROCESS-01 preregistration must remain frozen before execution")

    ftn, pbp, schedule_scope, games = _load_inputs(config_path)
    joined, source_audit = join_ftn_to_pbp(ftn, pbp)
    team_games = aggregate_ftn_team_games(joined, schedule_scope)
    features = build_matchup_features(games, team_games)
    evaluation = run_preregistered_evaluation(
        features,
        bootstrap_replicates=bootstrap_replicates,
    )
    predictions = evaluation.pop("predictions")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.csv"
    report_path = output_dir / "report.json"
    manifest_path = output_dir / "run_manifest.json"

    predictions.to_csv(predictions_path, index=False)
    report = {
        **evaluation,
        "source_audit": source_audit,
        "preregistration_sha256": _sha256(PREREG_PATH),
        "input_scope": {
            "seasons": list(SEASONS),
            "game_types": list(GAME_TYPES),
            "ftn_rows": int(len(ftn)),
            "pbp_rows": int(len(pbp)),
            "schedule_scope_games": int(len(schedule_scope)),
            "completed_market_games": int(len(games)),
            "team_game_rows": int(len(team_games)),
            "feature_rows": int(len(features)),
        },
    }
    report_path.write_text(
        json.dumps(_json_safe(report), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "source_sha": os.environ.get("GITHUB_SHA"),
        "preregistration": str(PREREG_PATH),
        "preregistration_sha256": _sha256(PREREG_PATH),
        "runtime_versions": _runtime_versions(),
        "artifacts": {
            "report": str(report_path),
            "predictions": str(predictions_path),
        },
    }
    manifest_path.write_text(
        json.dumps(_json_safe(manifest), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    args = parser.parse_args()
    report = run(
        config_path=args.config,
        output_dir=Path(args.output_dir),
        bootstrap_replicates=int(args.bootstrap_replicates),
    )
    print(json.dumps(_json_safe(report), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()

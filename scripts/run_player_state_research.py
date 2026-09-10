from __future__ import annotations

"""Build cached research-only chronological player state for v0.9A."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
import sklearn

from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.player_state_research import (
    build_game_player_features,
    build_player_state,
    v09a_feature_columns,
)

HISTORICAL_END = 2025


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "research_outputs/player_state",
) -> dict:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, HISTORICAL_END + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    bundle = load_advanced_data(bundle, seasons)

    build = build_player_state(
        bundle.pbp,
        snap_counts=bundle.snap_counts,
        depth_charts=bundle.depth_charts,
        ngs_passing=bundle.ngs_passing,
    )
    features = build_game_player_features(bundle.schedules, build.team_pregame_state)
    feature_cols = v09a_feature_columns(features)
    if not feature_cols:
        raise RuntimeError("No v0.9A player-state matchup features were built")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    build.player_game_roles.to_parquet(out / "player_game_roles.parquet", index=False)
    build.player_state.to_parquet(out / "chronological_player_state.parquet", index=False)
    build.team_pregame_state.to_parquet(out / "team_pregame_state.parquet", index=False)
    feature_export_cols = [
        column
        for column in ["game_id", "season", "week", "gameday", "away_team", "home_team", *feature_cols]
        if column in features.columns
    ]
    features[feature_export_cols].to_parquet(out / "v09a_game_features.parquet", index=False)
    (out / "player_data_audit.json").write_text(json.dumps(build.audit, indent=2), encoding="utf-8")

    max_pbp = int(pd.to_numeric(bundle.pbp.season, errors="coerce").max())
    missing_rates = {
        column: float(pd.to_numeric(features[column], errors="coerce").isna().mean())
        for column in feature_cols
    }
    manifest = {
        "status": "healthy",
        "mode": "research_only",
        "candidate_version": "0.9A-player-state-foundation",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "data_seasons": seasons,
        "maximum_pbp_season": max_pbp,
        "feature_set_hash": _feature_hash(feature_cols),
        "feature_columns": feature_cols,
        "random_seed": int(cfg["model"]["random_state"]),
        "games": int(len(features)),
        "player_game_role_observations": int(len(build.player_game_roles)),
        "chronological_player_state_rows": int(len(build.player_state)),
        "play_observations": int(len(bundle.pbp)),
        "exclusions": {
            "2026_outcomes": 0,
            "current_game_snaps": 0,
            "future_depth_charts": 0,
            "fuzzy_player_identity_matches": 0
        },
        "missing_data_rates": missing_rates,
        "package_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__
        },
        "production_outputs_modified": 0,
        "promotion_authorized": False
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": manifest, "audit": build.audit}, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="research_outputs/player_state")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()

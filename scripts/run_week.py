from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from nfl_forecast.pipeline import run, write_outputs
from nfl_forecast.diagnostics import (
    build_postgame_autopsies,
    build_team_profiles,
    build_weekly_brief,
    write_json,
)
from nfl_forecast.fst_diagnostics import build_fst_movement_attribution
from nfl_forecast.accountability_publication import build_history_scoreboard
from nfl_forecast.power_editorial_v2 import build_power_editorial_v2


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _preserve_leaderboard_schema(artifacts) -> None:
    """Keep the historical `Final Ensemble` row key stable for public/CI consumers.

    Its status text identifies it as the legacy 75/25 comparator. The official live
    winner-probability strategy is carried independently on each prediction row.
    """
    leaderboard = getattr(artifacts, "leaderboard", None)
    if leaderboard is None or leaderboard.empty or "model" not in leaderboard.columns:
        return
    mask = leaderboard["model"].eq("Legacy Final Ensemble")
    leaderboard.loc[mask, "model"] = "Final Ensemble"


def publish_accountability_feeds(artifacts, output_dir: str = "outputs") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if getattr(artifacts, "calibration", None) is not None:
        artifacts.calibration.to_csv(out / "calibration.csv", index=False)

    confidence_cols = [
        "game_id", "away_team", "home_team", "pick", "final_home_prob",
        "legacy_final_home_prob", "fst_pure_home_prob", "market_home_prob",
        "confidence", "legacy_confidence", "confidence_index", "confidence_conviction",
        "confidence_agreement", "confidence_consistency", "model_disagreement",
        "consistency_flag", "legacy_consistency_flag", "confidence_diagnostic_scope",
        "final_probability_strategy", "fst_artifact_id", "prediction_timestamp_utc",
    ]
    available = [c for c in confidence_cols if c in artifacts.predictions.columns]
    artifacts.predictions[available].to_csv(out / "confidence_diagnostics.csv", index=False)

    run_history = _read_csv(out / "run_history.csv")
    movement = build_fst_movement_attribution(run_history)
    movement.to_csv(out / "movement_attribution.csv", index=False)

    profiles = build_team_profiles(artifacts.power_ratings, artifacts.predictions)
    profiles.to_csv(out / "team_profiles.csv", index=False)

    brief = build_weekly_brief(artifacts.predictions, movement)
    write_json(out / "weekly_brief.json", brief)

    official = _read_csv(out / "prediction_history.csv")
    autopsies = build_postgame_autopsies(official)
    write_json(out / "postgame_autopsies.json", autopsies)

    # Publication-first accountability feeds. These summarize existing outputs;
    # they do not create new model inputs or change any locked forecast.
    published_power = _read_csv(out / "power_ratings.csv")
    write_json(out / "power_editorial.json", build_power_editorial_v2(published_power))
    write_json(out / "history_scoreboard.json", build_history_scoreboard(official))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--snapshot", choices=["EARLY","FINAL"], default="EARLY")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    artifacts = run(args.config, args.season, args.snapshot)
    _preserve_leaderboard_schema(artifacts)
    write_outputs(artifacts, "outputs")
    publish_accountability_feeds(artifacts, "outputs")
    print(artifacts.predictions[["away_team","home_team","final_home_prob","pick","expected_margin","expected_total","confidence"]].to_string(index=False))


if __name__ == "__main__":
    main()

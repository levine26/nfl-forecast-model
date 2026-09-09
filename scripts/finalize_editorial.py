from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.editorial_finalize import finalize_previews
from nfl_forecast.media_context import add_media_context, apply_source_first_reads


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    previews_path = out / "game_previews.json"
    evidence_path = out / "contextual_evidence.json"
    status_path = out / "context_source_status.json"
    previews = json.loads(previews_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    status = json.loads(status_path.read_text()) if status_path.exists() else {}

    season_values = pd.to_numeric(predictions.get("season"), errors="coerce").dropna()
    week_values = pd.to_numeric(predictions.get("week"), errors="coerce").dropna()
    season = int(season_values.iloc[0]) if not season_values.empty else 2026
    week = int(week_values.iloc[0]) if not week_values.empty else 0

    # Last-stage reporting pass: current media/reporting chooses the public story
    # angle while every numerical LevLine value remains untouched.
    evidence, media_status = add_media_context(
        predictions=predictions,
        evidence=evidence,
        season=season,
        week=week,
    )
    previews = apply_source_first_reads(previews, evidence, predictions)
    status["media_reporting"] = media_status
    status["editorial_finalizer"] = finalize_previews(predictions, previews, evidence)

    previews_path.write_text(json.dumps(previews, indent=2, sort_keys=True) + "\n")
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

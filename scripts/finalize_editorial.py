from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.editorial_finalize import finalize_previews
from nfl_forecast.media_context import fetch_media_context
from nfl_forecast.media_editorial import rewrite_reads_with_media


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

    # Editorial only: discover fresh public reporting and use it to choose/write the
    # Read before the final uniqueness gate. This runs after every quantitative and
    # contextual enrichment step, and no media value is passed back into LevLine.
    media, media_status = fetch_media_context(predictions, timeout=8)
    previews = rewrite_reads_with_media(previews, predictions, evidence, media)
    status["media_reporting"] = media_status
    status["editorial_finalizer"] = finalize_previews(predictions, previews, evidence)

    previews_path.write_text(json.dumps(previews, indent=2, sort_keys=True) + "\n")
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

    for game_id in sorted(previews):
        preview = previews[game_id]
        read = str((preview.get("paragraphs") or [""])[0])
        sources = ", ".join(
            str(item.get("source_name") or "") for item in (preview.get("reported_sources") or [])
        )
        print(f"FINAL READ {game_id} | media={bool((preview.get('editorial_voice') or {}).get('media_led'))} | sources={sources} | {read}")


if __name__ == "__main__":
    main()

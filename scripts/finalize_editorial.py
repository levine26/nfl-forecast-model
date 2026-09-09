from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads
from nfl_forecast.editorial_finalize import finalize_previews
from nfl_forecast.media_context import fetch_media_context
from nfl_forecast.media_editorial import rewrite_reads_with_media


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument(
        "--skip-copilot",
        action="store_true",
        help="Refresh deterministic current reporting without applying an older Copilot artifact.",
    )
    args = parser.parse_args()
    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    previews_path = out / "game_previews.json"
    evidence_path = out / "contextual_evidence.json"
    status_path = out / "context_source_status.json"
    previews = json.loads(previews_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    status = json.loads(status_path.read_text()) if status_path.exists() else {}

    # Deterministic fail-safe: discover/filter current reporting and build a source-first
    # Read. This layer remains available even if Copilot is unavailable or invalid.
    media, media_status = fetch_media_context(predictions, timeout=8)
    previews = rewrite_reads_with_media(previews, predictions, evidence, media)
    status["media_reporting"] = media_status

    # Primary human-synthesis layer: only a separately validated Copilot artifact may
    # supersede the deterministic fallback. The media-writer uses --skip-copilot first
    # so its prompt is always built from freshly discovered reporting, not old prose.
    if args.skip_copilot:
        copilot_status = {"status": "skipped_for_fresh_research", "games_applied": 0}
    else:
        previews, copilot_status = apply_copilot_reads(
            previews=previews,
            predictions=predictions,
            path=out / "copilot_media_reads.json",
        )
    status["copilot_media"] = copilot_status

    # Always run publication QA on the final text, regardless of which writer supplied it.
    status["editorial_finalizer"] = finalize_previews(predictions, previews, evidence)

    previews_path.write_text(json.dumps(previews, indent=2, sort_keys=True) + "\n")
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

    for game_id in sorted(previews):
        preview = previews[game_id]
        read = str((preview.get("paragraphs") or [""])[0])
        sources = ", ".join(
            str(item.get("source_name") or "") for item in (preview.get("reported_sources") or [])
        )
        voice = preview.get("editorial_voice") or {}
        print(
            f"FINAL READ {game_id} | media={bool(voice.get('media_led'))} "
            f"| copilot={bool(voice.get('copilot_researched'))} | sources={sources} | {read}"
        )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads
from nfl_forecast.editorial_finalize import finalize_previews
from nfl_forecast.media_context import fetch_media_context
from nfl_forecast.media_editorial import rewrite_reads_with_media


_GENERIC_VISIBLE_TITLE_SIGNALS = (
    "preview",
    "predictions",
    "prediction",
    "picks",
    "how to watch",
    "what to watch",
    "sizing up",
    "power rankings",
    "week 1 matchup",
    "week one matchup",
    "starting lineup",
)


def _title_key(item: dict) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(item.get("title") or "").lower()).strip()


def _is_generic_visible_title(item: dict) -> bool:
    title = _title_key(item)
    return any(signal in title for signal in _GENERIC_VISIBLE_TITLE_SIGNALS)


def _display_media(media: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], dict[str, int]]:
    counts = Counter(
        key
        for items in media.values()
        for item in items
        if (key := _title_key(item))
    )
    out: dict[str, list[dict]] = {}
    generic_rejected = 0
    cross_game_rejected = 0

    for game_id, items in media.items():
        candidates = []
        for item in items:
            key = _title_key(item)
            if not key:
                continue
            if counts[key] > 1:
                cross_game_rejected += 1
                continue
            if _is_generic_visible_title(item):
                generic_rejected += 1
                continue
            candidates.append(item)

        def rank(item: dict) -> tuple[bool, bool, float]:
            meta = item.get("metadata") or {}
            try:
                score = float(meta.get("editorial_score") or meta.get("source_priority") or 0)
            except Exception:
                score = 0.0
            return (
                bool(meta.get("trusted_source")),
                bool(meta.get("substantive")),
                score,
            )

        candidates.sort(key=rank, reverse=True)
        if candidates:
            out[game_id] = candidates

    return out, {
        "games_with_display_reporting": len(out),
        "generic_titles_rejected": generic_rejected,
        "cross_game_titles_rejected": cross_game_rejected,
    }


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

    media, media_status = fetch_media_context(predictions, timeout=8)
    display_media, display_status = _display_media(media)
    media_status.update(display_status)
    previews = rewrite_reads_with_media(previews, predictions, evidence, display_media)
    status["media_reporting"] = media_status

    if args.skip_copilot:
        copilot_status = {"status": "skipped_for_fresh_research", "games_applied": 0}
    else:
        previews, copilot_status = apply_copilot_reads(
            previews=previews,
            predictions=predictions,
            path=out / "copilot_media_reads.json",
        )
    status["copilot_media"] = copilot_status

    status["editorial_finalizer"] = finalize_previews(predictions, previews, evidence)

    previews_path.write_text(json.dumps(previews, indent=2, sort_keys=True) + "\n")
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

    for game_id in sorted(previews):
        preview = previews[game_id]
        paragraphs = [str(value) for value in (preview.get("paragraphs") or [])]
        paragraph1 = paragraphs[0] if paragraphs else ""
        paragraph2 = paragraphs[1] if len(paragraphs) > 1 else ""
        sources = ", ".join(
            str(item.get("source_name") or "") for item in (preview.get("reported_sources") or [])
        )
        voice = preview.get("editorial_voice") or {}
        print(
            f"FINAL READ {game_id} | media={bool(voice.get('media_led'))} "
            f"| copilot={bool(voice.get('copilot_researched'))} | sources={sources} "
            f"| P1={paragraph1} | P2={paragraph2}"
        )


if __name__ == "__main__":
    main()

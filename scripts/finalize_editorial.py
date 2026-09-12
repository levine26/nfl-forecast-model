from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

import pandas as pd

from nfl_forecast.copilot_media import apply_copilot_reads
from nfl_forecast.editorial_finalize import finalize_previews
from nfl_forecast.editorial_model_read import render_model_paragraph
from nfl_forecast.editorial_provider_fallback import merge_current_run_provider_status
from nfl_forecast.editorial_text_safety import sanitize_public_evidence, sanitize_preview_text
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


def _fallback_context(preview: dict, pick: str, opponent: str) -> str:
    for factor in preview.get("key_factors") or []:
        if isinstance(factor, dict):
            title = re.sub(r"\s+", " ", str(factor.get("title") or "")).strip()
            if title:
                return f"Football context: {title}"
    case = re.sub(r"\s+", " ", str(preview.get("case_for_pick") or "")).strip()
    return f"Football context: {case or f'{pick} execution against {opponent}'}"


def _canonicalize_fallback_model_paragraphs(previews: dict, predictions: pd.DataFrame) -> dict:
    """Make deterministic fallback Reads obey the same LevLine 3.0 public semantics."""
    rows = {str(row.get("game_id")): row for _, row in predictions.iterrows()}
    for game_id, preview in previews.items():
        row = rows.get(str(game_id))
        if row is None or not isinstance(preview, dict):
            continue
        paragraphs = [str(value) for value in (preview.get("paragraphs") or [])]
        paragraph1 = paragraphs[0] if paragraphs else ""
        pick = str(row.get("pick"))
        opponent = str(row.get("away_team")) if pick == str(row.get("home_team")) else str(row.get("home_team"))
        paragraph2 = render_model_paragraph(row, _fallback_context(preview, pick, opponent))
        preview["paragraphs"] = [paragraph1, paragraph2]
    return previews


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument(
        "--skip-copilot",
        action="store_true",
        help="Refresh deterministic current reporting without applying an older provider artifact.",
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

    # A real Groq production job owns a runner-local provider ledger in /tmp. It
    # survives `git reset --hard origin/main` during deterministic-output reconciliation
    # and also clears stale prior-run fallback flags when the current run succeeds.
    status = merge_current_run_provider_status(
        status,
        predictions.get("game_id", pd.Series(dtype=str)).astype(str),
    )

    # Repair only mechanical punctuation artifacts at the public boundary. Facts,
    # standardized injury/status language, and all model values remain unchanged.
    evidence, evidence_repairs = sanitize_public_evidence(evidence)
    previews, preview_repairs_before = sanitize_preview_text(previews)

    media, media_status = fetch_media_context(predictions, timeout=8)
    display_media, display_status = _display_media(media)
    media_status.update(display_status)
    previews = rewrite_reads_with_media(previews, predictions, evidence, display_media)
    previews = _canonicalize_fallback_model_paragraphs(previews, predictions)
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

    # Provider prose and deterministic rewrites pass through the same punctuation-only
    # boundary before uniqueness/editorial QA, so malformed source fragments cannot leak
    # into either the Read or Key Developments.
    previews, preview_repairs_after = sanitize_preview_text(previews)
    status["editorial_text_safety"] = {
        "status": "healthy",
        "evidence_repairs": int(evidence_repairs),
        "preview_repairs": int(preview_repairs_before + preview_repairs_after),
        "guardrail": "Punctuation-only publication repair; source facts, standardized status language, and LevLine model values are unchanged.",
    }

    status["editorial_finalizer"] = finalize_previews(predictions, previews, evidence)

    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
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
            f"| provider_researched={bool(voice.get('copilot_researched'))} | sources={sources} "
            f"| P1={paragraph1} | P2={paragraph2}"
        )


if __name__ == "__main__":
    main()
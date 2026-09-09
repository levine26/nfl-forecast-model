from __future__ import annotations

"""Apply pre-validated Copilot-written Reads without touching LevLine math."""

from pathlib import Path
import json
from typing import Any

import pandas as pd


def load_copilot_reads(path: str | Path) -> dict[str, dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return {}
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        return {}
    games = payload.get("games") if isinstance(payload, dict) else None
    return games if isinstance(games, dict) else {}


def apply_copilot_reads(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    path: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Overlay only already-validated source-backed prose; numerical fields are untouched."""
    generated = load_copilot_reads(path)
    if not generated:
        return previews, {"status": "unavailable", "games_applied": 0}

    expected = set(predictions.get("game_id", pd.Series(dtype=str)).astype(str))
    applied = 0
    for game_id, preview in previews.items():
        if str(game_id) not in expected:
            continue
        entry = generated.get(str(game_id))
        if not isinstance(entry, dict):
            continue
        headline = str(entry.get("headline") or "").strip()
        read = str(entry.get("read") or "").strip()
        sources = entry.get("sources") or []
        if not headline or not read or not isinstance(sources, list) or not sources:
            continue

        paragraphs = list(preview.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = read
        else:
            paragraphs = [read]
        preview["headline"] = headline
        preview["paragraphs"] = paragraphs
        preview["reported_sources"] = [
            {
                "title": str(source.get("title") or ""),
                "source_name": str(source.get("name") or ""),
                "source_url": str(source.get("url") or ""),
                "as_of": entry.get("generated_utc"),
            }
            for source in sources[:6]
            if isinstance(source, dict) and source.get("url")
        ]
        voice = dict(preview.get("editorial_voice") or {})
        voice.update({
            "media_led": True,
            "reporting_first": True,
            "copilot_researched": True,
            "game_specific": True,
            "fallback_templates_used": False,
        })
        preview["editorial_voice"] = voice
        preview["editorial_version"] = "media-copilot-v1"
        preview["source_first_guardrail"] = (
            "Copilot synthesized approved current reporting for the public Read; "
            "LevLine numerical outputs were not modified."
        )
        applied += 1

    status = "healthy" if applied == len(expected) and expected else "partial" if applied else "unavailable"
    return previews, {"status": status, "games_applied": applied, "file": str(path)}

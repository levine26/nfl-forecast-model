from __future__ import annotations

"""Apply pre-validated Copilot-written media Reads without touching LevLine math."""

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
    evidence: dict[str, list[dict[str, Any]]],
    predictions: pd.DataFrame,
    path: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Use validated Copilot Reads when no curated human Read already exists."""
    generated = load_copilot_reads(path)
    if not generated:
        return previews, evidence, {"status":"unavailable", "games_applied":0}

    rows = {str(row.game_id): row for _, row in predictions.iterrows()} if "game_id" in predictions.columns else {}
    applied = 0
    for game_id, preview in previews.items():
        # Hand-curated reporting remains the highest-confidence editorial source.
        if bool((preview.get("editorial_voice") or {}).get("source_first_reporting")):
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
        preview["reporting_sources"] = [
            {
                "title": str(source.get("title") or ""),
                "source_name": str(source.get("name") or ""),
                "source_url": str(source.get("url") or ""),
                "as_of": entry.get("generated_utc"),
            }
            for source in sources[:5]
            if isinstance(source, dict) and source.get("url")
        ]
        voice = dict(preview.get("editorial_voice") or {})
        voice.update({
            "evidence_led": True,
            "game_specific": True,
            "slate_aware": True,
            "source_first_reporting": True,
            "copilot_researched": True,
            "lead_source": "GitHub Copilot source synthesis",
        })
        preview["editorial_voice"] = voice
        spine = dict(preview.get("story_spine") or {})
        spine.update({"primary_family":"media_reporting", "primary_title":headline, "primary_mode":"reported_storyline"})
        preview["story_spine"] = spine
        preview["editorial_version"] = "source-first-copilot-v1"

        items = evidence.setdefault(str(game_id), [])
        for source in sources[:5]:
            if not isinstance(source, dict) or not source.get("url"):
                continue
            items.append({
                "category":"reporting",
                "title":str(source.get("title") or headline),
                "summary":"Source used by the Copilot editorial synthesis.",
                "strength":"Strong",
                "source_name":str(source.get("name") or "Current reporting"),
                "source_url":str(source.get("url")),
                "as_of":entry.get("generated_utc"),
                "side":"neutral",
                "relevance":"Current reporting used for editorial synthesis only.",
                "metadata":{
                    "family":"media_reporting",
                    "copilot_researched":True,
                    "promoted_to_model":False,
                    "provenance_grade":"B",
                },
            })
        if str(game_id) in rows:
            preview["source_first_guardrail"] = "Copilot researched and wrote the public Read; LevLine numerical outputs were not modified."
        applied += 1

    return previews, evidence, {"status":"healthy", "games_applied":applied, "file":str(path)}

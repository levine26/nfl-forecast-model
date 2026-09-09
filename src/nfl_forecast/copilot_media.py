from __future__ import annotations

"""Apply pre-validated Copilot-written Reads without touching LevLine math."""

from pathlib import Path
import json
from typing import Any

import pandas as pd


MAX_COPILOT_AGE_HOURS = 6.0
NEW_REPORT_GRACE_MINUTES = 5.0


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


def _utc(value: Any) -> pd.Timestamp | None:
    try:
        ts = pd.to_datetime(value, utc=True, errors="raise")
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts)


def _fresh_enough(entry: dict[str, Any], preview: dict[str, Any], now: pd.Timestamp) -> tuple[bool, str]:
    generated = _utc(entry.get("generated_utc"))
    if generated is None:
        return False, "missing_generated_timestamp"
    age_hours = max(0.0, (now - generated).total_seconds() / 3600.0)
    if age_hours > MAX_COPILOT_AGE_HOURS:
        return False, "copilot_artifact_stale"

    newest_report: pd.Timestamp | None = None
    for source in preview.get("reported_sources") or []:
        if not isinstance(source, dict):
            continue
        stamp = _utc(source.get("as_of"))
        if stamp is not None and (newest_report is None or stamp > newest_report):
            newest_report = stamp
    if newest_report is not None:
        grace = pd.Timedelta(minutes=NEW_REPORT_GRACE_MINUTES)
        if newest_report > generated + grace:
            return False, "newer_reporting_available"
    return True, "fresh"


def apply_copilot_reads(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    path: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Overlay only fresh, validated source-backed prose; numerical fields are untouched."""
    generated = load_copilot_reads(path)
    if not generated:
        return previews, {"status": "unavailable", "games_applied": 0, "skipped": {}}

    expected = set(predictions.get("game_id", pd.Series(dtype=str)).astype(str))
    now = pd.Timestamp.now(tz="UTC")
    applied = 0
    skipped: dict[str, str] = {}
    for game_id, preview in previews.items():
        if str(game_id) not in expected:
            continue
        entry = generated.get(str(game_id))
        if not isinstance(entry, dict):
            skipped[str(game_id)] = "missing_entry"
            continue
        headline = str(entry.get("headline") or "").strip()
        read = str(entry.get("read") or "").strip()
        sources = entry.get("sources") or []
        if not headline or not read or not isinstance(sources, list) or not sources:
            skipped[str(game_id)] = "invalid_entry"
            continue
        is_fresh, reason = _fresh_enough(entry, preview, now)
        if not is_fresh:
            skipped[str(game_id)] = reason
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
    return previews, {
        "status": status,
        "games_applied": applied,
        "games_expected": len(expected),
        "skipped": skipped,
        "file": str(path),
        "max_age_hours": MAX_COPILOT_AGE_HOURS,
        "new_report_grace_minutes": NEW_REPORT_GRACE_MINUTES,
    }

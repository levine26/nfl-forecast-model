from __future__ import annotations

"""Apply pre-validated provider matchup Reads without touching LevLine math.

A successful provider entry owns the human headline and matchup paragraph for that
specific game. Later deterministic context refreshes may add fresher supporting facts,
but they must not silently erase already-validated provider prose. Numerical LevLine
copy is always regenerated from the current canonical prediction row so keeping the
human Read cannot freeze an old probability, line, score, pick, or lock state.
"""

from pathlib import Path
import json
import re
from typing import Any

import pandas as pd

from nfl_forecast.editorial_model_read import render_model_paragraph

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


def _provider_state(entry: dict[str, Any], preview: dict[str, Any], now: pd.Timestamp) -> tuple[bool, str]:
    """Return hard usability plus a non-blocking freshness advisory.

    Provider age and newer deterministic reporting are diagnostic signals, not reasons
    to throw away a successful game-specific Read. The Groq/ChatGPT publication path
    already validates the researched entry before it can enter this artifact. Current
    Key Developments remain available alongside the Read, and paragraph 2 is rebuilt
    from the current canonical forecast every time this overlay is applied.
    """
    generated = _utc(entry.get("generated_utc"))
    if generated is None:
        return False, "missing_generated_timestamp"

    age_hours = max(0.0, (now - generated).total_seconds() / 3600.0)
    if age_hours > MAX_COPILOT_AGE_HOURS:
        return True, "provider_artifact_older_than_refresh_window"

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
            return True, "newer_reporting_available"
    return True, "fresh"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_provider_rationale(value: Any) -> str:
    text = _clean(value)
    words = re.findall(r"\b[\w'-]+\b", text)
    prohibited = re.compile(
        r"\d|%|\blevline\b|\bf-st\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b",
        flags=re.I,
    )
    if 12 <= len(words) <= 55 and not prohibited.search(text):
        return text if text[-1:] in ".!?" else text + "."
    return ""


def _rationale_from_artifact(entry: dict[str, Any], preview: dict[str, Any]) -> str:
    """Recover only qualitative provider rationale; all numbers are re-rendered."""
    direct = _safe_provider_rationale(entry.get("model_rationale"))
    if direct:
        return direct

    paragraph2 = _clean(entry.get("paragraph2"))
    if paragraph2:
        without_pick = re.sub(r"\s*The pick:.*$", "", paragraph2, flags=re.I).strip()
        candidates = re.split(r"(?<=[.!?])\s+", without_pick)
        for sentence in reversed(candidates):
            safe = _safe_provider_rationale(sentence)
            if safe:
                return safe

    for factor in preview.get("key_factors") or []:
        if isinstance(factor, dict):
            title = _clean(factor.get("title"))
            if title:
                return f"Football context: {title}."
    case = _clean(preview.get("case_for_pick"))
    if case:
        return f"Football context: {case}."
    headline = _clean(entry.get("headline"))
    return f"Football context: {headline}." if headline else ""


def apply_copilot_reads(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    path: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Overlay validated human prose per game; regenerate current LevLine facts."""
    generated = load_copilot_reads(path)
    if not generated:
        return previews, {"status": "unavailable", "games_applied": 0, "skipped": {}, "advisories": {}}

    expected = set(predictions.get("game_id", pd.Series(dtype=str)).astype(str))
    rows = {
        str(row.get("game_id")): row
        for _, row in predictions.iterrows()
        if str(row.get("game_id") or "").strip()
    }
    now = pd.Timestamp.now(tz="UTC")
    applied = 0
    skipped: dict[str, str] = {}
    advisories: dict[str, str] = {}

    for game_id, preview in previews.items():
        gid = str(game_id)
        if gid not in expected:
            continue
        entry = generated.get(gid)
        if not isinstance(entry, dict):
            skipped[gid] = "missing_entry"
            continue

        headline = _clean(entry.get("headline"))
        paragraph1 = _clean(entry.get("paragraph1"))
        sources = entry.get("sources") or []
        if not headline or not paragraph1 or not isinstance(sources, list) or not sources:
            skipped[gid] = "invalid_entry"
            continue

        usable, state = _provider_state(entry, preview, now)
        if not usable:
            skipped[gid] = state
            continue
        if state != "fresh":
            advisories[gid] = state

        row = rows.get(gid)
        if row is None:
            skipped[gid] = "missing_prediction_row"
            continue
        rationale = _rationale_from_artifact(entry, preview)
        paragraph2 = render_model_paragraph(row, rationale)

        # Provider owns the human Read only for this game. Deterministic paragraph 2
        # is rebuilt from the canonical row so current forecast semantics always win.
        preview["headline"] = headline
        preview["paragraphs"] = [paragraph1, paragraph2]
        preview["reported_sources"] = [
            {
                "title": _clean(source.get("title")),
                "source_name": _clean(source.get("name")),
                "source_url": _clean(source.get("url")),
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
            "two_paragraph_contract": True,
            "explicit_model_explanation": True,
            "explicit_final_pick": True,
            "fallback_templates_used": False,
            "provider_freshness_advisory": None if state == "fresh" else state,
        })
        preview["editorial_voice"] = voice
        preview["editorial_version"] = "matchup-model-pick-provider-v2"
        preview["source_first_guardrail"] = (
            "Validated provider reporting owns the human matchup Read for this game; "
            "current LevLine numbers are deterministically regenerated and provider prose never modifies the forecast."
        )
        applied += 1

    status = "healthy" if applied == len(expected) and expected else "partial" if applied else "unavailable"
    return previews, {
        "status": status,
        "games_applied": applied,
        "games_expected": len(expected),
        "skipped": skipped,
        "advisories": advisories,
        "file": str(path),
        "max_age_hours": MAX_COPILOT_AGE_HOURS,
        "new_report_grace_minutes": NEW_REPORT_GRACE_MINUTES,
        "authority_policy": "validated_provider_human_read_persists_per_game; canonical_model_paragraph_is_regenerated",
    }

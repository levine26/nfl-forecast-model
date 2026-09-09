from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any

import nflreadpy as nfl
import pandas as pd


NGS_SOURCE_URL = "https://nflreadr.nflverse.com/articles/dictionary_nextgen_stats.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def _norm_name(value: Any) -> str:
    return re.sub(r"[^a-z]", "", str(value or "").lower())


def _to_pandas(frame: Any) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    try:
        return frame.to_pandas()
    except Exception:
        return pd.DataFrame()


def _quarterbacks_from_evidence(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Return (side, QB name) from already verified current-starter history evidence."""
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        meta = item.get("metadata") or {}
        if meta.get("family") != "qb_opponent_history":
            continue
        title = str(item.get("title") or "")
        if " vs " not in title:
            continue
        name = title.split(" vs ", 1)[0].strip()
        side = str(item.get("side") or "neutral")
        key = (side, _norm_name(name))
        if name and key not in seen:
            found.append((side, name)); seen.add(key)
    return found


def _season_summary(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    work = frame.copy()
    if "season" in work.columns:
        work["season"] = pd.to_numeric(work["season"], errors="coerce")
        work = work[work["season"].eq(season)]
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")]
    if "week" in work.columns:
        work["week"] = pd.to_numeric(work["week"], errors="coerce")
        summary = work[work["week"].eq(0)]
        if not summary.empty:
            return summary
        work = work.sort_values("week").groupby("player_display_name", as_index=False).tail(1)
    return work


def build_ngs_qb_evidence(
    evidence: dict[str, list[dict[str, Any]]],
    season: int,
    frame: Any | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Add prior-season NFL Next Gen Stats profiles for current starting QBs.

    This layer is explanatory only. It does not create a LevLine input and it
    never blocks publication when NGS is missing or a player fails its minimum
    attempt threshold.
    """
    as_of = _now()
    latest_complete = season - 1
    try:
        raw = frame if frame is not None else nfl.load_nextgen_stats(latest_complete, stat_type="passing")
        ngs = _season_summary(_to_pandas(raw), latest_complete)
    except Exception as exc:
        return evidence, {
            "status": "degraded",
            "as_of": as_of,
            "season": latest_complete,
            "source": "NFL Next Gen Stats via nflverse",
            "source_url": NGS_SOURCE_URL,
            "error": str(exc)[:220],
            "guardrail": "NGS is optional explanatory context and never blocks or numerically changes LevLine.",
        }

    if ngs.empty or "player_display_name" not in ngs.columns:
        return evidence, {
            "status": "degraded",
            "as_of": as_of,
            "season": latest_complete,
            "source": "NFL Next Gen Stats via nflverse",
            "source_url": NGS_SOURCE_URL,
            "error": "No usable passing summary rows",
            "guardrail": "NGS is optional explanatory context and never blocks or numerically changes LevLine.",
        }

    ngs["_name"] = ngs["player_display_name"].map(_norm_name)
    added = 0
    matched = 0
    for game_id, items in evidence.items():
        qbs = _quarterbacks_from_evidence(items)
        if not qbs:
            continue
        titles = {str(item.get("title")) for item in items}
        for side, name in qbs:
            match = ngs[ngs["_name"].eq(_norm_name(name))]
            if match.empty:
                continue
            row = match.iloc[-1]
            attempts = int(_num(row.get("attempts")) or 0)
            if attempts < 50:
                continue
            matched += 1
            ttt = _num(row.get("avg_time_to_throw"))
            cpoe = _num(row.get("completion_percentage_above_expectation"))
            adot = _num(row.get("avg_intended_air_yards"))
            agg = _num(row.get("aggressiveness"))
            metrics = []
            if ttt is not None:
                metrics.append(f"{ttt:.2f}s average time to throw")
            if cpoe is not None:
                metrics.append(f"{cpoe:+.1f} completion percentage points over expectation")
            if adot is not None:
                metrics.append(f"{adot:.1f} average intended air yards")
            if agg is not None:
                metrics.append(f"{agg:.1f}% of attempts into tight windows")
            if len(metrics) < 2:
                continue
            title = f"{name}: Next Gen passing profile"
            if title in titles:
                continue
            summary = (
                f"NFL Next Gen Stats' {latest_complete} regular-season profile for {name}, over {attempts} attempts: "
                + "; ".join(metrics)
                + ". These tracking metrics describe how he played, not a standalone prediction for this matchup."
            )
            items.append({
                "category": "personnel",
                "title": title,
                "summary": summary,
                "strength": "Strong" if attempts >= 300 else "Moderate",
                "source_name": "NFL Next Gen Stats via nflverse",
                "source_url": NGS_SOURCE_URL,
                "as_of": as_of,
                "side": side,
                "sample_size": attempts,
                "relevance": "Prior-season tracking profile for the current starting quarterback",
                "promoted_to_model": False,
                "metadata": {
                    "family": "ngs_qb_profile",
                    "season": latest_complete,
                    "attempts": attempts,
                    "avg_time_to_throw": ttt,
                    "cpoe": cpoe,
                    "avg_intended_air_yards": adot,
                    "aggressiveness": agg,
                    "provenance_grade": "B",
                },
            })
            titles.add(title); added += 1

    return evidence, {
        "status": "healthy",
        "as_of": as_of,
        "season": latest_complete,
        "source": "NFL Next Gen Stats via nflverse",
        "source_url": NGS_SOURCE_URL,
        "qb_profiles_matched": matched,
        "evidence_items_added": added,
        "guardrail": "NGS adds player-level explanatory context only; it does not alter LevLine without separate chronological validation.",
    }

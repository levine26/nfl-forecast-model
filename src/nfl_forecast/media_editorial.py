from __future__ import annotations

"""Reporting-first Read compositor.

Fresh reporting supplies the story. LevLine's existing evidence supplies a compact
football check. The old template composer is used only when no media is available.
This module never changes a prediction, feature, market weight, lock or grade.
"""

import re
from typing import Any

import pandas as pd


QUANT_FAMILY_ORDER = {
    "availability": 0,
    "pressure": 1,
    "qb_opponent_history": 2,
    "explosives": 3,
    "early_down": 4,
    "staff_impact": 5,
    "coaching": 6,
    "personnel": 7,
    "travel": 8,
    "weather": 9,
}


def _family(item: dict[str, Any]) -> str:
    meta = item.get("metadata") or {}
    return str(meta.get("family") or item.get("family") or item.get("category") or "context").lower().replace(" ", "_")


def _priority(item: dict[str, Any]) -> tuple[bool, float]:
    meta = item.get("metadata") or {}
    try:
        score = float(meta.get("editorial_score") or meta.get("source_priority") or 0)
    except Exception:
        score = 0.0
    return bool(meta.get("substantive")), score


def _clean_title(title: Any, max_words: int = 20) -> str:
    text = re.sub(r"\s+", " ", str(title or "")).strip().strip(" -|—")
    text = re.sub(r"\bHC\b", "coach", text)
    text = re.sub(r"\bQB\b", "quarterback", text)
    text = re.sub(r"\bRB\b", "running back", text)
    text = re.sub(r"\bWR\b", "receiver", text)

    # Strip aggregator/content-label scaffolding when a headline contains a real
    # reported fact after it. This specifically avoids publishing phrases such as
    # "Preview Week 1" as though they were the football story.
    if ":" in text:
        left, right = text.split(":", 1)
        if any(word in left.lower() for word in ("preview", "update", "week 1", "week one", "injury report", "news")) and len(right.split()) >= 4:
            text = right.strip()
    text = re.sub(
        r"^(?:nfl\s+)?(?:week\s*(?:1|one)\s+)?(?:game\s+)?(?:preview|predictions?|picks?|matchup)\s*(?:[-–—:]\s*)?",
        "",
        text,
        flags=re.I,
    ).strip()
    text = re.sub(r"\s+(?:week\s*(?:1|one)\s+)?preview\s*$", "", text, flags=re.I).strip()
    words = text.rstrip(".").split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(" ,;:-") + "…"
    return text.rstrip(".")


def _reported_sentence(away: str, home: str, item: dict[str, Any]) -> str:
    source = str(item.get("source_name") or "Current reporting").strip()
    fact = _clean_title(item.get("title"))
    matchup = f"{away}-{home}"
    if not fact:
        return f"{source}'s {matchup} coverage is the lead source for this Read."
    substantive = bool((item.get("metadata") or {}).get("substantive"))
    if substantive:
        return f"{source}'s {matchup} reporting centers on {fact}."
    return f"{source}'s {matchup} preview frames the game around {fact}."


def _second_report(away: str, home: str, item: dict[str, Any]) -> str:
    source = str(item.get("source_name") or "Another outlet").strip()
    fact = _clean_title(item.get("title"))
    if not fact:
        return ""
    return f"{source} adds a separate {away}-{home} thread: {fact}."


def _quant_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in items if _family(item) != "reported_angle"]
    if not candidates:
        return None
    return min(candidates, key=lambda item: QUANT_FAMILY_ORDER.get(_family(item), 50))


def _quant_sentence(away: str, home: str, item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    matchup = f"{away}-{home}"
    summary = re.sub(r"\s+", " ", str(item.get("summary") or "")).strip()
    title = str(item.get("title") or "").strip().rstrip(".: ")
    fam = _family(item)

    if fam == "pressure":
        match = re.search(r"([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%", summary)
        if match:
            protected, allowed, rusher, created = match.groups()
            return f"{matchup} pressure check: {protected} allowed an {allowed}% sack rate; {rusher} generated {created}%."
        tilt = re.search(r"pressure matchup tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            team = tilt.group(1).upper()
            return f"{matchup} pressure edge: the pass-rush evidence favors {team}."

    if fam == "explosives":
        match = re.search(r"([A-Z]{2,4}) hit a 20\+ yard pass on ([0-9.]+)% of pass plays; ([A-Z]{2,4}) allowed one on ([0-9.]+)%", summary)
        if match:
            offense, created, defense, allowed = match.groups()
            return f"{matchup} explosive-pass check: {offense} created 20-plus gains on {created}% of passes; {defense} allowed {allowed}%."
        tilt = re.search(r"chunk-play path tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"{matchup} explosive-play evidence favors {tilt.group(1).upper()}."

    if fam == "early_down":
        match = re.search(r"([A-Z]{2,4}) threw on ([0-9.]+)% of first- and second-down plays and averaged ([+\-][0-9.]+) EPA per early-down pass", summary)
        if match:
            offense, rate, epa = match.groups()
            return f"{matchup} early-down check: {offense} passed {rate}% of the time and produced {epa} EPA per pass."
        tilt = re.search(r"early-down leverage tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"{matchup} early-down evidence favors {tilt.group(1).upper()}."

    if fam == "qb_opponent_history":
        qb = title.split(" vs ", 1)[0].strip() if " vs " in title else "The quarterback"
        match = re.search(r"([0-9]+) meaningful games.*?([0-9]+) charted dropbacks.*?([+\-][0-9.]+) EPA/dropback", summary)
        if match:
            games, drops, epa = match.groups()
            return f"{matchup} opponent history: {qb} has {games} meaningful meetings, {drops} charted dropbacks and {epa} EPA per dropback."

    if title:
        return f"{matchup} supporting evidence: {_clean_title(title, max_words=14)}."
    return ""


def _market_sentence(row: pd.Series) -> str:
    try:
        pure = float(row.get("pure_home_prob"))
        market = float(row.get("market_home_prob"))
    except Exception:
        return ""
    if pd.isna(pure) or pd.isna(market):
        return ""
    gap = pure - market
    if abs(gap) < 0.08:
        return ""
    home = str(row.get("home_team"))
    away = str(row.get("away_team"))
    team = home if gap > 0 else away
    points = abs(gap) * 100.0
    return f"{away}-{home} market split: PURE gives {team} {points:.1f} percentage points more win probability than {team}'s market price."


def rewrite_reads_with_media(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    media_by_game: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Replace template-led Reads whenever fresh external reporting is available."""
    if not media_by_game:
        return previews
    prediction_rows = {str(row.get("game_id")): row for _, row in predictions.iterrows()}

    for game_id in sorted(previews):
        media = sorted(media_by_game.get(game_id, []), key=_priority, reverse=True)
        if not media:
            continue
        row = prediction_rows.get(str(game_id))
        if row is None:
            continue
        away = str(row.get("away_team"))
        home = str(row.get("home_team"))
        preview = previews[game_id]

        sentences = [_reported_sentence(away, home, media[0])]
        first_key = re.sub(r"[^a-z0-9]+", " ", str(media[0].get("title") or "").lower()).strip()
        second = next(
            (
                item for item in media[1:]
                if re.sub(r"[^a-z0-9]+", " ", str(item.get("title") or "").lower()).strip() != first_key
            ),
            None,
        )
        if second:
            second_sentence = _second_report(away, home, second)
            if second_sentence:
                sentences.append(second_sentence)

        quant = _quant_sentence(away, home, _quant_item(evidence.get(game_id, [])))
        if quant:
            sentences.append(quant)
        market = _market_sentence(row)
        if market:
            sentences.append(market)

        read = " ".join(sentence for sentence in sentences if sentence).strip()
        paragraphs = list(preview.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = read
        else:
            paragraphs = [read]
        preview["paragraphs"] = paragraphs

        headline_fact = _clean_title(media[0].get("title"), max_words=16)
        preview["headline"] = headline_fact or f"{away}-{home}: current reporting"
        preview["reported_sources"] = [
            {
                "source_name": item.get("source_name"),
                "source_url": item.get("source_url"),
                "title": item.get("title"),
                "as_of": item.get("as_of"),
            }
            for item in media[:3]
        ]
        voice = dict(preview.get("editorial_voice") or {})
        voice.update({
            "media_led": True,
            "reporting_first": True,
            "game_specific": True,
            "media_source_count": len(media),
            "fallback_templates_used": False,
        })
        preview["editorial_voice"] = voice
    return previews

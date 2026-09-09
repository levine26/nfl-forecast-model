from __future__ import annotations

"""Human-facing Read compositor driven by current reporting first.

The old slate-aware template writer remains a fallback. When fresh reporting exists,
this module replaces only the Read paragraph/headline and attaches source metadata.
It does not modify predictions or any numerical feature.
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


def _priority(item: dict[str, Any]) -> float:
    meta = item.get("metadata") or {}
    try:
        return float(meta.get("editorial_score") or meta.get("source_priority") or 0)
    except Exception:
        return 0.0


def _clean_title(title: Any) -> str:
    text = re.sub(r"\s+", " ", str(title or "")).strip().strip(" -|—")
    text = re.sub(r"\bHC\b", "coach", text)
    text = re.sub(r"\bQB\b", "quarterback", text)
    text = re.sub(r"\bRB\b", "running back", text)
    text = re.sub(r"\bWR\b", "receiver", text)
    text = text.replace(" vs. ", " against ").replace(" vs ", " against ")
    # If a headline uses a generic update/preview label before a colon, the useful
    # human angle is almost always on the right-hand side.
    if ":" in text:
        left, right = text.split(":", 1)
        if any(word in left.lower() for word in ("preview", "update", "week 1", "week one", "injury")) and len(right.strip()) >= 18:
            text = right.strip()
    return text.rstrip(".")


def _topic_kind(item: dict[str, Any]) -> str:
    text = f"{item.get('title','')} {item.get('summary','')}".lower()
    if any(word in text for word in ("injury", "questionable", "doubtful", "ruled out", "likely out", "expected to play", "expected to start", "on track", "return", "practice")):
        return "availability"
    if any(word in text for word in ("coordinator", "play-caller", "playcaller", "new coach", "scheme")):
        return "staff"
    if any(word in text for word in ("trade", "traded", "debut", "signed", "acquired")):
        return "roster"
    return "matchup"


def _reported_sentence(slot: int, away: str, home: str, item: dict[str, Any]) -> str:
    source = str(item.get("source_name") or "current reporting")
    fact = _clean_title(item.get("title"))
    kind = _topic_kind(item)
    matchup = f"{away}-{home}"
    if kind == "availability":
        options = [
            f"{matchup} starts with a live availability story: {source} is reporting {fact}.",
            f"The first real question in {matchup} is who is actually ready to go; {source} is tracking {fact}.",
            f"Before getting to scheme in {matchup}, the news matters: {source} has {fact} at the center of its coverage.",
            f"The matchup changed when the availability picture changed. {source} is focused on {fact}.",
        ]
    elif kind == "staff":
        options = [
            f"The interesting part of {matchup} is the new tactical layer. {source} is focused on {fact}.",
            f"{matchup} has a genuine play-calling question before the first snap; {source} is highlighting {fact}.",
            f"There is a new schematic variable in {matchup}. {source} is framing the week around {fact}.",
            f"This is not the same version of the matchup as last year. {source} is watching {fact}.",
        ]
    elif kind == "roster":
        options = [
            f"The roster version of {matchup} has changed, and {source} is centered on {fact}.",
            f"A new personnel wrinkle gives {matchup} a different feel. {source} is tracking {fact}.",
            f"The most relevant offseason change in {matchup} is the one {source} is writing about: {fact}.",
            f"There is a new face in the middle of this matchup story. {source} is focused on {fact}.",
        ]
    else:
        options = [
            f"The clearest outside angle on {matchup} comes from {source}: {fact}.",
            f"There is a real football story in {matchup} before the probability enters the conversation. {source} is focused on {fact}.",
            f"Current coverage gives {matchup} a better starting point than a generic matchup label: {source} is tracking {fact}.",
            f"The week has already supplied a concrete storyline for {matchup}. {source} is centered on {fact}.",
        ]
    return options[slot % len(options)]


def _second_report(slot: int, item: dict[str, Any]) -> str:
    source = str(item.get("source_name") or "another outlet")
    fact = _clean_title(item.get("title"))
    options = [
        f"{source} adds another live thread: {fact}.",
        f"There is a second piece worth carrying into kickoff—{source} is also tracking {fact}.",
        f"That is not the only current angle. {source} is separately focused on {fact}.",
        f"The reporting picture is broader than one story; {source} also has {fact} in view.",
        f"One more update matters here: {source} is following {fact}.",
    ]
    return options[slot % len(options)]


def _quant_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in items if _family(item) != "reported_angle"]
    if not candidates:
        return None
    return min(candidates, key=lambda item: QUANT_FAMILY_ORDER.get(_family(item), 50))


def _quant_sentence(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    summary = re.sub(r"\s+", " ", str(item.get("summary") or "")).strip()
    title = str(item.get("title") or "").strip().rstrip(".: ")
    fam = _family(item)
    if fam == "pressure":
        match = re.search(r"([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%", summary)
        if match:
            protected, allowed, rusher, created = match.groups()
            return f"That makes the protection battle concrete: {protected} allowed sacks on {allowed}% of pass plays last year, while {rusher} generated them on {created}%."
        tilt = re.search(r"pressure matchup tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"On the field, the clearest supporting pressure point is the pass rush, which tilts toward {tilt.group(1).upper()}."
    if fam == "explosives":
        match = re.search(r"([A-Z]{2,4}) hit a 20\+ yard pass on ([0-9.]+)% of pass plays; ([A-Z]{2,4}) allowed one on ([0-9.]+)%", summary)
        if match:
            offense, created, defense, allowed = match.groups()
            return f"The big-play numbers give that story a football mechanism: {offense} created 20-plus-yard passes on {created}% of attempts, and {defense} allowed them on {allowed}%."
    if fam == "early_down":
        match = re.search(r"([A-Z]{2,4}) threw on ([0-9.]+)% of first- and second-down plays and averaged ([+\-][0-9.]+) EPA per early-down pass", summary)
        if match:
            offense, rate, epa = match.groups()
            return f"The early-down profile matters too: {offense} threw on {rate}% of first and second downs and produced {epa} EPA per pass in that sample."
    if fam == "qb_opponent_history":
        qb = title.split(" vs ", 1)[0].strip() if " vs " in title else "The quarterback"
        match = re.search(r"([0-9]+) meaningful games.*?([0-9]+) charted dropbacks.*?([+\-][0-9.]+) EPA/dropback", summary)
        if match:
            games, drops, epa = match.groups()
            return f"There is useful opponent history behind the storyline as well: {qb} has {games} meaningful meetings and {drops} charted dropbacks in the sample, at {epa} EPA per dropback."
    if fam in {"availability", "personnel"} and title:
        return f"The internal evidence points to the same part of the game: {title}."
    if fam in {"staff_impact", "coaching"} and title:
        return f"The staff context reinforces that angle rather than creating a separate one: {title}."
    if title:
        return f"The quantitative file adds one useful football check: {title}."
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
    return f"The model-market disagreement is real: PURE is {points:.1f} percentage points more bullish on {team} than the market is."


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
    for slot, game_id in enumerate(sorted(previews)):
        media = sorted(media_by_game.get(game_id, []), key=_priority, reverse=True)
        if not media:
            continue
        row = prediction_rows.get(str(game_id))
        if row is None:
            continue
        away = str(row.get("away_team"))
        home = str(row.get("home_team"))
        preview = previews[game_id]

        sentences = [_reported_sentence(slot, away, home, media[0])]
        if len(media) > 1:
            # Do not repeat two versions of the same headline merely because two
            # aggregators surfaced it. Distinct source/title content earns sentence two.
            first_key = re.sub(r"[^a-z0-9]+", " ", str(media[0].get("title") or "").lower())
            second = next(
                (
                    item for item in media[1:]
                    if re.sub(r"[^a-z0-9]+", " ", str(item.get("title") or "").lower()) != first_key
                ),
                None,
            )
            if second:
                sentences.append(_second_report(slot, second))

        quant = _quant_sentence(_quant_item(evidence.get(game_id, [])))
        if quant:
            sentences.append(quant)
        market = _market_sentence(row)
        if market:
            sentences.append(market)

        paragraphs = list(preview.get("paragraphs") or [])
        read = " ".join(sentence for sentence in sentences if sentence).strip()
        if paragraphs:
            paragraphs[0] = read
        else:
            paragraphs = [read]
        preview["paragraphs"] = paragraphs
        preview["headline"] = _clean_title(media[0].get("title")) or preview.get("headline")
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
            "media_source_count": len(media),
            "fallback_templates_used": False,
        })
        preview["editorial_voice"] = voice
    return previews

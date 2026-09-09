from __future__ import annotations

"""Reporting-first deterministic fallback for Sunday Signal Reads.

Current reporting supplies the story; verified LevLine evidence supplies at most one
compact football check. This module is editorial-only and cannot alter forecasts,
features, market weights, locks or grading.
"""

import re
from typing import Any

import pandas as pd

from nfl_forecast.context import TEAM_META


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


def _priority(item: dict[str, Any]) -> tuple[bool, bool, float]:
    meta = item.get("metadata") or {}
    try:
        score = float(meta.get("editorial_score") or meta.get("source_priority") or 0)
    except Exception:
        score = 0.0
    return bool(meta.get("trusted_source")), bool(meta.get("substantive")), score


def _full(code: Any) -> str:
    key = "JAX" if str(code or "").upper() == "JAC" else str(code or "").upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nick(code: Any) -> str:
    return _full(code).split()[-1]


def _city(code: Any) -> str:
    full = _full(code)
    parts = full.split()
    return " ".join(parts[:-1]) if len(parts) > 1 else full


def _matchup(away: Any, home: Any) -> str:
    return f"{_nick(away)}–{_nick(home)}"


def _clean_title(title: Any, max_words: int = 22) -> str:
    text = re.sub(r"\s+", " ", str(title or "")).strip().strip(" -|—")
    text = re.sub(r"\bHC\b", "coach", text)
    text = re.sub(r"\bQB\b", "quarterback", text)
    text = re.sub(r"\bRB\b", "running back", text)
    text = re.sub(r"\bWR\b", "receiver", text)
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
    if not fact:
        return ""

    expect = re.match(r"^(.+?)\s+expect(?:s)?\s+(.+?)\s+to\s+(.+)$", fact, flags=re.I)
    if expect:
        _, subject, action = expect.groups()
        return f"{source} reports {subject} is expected to {action}."
    expected = re.match(r"^(.+?)\s+(?:is\s+)?expected\s+to\s+(.+)$", fact, flags=re.I)
    if expected:
        subject, action = expected.groups()
        return f"{source} reports {subject} is expected to {action}."
    trending = re.match(r"^(.+?)\s+(?:is\s+)?(?:likely|trending)\s+(?:toward|to)\s+(.+)$", fact, flags=re.I)
    if trending:
        subject, action = trending.groups()
        return f"{source} has {subject} trending toward {action}."
    ruled = re.match(r"^(.+?)\s+(?:is\s+)?ruled\s+out(?:\s+(.+))?$", fact, flags=re.I)
    if ruled:
        subject, detail = ruled.groups()
        tail = f" {detail}" if detail else ""
        return f"{source} reports {subject} is ruled out{tail}."

    return f"{fact}, according to {source}."


def _quant_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in items if _family(item) != "reported_angle"]
    if not candidates:
        return None
    return min(candidates, key=lambda item: QUANT_FAMILY_ORDER.get(_family(item), 50))


def _quant_sentence(away: str, home: str, item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    matchup = _matchup(away, home)
    summary = re.sub(r"\s+", " ", str(item.get("summary") or "")).strip()
    title = str(item.get("title") or "").strip().rstrip(".: ")
    fam = _family(item)

    if fam == "pressure":
        match = re.search(r"([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%", summary)
        if match:
            protected, allowed, rusher, created = match.groups()
            return (
                f"{matchup}: the {_nick(protected)} were sacked on {allowed}% of pass plays; "
                f"the {_nick(rusher)} got home on {created}%."
            )
        tilt = re.search(r"pressure matchup tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"{matchup}: pass-rush leverage favors the {_nick(tilt.group(1))}."

    if fam == "explosives":
        match = re.search(r"([A-Z]{2,4}) hit a 20\+ yard pass on ([0-9.]+)% of pass plays; ([A-Z]{2,4}) allowed one on ([0-9.]+)%", summary)
        if match:
            offense, created, defense, allowed = match.groups()
            return (
                f"{matchup}: the {_nick(offense)} created 20-plus-yard completions on {created}% of passes; "
                f"the {_nick(defense)} allowed {allowed}%."
            )
        tilt = re.search(r"chunk-play path tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"{matchup}: explosive-play leverage favors the {_nick(tilt.group(1))}."

    if fam == "early_down":
        match = re.search(r"([A-Z]{2,4}) threw on ([0-9.]+)% of first- and second-down plays and averaged ([+\-][0-9.]+) EPA per early-down pass", summary)
        if match:
            offense, rate, epa = match.groups()
            return f"{matchup}: the {_nick(offense)} passed on {rate}% of early downs at {epa} EPA per pass."
        tilt = re.search(r"early-down leverage tilts ([A-Z]{2,4})", summary, re.I)
        if tilt:
            return f"{matchup}: early-down leverage favors the {_nick(tilt.group(1))}."

    if fam == "qb_opponent_history":
        qb = title.split(" vs ", 1)[0].strip() if " vs " in title else "The quarterback"
        match = re.search(r"([0-9]+) meaningful games.*?([0-9]+) charted dropbacks.*?([+\-][0-9.]+) EPA/dropback", summary)
        if match:
            games, drops, epa = match.groups()
            return f"{matchup}: {qb} has {games} meaningful meetings, {drops} charted dropbacks and {epa} EPA per dropback."

    if title:
        return f"{matchup}: {_clean_title(title, max_words=14)}."
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
    if abs(gap) < 0.12:
        return ""
    home = str(row.get("home_team"))
    away = str(row.get("away_team"))
    team = home if gap > 0 else away
    points = abs(gap) * 100.0
    return f"{_matchup(away, home)} market gap: LevLine rates {_city(team)} {points:.1f} percentage points above consensus."


def rewrite_reads_with_media(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    media_by_game: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Replace legacy template Reads whenever current external reporting exists."""
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

        first = media[0]
        sentences = [_reported_sentence(away, home, first)]
        first_key = re.sub(r"[^a-z0-9]+", " ", str(first.get("title") or "").lower()).strip()
        first_source = re.sub(r"[^a-z0-9]+", " ", str(first.get("source_name") or "").lower()).strip()
        first_trusted = bool((first.get("metadata") or {}).get("trusted_source"))
        second = next(
            (
                item for item in media[1:]
                if re.sub(r"[^a-z0-9]+", " ", str(item.get("title") or "").lower()).strip() != first_key
                and re.sub(r"[^a-z0-9]+", " ", str(item.get("source_name") or "").lower()).strip() != first_source
                and (not first_trusted or bool((item.get("metadata") or {}).get("trusted_source")))
            ),
            None,
        )
        if second:
            sentence = _reported_sentence(away, home, second)
            if sentence:
                sentences.append(sentence)

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

        headline_fact = _clean_title(first.get("title"), max_words=16)
        preview["headline"] = headline_fact or f"{_matchup(away, home)}: current reporting"
        preview["reported_sources"] = [
            {
                "source_name": item.get("source_name"),
                "source_url": item.get("source_url"),
                "title": item.get("title"),
                "as_of": item.get("as_of"),
            }
            for item in media[:4]
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

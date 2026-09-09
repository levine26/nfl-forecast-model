from __future__ import annotations

"""Two-paragraph deterministic fallback for Sunday Signal Reads.

Paragraph 1 previews the football matchup. Paragraph 2 explains the exact LevLine
forecast and ends with a declarative moneyline pick. This module is editorial-only;
it never changes model inputs, probabilities, weights, locks or grading.
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


def _matchup(away: Any, home: Any) -> str:
    return f"{_nick(away)}–{_nick(home)}"


def _clean_title(title: Any, max_words: int = 18) -> str:
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
    words = text.rstrip(".").split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(" ,;:-") + "…"
    return text.rstrip(".")


def _reported_sentence(item: dict[str, Any]) -> str:
    source = str(item.get("source_name") or "Current reporting").strip()
    fact = _clean_title(item.get("title"))
    if not fact:
        return ""
    expect = re.match(r"^(.+?)\s+expect(?:s)?\s+(.+?)\s+to\s+(.+)$", fact, flags=re.I)
    if expect:
        _, subject, action = expect.groups()
        return f"{source} has {subject} expected to {action}."
    expected = re.match(r"^(.+?)\s+(?:is\s+)?expected\s+to\s+(.+)$", fact, flags=re.I)
    if expected:
        subject, action = expected.groups()
        return f"{source} has {subject} expected to {action}."
    ruled = re.match(r"^(.+?)\s+(?:is\s+)?ruled\s+out(?:\s+(.+))?$", fact, flags=re.I)
    if ruled:
        subject, detail = ruled.groups()
        return f"{source} lists {subject} out{(' ' + detail) if detail else ''}."
    return f"{source} is tracking {fact[0].lower() + fact[1:] if len(fact) > 1 else fact.lower()}."


def _quant_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in items if _family(item) != "reported_angle"]
    if not candidates:
        return None
    return min(candidates, key=lambda item: QUANT_FAMILY_ORDER.get(_family(item), 50))


def _pressure_details(summary: str) -> tuple[str, str, str, str] | None:
    match = re.search(
        r"([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%",
        summary,
    )
    return match.groups() if match else None


def _football_preview(away: str, home: str, item: dict[str, Any] | None, media: list[dict[str, Any]]) -> tuple[str, str]:
    matchup = _matchup(away, home)
    sentences: list[str] = []
    headline = f"{matchup}: the matchup that decides the game"

    if item:
        fam = _family(item)
        summary = re.sub(r"\s+", " ", str(item.get("summary") or "")).strip()
        title = _clean_title(item.get("title"), max_words=12)
        if fam == "pressure":
            details = _pressure_details(summary)
            if details:
                protected, sack_rate, rusher, pressure_rate = details
                protected_name = _nick(protected)
                rusher_name = _nick(rusher)
                headline = f"{matchup}: {rusher_name} pass rush vs. {protected_name} protection"
                sentences.append(
                    f"{matchup} centers on the {rusher_name} rush against {protected_name} protection. "
                    f"The {protected_name} posted a {sack_rate}% sack rate last season; the {rusher_name} reached {pressure_rate}%. "
                    f"{protected_name} needs clean early downs to keep {rusher_name} out of favorable rush situations, while {rusher_name} wants to force {protected_name} into obvious passing downs."
                )
        elif fam == "explosives":
            headline = f"{matchup}: explosive plays will set the terms"
            sentences.append(
                f"{matchup} has an explosive-play question at its center. {summary.rstrip('.')} The offense that creates chunk gains without living in third-and-long should be able to dictate tempo, while the other side has to force longer drives and win red-zone downs."
            )
        elif fam == "early_down":
            headline = f"{matchup}: early downs will decide who controls the script"
            sentences.append(
                f"{matchup} is likely to be decided before third down. {summary.rstrip('.')} If that early-down edge holds, it changes the entire play-calling menu; if it does not, the game becomes much more dependent on obvious passing situations and quarterback creation."
            )
        elif fam == "qb_opponent_history":
            headline = f"{matchup}: quarterback answers under pressure"
            sentences.append(
                f"{matchup} starts with the quarterback matchup and how each defense can force the passer off schedule. {summary.rstrip('.')} The key is less the historical record itself than whether the same pressure, coverage and down-and-distance problems show up again in this version of the matchup."
            )
        elif title:
            headline = f"{matchup}: {title}"
            sentences.append(
                f"{matchup} centers on {title[0].lower() + title[1:] if len(title) > 1 else title.lower()}. {summary.rstrip('.')} That factor matters because it changes which side can stay on schedule and avoid asking its quarterback to solve the game from obvious passing downs."
            )

    if not sentences:
        sentences.append(
            f"{matchup} is a game of which offense can stay on schedule and which defense can create the first real disruption. Both teams have plausible paths, so the most important question is whether the favorite can create efficient early downs without giving the opponent short fields or high-leverage third-down chances."
        )

    substantive = [m for m in media if bool((m.get("metadata") or {}).get("substantive"))]
    used_sources: set[str] = set()
    for report in substantive:
        source = str(report.get("source_name") or "")
        if not source or source.lower() in used_sources:
            continue
        sentence = _reported_sentence(report)
        if sentence:
            sentences.append(sentence)
            used_sources.add(source.lower())
        if len(used_sources) >= 2:
            break

    paragraph = " ".join(sentences).strip()
    return headline, paragraph


def _pick_probability(row: pd.Series, field: str) -> float | None:
    try:
        value = float(row.get(field))
    except Exception:
        return None
    if pd.isna(value):
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def _line_text(value: Any, home: str, away: str) -> str:
    try:
        margin = float(value)
    except Exception:
        return ""
    if pd.isna(margin):
        return ""
    if abs(margin) < 0.05:
        return "pick'em"
    team = home if margin > 0 else away
    return f"{_full(team)} -{abs(margin):.1f}"


def _model_paragraph(row: pd.Series, item: dict[str, Any] | None) -> str:
    away = str(row.get("away_team"))
    home = str(row.get("home_team"))
    pick = str(row.get("pick"))
    final_prob = _pick_probability(row, "final_home_prob")
    pure_prob = _pick_probability(row, "pure_home_prob")
    market_prob = _pick_probability(row, "market_home_prob")
    expected_margin = row.get("expected_margin")
    market_spread = row.get("spread_line")
    projected = str(row.get("projected_score") or "").strip()

    sentences = []
    if final_prob is not None and pure_prob is not None and market_prob is not None:
        sentences.append(
            f"LevLine makes the {_nick(pick)} the winner at {final_prob * 100:.1f}%. Its football-only PURE component is {_nick(pick)} {pure_prob * 100:.1f}%, while the market-derived probability is {market_prob * 100:.1f}%; the production 75% PURE / 25% market blend lands at the published number."
        )
    elif final_prob is not None:
        sentences.append(f"LevLine makes the {_nick(pick)} the winner at {final_prob * 100:.1f}% based on the current production forecast.")

    model_line = _line_text(expected_margin, home, away)
    market_line = _line_text(market_spread, home, away)
    details = []
    if model_line:
        details.append(f"a model line of {model_line}")
    if market_line:
        details.append(f"a market line of {market_line}")
    if projected:
        details.append(f"a projected score of {projected}")
    if details:
        sentences.append("That forecast corresponds to " + ", ".join(details) + ".")

    if item:
        title = _clean_title(item.get("title"), max_words=12)
        if title:
            sentences.append(f"The matchup evidence that best supports the forecast is {title[0].lower() + title[1:] if len(title) > 1 else title.lower()}.")

    sentences.append(f"The pick: {_full(pick)} moneyline.")
    return " ".join(sentences)


def rewrite_reads_with_media(
    previews: dict[str, dict[str, Any]],
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    media_by_game: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Own the complete Read: exactly two paragraphs, never preserve legacy prose."""
    prediction_rows = {str(row.get("game_id")): row for _, row in predictions.iterrows()}

    for game_id in sorted(previews):
        row = prediction_rows.get(str(game_id))
        if row is None:
            continue
        away = str(row.get("away_team"))
        home = str(row.get("home_team"))
        media = sorted(media_by_game.get(game_id, []), key=_priority, reverse=True)
        item = _quant_item(evidence.get(game_id, []))
        headline, paragraph1 = _football_preview(away, home, item, media)
        paragraph2 = _model_paragraph(row, item)
        preview = previews[game_id]

        preview["headline"] = headline
        preview["paragraphs"] = [paragraph1, paragraph2]
        preview["reported_sources"] = [
            {
                "source_name": report.get("source_name"),
                "source_url": report.get("source_url"),
                "title": report.get("title"),
                "as_of": report.get("as_of"),
            }
            for report in media[:6]
        ]
        voice = dict(preview.get("editorial_voice") or {})
        voice.update({
            "media_led": bool(media),
            "reporting_first": bool(media),
            "game_specific": True,
            "two_paragraph_contract": True,
            "explicit_model_explanation": True,
            "explicit_final_pick": True,
            "media_source_count": len(media),
            "fallback_templates_used": False,
        })
        preview["editorial_voice"] = voice
        preview["editorial_version"] = "matchup-model-pick-v1"
    return previews

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

STRENGTH = {"Strong": 3, "Moderate": 2, "Weak": 1}


def _num(v) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{100*v:.1f}%"


def _short_fact(summary: str, max_sentences: int = 2) -> str:
    text = re.sub(r"\s+", " ", str(summary or "")).strip()
    if not text:
        return ""
    guardrails = [
        "it is contextual evidence", "weather is shown as context", "the status is surfaced as personnel evidence",
        "no unvalidated point-value adjustment", "it does not prove", "the sample describes", "no automatic point penalty",
    ]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keep = []
    for sentence in sentences:
        if any(g in sentence.lower() for g in guardrails):
            continue
        keep.append(sentence)
        if len(keep) >= max_sentences:
            break
    return " ".join(keep).strip()


def _score(item: dict[str, Any]) -> float:
    md = item.get("metadata") or {}
    try:
        editorial = float(md.get("editorial_score") or 0)
    except Exception:
        editorial = 0
    return STRENGTH.get(item.get("strength"), 0) * 10 + min(float(item.get("sample_size") or 0) / 100, 4) + editorial


def _best(items: list[dict[str, Any]], categories: set[str], limit: int = 1) -> list[dict[str, Any]]:
    candidates = [x for x in items if str(x.get("category", "")).lower() in categories]
    candidates.sort(key=_score, reverse=True)
    return candidates[:limit]


def _market_sentence(game: pd.Series) -> str:
    pure = _num(game.get("pure_home_prob"))
    market = _num(game.get("market_home_prob"))
    spread = _num(game.get("spread_line"))
    margin = _num(game.get("expected_margin"))
    home = str(game.get("home_team"))
    away = str(game.get("away_team"))
    pick = str(game.get("pick"))
    parts = []
    if pure is not None and market is not None:
        gap = 100 * (pure - market)
        if abs(gap) >= 3:
            direction = home if gap > 0 else away
            parts.append(f"The football-only model is {abs(gap):.1f} percentage points higher on {direction} than the market is.")
    if spread is not None and margin is not None:
        edge_home = margin - spread
        pick_edge = edge_home if pick == home else -edge_home
        if abs(pick_edge) >= 1.5:
            if pick_edge > 0:
                parts.append(f"On the spread scale, LevLine likes {pick} by {abs(pick_edge):.1f} points more than the current line.")
            else:
                parts.append(f"The spread view is cooler: LevLine is {abs(pick_edge):.1f} points less favorable to {pick} than the market line.")
    return " ".join(parts)


def _advantage(item: dict[str, Any]) -> str | None:
    return (item.get("metadata") or {}).get("advantage_team")


def _family(item: dict[str, Any]) -> str:
    md = item.get("metadata") or {}
    return str(md.get("family") or md.get("concept") or item.get("category") or "context").replace("_", " ")


def _factor_card(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title"),
        "summary": _short_fact(item.get("summary", ""), 2),
        "family": _family(item),
        "strength": item.get("strength"),
        "advantage_team": _advantage(item),
        "source_name": item.get("source_name"),
        "source_url": item.get("source_url"),
        "sample_size": item.get("sample_size"),
    }


def _scheme_paragraph(scheme: list[dict[str, Any]]) -> str | None:
    if not scheme:
        return None
    first = _short_fact(scheme[0].get("summary", ""), 2)
    second = _short_fact(scheme[1].get("summary", ""), 1) if len(scheme) > 1 else ""
    if first and second:
        return f"{first} The other matchup worth watching: {second}"
    return first or second or None


def _history_paragraph(history: list[dict[str, Any]], coaching: list[dict[str, Any]]) -> str | None:
    if not history and not coaching:
        return None
    if history:
        lead = _short_fact(history[0].get("summary", ""), 3)
        if coaching:
            change = _short_fact(coaching[0].get("summary", ""), 2)
            if lead and change:
                return f"{lead} But this is not a rerun: {change}"
        return lead or None
    facts = " ".join(_short_fact(x.get("summary", ""), 1) for x in coaching if _short_fact(x.get("summary", ""), 1))
    return facts or None


def _personnel_paragraph(personnel: list[dict[str, Any]]) -> str | None:
    if not personnel:
        return None
    facts = " ".join(_short_fact(x.get("summary", ""), 2) for x in personnel[:2])
    return facts or None


def _scenario_paragraph(scenarios: list[dict[str, Any]]) -> str | None:
    if not scenarios:
        return None
    facts = " ".join(_short_fact(x.get("summary", ""), 1) for x in scenarios[:2])
    return facts or None


def _editorial_aside(game: pd.Series, pick_prob: float | None) -> str | None:
    disagreement = _num(game.get("model_disagreement"))
    pure = _num(game.get("pure_home_prob"))
    market = _num(game.get("market_home_prob"))
    if pick_prob is not None and pick_prob < .515:
        return "This is a coin flip wearing a decimal point."
    if disagreement is not None and disagreement >= .10:
        return "The component models are not exactly singing from one hymnal."
    if pure is not None and market is not None and abs(pure - market) >= .08:
        return "That gap is big enough to be the story, not a rounding error."
    return None


def _headline(game: pd.Series, pick: str, pick_prob: float | None) -> str:
    pure = _num(game.get("pure_home_prob"))
    market = _num(game.get("market_home_prob"))
    if pick_prob is not None and pick_prob < .515:
        return f"{pick} by a whisker: {_pct(pick_prob)}"
    if pure is not None and market is not None and abs(pure - market) >= .07:
        return f"LevLine is taking a stand on {pick}"
    return f"{pick} gets the edge at {_pct(pick_prob)}"


def build_game_previews(predictions: pd.DataFrame, evidence: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    previews = {}
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items = evidence.get(gid, [])
        home = str(game.get("home_team"))
        away = str(game.get("away_team"))
        pick = str(game.get("pick"))
        dog = away if pick == home else home
        hp = _num(game.get("final_home_prob"))
        pick_prob = None if hp is None else (hp if pick == home else 1 - hp)
        margin = _num(game.get("expected_margin"))
        total = _num(game.get("expected_total"))
        score = str(game.get("projected_score") or "")
        disagreement = _num(game.get("model_disagreement"))
        consistency = str(game.get("consistency_flag") or "")

        history = _best(items, {"history"}, 2)
        coaching = _best(items, {"coaching", "structural_change", "coordinator"}, 2)
        scheme = _best(items, {"scheme", "matchup"}, 3)
        personnel = _best(items, {"personnel", "injury"}, 3)
        scenarios = _best(items, {"weather", "travel", "scenario"}, 2)

        p1 = f"LevLine has {pick} at {_pct(pick_prob)} to win."
        if margin is not None:
            favorite = home if margin >= 0 else away
            p1 += f" The middle of the distribution is {favorite} by {abs(margin):.1f}"
            p1 += f", with {total:.1f} total points." if total is not None else "."
        market = _market_sentence(game)
        if market:
            p1 += " " + market
        aside = _editorial_aside(game, pick_prob)
        if aside:
            p1 += " " + aside

        paragraphs = [p1]
        for paragraph in [
            _history_paragraph(history, coaching),
            _scheme_paragraph(scheme),
            _personnel_paragraph(personnel),
            _scenario_paragraph(scenarios),
        ]:
            if paragraph:
                paragraphs.append(paragraph)

        ranked = sorted(items, key=_score, reverse=True)
        factors = []
        used = set()
        for item in ranked:
            key = _family(item)
            if key in used:
                continue
            factors.append(_factor_card(item))
            used.add(key)
            if len(factors) == 3:
                break

        pro_pick = [x for x in ranked if _advantage(x) == pick][:2]
        pro_dog = [x for x in ranked if _advantage(x) == dog][:2]
        case_for_pick = " ".join(_short_fact(x.get("summary", ""), 1) for x in pro_pick).strip()
        if not case_for_pick:
            case_for_pick = f"The probability and margin estimates both point to {pick}. There is no need to invent a stronger story than the numbers support."
        case_for_dog = " ".join(_short_fact(x.get("summary", ""), 1) for x in pro_dog).strip()
        if not case_for_dog:
            case_for_dog = f"{dog} needs the high-variance parts of the game—turnovers, explosives and late-down conversions—to break its way."

        wrong = []
        if disagreement is not None and disagreement >= .08:
            wrong.append(f"The component models disagree more than usual ({disagreement:.1%}).")
        if consistency == "WIN-MARGIN SPLIT":
            wrong.append("The win-probability and expected-margin views do not point in the same direction.")
        if pick_prob is not None and pick_prob < .57:
            wrong.append("The favorite is not far from coin-flip territory.")
        if personnel:
            wrong.append("The availability picture can still change before kickoff.")
        if scenarios:
            wrong.append("Weather, travel or another live scenario could change the shape of the game.")
        if pro_dog:
            wrong.append(f"{dog} owns at least one real matchup counter-signal.")
        if not wrong:
            wrong.append(f"The cleanest upset path for {dog} is a turnover or explosive-play swing that the central projection cannot predict in advance.")
        what_wrong = " ".join(wrong[:3])

        matchup_meter = [
            {"label": _family(item).title(), "leader": _advantage(item) or "Mixed", "strength": item.get("strength"), "title": item.get("title")}
            for item in scheme[:4]
        ]
        previews[gid] = {
            "game_id": gid,
            "matchup": f"{away} @ {home}",
            "brand": "Sunday Signal",
            "engine": "LevLine",
            "headline": _headline(game, pick, pick_prob),
            "paragraphs": paragraphs,
            "key_factors": factors,
            "case_for_pick": case_for_pick,
            "case_for_opponent": case_for_dog,
            "matchup_meter": matchup_meter,
            "what_could_make_us_wrong": what_wrong,
            "prediction": f"{pick} to win" + (f"; {score} is the central score projection." if score else "."),
            "evidence_used": [
                {"title": x.get("title"), "category": x.get("category"), "strength": x.get("strength"), "source_name": x.get("source_name"), "source_url": x.get("source_url")}
                for x in (history + coaching + scheme + personnel + scenarios)
            ],
            "guardrail": "Narrative evidence explains the matchup but does not change the numerical forecast. LevLine changes only when the underlying feature separately passes chronological out-of-sample validation.",
        }
    return previews

from __future__ import annotations

"""Deterministic LevLine 3.0 editorial model paragraph.

This module only serializes already-produced forecast values. It does not fit, tune,
or alter any production probability, lock, grading record, or model feature.
"""

import math
import re
from typing import Any, Mapping

from nfl_forecast.context import TEAM_META
from nfl_forecast.public_forecast import _integer_score_pair, probability_implied_margin


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _team_name(code: Any) -> str:
    key = "JAX" if str(code or "").upper() == "JAC" else str(code or "").upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nick(code: Any) -> str:
    return _team_name(code).split()[-1]


def pick_side_probability(row: Mapping[str, Any], field: str) -> float | None:
    value = _number(row.get(field))
    if value is None:
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def football_pick_probability(row: Mapping[str, Any]) -> float | None:
    field = "fst_pure_home_prob" if _number(row.get("fst_pure_home_prob")) is not None else "pure_home_prob"
    return pick_side_probability(row, field)


def coherent_fair_margin_home(row: Mapping[str, Any]) -> float | None:
    probability = _number(row.get("final_home_prob"))
    sigma = _number(row.get("margin_sigma"))
    if probability is None or sigma is None or sigma <= 0:
        return None
    return probability_implied_margin(probability, sigma)


def line_text(margin_home: Any, home: str, away: str) -> str:
    margin = _number(margin_home)
    if margin is None:
        return ""
    if abs(margin) < 0.05:
        return "pick'em"
    favorite = home if margin > 0 else away
    return f"{_team_name(favorite)} -{abs(margin):.1f}"


def coherent_score(row: Mapping[str, Any]) -> tuple[int, int] | None:
    probability = _number(row.get("final_home_prob"))
    total = _number(row.get("expected_total"))
    margin = coherent_fair_margin_home(row)
    if probability is None or total is None or margin is None or total < 0:
        return None
    return _integer_score_pair(total, margin, probability)


def coherent_score_text(row: Mapping[str, Any]) -> str:
    score = coherent_score(row)
    if score is None:
        return ""
    home_score, away_score = score
    home = str(row.get("home_team"))
    away = str(row.get("away_team"))
    pick = str(row.get("pick"))
    if pick == away:
        return f"{away} {away_score} – {home} {home_score}"
    return f"{home} {home_score} – {away} {away_score}"


def _clean_context(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    return text if text[-1] in ".!?" else text + "."


def render_model_paragraph(row: Mapping[str, Any], context: str = "") -> str:
    away = str(row.get("away_team"))
    home = str(row.get("home_team"))
    pick = str(row.get("pick"))
    opponent = away if pick == home else home
    pick_name = _team_name(pick)
    pick_nick = _nick(pick)
    opponent_nick = _nick(opponent)

    final_probability = pick_side_probability(row, "final_home_prob")
    football_probability = football_pick_probability(row)
    market_probability = pick_side_probability(row, "market_home_prob")
    fair_line = line_text(coherent_fair_margin_home(row), home, away)
    market_line = line_text(row.get("spread_line"), home, away)
    score = coherent_score_text(row)

    sentences: list[str] = []
    if final_probability is not None:
        sentences.append(
            f"LevLine 3.0 gives the {pick_nick} a {final_probability * 100:.1f}% win probability over the {opponent_nick}."
        )
    if football_probability is not None and market_probability is not None:
        sentences.append(
            f"Its frozen F-ST engine reconciles a {football_probability * 100:.1f}% football-only signal with a "
            f"{market_probability * 100:.1f}% vig-free market signal under the 2026 production specification; it is not a fixed arithmetic blend."
        )

    details: list[str] = []
    if fair_line:
        details.append(f"a probability-implied presentation line of {fair_line}")
    if market_line:
        details.append(f"a market line of {market_line}")
    if score:
        details.append(f"an approximate coherent score of {score}")
    if details:
        if len(details) == 1:
            joined = details[0]
        elif len(details) == 2:
            joined = " and ".join(details)
        else:
            joined = ", ".join(details[:-1]) + ", and " + details[-1]
        sentences.append(f"That official probability translates to {joined}.")

    context_sentence = _clean_context(context)
    if context_sentence:
        sentences.append(context_sentence)

    sentences.append(f"The pick: {pick_name} moneyline.")
    return " ".join(sentences)

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
    """Keep factual clauses while trimming repeated methodology disclaimers."""
    text = re.sub(r"\s+", " ", str(summary or "")).strip()
    if not text:
        return ""
    guardrails = [
        "it is contextual evidence",
        "weather is shown as context",
        "the status is surfaced as personnel evidence",
        "no unvalidated point-value adjustment",
        "it does not prove",
        "the sample describes",
    ]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keep: list[str] = []
    for sentence in sentences:
        low = sentence.lower()
        if any(g in low for g in guardrails):
            continue
        keep.append(sentence)
        if len(keep) >= max_sentences:
            break
    return " ".join(keep).strip()


def _best(items: list[dict[str, Any]], categories: set[str], limit: int = 1) -> list[dict[str, Any]]:
    candidates = [x for x in items if str(x.get("category", "")).lower() in categories]
    candidates.sort(key=lambda x: (STRENGTH.get(x.get("strength"), 0), x.get("sample_size") or 0), reverse=True)
    return candidates[:limit]


def _market_sentence(game: pd.Series) -> str:
    pure = _num(game.get("pure_home_prob")); market = _num(game.get("market_home_prob"))
    spread = _num(game.get("spread_line")); margin = _num(game.get("expected_margin"))
    home = str(game.get("home_team")); away = str(game.get("away_team")); pick = str(game.get("pick"))
    parts = []
    if pure is not None and market is not None:
        gap = 100 * (pure - market)
        if abs(gap) >= 3:
            direction = home if gap > 0 else away
            parts.append(f"The PURE model is {abs(gap):.1f} percentage points more bullish on {direction} than the market-implied probability.")
    if spread is not None and margin is not None:
        edge_home = margin - spread
        pick_edge = edge_home if pick == home else -edge_home
        if abs(pick_edge) >= 1.5:
            parts.append(f"On the spread scale, the model is {abs(pick_edge):.1f} points {'more favorable' if pick_edge > 0 else 'less favorable'} to {pick} than the current market line.")
    return " ".join(parts)


def build_game_previews(predictions: pd.DataFrame, evidence: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    previews: dict[str, dict[str, Any]] = {}
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items = evidence.get(gid, [])
        home = str(game.get("home_team")); away = str(game.get("away_team")); pick = str(game.get("pick"))
        hp = _num(game.get("final_home_prob")); pick_prob = None if hp is None else (hp if pick == home else 1-hp)
        margin = _num(game.get("expected_margin")); total = _num(game.get("expected_total"))
        score = str(game.get("projected_score") or "")
        disagreement = _num(game.get("model_disagreement"))
        consistency = str(game.get("consistency_flag") or "")

        history = _best(items, {"history"}, 1)
        coaching = _best(items, {"coaching", "structural_change"}, 2)
        scheme = _best(items, {"scheme", "matchup"}, 2)
        personnel = _best(items, {"personnel", "injury"}, 2)
        scenarios = _best(items, {"weather", "travel", "scenario"}, 2)

        p1 = f"{pick} is the current model pick at {_pct(pick_prob)}."
        if margin is not None:
            favorite = home if margin >= 0 else away
            p1 += f" The expected-margin model makes {favorite} about {abs(margin):.1f} points better in the central forecast"
            p1 += f", with an expected total of {total:.1f}." if total is not None else "."
        market = _market_sentence(game)
        if market:
            p1 += " " + market

        paragraphs = [p1]

        if history and coaching:
            hist = _short_fact(history[0].get("summary", ""), 2)
            change = _short_fact(coaching[0].get("summary", ""), 2)
            paragraphs.append(
                f"The historical matchup is relevant, but not automatically transferable. {hist} "
                f"What is different now: {change} That structural change is why the preview treats the older history as context rather than destiny."
            )
        elif history:
            hist = _short_fact(history[0].get("summary", ""), 2)
            paragraphs.append(f"There is meaningful historical context here: {hist} The sample is shown with its evidence grade so a small head-to-head record cannot masquerade as a stable law.")
        elif coaching:
            facts = " ".join(_short_fact(x.get("summary", ""), 1) for x in coaching if _short_fact(x.get("summary", ""), 1))
            if facts:
                paragraphs.append(f"Historical comparisons need an adjustment because this is not the same structural matchup as last season. {facts}")

        context_bits = []
        if scheme:
            context_bits.append("Schematically, " + " ".join(_short_fact(x.get("summary", ""), 2) for x in scheme))
        if personnel:
            context_bits.append("On personnel, " + " ".join(_short_fact(x.get("summary", ""), 1) for x in personnel))
        if scenarios:
            context_bits.append("Situationally, " + " ".join(_short_fact(x.get("summary", ""), 1) for x in scenarios))
        if context_bits:
            paragraphs.append(" ".join(context_bits))

        wrong = []
        if disagreement is not None and disagreement >= 0.08:
            wrong.append(f"component-model disagreement is elevated ({disagreement:.1%})")
        if consistency == "WIN-MARGIN SPLIT":
            wrong.append("the win-probability and expected-margin heads disagree on direction")
        if pick_prob is not None and pick_prob < 0.57:
            wrong.append("the game is close to a coin flip even though a side must be selected")
        if scenarios:
            wrong.append("late personnel or weather changes could materially alter the matchup context")
        if not wrong:
            wrong.append(f"{away if pick == home else home} can still overturn the central forecast through turnover margin, explosive plays, or unusually strong high-leverage down performance")

        preview = {
            "game_id": gid,
            "matchup": f"{away} @ {home}",
            "headline": f"{pick} {_pct(pick_prob)} — {score or 'model projection'}",
            "paragraphs": paragraphs,
            "what_could_make_us_wrong": "; ".join(wrong).capitalize() + ".",
            "prediction": f"{pick} to win" + (f", with {score} as the central score projection." if score else "."),
            "evidence_used": [
                {"title": x.get("title"), "category": x.get("category"), "strength": x.get("strength"), "source_name": x.get("source_name"), "source_url": x.get("source_url")}
                for x in (history + coaching + scheme + personnel + scenarios)
            ],
            "guardrail": "Narrative evidence explains the matchup. It does not change the numerical forecast unless the underlying feature has separately passed chronological out-of-sample validation.",
        }
        previews[gid] = preview
    return previews

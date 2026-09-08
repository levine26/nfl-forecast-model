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
    guardrails = ["it is contextual evidence","weather is shown as context","the status is surfaced as personnel evidence","no unvalidated point-value adjustment","it does not prove","the sample describes","no automatic point penalty"]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keep=[]
    for sentence in sentences:
        if any(g in sentence.lower() for g in guardrails):
            continue
        keep.append(sentence)
        if len(keep)>=max_sentences:
            break
    return " ".join(keep).strip()


def _score(item: dict[str, Any]) -> float:
    md=item.get("metadata") or {}
    try: editorial=float(md.get("editorial_score") or 0)
    except Exception: editorial=0
    return STRENGTH.get(item.get("strength"),0)*10 + min(float(item.get("sample_size") or 0)/100,4)+editorial


def _best(items: list[dict[str, Any]], categories: set[str], limit: int = 1) -> list[dict[str, Any]]:
    candidates=[x for x in items if str(x.get("category","")).lower() in categories]
    candidates.sort(key=_score, reverse=True)
    return candidates[:limit]


def _market_sentence(game: pd.Series) -> str:
    pure=_num(game.get("pure_home_prob")); market=_num(game.get("market_home_prob")); spread=_num(game.get("spread_line")); margin=_num(game.get("expected_margin")); home=str(game.get("home_team")); away=str(game.get("away_team")); pick=str(game.get("pick")); parts=[]
    if pure is not None and market is not None:
        gap=100*(pure-market)
        if abs(gap)>=3:
            direction=home if gap>0 else away
            parts.append(f"LevLine's football-only probability is {abs(gap):.1f} percentage points more bullish on {direction} than the market-implied probability.")
    if spread is not None and margin is not None:
        edge_home=margin-spread; pick_edge=edge_home if pick==home else -edge_home
        if abs(pick_edge)>=1.5:
            parts.append(f"On the spread scale, LevLine is {abs(pick_edge):.1f} points {'more favorable' if pick_edge>0 else 'less favorable'} to {pick} than the current market line.")
    return " ".join(parts)


def _advantage(item: dict[str, Any]) -> str | None:
    return (item.get("metadata") or {}).get("advantage_team")


def _family(item: dict[str, Any]) -> str:
    md=item.get("metadata") or {}
    return str(md.get("family") or md.get("concept") or item.get("category") or "context").replace("_"," ")


def _factor_card(item: dict[str, Any]) -> dict[str, Any]:
    return {"title":item.get("title"),"summary":_short_fact(item.get("summary",""),2),"family":_family(item),"strength":item.get("strength"),"advantage_team":_advantage(item),"source_name":item.get("source_name"),"source_url":item.get("source_url"),"sample_size":item.get("sample_size")}


def _scheme_paragraph(scheme: list[dict[str, Any]]) -> str | None:
    if not scheme: return None
    lead=scheme[0]; fact=_short_fact(lead.get("summary",""),2); family=_family(lead)
    openers={"pressure":"The clearest tactical stress point is protection versus pressure.","explosives":"The most volatile matchup is the explosive-pass battle.","early down":"Early downs may determine who controls the script.","run front":"The run-game question starts with the structure of the defensive front.","alignment":"Formation identity is unusually relevant in this matchup.","third down":"Drive sustainability is one of the more important matchup levers.","yac":"The yards-after-catch battle is more meaningful here than it is in a typical game.","motion":"Pre-snap motion creates one of the cleaner tactical contrasts in this game.","play action":"Play action is one of the more consequential schematic intersections.","rpo":"The RPO game creates a specific conflict for the defense.","screen":"The screen game is a small but distinctive matchup lever."}
    paragraph=f"{openers.get(family,'The strongest scheme-specific signal comes from a distinct tactical interaction.')} {fact}"
    if len(scheme)>1:
        second=_short_fact(scheme[1].get("summary",""),1)
        if second: paragraph+=f" A second, different lever: {second}"
    return paragraph


def _history_paragraph(history: list[dict[str, Any]], coaching: list[dict[str, Any]]) -> str | None:
    if history and coaching:
        hist=_short_fact(history[0].get("summary",""),2); change=_short_fact(coaching[0].get("summary",""),2)
        return f"The historical matchup is relevant, but not automatically transferable. {hist} What is different now: {change} That is why Sunday Signal treats the old result as evidence, not destiny."
    if history:
        hist=_short_fact(history[0].get("summary",""),2)
        return f"There is useful historical context: {hist} The evidence grade and sample size stay visible so a small head-to-head sample cannot masquerade as a stable law."
    if coaching:
        facts=" ".join(_short_fact(x.get("summary",""),1) for x in coaching if _short_fact(x.get("summary",""),1))
        if facts: return f"Older matchup history needs to be discounted because the decision-makers changed. {facts}"
    return None


def _personnel_paragraph(personnel: list[dict[str, Any]]) -> str | None:
    if not personnel: return None
    facts=" ".join(_short_fact(x.get("summary",""),2) for x in personnel[:2])
    return f"Availability is part of the matchup rather than a generic injury list. {facts}" if facts else None


def _scenario_paragraph(scenarios: list[dict[str, Any]]) -> str | None:
    if not scenarios: return None
    facts=" ".join(_short_fact(x.get("summary",""),1) for x in scenarios[:2])
    return f"The main situational branch is this: {facts}" if facts else None


def build_game_previews(predictions: pd.DataFrame, evidence: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    previews={}
    for _,game in predictions.iterrows():
        gid=str(game.get("game_id")); items=evidence.get(gid,[]); home=str(game.get("home_team")); away=str(game.get("away_team")); pick=str(game.get("pick")); dog=away if pick==home else home
        hp=_num(game.get("final_home_prob")); pick_prob=None if hp is None else (hp if pick==home else 1-hp); margin=_num(game.get("expected_margin")); total=_num(game.get("expected_total")); score=str(game.get("projected_score") or ""); disagreement=_num(game.get("model_disagreement")); consistency=str(game.get("consistency_flag") or "")
        history=_best(items,{"history"},2); coaching=_best(items,{"coaching","structural_change","coordinator"},2); scheme=_best(items,{"scheme","matchup"},3); personnel=_best(items,{"personnel","injury"},3); scenarios=_best(items,{"weather","travel","scenario"},2)

        p1=f"LevLine makes {pick} the current pick at {_pct(pick_prob)}."
        if margin is not None:
            favorite=home if margin>=0 else away; p1+=f" The central margin is {favorite} by {abs(margin):.1f}"; p1+=f", with a projected total of {total:.1f}." if total is not None else "."
        market=_market_sentence(game)
        if market: p1+=" "+market
        paragraphs=[p1]
        for paragraph in [_scheme_paragraph(scheme),_history_paragraph(history,coaching),_personnel_paragraph(personnel),_scenario_paragraph(scenarios)]:
            if paragraph: paragraphs.append(paragraph)

        ranked=sorted(items,key=_score,reverse=True); factors=[]; used=set()
        for item in ranked:
            key=_family(item)
            if key in used: continue
            factors.append(_factor_card(item)); used.add(key)
            if len(factors)==3: break

        pro_pick=[x for x in ranked if _advantage(x)==pick][:2]; pro_dog=[x for x in ranked if _advantage(x)==dog][:2]
        case_for_pick=" ".join(_short_fact(x.get("summary",""),1) for x in pro_pick).strip() or f"LevLine's combined probability and margin heads favor {pick}; the strongest supporting evidence is shown in the matchup factors above."
        case_for_dog=" ".join(_short_fact(x.get("summary",""),1) for x in pro_dog).strip() or f"{dog}'s path is to beat the assumptions behind LevLine's efficiency edge, especially through turnovers, explosive plays, and high-leverage downs."

        wrong=[]
        if disagreement is not None and disagreement>=.08: wrong.append(f"component-model disagreement is elevated ({disagreement:.1%})")
        if consistency=="WIN-MARGIN SPLIT": wrong.append("the win-probability and expected-margin heads disagree on direction")
        if pick_prob is not None and pick_prob<.57: wrong.append("the game is close to a coin flip even though a side must be selected")
        if personnel: wrong.append("the official availability picture can still change before kickoff")
        if scenarios: wrong.append("the active weather/travel/personnel scenario could shift the game script")
        if pro_dog: wrong.append(f"{dog} owns at least one matchup-specific counter-signal in the evidence set")
        if not wrong: wrong.append(f"{dog} can still overturn the central forecast through turnover margin, explosive plays, or unusually strong high-leverage-down performance")

        matchup_meter=[{"label":_family(item).title(),"leader":_advantage(item) or "Mixed","strength":item.get("strength"),"title":item.get("title")} for item in scheme[:4]]
        previews[gid]={"game_id":gid,"matchup":f"{away} @ {home}","brand":"Sunday Signal","engine":"LevLine","headline":f"{pick} {_pct(pick_prob)} — {score or 'model projection'}","paragraphs":paragraphs,"key_factors":factors,"case_for_pick":case_for_pick,"case_for_opponent":case_for_dog,"matchup_meter":matchup_meter,"what_could_make_us_wrong":"; ".join(wrong).capitalize()+".","prediction":f"{pick} to win"+(f", with {score} as the central score projection." if score else "."),"evidence_used":[{"title":x.get("title"),"category":x.get("category"),"strength":x.get("strength"),"source_name":x.get("source_name"),"source_url":x.get("source_url")} for x in (history+coaching+scheme+personnel+scenarios)],"guardrail":"Narrative evidence explains the matchup. It does not change LevLine unless the underlying feature separately passes chronological out-of-sample validation."}
    return previews
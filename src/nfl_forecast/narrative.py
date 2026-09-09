from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import pandas as pd

STRENGTH = {"Strong": 3, "Moderate": 2, "Weak": 1}
CATEGORY_STORY_BONUS = {
    "injury": 7.0,
    "personnel": 7.0,
    "history": 4.0,
    "coaching": 4.0,
    "structural_change": 4.0,
    "coordinator": 4.0,
    "weather": 3.0,
    "travel": 2.0,
    "scenario": 2.0,
    "scheme": 0.0,
    "matchup": 0.0,
}
FAMILY_LABELS = {
    "qb_opponent_history": "QB history",
    "availability": "Availability",
    "pressure": "Pressure",
    "explosives": "Explosives",
    "early_down": "Early downs",
    "third_down": "Third down",
    "yac": "YAC",
    "run_front": "Run front",
    "alignment": "Formation",
    "motion": "Motion",
    "play_action": "Play action",
    "rpo": "RPO",
    "screen": "Screens",
    "coaching": "Staff",
    "coordinator": "Coordinator",
    "structural_change": "Staff change",
    "weather": "Weather",
    "travel": "Travel",
    "scenario": "Game state",
}


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


def _category(item: dict[str, Any]) -> str:
    return str(item.get("category") or "context").lower()


def _score(item: dict[str, Any]) -> float:
    md = item.get("metadata") or {}
    try:
        editorial = float(md.get("editorial_score") or 0)
    except Exception:
        editorial = 0
    return STRENGTH.get(item.get("strength"), 0) * 10 + min(float(item.get("sample_size") or 0) / 100, 4) + editorial


def _story_score(item: dict[str, Any]) -> float:
    md = item.get("metadata") or {}
    bonus = CATEGORY_STORY_BONUS.get(_category(item), 0.0)
    if str(md.get("family") or "").lower() == "qb_opponent_history":
        bonus += 5.0
    return _score(item) + bonus


def _best(items: list[dict[str, Any]], categories: set[str], limit: int = 1) -> list[dict[str, Any]]:
    candidates = [x for x in items if _category(x) in categories]
    candidates.sort(key=_score, reverse=True)
    return candidates[:limit]


def _advantage(item: dict[str, Any]) -> str | None:
    return (item.get("metadata") or {}).get("advantage_team")


def _family(item: dict[str, Any]) -> str:
    md = item.get("metadata") or {}
    raw = str(md.get("family") or md.get("concept") or item.get("category") or "context").lower()
    return raw.replace(" ", "_")


def _family_label(item: dict[str, Any]) -> str:
    fam = _family(item)
    return FAMILY_LABELS.get(fam, fam.replace("_", " ").title())


def _stable_variant(game_id: str, salt: str, options: list[str]) -> str:
    if not options:
        return ""
    digest = hashlib.blake2s(f"{game_id}|{salt}".encode("utf-8"), digest_size=4).digest()
    return options[int.from_bytes(digest, "big") % len(options)]


def _opponent(team: str | None, home: str, away: str) -> str:
    if team == home:
        return away
    if team == away:
        return home
    return away


def _subject_from_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    for marker in [" vs ", ":", " — "]:
        if marker in title:
            return title.split(marker, 1)[0].strip()
    return title


def _story_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(items, key=_story_score, reverse=True)
    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for item in ranked:
        fam = _family(item)
        if fam in used:
            continue
        out.append(item)
        used.add(fam)
    return out


def _angle_sentence(game_id: str, item: dict[str, Any] | None, pick: str, home: str, away: str) -> str:
    if item is None:
        return _stable_variant(game_id, "angle-fallback", [
            f"There is no single matchup gimmick carrying this forecast. {pick} simply owns the cleaner overall profile.",
            f"This is more accumulation than knockout punch: {pick} has the better collection of small edges.",
            f"The case for {pick} is broad rather than flashy. Nothing has to get weird for the forecast to make sense.",
        ])
    fam = _family(item)
    leader = _advantage(item)
    other = _opponent(leader, home, away)
    subject = _subject_from_title(item)

    if fam == "qb_opponent_history":
        qb = subject or "The quarterback"
        return _stable_variant(game_id, fam, [
            f"{qb} brings actual memory into this matchup, which is rare enough in Week 1 to matter. The useful question is not whether the old tape exists; it is which parts of it still travel.",
            f"This is not a blank-slate quarterback matchup. {qb} has seen this opponent before, so the intrigue is in what survived the changes around him.",
            f"There is real prior tape on {qb} against this opponent. That makes the matchup less hypothetical, but not necessarily more predictable.",
        ])
    if fam == "pressure":
        if leader:
            return _stable_variant(game_id, fam, [
                f"This game has a clean pressure question, and {leader} owns the better side of it. If {other} keeps landing in obvious passing downs, the pocket can dictate the rest of the afternoon.",
                f"The pocket is where this matchup can tilt fastest. {leader} has the leverage there; {other}'s job is to keep third-and-long from becoming the default setting.",
                f"Before worrying about coverage rotations or fourth-down choices, start up front. The pressure matchup gives {leader} the clearest way to take control.",
            ])
        return f"The pocket is the first place to look. Whichever side controls obvious passing downs will have the cleanest route to dictating the game."
    if fam == "explosives":
        if leader:
            return _stable_variant(game_id, fam, [
                f"The geometry of this game favors {leader}. It has the cleaner route to chunk plays; {other} would rather turn every possession into a twelve-play negotiation.",
                f"This matchup can change in two snaps if {leader} gets the explosive-play game it wants. {other}'s best answer is to make the field feel very long.",
                f"The possession count may matter less than who owns the big plays. Right now that part of the matchup tilts {leader}.",
            ])
        return "The explosive-play battle is the hinge here. A couple of chunk gains can rewrite an otherwise even game."
    if fam == "early_down":
        if leader:
            return _stable_variant(game_id, fam, [
                f"First and second down are the hinge. {leader} has the better setup to stay ahead of the chains, which keeps the entire call sheet available.",
                f"This one may be decided before third down arrives. {leader} has the cleaner early-down profile and a better chance to make the defense defend the whole playbook.",
                f"Watch second down. If {leader} keeps getting there with choices instead of problems, the matchup starts bending in its direction.",
            ])
        return "This game is mostly about staying on schedule. The side that wins first and second down gets to keep its real offense on the field."
    if fam == "third_down":
        if leader:
            return _stable_variant(game_id, fam, [
                f"Third down is where {leader} can turn a close matchup into a possession advantage. A few conversions either way could become the whole game.",
                f"There is a tax on every failed early down in this matchup, and {leader} is better positioned to collect it on third down.",
                f"If this stays close into the fourth quarter, the third-down matchup is the piece most likely to have quietly decided why.",
            ])
        return "Third down is the pressure valve here. Two or three high-leverage conversions could decide the possession math."
    if fam == "yac":
        if leader:
            return _stable_variant(game_id, fam, [
                f"The catch is only half the play here. {leader} has the better chance to turn routine completions into drive-changing gains after the ball arrives.",
                f"This matchup asks the defense to tackle cleanly in space. That is exactly where {leader} can make ordinary throws expensive.",
                f"The passing game does not need to live deep for {leader} to create explosives. The danger is what happens after the completion.",
            ])
        return "The quiet matchup is tackling after the catch. Short completions can become explosives if the first defender loses."
    if fam == "run_front":
        if leader:
            return _stable_variant(game_id, fam, [
                f"This game may announce itself in the first two drives. {leader} has the better answer in the box, and that can determine whether play action ever gets comfortable.",
                f"Start with the run front. If {leader} wins that argument without extra help, everything behind it gets easier.",
                f"The numbers point to a trench game first and a quarterback game second. That ordering favors {leader}.",
            ])
        return "The first clue should come on the ground. If one side can run without forcing extra bodies into the box, the rest of the matchup opens up."
    if fam in {"alignment", "motion", "play_action", "rpo", "screen"}:
        concept = FAMILY_LABELS.get(fam, fam.replace("_", " "))
        if leader:
            return _stable_variant(game_id, fam, [
                f"The schematic wrinkle to watch is {concept.lower()}. {leader} has the better fit there, which can force {other} to declare answers earlier than it wants.",
                f"This is one of those matchups where formation and sequencing matter as much as raw talent. The {concept.lower()} layer currently tilts {leader}.",
                f"The chess move here is {concept.lower()}. If {leader} gets the looks it wants, the defense can spend the afternoon reacting instead of dictating.",
            ])
        return f"The schematic hinge is {concept.lower()}. It is the clearest place where formation and sequencing can change the matchup."
    if fam == "availability":
        player = subject or "The personnel board"
        return _stable_variant(game_id, fam, [
            f"Personnel comes before tactics in this one. {player} changes what each side can ask of the matchup, even before the first play call.",
            f"The first matchup is the active roster. {player} is the personnel note with the most ability to reshape how this game is played.",
            f"This is a game where one availability line can change the geometry. {player} is the name worth checking before getting cute with scheme.",
        ])
    if fam in {"coaching", "coordinator", "structural_change"}:
        return _stable_variant(game_id, fam, [
            "The old scouting report needs edits. New decision-makers change which tendencies are actually portable into this matchup.",
            "There is useful old tape here, but the play callers changed. That makes current tendencies more valuable than the franchise-level history.",
            "This is a continuity game in reverse: the staff changes matter because they make familiar opponents less familiar than the logos suggest.",
        ])
    if fam == "weather":
        return _stable_variant(game_id, fam, [
            "The environment deserves a seat at the table here. It is not the forecast, but it can decide which parts of the playbook are easiest to access.",
            "This is one of the few matchups where the conditions can change the style of game before either team does.",
            "Weather is not the thesis, but it can change the cost of chasing explosives and field position in this matchup.",
        ])
    if fam in {"travel", "scenario"}:
        return _stable_variant(game_id, fam, [
            "The situational layer matters more than usual here. Rest, travel and game state can determine which team gets to play on schedule.",
            "This matchup has a real situational wrinkle, and it mostly matters because it changes how much margin for error each offense has.",
            "There is a game-state angle here that is easy to miss on a stat sheet. It can matter most if the score stays tight into the second half.",
        ])
    title = str(item.get("title") or _family_label(item))
    return f"The defining matchup is {title.lower()}. That is the cleanest football reason this game can move away from a generic coin-flip script."


def _secondary_sentence(game_id: str, item: dict[str, Any] | None, primary: dict[str, Any] | None, pick: str, home: str, away: str) -> str:
    if item is None:
        return "The rest of the case is accumulation: small edges that point the same way rather than one overwhelming mismatch."
    fam = _family(item)
    leader = _advantage(item)
    label = _family_label(item).lower()
    if primary and _advantage(primary) and leader and leader != _advantage(primary):
        return _stable_variant(game_id, "secondary-counter", [
            f"The counterweight is {label}: that part of the matchup tilts {leader}, so the favorite does not get a free pass.",
            f"There is a real answer on the other side. The {label} matchup favors {leader}, which is why the game is not as simple as the headline probability.",
            f"The tension comes from {label}. That edge belongs to {leader}, giving the underdog a concrete way to make the forecast uncomfortable.",
        ])
    if leader:
        return _stable_variant(game_id, "secondary-align", [
            f"The {label} matchup points the same way, giving {leader} a second route to control the terms of the game.",
            f"That is not the only edge. {label.title()} also leans {leader}, which makes the case more structural than singular.",
            f"The supporting argument is {label}: another part of the game that currently favors {leader}.",
        ])
    return _stable_variant(game_id, "secondary-neutral", [
        f"The secondary thread is {label}. It matters more as context than as a clean edge for either sideline.",
        f"There is also a {label} wrinkle worth carrying into kickoff, even if it does not belong neatly to one team.",
        f"The other useful lens is {label}. It adds texture to the matchup without pretending to be a standalone prediction.",
    ])


def _market_read(game_id: str, game: pd.Series, pick: str, home: str, away: str) -> str | None:
    pure = _num(game.get("pure_home_prob"))
    market = _num(game.get("market_home_prob"))
    spread = _num(game.get("spread_line"))
    margin = _num(game.get("expected_margin"))
    if pure is not None and market is not None:
        gap = 100 * (pure - market)
        if abs(gap) >= 5:
            direction = home if gap > 0 else away
            return _stable_variant(game_id, "market-gap", [
                f"The interesting split is with the market: PURE is {abs(gap):.1f} percentage points more bullish on {direction}. The 25% market blend pulls LevLine toward consensus, but it does not erase the disagreement.",
                f"Consensus pricing and the football-only model are telling different versions of this game. PURE is {abs(gap):.1f} points higher on {direction}, and LevLine keeps enough of that disagreement to make it visible.",
                f"The market is the dissenting vote here. PURE sits {abs(gap):.1f} percentage points higher on {direction}; the published blend respects the market without surrendering to it.",
            ])
    if spread is not None and margin is not None:
        edge_home = margin - spread
        pick_edge = edge_home if pick == home else -edge_home
        if pick_edge >= 2.0:
            return f"The probability is not the only signal. LevLine's central margin is {pick_edge:.1f} points more favorable to {pick} than the current spread."
    return None


def _factor_takeaway(item: dict[str, Any]) -> str:
    fam = _family(item)
    leader = _advantage(item)
    who = leader or "Neither side"
    templates = {
        "pressure": f"The pressure matchup tilts {who}; obvious passing downs are where it can become decisive.",
        "explosives": f"The chunk-play path tilts {who}; the opponent's answer is forcing longer drives.",
        "early_down": f"Early-down leverage tilts {who}, which matters because it keeps the full playbook available.",
        "third_down": f"Third-down possession leverage tilts {who}; a few conversions can swing the entire game script.",
        "yac": f"The after-catch matchup tilts {who}; routine completions can become the hidden explosives.",
        "run_front": f"The box matchup tilts {who}; that is the first place to watch before play action and coverage rotations matter.",
        "alignment": f"Formation and alignment give {who} the cleaner schematic setup.",
        "qb_opponent_history": "There is usable quarterback-opponent history here, but current staff and personnel decide how much of it travels.",
        "availability": "The personnel board materially shapes the matchup and deserves a final check close to kickoff.",
        "coaching": "Staff changes make current tendencies more useful than old franchise-level head-to-head results.",
        "coordinator": "Coordinator continuity is part of how much prior matchup history should be trusted.",
        "weather": "Conditions can change which style of football is cheapest to play, even without changing the official probability by hand.",
        "travel": "The situational edge is about schedule and game state more than raw team quality.",
    }
    return templates.get(fam, f"{_family_label(item)} is one of the matchup's clearest live signals.")


def _factor_card(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title"),
        "summary": _factor_takeaway(item),
        "family": _family(item),
        "strength": item.get("strength"),
        "advantage_team": _advantage(item),
        "source_name": item.get("source_name"),
        "source_url": item.get("source_url"),
        "sample_size": item.get("sample_size"),
    }


def _case_sentence(team: str, ranked: list[dict[str, Any]], positive: bool = True) -> str:
    matches = [x for x in ranked if _advantage(x) == team]
    if not matches:
        return f"{team}'s case is less about one clean mismatch and more about creating the high-leverage swing plays that sit outside the central projection."
    labels = []
    for item in matches:
        label = _family_label(item).lower()
        if label not in labels:
            labels.append(label)
        if len(labels) == 2:
            break
    if len(labels) == 1:
        return f"The cleanest case for {team} runs through {labels[0]}. That is the matchup lever most capable of changing the game's shape."
    return f"The case for {team} is built on two different levers: {labels[0]} and {labels[1]}. If both show up, the game can move quickly in its direction."


def _headline(game_id: str, game: pd.Series, pick: str, pick_prob: float | None, primary: dict[str, Any] | None, home: str, away: str) -> str:
    pure = _num(game.get("pure_home_prob"))
    market = _num(game.get("market_home_prob"))
    if pure is not None and market is not None and abs(pure - market) >= .07:
        return _stable_variant(game_id, "headline-market", [
            f"LevLine sees {pick} differently than the market",
            f"{pick} is where LevLine breaks from consensus",
            f"The market and LevLine disagree on {pick}",
        ])
    if pick_prob is not None and pick_prob < .515:
        return _stable_variant(game_id, "headline-flip", [
            f"{pick}, barely",
            f"A one-possession argument with {pick} on top",
            f"LevLine gives {pick} the thinnest edge",
        ])
    fam = _family(primary) if primary else ""
    leader = _advantage(primary) if primary else None
    if fam == "pressure":
        return f"{pick}'s game starts in the pocket" if leader == pick else f"{pick} has a pressure problem to solve"
    if fam == "explosives":
        return f"This game turns on who owns the explosives"
    if fam == "early_down":
        return f"{pick}'s path runs through first and second down"
    if fam == "qb_opponent_history":
        return f"Prior tape gives this matchup an extra layer"
    if fam == "availability":
        return f"Personnel is the first matchup to solve"
    if fam in {"coaching", "coordinator", "structural_change"}:
        return "The logos are familiar. The decision-makers are not."
    if fam == "yac":
        return "The hidden explosive play is after the catch"
    if fam == "run_front":
        return "This one starts in the box"
    return _stable_variant(game_id, "headline-default", [
        f"{pick} has the cleaner case",
        f"Why LevLine lands on {pick}",
        f"The matchup tilts {pick}",
    ])


def _live_matchup_meter(game: pd.Series, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = _story_candidates(items)
    live_categories = {"injury", "personnel", "history", "coaching", "structural_change", "coordinator", "weather", "travel", "scenario"}
    tactical_categories = {"scheme", "matchup"}
    chosen: list[dict[str, Any]] = []
    used: set[str] = set()

    def add(pool: list[dict[str, Any]], limit: int) -> None:
        for item in pool:
            fam = _family(item)
            if fam in used:
                continue
            chosen.append(item)
            used.add(fam)
            if len(chosen) >= limit:
                return

    live = [x for x in ranked if _category(x) in live_categories]
    tactical = [x for x in ranked if _category(x) in tactical_categories]
    if live:
        add(live, 1)
    add(tactical, 3)
    add(ranked, 4)

    rows = []
    for item in chosen[:4]:
        leader = _advantage(item)
        rows.append({
            "label": _family_label(item),
            "leader": leader or "Watch",
            "strength": item.get("strength") or "Context",
            "title": item.get("title"),
            "source_name": item.get("source_name"),
            "as_of": item.get("as_of"),
            "family": _family(item),
        })
    return rows


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
        disagreement = _num(game.get("model_disagreement"))
        consistency = str(game.get("consistency_flag") or "")
        score = str(game.get("projected_score") or "")

        history = _best(items, {"history"}, 2)
        coaching = _best(items, {"coaching", "structural_change", "coordinator"}, 2)
        scheme = _best(items, {"scheme", "matchup"}, 4)
        personnel = _best(items, {"personnel", "injury"}, 3)
        scenarios = _best(items, {"weather", "travel", "scenario"}, 2)

        story = _story_candidates(items)
        primary = story[0] if story else None
        secondary = story[1] if len(story) > 1 else None
        first = _angle_sentence(gid, primary, pick, home, away)
        second = _secondary_sentence(gid, secondary, primary, pick, home, away)
        market = _market_read(gid, game, pick, home, away)
        paragraphs = [f"{first} {second}"]
        if market:
            paragraphs.append(market)

        ranked = sorted(items, key=_story_score, reverse=True)
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

        case_for_pick = _case_sentence(pick, ranked)
        case_for_dog = _case_sentence(dog, ranked)

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
        if any(_advantage(x) == dog for x in ranked):
            wrong.append(f"{dog} owns at least one real matchup counter-signal.")
        if not wrong:
            wrong.append(f"The cleanest upset path for {dog} is a turnover or explosive-play swing that the central projection cannot predict in advance.")
        what_wrong = " ".join(wrong[:3])

        matchup_meter = _live_matchup_meter(game, items)
        previews[gid] = {
            "game_id": gid,
            "matchup": f"{away} @ {home}",
            "brand": "Sunday Signal",
            "engine": "LevLine",
            "headline": _headline(gid, game, pick, pick_prob, primary, home, away),
            "paragraphs": paragraphs,
            "story_spine": {
                "primary_family": _family(primary) if primary else None,
                "primary_title": primary.get("title") if primary else None,
                "secondary_family": _family(secondary) if secondary else None,
                "secondary_title": secondary.get("title") if secondary else None,
            },
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

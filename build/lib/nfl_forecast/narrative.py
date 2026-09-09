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
LIVE_CATEGORIES = {
    "injury", "personnel", "history", "coaching", "structural_change",
    "coordinator", "weather", "travel", "scenario",
}
TACTICAL_CATEGORIES = {"scheme", "matchup"}


def _num(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except Exception:
        return None


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def _category(item: dict[str, Any]) -> str:
    return str(item.get("category") or "context").lower()


def _score(item: dict[str, Any]) -> float:
    metadata = item.get("metadata") or {}
    try:
        editorial = float(metadata.get("editorial_score") or 0)
    except Exception:
        editorial = 0.0
    try:
        sample = float(item.get("sample_size") or 0)
    except Exception:
        sample = 0.0
    return STRENGTH.get(str(item.get("strength")), 0) * 10 + min(sample / 100, 4) + editorial


def _story_score(item: dict[str, Any]) -> float:
    bonus = CATEGORY_STORY_BONUS.get(_category(item), 0.0)
    if _family(item) == "qb_opponent_history":
        bonus += 5.0
    return _score(item) + bonus


def _best(items: list[dict[str, Any]], categories: set[str], limit: int = 1) -> list[dict[str, Any]]:
    candidates = [item for item in items if _category(item) in categories]
    return sorted(candidates, key=_score, reverse=True)[:limit]


def _advantage(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    return (item.get("metadata") or {}).get("advantage_team")


def _family(item: dict[str, Any] | None) -> str:
    if not item:
        return "context"
    metadata = item.get("metadata") or {}
    raw = str(metadata.get("family") or metadata.get("concept") or item.get("category") or "context").lower()
    return raw.replace(" ", "_")


def _family_label(item: dict[str, Any]) -> str:
    family = _family(item)
    return FAMILY_LABELS.get(family, family.replace("_", " ").title())


def _stable_variant(game_id: str, salt: str, options: list[str]) -> str:
    digest = hashlib.blake2s(f"{game_id}|{salt}".encode("utf-8"), digest_size=4).digest()
    return options[int.from_bytes(digest, "big") % len(options)] if options else ""


def _opponent(team: str | None, home: str, away: str) -> str:
    if team == home:
        return away
    if team == away:
        return home
    return away


def _subject_from_title(item: dict[str, Any] | None, home: str, away: str) -> str | None:
    if not item:
        return None
    title = str(item.get("title") or "").strip()
    subject = title
    for marker in [" vs ", ":", " — ", " - "]:
        if marker in subject:
            subject = subject.split(marker, 1)[0].strip()
            break
    if not subject:
        return None
    # Team-level injury notes used to become sentences such as "NE is the name
    # worth checking." Treat abbreviations as a board-level personnel item.
    if subject in {home, away} or re.fullmatch(r"[A-Z]{2,4}", subject):
        return None
    return subject


def _story_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(items, key=_story_score, reverse=True)
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for item in ranked:
        family = _family(item)
        if family in used:
            continue
        selected.append(item)
        used.add(family)
    return selected


def _choose_story(story: list[dict[str, Any]], pick: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    """Choose a lead that normally supports the published pick.

    A previous version simply used the highest editorial score. That could make
    a Vegas pick open with two Miami advantages. Supporting evidence now gets
    first right of refusal; neutral live context may lead when no supporting
    signal exists. A counter-signal leads only as an explicitly framed problem.
    """
    supporting = [item for item in story if _advantage(item) == pick]
    neutral_live = [item for item in story if _advantage(item) is None and _category(item) in LIVE_CATEGORIES]
    neutral = [item for item in story if _advantage(item) is None]
    counter = [item for item in story if _advantage(item) not in {None, pick}]

    if supporting:
        primary = supporting[0]
        mode = "support"
    elif neutral_live:
        primary = neutral_live[0]
        mode = "neutral"
    elif neutral:
        primary = neutral[0]
        mode = "neutral"
    elif counter:
        primary = counter[0]
        mode = "counter"
    else:
        return None, None, "fallback"

    remainder = [item for item in story if item is not primary]
    # The second beat should add tension when possible, not say the same thing twice.
    if mode == "support":
        secondary = next((item for item in remainder if _advantage(item) not in {None, pick}), None)
        if secondary is None:
            secondary = next((item for item in remainder if _advantage(item) == pick), None)
        if secondary is None:
            secondary = next(iter(remainder), None)
    else:
        secondary = next((item for item in remainder if _advantage(item) == pick), None)
        if secondary is None:
            secondary = next(iter(remainder), None)
    return primary, secondary, mode


def _qb_history_angle(game_id: str, item: dict[str, Any], pick: str, home: str, away: str, mode: str) -> str:
    qb = _subject_from_title(item, home, away) or "The quarterback"
    opponent = home if str((item.get("metadata") or {}).get("current_team")) == away else away
    latest = (item.get("metadata") or {}).get("latest_meeting") or {}
    stage = str(latest.get("stage") or latest.get("human_label") or "").lower()
    biggest_stage = "super bowl" in stage

    if mode == "counter":
        return _stable_variant(game_id, "qb-counter", [
            f"The biggest complication in the {pick} case is that {qb} is not seeing {opponent} cold. There is real prior tape here, and the lower history section explains exactly how much of it should travel.",
            f"{pick} is the forecast, but {qb}'s history with {opponent} is the part that keeps the matchup from feeling clean. The useful question is what survives the staff and personnel changes around that old tape.",
            f"If {pick} is wrong, {qb}'s familiarity with {opponent} is one plausible reason. This is prior experience worth respecting, not a recycled head-to-head record.",
        ])

    if biggest_stage:
        return _stable_variant(game_id, "qb-super-bowl", [
            f"{qb} has already seen {opponent} under the brightest possible lights. That history gives this matchup a real reference point; the question is what still applies after the offseason changed the people around it.",
            f"This is not theoretical tape for {qb}: the last meeting with {opponent} came on the sport's biggest stage. Sunday Signal treats that as context, then asks which parts of the matchup actually survived into 2026.",
            f"{qb} and {opponent} have a recent history that matters more than a random franchise head-to-head. The old game is a reference point, not a script for the sequel.",
        ])

    return _stable_variant(game_id, "qb-history", [
        f"{qb} brings actual memory of {opponent} into this matchup. That makes the scouting problem more concrete, but the value is in what carried forward—not in pretending the old game will replay itself.",
        f"This is not a blank-slate quarterback matchup: {qb} has already worked through {opponent}'s answers before. The lower history file handles the exact sample; the Read cares about what remains transferable.",
        f"There is usable prior tape on {qb} against {opponent}. For the {pick} case, the important part is how that familiarity interacts with the current staff, protection and personnel rather than the old final score.",
    ])


def _availability_angle(game_id: str, item: dict[str, Any], pick: str, home: str, away: str, mode: str) -> str:
    player = _subject_from_title(item, home, away)
    if player:
        return _stable_variant(game_id, "availability-player", [
            f"Before the chalkboard comes the active list. {player}'s status is the personnel variable most capable of changing how {away}-{home} is played.",
            f"The first matchup in {away}-{home} is availability. {player} is the name that can change which schematic answers are realistic once the ball is kicked.",
            f"{player} is the roster hinge in this game. The forecast does not invent an injury point value, but the matchup story changes if that role changes.",
        ])
    return _stable_variant(game_id, "availability-board", [
        f"The {away}-{home} personnel board deserves one more look before scheme takes over. Availability can change the shape of this matchup even though LevLine does not hand-enter an injury adjustment.",
        f"For {away}-{home}, the active roster is part of the matchup. The official report matters because it changes what each side can ask of its offense and defense, not because Sunday Signal assigns a made-up point value.",
        f"There is a live personnel question in {away}-{home}. That belongs in the football story, while the numerical forecast stays disciplined about adjustments it has not validated.",
    ])


def _angle_sentence(game_id: str, item: dict[str, Any] | None, pick: str, home: str, away: str, mode: str) -> str:
    if item is None:
        return _stable_variant(game_id, "fallback", [
            f"There is no single gimmick carrying the {pick} forecast in {away}-{home}. It is an accumulation case: more small edges point the same way than the other.",
            f"{pick} gets the call in {away}-{home} without one knockout mismatch. The model is leaning on the shape of the whole profile rather than a single stat.",
            f"The {pick} case in {away}-{home} is broad rather than flashy. Nothing exotic has to happen for the central forecast to make sense.",
        ])

    family = _family(item)
    leader = _advantage(item)
    other = _opponent(leader, home, away)
    if family == "qb_opponent_history":
        return _qb_history_angle(game_id, item, pick, home, away, mode)
    if family == "availability":
        return _availability_angle(game_id, item, pick, home, away, mode)

    if mode == "counter" and leader:
        return _stable_variant(game_id, f"counter-{family}", [
            f"The strongest matchup signal actually points away from {pick}: {_family_label(item).lower()} tilts {leader}. The {pick} forecast survives because the full model is broader than that one problem, but this is the first place to test it.",
            f"There is a real hole in the {pick} case, and it is {_family_label(item).lower()}. {leader} owns that piece of {away}-{home}; if it becomes the dominant game script, the upset path is not hard to draw.",
            f"{pick} is the model side, but {_family_label(item).lower()} is the matchup that argues back. That advantage belongs to {leader}, so the forecast needs the rest of the game to keep it contained.",
        ])

    if family == "pressure" and leader:
        return _stable_variant(game_id, "pressure", [
            f"The {pick} case starts in the pocket. {leader} owns the cleaner pressure matchup in {away}-{home}, and obvious passing downs are where that edge can become the rest of the game.",
            f"Before coverage rotations or fourth-down choices, start up front: {leader} has the leverage in the {away}-{home} pressure battle. That is the most direct football argument behind the {pick} side.",
            f"The pocket can tilt {away}-{home} fastest. {leader} has the better setup there; {other}'s job is to keep third-and-long from becoming a recurring appointment.",
        ])
    if family == "explosives" and leader:
        return _stable_variant(game_id, "explosives", [
            f"The geometry of {away}-{home} favors {leader}. It has the cleaner route to chunk plays, while {other} would rather turn every possession into a twelve-play negotiation.",
            f"The {pick} forecast has an explosive-play spine. {leader} can change {away}-{home} in two snaps; {other}'s best answer is to make the field feel very long.",
            f"Possession count may matter less than who owns the big plays in {away}-{home}. That part of the matchup currently tilts {leader}, which is a clean reason to like {pick}.",
        ])
    if family == "early_down" and leader:
        return _stable_variant(game_id, "early-down", [
            f"For {leader}, {away}-{home} can be won before third down arrives. Staying ahead of the chains keeps the full call sheet alive and is the cleanest early reason to trust the {pick} side.",
            f"First and second down are the hinge in {away}-{home}. {leader} has the better setup to stay on schedule, which means the defense has to keep honoring the whole playbook.",
            f"Watch second down in {away}-{home}. If {leader} keeps arriving there with choices instead of problems, the game starts bending toward the {pick} forecast.",
        ])
    if family == "third_down" and leader:
        return _stable_variant(game_id, "third-down", [
            f"Third down is where {leader} can turn {away}-{home} into a possession advantage. In a game like this, three conversions can quietly become the whole box score.",
            f"There is a tax on every failed early down in {away}-{home}, and {leader} is better positioned to collect it. That high-leverage edge supports the {pick} case.",
            f"If {away}-{home} is still tight in the fourth quarter, the third-down matchup favoring {leader} is the piece most likely to have decided why.",
        ])
    if family == "yac" and leader:
        return _stable_variant(game_id, "yac", [
            f"In {away}-{home}, the catch is only half the play. {leader} has the cleaner chance to turn routine completions into drive-changing gains after the ball arrives.",
            f"The {pick} case can live underneath the coverage. {leader}'s after-catch matchup makes ordinary throws more expensive for {other} than they look at release.",
            f"{leader} does not need to live deep to create explosives in {away}-{home}. The danger for {other} is what happens after the completion.",
        ])
    if family == "run_front" and leader:
        return _stable_variant(game_id, "run-front", [
            f"{away}-{home} may announce itself in the first two drives. {leader} owns the better box matchup, and that can decide whether play action ever gets comfortable.",
            f"Start with the run front in {away}-{home}. If {leader} wins that argument without extra help, everything behind the {pick} case gets easier.",
            f"The numbers make {away}-{home} a trench game first and a quarterback game second. That ordering favors {leader} and supports the {pick} side.",
        ])
    if family in {"alignment", "motion", "play_action", "rpo", "screen"}:
        concept = FAMILY_LABELS.get(family, family.replace("_", " ")).lower()
        if leader:
            return _stable_variant(game_id, family, [
                f"The schematic wrinkle in {away}-{home} is {concept}. {leader} has the cleaner fit there, which can force {other} to declare answers earlier than it wants.",
                f"Formation and sequencing matter in {away}-{home}, and the {concept} layer currently tilts {leader}. That gives the {pick} case a tactical route that is more specific than raw talent.",
                f"The chess move in {away}-{home} is {concept}. If {leader} gets the looks it wants, {other} can spend too much of the afternoon reacting instead of dictating.",
            ])
    if family in {"coaching", "coordinator", "structural_change"}:
        return _stable_variant(game_id, "staff", [
            f"The logos in {away}-{home} may be familiar, but the decision-makers are not. That makes current tendencies more useful to the {pick} read than recycled franchise head-to-heads.",
            f"The old {away}-{home} scouting report needs edits. Staff changes alter which tendencies are portable, so the {pick} case has to be built on the current version of these teams.",
            f"{away}-{home} is a continuity game in reverse: new play callers make familiar opponents less familiar than the logos suggest. That matters to how much old tape LevLine should trust.",
        ])
    if family == "weather":
        return _stable_variant(game_id, "weather", [
            f"The environment gets a real vote in {away}-{home}. It is not the forecast by itself, but it can decide which parts of the {pick} game plan are cheapest to access.",
            f"Conditions can change the style of {away}-{home} before either team does. The {pick} forecast still stands on the model, while weather shapes which routes to that outcome are realistic.",
            f"Weather is not the thesis of {away}-{home}, but it can change the cost of chasing explosives and field position. That is why it belongs in the Read without becoming a hand-entered adjustment.",
        ])
    if family in {"travel", "scenario"}:
        return _stable_variant(game_id, "situation", [
            f"There is a real game-state wrinkle in {away}-{home}. Rest, travel or sequencing matters because it changes how much margin for error the {pick} side has, not because it replaces team quality.",
            f"The situational layer is unusually relevant in {away}-{home}. It mostly matters through who gets to play on schedule, which is the context around the {pick} forecast rather than the forecast itself.",
            f"{away}-{home} has a situational angle that a box-score model can hide. If the game stays tight, that context can matter more in the second half than it does on the opening drive.",
        ])

    title = str(item.get("title") or _family_label(item))
    return f"The defining football question in {away}-{home} is {title.lower()}. That is the most specific matchup lens around the {pick} forecast."


def _secondary_sentence(game_id: str, item: dict[str, Any] | None, primary: dict[str, Any] | None, pick: str, home: str, away: str) -> str:
    if item is None:
        return f"The rest of the {pick} case is accumulation: several smaller edges point the same way rather than one mismatch doing all the work."
    leader = _advantage(item)
    label = _family_label(item).lower()
    primary_leader = _advantage(primary)
    if leader and leader != pick:
        return _stable_variant(game_id, "secondary-counter", [
            f"The counterweight in {away}-{home} is {label}: that piece belongs to {leader}, giving the other side a concrete way to stress the {pick} forecast.",
            f"The argument is not one-way. {leader} owns the {label} edge in {away}-{home}, which is the cleanest answer to the {pick} case.",
            f"The tension comes from {label}. That advantage belongs to {leader}, so {pick} does not get a free pass through this matchup.",
        ])
    if leader == pick:
        return _stable_variant(game_id, "secondary-support", [
            f"The {label} matchup points the same way in {away}-{home}, giving {pick} a second route to control the terms of the game.",
            f"That is not the only {pick} edge: {label} also leans its way, which makes the case more structural than singular.",
            f"The supporting argument is {label}. It gives {pick} another matchup lever if the primary plan gets taken away.",
        ])
    if primary_leader == pick:
        return f"The secondary thread in {away}-{home} is {label}. It adds context to the {pick} case without pretending to be a clean edge for either sideline."
    return f"There is also a {label} wrinkle in {away}-{home}. It matters as context while the {pick} case is decided elsewhere."


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
                f"The market is the other story in {away}-{home}: PURE is {abs(gap):.1f} percentage points more bullish on {direction}. The 25% market blend pulls LevLine toward consensus without erasing the disagreement.",
                f"Consensus pricing and the football-only model tell different versions of {away}-{home}. PURE is {abs(gap):.1f} points higher on {direction}, and LevLine keeps enough of that split visible to matter.",
                f"The market is the dissenting vote in {away}-{home}. PURE sits {abs(gap):.1f} percentage points higher on {direction}; the published blend respects that outside information without surrendering the football view.",
            ])
    if spread is not None and margin is not None:
        edge_home = margin - spread
        pick_edge = edge_home if pick == home else -edge_home
        if pick_edge >= 2.0:
            return f"The probability is not the only {pick} signal in {away}-{home}: LevLine's central margin is {pick_edge:.1f} points more favorable than the current spread."
    return None


def _factor_takeaway(item: dict[str, Any]) -> str:
    family = _family(item)
    leader = _advantage(item)
    who = leader or "Neither side"
    templates = {
        "pressure": f"The pressure matchup tilts {who}; obvious passing downs are where it can become decisive.",
        "explosives": f"The chunk-play path tilts {who}; the opponent's answer is forcing longer drives.",
        "early_down": f"Early-down leverage tilts {who}, which matters because it keeps the full playbook available.",
        "third_down": f"Third-down possession leverage tilts {who}; a few conversions can swing the game script.",
        "yac": f"The after-catch matchup tilts {who}; routine completions can become the hidden explosives.",
        "run_front": f"The box matchup tilts {who}; that is the first place to watch before play action matters.",
        "alignment": f"Formation and alignment give {who} the cleaner schematic setup.",
        "qb_opponent_history": "There is usable quarterback-opponent history here; the detailed section below handles the actual meetings and how much should carry forward.",
        "availability": "The personnel board can reshape the matchup and deserves a final check close to kickoff.",
        "coaching": "Staff changes make current tendencies more useful than old franchise-level head-to-heads.",
        "coordinator": "Coordinator continuity changes how much prior matchup history should be trusted.",
        "weather": "Conditions can change which style of football is cheapest to play without becoming a hand-entered probability adjustment.",
        "travel": "The situational edge is about schedule and game state more than raw team quality.",
    }
    return templates.get(family, f"{_family_label(item)} is one of this matchup's clearest live signals.")


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


def _case_sentence(team: str, ranked: list[dict[str, Any]]) -> str:
    matches = [item for item in ranked if _advantage(item) == team]
    if not matches:
        return f"{team}'s case is less about one clean mismatch and more about creating the high-leverage swing plays that sit outside the central projection."
    labels: list[str] = []
    for item in matches:
        label = _family_label(item).lower()
        if label not in labels:
            labels.append(label)
        if len(labels) == 2:
            break
    if len(labels) == 1:
        return f"The cleanest case for {team} runs through {labels[0]}. That is the matchup lever most capable of changing the game's shape."
    return f"The case for {team} has two distinct levers: {labels[0]} and {labels[1]}. If both show up, the game can move quickly in its direction."


def _headline(game_id: str, game: pd.Series, pick: str, pick_prob: float | None, primary: dict[str, Any] | None, mode: str, home: str, away: str) -> str:
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
    family = _family(primary)
    if mode == "counter":
        return f"{pick} is the pick; {_family_label(primary).lower()} is the problem"
    headlines = {
        "pressure": f"{pick}'s game starts in the pocket",
        "explosives": f"{pick}'s edge lives in the explosive-play battle",
        "early_down": f"{pick}'s path runs through first and second down",
        "qb_opponent_history": f"{pick}: prior tape changes the Week 1 read",
        "availability": f"{pick}'s forecast starts with the personnel board",
        "coaching": f"{pick} in a matchup with new decision-makers",
        "coordinator": f"{pick} in a matchup with new decision-makers",
        "structural_change": f"{pick} in a matchup with new decision-makers",
        "yac": f"{pick}'s hidden edge comes after the catch",
        "run_front": f"{pick}'s case starts in the box",
        "third_down": f"{pick}'s high-leverage edge is third down",
    }
    return headlines.get(family) or _stable_variant(game_id, "headline-default", [
        f"{pick} has the cleaner case in {away}-{home}",
        f"Why LevLine lands on {pick} in {away}-{home}",
        f"The {away}-{home} matchup tilts {pick}",
    ])


def _live_matchup_meter(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = _story_candidates(items)
    selected: list[dict[str, Any]] = []
    used: set[str] = set()

    def add(pool: list[dict[str, Any]], limit: int) -> None:
        for item in pool:
            family = _family(item)
            if family in used:
                continue
            selected.append(item)
            used.add(family)
            if len(selected) >= limit:
                return

    live = [item for item in ranked if _category(item) in LIVE_CATEGORIES]
    tactical = [item for item in ranked if _category(item) in TACTICAL_CATEGORIES]
    if live:
        add(live, 1)
    add(tactical, 3)
    add(ranked, 4)

    return [
        {
            "label": _family_label(item),
            "leader": _advantage(item) or "Watch",
            "strength": item.get("strength") or "Context",
            "title": item.get("title"),
            "source_name": item.get("source_name"),
            "as_of": item.get("as_of"),
            "family": _family(item),
        }
        for item in selected[:4]
    ]


def build_game_previews(predictions: pd.DataFrame, evidence: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    previews: dict[str, dict[str, Any]] = {}
    for _, game in predictions.iterrows():
        game_id = str(game.get("game_id"))
        items = evidence.get(game_id, [])
        home = str(game.get("home_team"))
        away = str(game.get("away_team"))
        pick = str(game.get("pick"))
        opponent = away if pick == home else home
        home_prob = _num(game.get("final_home_prob"))
        pick_prob = None if home_prob is None else (home_prob if pick == home else 1 - home_prob)
        disagreement = _num(game.get("model_disagreement"))
        consistency = str(game.get("consistency_flag") or "")
        score = str(game.get("projected_score") or "")

        history = _best(items, {"history"}, 2)
        coaching = _best(items, {"coaching", "structural_change", "coordinator"}, 2)
        scheme = _best(items, {"scheme", "matchup"}, 4)
        personnel = _best(items, {"personnel", "injury"}, 3)
        scenarios = _best(items, {"weather", "travel", "scenario"}, 2)

        story = _story_candidates(items)
        primary, secondary, mode = _choose_story(story, pick)
        first = _angle_sentence(game_id, primary, pick, home, away, mode)
        second = _secondary_sentence(game_id, secondary, primary, pick, home, away)
        paragraphs = [f"{first} {second}"]
        market = _market_read(game_id, game, pick, home, away)
        if market:
            paragraphs.append(market)

        ranked = sorted(items, key=_story_score, reverse=True)
        factors: list[dict[str, Any]] = []
        used_families: set[str] = set()
        for item in ranked:
            family = _family(item)
            if family in used_families:
                continue
            factors.append(_factor_card(item))
            used_families.add(family)
            if len(factors) == 3:
                break

        wrong: list[str] = []
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
        if any(_advantage(item) == opponent for item in ranked):
            wrong.append(f"{opponent} owns at least one real matchup counter-signal.")
        if not wrong:
            wrong.append(f"The cleanest upset path for {opponent} is a turnover or explosive-play swing that the central projection cannot predict in advance.")

        previews[game_id] = {
            "game_id": game_id,
            "matchup": f"{away} @ {home}",
            "brand": "Sunday Signal",
            "engine": "LevLine",
            "headline": _headline(game_id, game, pick, pick_prob, primary, mode, home, away),
            "paragraphs": paragraphs,
            "story_spine": {
                "primary_family": _family(primary) if primary else None,
                "primary_title": primary.get("title") if primary else None,
                "primary_mode": mode,
                "primary_advantage_team": _advantage(primary),
                "secondary_family": _family(secondary) if secondary else None,
                "secondary_title": secondary.get("title") if secondary else None,
                "secondary_advantage_team": _advantage(secondary),
            },
            "key_factors": factors,
            "case_for_pick": _case_sentence(pick, ranked),
            "case_for_opponent": _case_sentence(opponent, ranked),
            "matchup_meter": _live_matchup_meter(items),
            "what_could_make_us_wrong": " ".join(wrong[:3]),
            "prediction": f"{pick} to win" + (f"; {score} is the central score projection." if score else "."),
            "evidence_used": [
                {
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "strength": item.get("strength"),
                    "source_name": item.get("source_name"),
                    "source_url": item.get("source_url"),
                }
                for item in (history + coaching + scheme + personnel + scenarios)
            ],
            "guardrail": "Narrative evidence explains the matchup but does not change the numerical forecast. LevLine changes only when the underlying feature separately passes chronological out-of-sample validation.",
        }
    return previews

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

import pandas as pd


FAMILY_LABELS = {
    "qb_opponent_history": "quarterback history",
    "availability": "availability",
    "pressure": "pressure",
    "explosives": "explosive plays",
    "early_down": "early downs",
    "third_down": "third down",
    "yac": "yards after the catch",
    "run_front": "the run front",
    "alignment": "formation",
    "motion": "motion",
    "play_action": "play action",
    "rpo": "RPOs",
    "screen": "the screen game",
    "coaching": "staff continuity",
    "coordinator": "coordinator change",
    "structural_change": "staff change",
    "weather": "weather",
    "travel": "travel",
    "scenario": "game state",
}


def _clean_family(value: Any) -> str:
    return str(value or "context").lower().replace(" ", "_")


def _label(family: str) -> str:
    return FAMILY_LABELS.get(family, family.replace("_", " "))


def _qb_from_title(title: Any) -> str:
    text = str(title or "").strip()
    if " vs " in text:
        return text.split(" vs ", 1)[0].strip()
    return "the quarterback"


def _pick_row(predictions: pd.DataFrame, game_id: str) -> pd.Series | None:
    if predictions is None or predictions.empty or "game_id" not in predictions.columns:
        return None
    match = predictions[predictions["game_id"].astype(str).eq(str(game_id))]
    return None if match.empty else match.iloc[0]


def _lead_pressure(slot: int, pick: str, leader: str, other: str, matchup: str) -> str:
    options = [
        f"Start with the pocket. {pick}'s case is that {leader} can turn ordinary long-yardage situations into the defining feature of {matchup}; {other} has to keep third-and-obvious off the menu.",
        f"{matchup} has a pressure economy: every lost early down gets more expensive for {other}. That is where {leader} can make the {pick} edge compound instead of merely survive.",
        f"The forecast does not need {pick} to win every phase. It needs {leader} to own the moments when {other} has to announce pass, because those snaps are where this matchup can stop being subtle.",
        f"There is a direct route for {pick} to control {matchup}: make the pocket shrink before the route concept has time to matter. {leader} has the better setup to do it.",
        f"Watch how often {other} gets a comfortable, on-schedule dropback. If the answer is 'not many,' the rest of the {pick} case gets much easier to understand.",
        f"The hidden scoreboard in {matchup} may be obvious passing downs. {leader} is better equipped to win those snaps, and {pick} benefits every time the game is forced into them.",
    ]
    return options[slot % len(options)]


def _lead_explosives(slot: int, pick: str, leader: str, other: str, matchup: str) -> str:
    options = [
        f"This is a geometry game. {leader} has the cleaner way to make the field suddenly smaller, while {other} would rather turn {matchup} into a sequence of patient twelve-play drives.",
        f"The fastest route through {matchup} belongs to {leader}. One or two chunk plays can do more for the {pick} case than a dozen tidy five-yard gains.",
        f"If {matchup} feels even snap to snap, do not assume it is even on the scoreboard. {leader}'s explosive-play edge gives {pick} a way to create separation without owning every possession.",
        f"The shortcut belongs to {leader}. {other} can defend well for ten snaps and still lose the drive on the eleventh, which is why the {pick} forecast is so sensitive to the big-play battle.",
        f"Field position can change violently in this matchup. {leader} is the side more likely to create that kind of swing, and {pick} does not need many of them before the game script tilts.",
        f"The {pick} forecast is betting on leverage, not volume. {leader}'s best plays are more capable of flipping the field in one shot; {other}'s job is to make every yard expensive.",
    ]
    return options[slot % len(options)]


def _lead_early_down(slot: int, pick: str, leader: str, other: str, matchup: str) -> str:
    options = [
        f"The important downs may be the boring ones. {leader} has the better chance to keep {matchup} on schedule, which lets the {pick} offense call what it wants instead of what the sticks demand.",
        f"For {pick}, the game starts before third down. If {leader} keeps winning first and second down, {other} has to defend the whole call sheet rather than hunt obvious situations.",
        f"Second-and-manageable is the quiet currency in {matchup}. {leader} is more likely to keep earning it, and that is how the {pick} case can become methodical instead of dramatic.",
        f"A lot of this forecast lives in down-and-distance. {leader} has the cleaner early-down profile, so {pick} is less likely to spend the afternoon asking its quarterback to rescue bad situations.",
        f"The easiest way for {pick} to make {matchup} look ordinary is to stay out of obvious passing downs. {leader} is better positioned to do that from the first series onward.",
    ]
    return options[slot % len(options)]


def _lead_qb_history(slot: int, pick: str, leader: str, other: str, matchup: str, title: Any) -> str:
    quarterback = _qb_from_title(title)
    options = [
        f"{quarterback} is not entering {matchup} with a blank notebook. The prior tape matters because it gives both sides a real reference point; the {pick} case turns on what remains transferable after the surrounding system changed.",
        f"There is actual memory in this quarterback matchup. {quarterback} has seen this opponent's problems before, so the interesting part is not the old box score—it is which answers still exist in 2026.",
        f"Prior meetings give {matchup} a useful baseline without turning it into a rerun. For {pick}, the value is in what {quarterback} already knows and what the current staff can still exploit.",
        f"This is one of the rare Week 1 games with meaningful quarterback history attached. {quarterback}'s old tape makes the matchup less hypothetical, while the current personnel keeps it from being predictive by itself.",
        f"The logos are only part of the familiarity here. {quarterback} has real experience in this matchup, and the {pick} read is about separating durable lessons from details that belonged to an older version of the teams.",
    ]
    return options[slot % len(options)]


def _lead_availability(slot: int, pick: str, leader: str, other: str, matchup: str, title: Any) -> str:
    options = [
        f"Before scheme comes the active roster. {matchup} has a live personnel question that can change what each side is able to call, even though LevLine does not invent a point value for it.",
        f"The first thing to re-check in {matchup} is personnel, not formation. The official availability picture can change the football logic around {pick} without becoming an unvalidated manual adjustment.",
        f"There is a roster-level hinge in {matchup}. Sunday Signal treats it as a change in what the teams can reasonably ask of the matchup—not as a license to make up injury points.",
        f"This forecast has a personnel footnote worth watching all the way to kickoff. If the active list changes, the tactical route to a {pick} win can change with it.",
    ]
    return options[slot % len(options)]


def _lead_generic(slot: int, family: str, pick: str, leader: str, other: str, matchup: str) -> str:
    label = _label(family)
    options = [
        f"The cleanest football lens in {matchup} is {label}. That part of the game tilts {leader}, giving the {pick} forecast a matchup-specific reason rather than a generic favorite's case.",
        f"For {pick}, {label} is the lever that matters most. If {leader} can keep that part of {matchup} on its terms, the rest of the forecast has room to breathe.",
        f"{matchup} has one matchup feature that keeps surfacing: {label}. It currently favors {leader}, and that is the thread connecting the football to the {pick} number.",
        f"The {pick} case becomes easiest to see through {label}. {leader} owns the better setup there, while {other} needs the game to be decided somewhere else.",
    ]
    return options[slot % len(options)]


def _lead(slot: int, family: str, pick: str, leader: str, other: str, matchup: str, title: Any) -> str:
    if family == "pressure":
        return _lead_pressure(slot, pick, leader, other, matchup)
    if family == "explosives":
        return _lead_explosives(slot, pick, leader, other, matchup)
    if family == "early_down":
        return _lead_early_down(slot, pick, leader, other, matchup)
    if family == "qb_opponent_history":
        return _lead_qb_history(slot, pick, leader, other, matchup, title)
    if family == "availability":
        return _lead_availability(slot, pick, leader, other, matchup, title)
    return _lead_generic(slot, family, pick, leader, other, matchup)


def _second(counter_slot: int, family: str, advantage: str | None, pick: str, opponent: str, matchup: str) -> str:
    label = _label(family)
    if advantage and advantage != pick:
        options = [
            f"The rebuttal belongs to {advantage}: {label}. If that becomes the dominant texture of {matchup}, the cleaner {pick} path gets a lot narrower.",
            f"The warning label is {label}. {advantage} owns that piece of the matchup, so the {pick} forecast is strongest when the game is decided somewhere else.",
            f"There is an honest countercase here: {advantage} has the better {label} setup. That is the part of {matchup} most capable of making LevLine uncomfortable.",
            f"What keeps this from being one-way is {label}. That edge sits with {advantage}, giving {opponent} a specific upset mechanism rather than a vague 'anything can happen' argument.",
            f"The upset path starts with {label}. {advantage} has the advantage there, and {pick} cannot afford to let that single matchup swallow the rest of the game.",
            f"LevLine can be right about the main {pick} edge and still lose if {advantage} turns {label} into the story. That is the tension worth carrying into kickoff.",
        ]
        return options[counter_slot % len(options)]
    if advantage == pick:
        options = [
            f"And the case has a second leg: {label} also tilts {pick}. That matters if the primary route gets neutralized.",
            f"{pick} is not leaning on one matchup alone. The {label} edge points the same way and gives the forecast another route to become true.",
            f"There is supporting evidence in a different part of the game too: {label} favors {pick}, making the case broader than the headline angle.",
            f"If the first plan stalls, {label} gives {pick} another place to find leverage. That redundancy is part of why the overall profile holds up.",
            f"The supporting thread is {label}, another area where {pick} has the cleaner setup. The forecast has more than one way to cash its football thesis.",
        ]
        return options[counter_slot % len(options)]
    options = [
        f"The surrounding context is {label}. It does not belong cleanly to either sideline, but it can change which version of {matchup} actually shows up.",
        f"One neutral variable still matters: {label}. It is context around the {pick} case rather than a reason to reverse it.",
        f"The extra wrinkle is {label}. It changes the texture of {matchup} without pretending to be a standalone edge.",
    ]
    return options[counter_slot % len(options)]


def polish_preview_slate(previews: dict[str, dict], predictions: pd.DataFrame) -> dict[str, dict]:
    """Give same-family games different cadence while preserving the evidence spine.

    The underlying story selection remains deterministic and sourced. This pass
    only changes the top-level synthesis paragraph; detail modules below retain
    the exact evidence, samples and source links.
    """
    primary_counts: dict[str, int] = defaultdict(int)
    secondary_counts: dict[tuple[str, str], int] = defaultdict(int)

    for game_id in sorted(previews):
        preview = previews[game_id]
        row = _pick_row(predictions, game_id)
        if row is None:
            continue
        home = str(row.get("home_team"))
        away = str(row.get("away_team"))
        pick = str(row.get("pick"))
        opponent = away if pick == home else home
        matchup = f"{away}-{home}"
        spine = preview.get("story_spine") or {}
        primary_family = _clean_family(spine.get("primary_family"))
        primary_team = str(spine.get("primary_advantage_team") or pick)
        primary_title = spine.get("primary_title")
        if spine.get("primary_mode") == "counter":
            # Counter-led Reads are already explicitly framed by the base composer.
            continue

        primary_slot = primary_counts[primary_family]
        primary_counts[primary_family] += 1
        lead = _lead(primary_slot, primary_family, pick, primary_team, opponent, matchup, primary_title)

        secondary_family = _clean_family(spine.get("secondary_family"))
        secondary_team = spine.get("secondary_advantage_team")
        second_key = (primary_family, secondary_family)
        secondary_slot = secondary_counts[second_key]
        secondary_counts[second_key] += 1
        second = "" if not spine.get("secondary_family") else _second(secondary_slot, secondary_family, secondary_team, pick, opponent, matchup)

        paragraphs = list(preview.get("paragraphs") or [])
        synthesis = f"{lead} {second}".strip()
        if paragraphs:
            paragraphs[0] = synthesis
        else:
            paragraphs = [synthesis]
        preview["paragraphs"] = paragraphs
        preview["editorial_voice"] = {
            "primary_variant": primary_slot,
            "secondary_variant": secondary_slot if spine.get("secondary_family") else None,
            "slate_aware": True,
        }
    return previews

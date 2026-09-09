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
        f"Start with the pocket. The case for {pick} is that long-yardage situations can become the defining feature of {matchup}; {other} has to keep third-and-obvious off the menu.",
        f"{matchup} has a pressure economy: every lost early down gets more expensive for {other}. That is where the edge can compound instead of merely survive for {pick}.",
        f"The forecast does not need {pick} to win every phase. It needs the pressure advantage to own the moments when {other} has to announce pass, because those snaps are where this matchup can stop being subtle.",
        f"There is a direct route for {pick} to control {matchup}: make the pocket shrink before the route concept has time to matter. The setup favors that approach.",
        f"Watch how often {other} gets a comfortable, on-schedule dropback. If the answer is 'not many,' the rest of the {pick} case gets much easier to understand.",
        f"The hidden scoreboard in {matchup} may be obvious passing downs. Those snaps favor {leader}, and every one of them makes the {pick} path cleaner.",
        f"The most expensive mistake for {other} may be arriving at third down with only one credible answer. The pressure edge gives {pick} a chance to turn predictable downs into possession swings.",
        f"This matchup gets simpler for {pick} every time the down-and-distance gets harder for {other}. The pressure profile is built to make those predictable pass situations feel even more predictable.",
        f"Pocket comfort is the resource to watch in {matchup}. {leader} has the better chance to ration it, which can force {other} to play at a faster tempo than it wants.",
        f"The pressure edge matters here because it changes the menu, not just the sack total. If {other} keeps getting sped up, {pick} gets to defend a narrower version of the offense.",
    ]
    return options[slot % len(options)]


def _lead_explosives(slot: int, pick: str, leader: str, other: str, matchup: str) -> str:
    options = [
        f"This is a geometry game. {leader} has the cleaner way to make the field suddenly smaller, while {other} would rather turn {matchup} into a sequence of patient twelve-play drives.",
        f"The fastest route through {matchup} belongs to {leader}. One or two chunk plays can do more for the {pick} case than a dozen tidy five-yard gains.",
        f"If {matchup} feels even snap to snap, do not assume it is even on the scoreboard. The explosive-play edge gives {pick} a way to create separation without owning every possession.",
        f"The shortcut belongs to {leader}. {other} can defend well for ten snaps and still lose the drive on the eleventh, which is why the {pick} forecast is so sensitive to the big-play battle.",
        f"Field position can change violently in this matchup. {leader} is more likely to create that kind of swing, and {pick} does not need many before the game script tilts.",
        f"The {pick} forecast is betting on leverage, not volume. The best plays on that side are more capable of flipping the field in one shot; {other}'s job is to make every yard expensive.",
        f"The possession count is secondary if {leader} keeps winning the high-value snaps. In {matchup}, the {pick} side has the cleaner path to scoring without needing a perfect drive.",
        f"A defense can be right nine times and still be wrong once in a way that costs seven points. That asymmetry is what gives the {pick} case its clearest leverage in {matchup}.",
    ]
    return options[slot % len(options)]


def _lead_early_down(slot: int, pick: str, leader: str, other: str, matchup: str) -> str:
    options = [
        f"The important downs may be the boring ones. {leader} has the better chance to keep {matchup} on schedule, which lets the {pick} offense call what it wants instead of what the sticks demand.",
        f"For {pick}, the game starts before third down. If the early-down edge holds, {other} has to defend the whole call sheet rather than hunt obvious situations.",
        f"Second-and-manageable is the quiet currency in {matchup}. {leader} is more likely to keep earning it, and that is how the {pick} case can become methodical instead of dramatic.",
        f"A lot of this forecast lives in down-and-distance. The cleaner early-down profile means {pick} is less likely to spend the afternoon asking its quarterback to rescue bad situations.",
        f"The easiest way for {pick} to make {matchup} look ordinary is to stay out of obvious passing downs. The early-down setup makes that path realistic from the first series onward.",
        f"First down is where the playbook either stays wide or starts collapsing. {leader} has the better chance to keep all of its answers available, which is the foundation of the {pick} case.",
        f"The leverage in {matchup} can be built quietly: four useful yards here, a manageable second down there. Those small wins are how {pick} can force {other} to defend everything.",
        f"The {pick} path is less about one spectacular call than avoiding bad questions. The early-down edge reduces how often {other} gets to dictate what comes next.",
    ]
    return options[slot % len(options)]


def _lead_qb_history(slot: int, pick: str, leader: str, other: str, matchup: str, title: Any) -> str:
    quarterback = _qb_from_title(title)
    options = [
        f"{quarterback} is not entering {matchup} with a blank notebook. The prior tape gives both sides a real reference point; the {pick} case turns on what remains transferable after the surrounding system changed.",
        f"There is actual memory in this quarterback matchup. {quarterback} has seen this opponent's problems before, so the interesting part is not the old box score—it is which answers still exist in 2026.",
        f"Prior meetings give {matchup} a useful baseline without turning it into a rerun. For {pick}, the value is in what {quarterback} already knows and what the current staff can still exploit.",
        f"This is one of the rare Week 1 games with meaningful quarterback history attached. {quarterback}'s old tape makes the matchup less hypothetical, while the current personnel keeps it from being predictive by itself.",
        f"The logos are only part of the familiarity here. {quarterback} has real experience in this matchup, and the {pick} read is about separating durable lessons from details that belonged to an older version of the teams.",
        f"The opponent is familiar to {quarterback}, but the context is not frozen in time. That makes {matchup} useful as a recognition test for the {pick} case rather than a simple replay of prior results.",
        f"Old meetings matter most when they reveal a problem that still exists. {quarterback} gives {pick} a head start on that search in {matchup}, while the current staff determines whether the old answer still fits.",
        f"There is enough quarterback history here to inform the opening hypothesis, not enough to end the argument. {quarterback}'s experience gives the {pick} side a reference point that still has to survive the 2026 version of {matchup}.",
    ]
    return options[slot % len(options)]


def _lead_availability(slot: int, pick: str, leader: str, other: str, matchup: str, title: Any) -> str:
    options = [
        f"Before scheme comes the active roster. {matchup} has a live personnel question that can change what each side is able to call, even though LevLine does not invent a point value for it.",
        f"The first thing to re-check in {matchup} is personnel, not formation. The official availability picture can change the football logic around {pick} without becoming an unvalidated manual adjustment.",
        f"There is a roster-level hinge in {matchup}. Sunday Signal treats it as a change in what the teams can reasonably ask of the matchup—not as a license to make up injury points.",
        f"This forecast has a personnel footnote worth watching all the way to kickoff. If the active list changes, the tactical route to a {pick} win can change with it.",
        f"The matchup tree in {matchup} starts with who is actually available. That question can narrow or widen the {pick} path before any coordinator makes a call.",
        f"Some games begin with formation; this one begins with the inactive list. The personnel answer changes what the {pick} side can reasonably expect to attack.",
    ]
    return options[slot % len(options)]


def _lead_generic(slot: int, family: str, pick: str, leader: str, other: str, matchup: str) -> str:
    label = _label(family)
    options = [
        f"The cleanest football lens in {matchup} is {label}. That part of the game tilts {leader}, giving the {pick} forecast a matchup-specific reason rather than a generic favorite's case.",
        f"For {pick}, {label} is the lever that matters most. If {leader} can keep that part of {matchup} on its terms, the rest of the forecast has room to breathe.",
        f"{matchup} has one feature that keeps surfacing: {label}. It currently favors {leader}, and that is the thread connecting the football to the {pick} number.",
        f"The {pick} case becomes easiest to see through {label}. {leader} owns the better setup there, while {other} needs the game to be decided somewhere else.",
        f"If one layer deserves the first look in {matchup}, it is {label}. That matchup currently belongs to {leader}, which gives the {pick} forecast its clearest football anchor.",
        f"The argument for {pick} is not abstract here: it runs through {label}. {leader} has the better setup in that phase, while {other} needs to redirect the game toward a different question.",
        f"The lens that best explains {pick} is {label}. {leader} owns that piece, and the rest of the game is about whether {other} can move the fight elsewhere.",
        f"One feature keeps the {pick} case grounded in football rather than probability alone: {label}. It tilts toward {leader} and gives {matchup} a specific pressure point.",
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
            f"The answer on the other side is {advantage}'s {label} edge; if it becomes the dominant texture of {matchup}, the cleaner {pick} path gets much narrower.",
            f"The warning is {label}: {advantage} owns that piece of the matchup, so the {pick} forecast is strongest when the game is decided somewhere else.",
            f"There is an honest countercase here. {advantage} has the better {label} setup, the part of {matchup} most capable of making LevLine uncomfortable.",
            f"What keeps this from being one-way is {label}. That edge sits with {advantage}, giving {opponent} a specific upset mechanism rather than a vague 'anything can happen' argument.",
            f"The upset path starts with {label}. That advantage belongs to {advantage}, and {pick} cannot afford to let a single matchup swallow the rest of the game.",
            f"LevLine can be right about the main {pick} edge and still lose if {advantage} turns {label} into the story. That is the tension worth carrying into kickoff.",
        ]
        return options[counter_slot % len(options)]
    if advantage == pick:
        options = [
            f"The case also has a second leg: {label} tilts {pick}. That matters if the primary route gets neutralized.",
            f"{pick} is not leaning on one matchup alone. The {label} edge points the same way and gives the forecast another route to become true.",
            f"A different part of the game supports the same side too: {label} favors {pick}, making the case broader than the headline angle.",
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
    """Make each game file evidence-led instead of template-led."""
    def advantage(item: dict[str, Any] | None) -> str | None:
        if not item:
            return None
        meta = item.get("metadata") or {}
        value = item.get("advantage_team") or meta.get("advantage_team")
        return str(value) if value else None

    def family(item: dict[str, Any] | None) -> str:
        if not item:
            return "context"
        meta = item.get("metadata") or {}
        return _clean_family(meta.get("family") or item.get("family") or item.get("category"))

    def candidates(preview: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key in ("key_factors", "matchup_meter", "notebook"):
            for item in preview.get(key) or []:
                if isinstance(item, dict):
                    rows.append(item)
        return rows

    def detail(preview: dict[str, Any], title: Any) -> dict[str, Any] | None:
        wanted = str(title or "").strip()
        return next((item for item in candidates(preview) if str(item.get("title") or "").strip() == wanted), None) if wanted else None

    def usable(item: dict[str, Any] | None) -> bool:
        if not item:
            return False
        summary = str(item.get("summary") or "").strip()
        lowered = summary.lower()
        if len(summary.split()) < 7:
            return False
        fam = family(item)
        if ("nflverse schedule sample" in lowered and fam != "rivalry") or "need variance in the high-leverage parts" in lowered:
            return False
        return True

    def specific_summary(item: dict[str, Any]) -> str:
        summary = str(item.get("summary") or "").strip()
        fam = family(item)
        if not summary:
            return ""
        if fam == "qb_opponent_history":
            match = re.search(
                r"^In the nflverse play-by-play sample since 2021, (.+?) has ([0-9]+) meaningful games against ([A-Z]{2,4}); the most recent was (.+?)\. Over ([0-9]+) charted dropbacks in those games, (?:he|she|they) averaged ([+\-][0-9.]+) EPA/dropback with a ([0-9.]+)% positive-EPA rate",
                summary,
            )
            if match:
                quarterback, games, opponent, latest, dropbacks, epa, positive = match.groups()
                return f"{quarterback}–{opponent} recent sample: {games} meaningful games, {dropbacks} dropbacks, {epa} EPA/dropback, {positive}% positive-EPA; latest: {latest}."
        if fam == "rivalry":
            match = re.search(
                r"^Since 2021, ([A-Za-z0-9]+) and ([A-Za-z0-9]+) have played ([0-9]+) completed games in the nflverse schedule sample: ([A-Za-z0-9]+) is ([0-9]+-[0-9]+)\. The most recent finished (.+?)\.$",
                summary,
            )
            if match:
                team_a, team_b, games, leader, record, latest = match.groups()
                return f"{team_a}-{team_b} since 2021: {games} meetings, {leader} {record}; latest: {latest}."
        if fam == "pressure":
            match = re.search(r"^([A-Z]{2,4}) gave up sacks on ([0-9.]+)% of pass plays last season; ([A-Z]{2,4}) got home on ([0-9.]+)%", summary)
            if match:
                protected, allowed, rusher, created = match.groups()
                return f"{protected} protection: {allowed}% sack rate; {rusher} pass rush: {created}% sack rate."
        if fam == "explosives":
            match = re.search(r"^([A-Z]{2,4}) hit a 20\+ yard pass on ([0-9.]+)% of pass plays; ([A-Z]{2,4}) allowed one on ([0-9.]+)%", summary)
            if match:
                offense, created, defense, allowed = match.groups()
                return f"{offense} explosives: {created}% of passes gained 20+ yards; {defense} allowed 20+ on {allowed}%."
        if fam == "early_down":
            match = re.search(r"^([A-Z]{2,4}) threw on ([0-9.]+)% of first- and second-down plays and averaged ([+\-][0-9.]+) EPA per early-down pass\. ([A-Z]{2,4}) allowed ([+\-][0-9.]+)", summary)
            if match:
                offense, rate, epa, defense, allowed = match.groups()
                return f"{offense} early downs: {rate}% pass rate and {epa} EPA per pass; {defense} allowed {allowed}."
        title = str(item.get("title") or _label(fam)).strip().rstrip('.:')

        # Some downstream evidence enrichers intentionally replace raw statistical
        # summaries with short football interpretations. Those interpretations are
        # useful in detail cards, but their reusable sentence tails must never leak
        # back into the public game-file cases. Keep the public renderer anchored to
        # the matchup title and the actual side of the evidence.
        if fam == "pressure":
            tilt = re.search(r"pressure matchup tilts ([A-Z]{2,4})", summary, re.I)
            if tilt:
                return f"{title}: pass-rush leverage favors {tilt.group(1).upper()}."
        if fam == "explosives":
            tilt = re.search(r"chunk-play path tilts ([A-Z]{2,4})", summary, re.I)
            if tilt:
                return f"{title}: explosive-pass leverage favors {tilt.group(1).upper()}."
        if fam == "early_down":
            tilt = re.search(r"early-down leverage tilts ([A-Z]{2,4})", summary, re.I)
            if tilt:
                return f"{title}: early-down leverage favors {tilt.group(1).upper()}."
        if fam in {"staff_impact", "coaching", "personnel", "injury", "history", "qb_opponent_history"}:
            return f"{title}: {_label(fam)} context."
        if fam == "rivalry":
            return f"{title}: rivalry history."

        sentences = [part.strip() for part in summary.split(". ") if part.strip()]
        if not sentences:
            return summary
        if fam in {"international_event", "international_travel"}:
            kept = sentences[:2]
            result = ". ".join(kept)
            if summary.endswith(".") and not result.endswith("."):
                result += "."
            return result

        # Fail closed on unparsed public evidence: use a compact title-anchored
        # formulation instead of importing an arbitrary reusable source sentence.
        return f"{title}: {_label(fam)} evidence."

    def beat(item: dict[str, Any]) -> str:
        title = str(item.get("title") or "").strip().rstrip('.:')
        summary = specific_summary(item)
        return summary if not title or title.lower() in summary.lower()[: max(90, len(title) + 15)] else f"{title}: {summary}"

    def read_hook(slot: int, item: dict[str, Any], pick: str, opponent: str) -> str:
        title = str(item.get("title") or _label(family(item))).strip().rstrip('.:')
        hooks = [
            f"{title} gets first billing in this file. It is the sourced matchup fact that most clearly explains why {pick} has a path to control the terms rather than merely survive them.",
            f"The opening question is not the spread; it is {title}. That evidence tells us which part of the field {opponent} must solve before the broader forecast can be trusted.",
            f"Build the football case from {title} outward. The number matters because this particular matchup can dictate play selection, down-and-distance, and the kind of possessions both staffs are forced to manage.",
            f"{title} is the hinge worth isolating before anything else. If that edge shows up as the source data suggests, the {pick} projection has a concrete mechanism instead of a generic favorite's argument.",
            f"This matchup file starts below the headline level with {title}. It gives the forecast a tactical center of gravity and identifies exactly where {opponent} has to keep the game from tilting.",
            f"The most useful first read is {title}, not a broad power-rating story. That sourced detail narrows the game to a football problem the {pick} side can repeatedly test.",
            f"There is one place to begin the film-room version of this forecast: {title}. Its value is that it connects the underlying data to a repeatable on-field question for both teams.",
            f"{title} deserves the first paragraph because it can alter the menu available to each coordinator. That makes it more informative for this game than a generic statement about which roster is stronger.",
            f"Strip away the win probability for a moment and look at {title}. This is the evidence thread most capable of turning the model's preference into a recognizable game script.",
            f"The clearest route from data to football runs through {title}. It tells us what {pick} can press, what {opponent} must protect, and where the forecast is most likely to become visible.",
            f"Treat {title} as the matchup's organizing fact. It does not decide the game by itself, but it gives the {pick} case a specific lever that can be checked snap by snap.",
            f"Before the game branches into turnovers, fourth downs, and variance, {title} supplies the cleanest baseline. It is the part of this matchup where the evidence gives one side a defined structural advantage.",
            f"The first layer of this forecast is {title}. That detail matters because it can force a response from {opponent}, and forced responses are where a pregame edge starts changing the rest of the call sheet.",
            f"{title} is the best place to test whether the model's preference has real football substance. The evidence there creates a matchup-specific burden that {opponent} cannot solve with probability or reputation.",
            f"Rather than start with the final percentage, start with {title}. It provides the most concrete explanation for how {pick} can create leverage and where the opposing plan has to be unusually clean.",
            f"This read is anchored by {title} because it links source data to an identifiable coaching decision. If the matchup behaves that way, the {pick} side can make the game look like its preferred version.",
        ]
        return hooks[slot % len(hooks)]

    special_families = {"international_event", "rivalry", "international_travel"}
    for slate_index, game_id in enumerate(sorted(previews)):
        preview = previews[game_id]
        row = _pick_row(predictions, game_id)
        if row is None:
            continue
        home, away, pick = str(row.get("home_team")), str(row.get("away_team")), str(row.get("pick"))
        opponent = away if pick == home else home
        spine = preview.get("story_spine") or {}
        all_items = candidates(preview)

        selected: list[dict[str, Any]] = []
        special = next((item for item in all_items if family(item) in special_families and usable(item)), None)
        if special:
            selected.append(special)
        for title in (spine.get("primary_title"), spine.get("secondary_title")):
            item = detail(preview, title)
            if usable(item) and item not in selected:
                selected.append(item)
        for item in preview.get("key_factors") or []:
            if usable(item) and item not in selected:
                selected.append(item)
            if len(selected) >= 3:
                break

        if selected:
            preview["headline"] = str(selected[0].get("title") or f"{away}-{home}").strip()
            evidence_beats = " ".join(beat(item) for item in selected[:2]).strip()
            if family(selected[0]) in special_families:
                lead = evidence_beats
            else:
                lead = f"{read_hook(slate_index, selected[0], pick, opponent)} {evidence_beats}".strip()
        else:
            preview["headline"] = f"{away}-{home} matchup file"
            lead = f"{away}-{home}: sourced lead unavailable."
        paragraphs = list(preview.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = lead
        else:
            paragraphs = [lead]
        preview["paragraphs"] = paragraphs

        support = next((item for item in all_items if usable(item) and advantage(item) == pick), None)
        counter = next((item for item in all_items if usable(item) and advantage(item) == opponent), None)
        neutral = [item for item in selected if usable(item)]
        pick_item = support or (neutral[0] if neutral else None)
        opponent_item = counter or (neutral[1] if len(neutral) > 1 else None)
        preview["case_for_pick"] = beat(pick_item) if pick_item else f"{pick} in {away}-{home}: featured evidence unavailable."
        preview["case_for_opponent"] = beat(opponent_item) if opponent_item else f"{opponent} in {away}-{home}: featured counter unavailable."
        preview["what_could_make_us_wrong"] = (
            f"{opponent}'s counter in {away}-{home}: {specific_summary(counter)}" if counter
            else f"{away}-{home}: no sourced {opponent} counter clears the publication threshold."
        )
        preview["editorial_voice"] = {
            "evidence_led": True,
            "game_specific": True,
            "slate_aware": True,
            "primary_variant": slate_index,
            "secondary_variant": slate_index,
            "lead_items": [str(item.get("title") or "") for item in selected[:2]],
        }
    return previews

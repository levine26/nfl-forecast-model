from __future__ import annotations

import re
from typing import Any

import pandas as pd


TEAM = {
    "ARI":"Cardinals","ATL":"Falcons","BAL":"Ravens","BUF":"Bills","CAR":"Panthers","CHI":"Bears","CIN":"Bengals","CLE":"Browns",
    "DAL":"Cowboys","DEN":"Broncos","DET":"Lions","GB":"Packers","HOU":"Texans","IND":"Colts","JAX":"Jaguars","JAC":"Jaguars",
    "KC":"Chiefs","LA":"Rams","LAC":"Chargers","LV":"Raiders","MIA":"Dolphins","MIN":"Vikings","NE":"Patriots","NO":"Saints",
    "NYG":"Giants","NYJ":"Jets","PHI":"Eagles","PIT":"Steelers","SEA":"Seahawks","SF":"49ers","TB":"Buccaneers","TEN":"Titans","WAS":"Commanders",
}
BANNED = (
    "two distinct levers", "real matchup counter-signal", "the answer on the other side", "cleaner path gets much narrower",
    "there is actual memory in this quarterback matchup", "prior meetings give", "this is a geometry game",
    "the case also has a second leg", "the supporting thread is", "the extra wrinkle is",
)
STANDARDIZED_STATUS_PATTERNS = (
    re.compile(
        r"\bthe official nfl injury report lists\b.*?\b(?:did not participate in practice|limited participation in practice|full participation in practice|out|doubtful|questionable)\b",
        re.I,
    ),
    re.compile(
        r"\bno game[- ]status designation is posted yet,?\s+so this is treated as availability context rather than an assumption the player will be inactive\b",
        re.I,
    ),
    re.compile(r"\blevline does not make up an injury point value for it\b", re.I),
)
STAT_BOILERPLATE_TERMS = {
    "plays", "play", "attempts", "attempt", "dropbacks", "dropback", "snaps", "snap",
    "targets", "target", "yards", "yard", "sacks", "sack", "rate", "epa", "pressure",
    "pressures", "blitz", "blitzes", "passes", "pass", "rushes", "rush",
}
STANDARDIZED_EVIDENCE_FRAGMENTS = (
    "passing game backdrop",
    "relevant opponent side profile",
    "usage is context for the role",
)


def _nick(team: Any) -> str:
    return TEAM.get(str(team or ""), str(team or ""))


def _family(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return str((item.get("metadata") or {}).get("family") or item.get("family") or item.get("category") or "").lower()


def _advantage(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    value = (item.get("metadata") or {}).get("advantage_team") or item.get("advantage_team")
    return str(value) if value else None


def _subject(title: str) -> str | None:
    text = str(title or "").strip()
    if " vs " in text:
        return text.split(" vs ", 1)[0].strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return None


def _headline(pick: str, opponent: str, primary: dict[str, Any] | None) -> str:
    p, o = _nick(pick), _nick(opponent)
    family = _family(primary)
    title = str((primary or {}).get("title") or "")
    subject = _subject(title)
    if family == "pressure":
        return f"{o}' protection is the pressure point against the {p}"
    if family == "explosives":
        return f"The {p}' shortcut is the big-play battle"
    if family == "early_down":
        return f"The {p} can make this game easier before third down"
    if family == "third_down":
        return f"Third down is where the {p} can tilt the possession count"
    if family == "yac":
        return f"The {p} can turn ordinary completions into the swing plays"
    if family == "qb_opponent_history" and subject:
        return f"{subject} has seen this opponent before — but the context has changed"
    if family == "availability" and subject:
        return f"{subject}'s status is the matchup hinge"
    if family in {"staff_impact", "coaching", "coordinator", "structural_change"}:
        return f"A new decision-maker changes the starting point for the {p}"
    return f"The {p} get the edge, but this game has more than one argument"


def _notebook_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "international_event": 100,
        "rivalry": 95,
        "international_travel": 90,
        "recent_series": 80,
        "career_qb_opponent_ledger": 75,
        "ngs_qb_profile": 65,
        "staff_impact": 60,
        "structural_change": 55,
    }
    candidates = [item for item in items if _family(item) in priority]
    candidates.sort(key=lambda item: (priority[_family(item)], int(item.get("sample_size") or 0)), reverse=True)
    selected = []
    used_family_count: dict[str, int] = {}
    for item in candidates:
        family = _family(item)
        if family in {"career_qb_opponent_ledger", "ngs_qb_profile"} and used_family_count.get("players", 0) >= 2:
            continue
        selected.append(item)
        if family in {"career_qb_opponent_ledger", "ngs_qb_profile"}:
            used_family_count["players"] = used_family_count.get("players", 0) + 1
        if len(selected) >= 5:
            break
    return selected


def _editorial_uniqueness_text(text: str) -> str:
    """Remove standardized factual/status boilerplate before substantive prose QA."""
    scrubbed = str(text or "")
    for pattern in STANDARDIZED_STATUS_PATTERNS:
        scrubbed = pattern.sub(" ", scrubbed)
    return scrubbed


def _uniqueness_segments(text: str) -> list[str]:
    """Never manufacture duplicate prose by sliding an n-gram across sentences."""
    scrubbed = _editorial_uniqueness_text(text)
    return [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+|(?<=;)\s+", scrubbed)
        if segment.strip()
    ]


def _is_standardized_fact_ngram(words: list[str]) -> bool:
    """Exempt evidence-reporting scaffolds while keeping interpretation prose gated."""
    gram = " ".join(words)
    if "last season" in gram and any(token in STAT_BOILERPLATE_TERMS for token in words):
        return True
    if any(fragment in gram for fragment in STANDARDIZED_EVIDENCE_FRAGMENTS):
        return True
    return False


def finalize_previews(predictions: pd.DataFrame, previews: dict[str, dict[str, Any]], evidence: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = {str(row.game_id): row for _, row in predictions.iterrows()}
    headlines = []
    for game_id, preview in previews.items():
        row = rows.get(str(game_id))
        if row is None:
            continue
        items = list(evidence.get(str(game_id), []))
        by_title = {str(item.get("title") or ""): item for item in items}
        pick = str(row.get("pick")); home = str(row.get("home_team")); away = str(row.get("away_team"))
        opponent = away if pick == home else home

        for factor in preview.get("key_factors") or []:
            match = by_title.get(str(factor.get("title") or ""))
            if match and match.get("summary"):
                factor["summary"] = str(match["summary"])
                factor["source_url"] = match.get("source_url")
                factor["source_name"] = match.get("source_name")

        for meter in preview.get("matchup_meter") or []:
            match = by_title.get(str(meter.get("title") or ""))
            if match and match.get("summary"):
                meter["summary"] = str(match["summary"])

        existing = {str(item.get("title") or "") for item in preview.get("notebook") or []}
        notebook = list(preview.get("notebook") or [])
        for item in _notebook_candidates(items):
            title = str(item.get("title") or "Notebook")
            if title in existing:
                continue
            notebook.append({
                "title": title,
                "summary": str(item.get("summary") or ""),
                "source_url": item.get("source_url"),
                "source_name": item.get("source_name"),
                "family": _family(item),
                "provenance_grade": (item.get("metadata") or {}).get("provenance_grade"),
            })
            existing.add(title)
        preview["notebook"] = notebook[:5]

        current = str(preview.get("headline") or "")
        is_special = bool(re.search(r"Melbourne|Australia|rivalry", current, re.I))
        is_game_specific = bool((preview.get("editorial_voice") or {}).get("game_specific"))
        if not is_special and not is_game_specific:
            primary_title = str((preview.get("story_spine") or {}).get("primary_title") or "")
            primary = by_title.get(primary_title)
            if primary is None:
                primary = next((item for item in items if _advantage(item) == pick), None)
            preview["headline"] = _headline(pick, opponent, primary)
        headlines.append(str(preview.get("headline") or ""))
        preview["editorial_version"] = "story-desk-v3"

    public = " ".join(
        " ".join([
            str(preview.get("headline") or ""),
            " ".join(str(x) for x in (preview.get("paragraphs") or [])),
            str(preview.get("case_for_pick") or ""),
            str(preview.get("case_for_opponent") or ""),
            str(preview.get("what_could_make_us_wrong") or ""),
        ]).lower()
        for preview in previews.values()
    )
    found = [phrase for phrase in BANNED if phrase in public]
    if found:
        raise ValueError(f"publication still contains banned template phrases: {found}")

    ngram_games: dict[str, set[str]] = {}
    for game_id, preview in previews.items():
        paragraphs = preview.get("paragraphs") or []
        texts = [str(preview.get("headline") or "")]
        if paragraphs:
            texts.append(str(paragraphs[0]))
        texts.extend([
            str(preview.get("case_for_pick") or ""),
            str(preview.get("case_for_opponent") or ""),
            str(preview.get("what_could_make_us_wrong") or ""),
        ])
        for text in texts:
            for segment in _uniqueness_segments(text):
                words = re.findall(r"\d+(?:\.\d+)?|[a-z]+(?:'[a-z]+)?", segment.lower())
                for index in range(max(0, len(words) - 6)):
                    window = words[index:index+7]
                    if _is_standardized_fact_ngram(window):
                        continue
                    gram = " ".join(window)
                    ngram_games.setdefault(gram, set()).add(str(game_id))
    repeated = {gram: sorted(games) for gram, games in ngram_games.items() if len(games) > 1}
    if repeated:
        sample = list(repeated.items())[:5]
        raise ValueError(f"publication repeats game-file prose across matchups: {sample}")

    if len(headlines) != len(set(headlines)):
        raise ValueError("publication headlines are not unique across the slate")
    return {
        "status":"healthy",
        "editorial_version":"story-desk-v3",
        "games":len(headlines),
        "unique_headlines":len(set(headlines)),
        "guardrail":"Final editorial pass changes only public explanation and story hierarchy, never LevLine probabilities.",
    }

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _num(value):
    try:
        value = float(value)
        return None if pd.isna(value) else round(value, 4)
    except Exception:
        return None


def _pick_probability(row: pd.Series, field: str) -> float | None:
    value = _num(row.get(field))
    if value is None:
        return None
    return round(value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value, 4)


def _packet(row: pd.Series, previews: dict, evidence: dict) -> dict:
    gid = str(row.get("game_id"))
    preview = previews.get(gid, {}) if isinstance(previews, dict) else {}
    reported = []
    for item in preview.get("reported_sources") or []:
        if not isinstance(item, dict):
            continue
        reported.append({
            "name": item.get("source_name"),
            "title": item.get("title"),
            "url": item.get("source_url"),
            "as_of": item.get("as_of"),
        })

    football = []
    for item in evidence.get(gid, []) if isinstance(evidence, dict) else []:
        if len(football) >= 8:
            break
        if not isinstance(item, dict):
            continue
        strength = str(item.get("strength") or "")
        if strength not in {"Strong", "Moderate"}:
            continue
        family = str((item.get("metadata") or {}).get("family") or item.get("category") or "")
        if family == "reported_angle":
            continue
        football.append({
            "family": family,
            "title": item.get("title"),
            "summary": item.get("summary"),
            "advantage_team": item.get("advantage_team"),
            "strength": strength,
            "source_name": item.get("source_name"),
            "source_url": item.get("source_url"),
        })

    return {
        "game_id": gid,
        "season": int(float(row.get("season"))),
        "week": int(float(row.get("week"))),
        "gameday": str(row.get("gameday")),
        "gametime": str(row.get("gametime")),
        "away_team": str(row.get("away_team")),
        "home_team": str(row.get("home_team")),
        "levline_pick": str(row.get("pick")),
        "levline_pick_probability": _pick_probability(row, "final_home_prob"),
        "pure_pick_probability": _pick_probability(row, "pure_home_prob"),
        "market_pick_probability": _pick_probability(row, "market_home_prob"),
        "expected_margin_home": _num(row.get("expected_margin")),
        "market_spread_home": _num(row.get("spread_line")),
        "projected_score": str(row.get("projected_score") or ""),
        "confidence": str(row.get("confidence") or ""),
        "model_version": str(row.get("model_version") or ""),
        "production_blend": "75% PURE / 25% MARKET",
        "discovered_reporting": reported[:6],
        "verified_football_context": football,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--prompt-file", default="/tmp/sunday-signal-media-prompt.txt")
    args = parser.parse_args()
    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    previews = json.loads((out / "game_previews.json").read_text())
    evidence = json.loads((out / "contextual_evidence.json").read_text())
    packets = [_packet(row, previews, evidence) for _, row in predictions.iterrows()]

    prompt = """You are the senior NFL preview writer for Sunday Signal. Research and write the public game preview for every game below.

THIS IS A MATCHUP PREVIEW, NOT A NEWS ROUNDUP.
Every Read must contain exactly TWO paragraphs with different jobs.

PARAGRAPH 1 — THE MATCHUP
Write 55-100 words explaining how the game is likely to be decided. Identify the actual football tension: quarterback situation, protection/pass rush, coverage matchup, explosive plays, early-down efficiency, run-game leverage, injuries, coaching changes, travel/weather, or another concrete factor. Current reporting should inform the paragraph, but NEVER copy article headlines into prose and NEVER write "according to [outlet]" sentence after sentence. Synthesize the reporting into one coherent preview. The paragraph must discuss both teams and explain what each side needs to do.

PARAGRAPH 2 — WHY LEVLINE PICKS THIS SIDE
Write 60-110 words explaining the model decision explicitly. State LevLine's win probability for the picked team. Explain the 75% PURE / 25% MARKET blend using the supplied PURE and market pick-side probabilities when both exist. State the projected margin/model line and projected score whenever supplied. State the market spread whenever supplied, and compare it directly with LevLine's model line so the disagreement or agreement is explicit. Tie those numbers to one or two verified football factors from the packet so the paragraph answers WHY the model lands where it does. Do not pretend a factor is a model feature unless the packet says it is; describe it as contextual support when appropriate. The FINAL SENTENCE MUST be exactly: "The pick: <picked team name> moneyline."

VOICE
- Human NFL analyst: clear, confident, conversational, specific.
- No database labels such as "DEN-KC market gap" or "player history context."
- No headline dumps, SEO language, TV/live-stream information, or generic betting-copy filler.
- Avoid phrases such as "coverage highlights", "pressure note", "history note", "the cleanest lens", "the hinge", "the matchup file", "strip away the probability", "consensus pricing and the football-only model tell different versions", or "keeps enough of that split visible to matter".
- Do not write raw source headlines followed by "according to".
- Do not use PURE as a mysterious standalone noun. Explain it naturally as Sunday Signal's football-only model component.
- Do not invent injuries, roster facts, statistics, model inputs, source URLs, or causal claims.
- Paraphrase reporting. Quotes should be avoided unless necessary.
- Vary sentence structure across the slate.

RESEARCH PRIORITY
1. ESPN / ESPN NFL Nation
2. The Athletic / New York Times
3. NFL.com / official team reporting
4. AP, CBS Sports, Yahoo Sports, NBC Sports, FOX Sports, Sports Illustrated
5. Credible attributable public X/Twitter reporting when accessible
Prefer the last 7 days, and the last 48 hours for injuries/starters/availability. Use at least two independent approved-domain sources per game whenever possible.

OUTPUT
Return ONLY one syntactically valid JSON object, no Markdown and no commentary, with exactly this schema:
{"games":{"GAME_ID":{"headline":"matchup-oriented headline","paragraph1":"...","paragraph2":"...","sources":[{"name":"ESPN","title":"article/report title","url":"https://..."},{"name":"NFL.com","title":"...","url":"https://..."}]}}}
Every supplied game_id must appear exactly once.

CRITICAL SERIALIZATION RULES
- The response must parse with a standard JSON parser exactly as returned.
- Use JSON double quotes only as delimiters. Escape every literal double quote inside strings, or paraphrase/remove it.
- Do not use trailing commas, comments, Markdown fences, concatenated objects, or truncated game objects.
- Before returning, internally verify every object/array is closed and every property is comma-separated.

GAME PACKET
""" + json.dumps({"games": packets}, indent=2)
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote Copilot editorial prompt for {len(packets)} games -> {args.prompt_file}")


if __name__ == "__main__":
    main()

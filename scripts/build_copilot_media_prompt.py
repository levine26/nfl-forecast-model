from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _num(value):
    try:
        return round(float(value), 4)
    except Exception:
        return None


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
        if len(football) >= 7:
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
        "final_home_probability": _num(row.get("final_home_prob")),
        "pure_home_probability": _num(row.get("pure_home_prob")),
        "market_home_probability": _num(row.get("market_home_prob")),
        "projected_score": str(row.get("projected_score") or ""),
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

    prompt = """You are the senior NFL editor for Sunday Signal. Research and write the public pregame Read for every game in the packet below.

GOAL
Write like a strong human NFL preview writer, not a model explaining itself and not a search-results summary. The opening sentence should identify the actual football/news story of the matchup: a quarterback change, injury, coaching transition, rivalry angle, schematic stress point, travel/event context, or another concrete reason a fan should care. Use the supplied reporting as a research lead, then verify and improve it with current approved-domain reporting. The LevLine probabilities are background context only.

RESEARCH PRIORITY
1. ESPN / ESPN NFL Nation
2. The Athletic / New York Times
3. NFL.com and official NFL/team reporting available through approved domains
4. Associated Press, CBS Sports, Yahoo Sports, NBC Sports, FOX Sports, Sports Illustrated
5. Credible public X/Twitter reporting when accessible and attributable
Prefer the last 7 days, and the last 48 hours for injuries, starters and availability. Use at least two independent current sources per game whenever possible. Never invent a fact, roster move, injury status, quote, statistic or source URL.

WRITING RULES
- 85-145 words per Read, normally 3-5 sentences.
- Natural sportswriter voice with concrete people, stakes and tension.
- Synthesize; never write phrases such as 'coverage highlights', 'pressure note', 'history note', 'PURE has', 'start with', 'the cleanest lens', 'the hinge', 'the case for', 'the matchup file', or 'strip away the probability'.
- Do not dump EPA/sack/explosive rates. Use at most one compact quantitative sentence when it genuinely explains the story.
- Do not mimic source prose or quote more than a few words; paraphrase.
- Make uncertainty explicit: expected, questionable, competition, trending, etc.
- Vary sentence structure and openings across the slate.
- Mention LevLine only if its disagreement with the broader consensus materially sharpens the story; keep it to one natural closing clause.
- Do not change, recalculate, or recommend changes to LevLine probabilities.

OUTPUT
Return ONLY one syntactically valid JSON object, no Markdown and no commentary, with exactly this schema:
{"games":{"GAME_ID":{"headline":"...","read":"...","sources":[{"name":"ESPN","title":"article/report title","url":"https://..."},{"name":"NFL.com","title":"...","url":"https://..."}]}}}
Every supplied game_id must appear exactly once. Source URLs must be real URLs you actually used. Use two or more approved-domain sources per game whenever available.
CRITICAL SERIALIZATION RULES:
- The response must parse with a standard JSON parser exactly as returned.
- Use JSON double quotes only as delimiters. Escape every literal double quote inside a headline, Read, source title or URL, or better paraphrase/remove embedded quotation marks.
- Do not use trailing commas, comments, ellipses outside strings, concatenated JSON objects, or Markdown fences.
- Before returning the response, check internally that every object/array is closed and every property is comma-separated.
- Do not shorten the response by truncating a game or source object; complete all 16 games.

GAME PACKET
""" + json.dumps({"games": packets}, indent=2)
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote Copilot editorial prompt for {len(packets)} games -> {args.prompt_file}")


if __name__ == "__main__":
    main()

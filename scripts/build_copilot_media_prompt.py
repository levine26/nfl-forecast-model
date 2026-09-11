from __future__ import annotations

"""Build the Sunday Signal editorial-research packet.

The legacy filename is retained as an internal compatibility contract. The active
provider is Groq. Provider prompts intentionally contain no LevLine probabilities,
lines, score projections, blend formulas, or diagnostic margin values: deterministic
code owns every published model number after research is complete.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


def _packet(row: pd.Series, previews: dict, evidence: dict) -> dict:
    gid = str(row.get("game_id"))
    preview = previews.get(gid, {}) if isinstance(previews, dict) else {}
    reported = []
    for item in preview.get("reported_sources") or []:
        if not isinstance(item, dict):
            continue
        # Discovery URLs can be Google/Bing RSS redirects. They are deliberately
        # omitted from the provider packet so the writer cannot echo an aggregator
        # URL as public provenance. The deterministic composer resolves/canonicalizes
        # source URLs after research.
        reported.append({
            "name": item.get("source_name"),
            "title": item.get("title"),
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
        })

    return {
        "game_id": gid,
        "season": int(float(row.get("season"))),
        "week": int(float(row.get("week"))),
        "gameday": str(row.get("gameday")),
        "gametime": str(row.get("gametime")),
        "away_team": str(row.get("away_team")),
        "home_team": str(row.get("home_team")),
        # Groq only needs to know which side the production system selected so it
        # can explain football context for that side. It receives no model numerics.
        "levline_pick": str(row.get("pick")),
        "confidence_label": str(row.get("confidence") or ""),
        "production_strategy": str(row.get("final_probability_strategy") or ""),
        "production_artifact": str(row.get("fst_artifact_id") or ""),
        "provider_scope": "editorial_research_only_no_model_numerics",
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

    prompt = """You are the senior NFL preview writer for Sunday Signal. Research every supplied game and return the human editorial layer only. Deterministic code will add and verify every published LevLine number after your response.

THIS IS A MATCHUP PREVIEW, NOT A NEWS ROUNDUP.
For every game you write three human fields: a headline, one matchup paragraph, and one short model-rationale sentence. Do NOT write the final numerical model paragraph yourself.

HEADLINE
Write one matchup-oriented headline. It should identify the football tension, not repeat an article headline or use generic betting language.

PARAGRAPH 1 — THE MATCHUP
Write 55-100 words explaining how the game is likely to be decided. Identify the actual football tension: quarterback situation, protection/pass rush, coverage matchup, explosive plays, early-down efficiency, run-game leverage, injuries, coaching changes, travel/weather, or another concrete factor. Current reporting should inform the paragraph, but NEVER copy article headlines into prose and NEVER write "according to [outlet]" sentence after sentence. Synthesize the reporting into one coherent preview. Discuss both teams and explain what each side needs to do.

MODEL_RATIONALE — CONTEXT ONLY
Write 18-40 words tying one or two verified football factors to the LevLine side. This is contextual support only. Do NOT include any number, percentage, spread, projected score, PURE value, market value, F-ST value, model line, blend/weight formula, the word moneyline, or a final pick sentence. The research packet intentionally contains no LevLine numerical internals. Deterministic code owns those facts and will build paragraph 2 after your response.

VOICE
- Human NFL analyst: clear, confident, conversational, specific.
- No database labels such as "DEN-KC market gap" or "player history context."
- No headline dumps, SEO language, TV/live-stream information, or generic betting-copy filler.
- Avoid phrases such as "coverage highlights", "pressure note", "history note", "the cleanest lens", "the hinge", "the matchup file", "strip away the probability", "consensus pricing and the football-only model tell different versions", or "keeps enough of that split visible to matter".
- Do not invent injuries, roster facts, statistics, model inputs, source URLs, or causal claims.
- Paraphrase reporting. Quotes should be avoided unless necessary.
- Vary sentence structure across the slate; no seven-word substantive phrase should repeat across games. Standardized official injury/status wording may repeat when factually necessary.

RESEARCH PRIORITY
1. ESPN / ESPN NFL Nation
2. The Athletic / New York Times
3. NFL.com and the two clubs' official team websites
4. AP, CBS Sports, Yahoo Sports, NBC Sports, FOX Sports, Sports Illustrated
5. Credible attributable public X/Twitter reporting when accessible
Prefer the last 7 days, and the last 48 hours for injuries/starters/availability. When an older packet lead conflicts with newer reporting, use the newest verified report and describe the current state. For late quarterback changes, explicitly identify who is now expected to start when verified.

SOURCE RULES — STRICT
- Return at least two independent sources per game from the approved publishers above. Official team reporting is approved and preferred when national coverage is thin.
- Return DIRECT publisher URLs only. Never return news.google.com, bing.com, an RSS redirect, nflverse, GitHub, Wikipedia, or another aggregator/data URL in `sources`.
- If the packet lists a discovered article, use its title/name only as a research lead; open/research the publisher and return a direct approved publisher URL.
- Do not fabricate a URL. If a discovered item cannot be resolved, research another approved source.

OUTPUT
Return ONLY one syntactically valid JSON object, no Markdown and no commentary, with exactly this schema:
{"games":{"GAME_ID":{"headline":"matchup-oriented headline","paragraph1":"55-100 word matchup preview","model_rationale":"18-40 words, context only, no numbers","sources":[{"name":"ESPN","title":"article/report title","url":"https://www.espn.com/..."},{"name":"NFL.com","title":"article/report title","url":"https://www.nfl.com/..."}]}}}
Every supplied game_id must appear exactly once.

CRITICAL SERIALIZATION RULES
- The response must parse with a standard JSON parser exactly as returned.
- Use JSON double quotes only as delimiters. Escape every literal double quote inside strings, or paraphrase/remove it.
- Do not use trailing commas, comments, Markdown fences, concatenated objects, or truncated game objects.
- Before returning, internally verify every object/array is closed and every property is comma-separated.

GAME PACKET
""" + json.dumps({"games": packets}, indent=2)
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote Groq editorial-research prompt for {len(packets)} games -> {args.prompt_file}")


if __name__ == "__main__":
    main()

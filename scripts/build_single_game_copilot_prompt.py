from __future__ import annotations

"""Build a focused Copilot editorial prompt for exactly one NFL matchup."""

import argparse
import json
from pathlib import Path

import pandas as pd

from build_copilot_media_prompt import _packet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--feedback-file", default="")
    args = parser.parse_args()

    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    matches = predictions[predictions["game_id"].astype(str) == str(args.game_id)]
    if len(matches) != 1:
        raise SystemExit(f"expected one row for {args.game_id}, found {len(matches)}")

    previews = json.loads((out / "game_previews.json").read_text(encoding="utf-8"))
    evidence = json.loads((out / "contextual_evidence.json").read_text(encoding="utf-8"))
    packet = _packet(matches.iloc[0], previews, evidence)

    feedback = ""
    if args.feedback_file and Path(args.feedback_file).exists():
        prior = Path(args.feedback_file).read_text(encoding="utf-8", errors="replace").strip()
        if prior:
            feedback = (
                "\nPRIOR FULL-SLATE VALIDATION FEEDBACK\n"
                "A previous candidate failed publication. Avoid every repeated phrase named below and make source coverage especially explicit. "
                "Do not change or invent facts merely to satisfy this feedback.\n"
                + prior[-6000:]
                + "\n"
            )

    prompt = f"""You are the senior NFL preview writer for Sunday Signal. Research ONE supplied game and return only its human editorial layer. Deterministic code will add and verify every published LevLine number after your response.

THIS IS A MATCHUP PREVIEW, NOT A NEWS ROUNDUP.
Write three human fields: a headline, one matchup paragraph, and one short model-rationale sentence. Do NOT write the final numerical model paragraph yourself.

HEADLINE
Write one matchup-oriented headline identifying the football tension. Do not copy an article headline or use generic betting language.

PARAGRAPH 1 — THE MATCHUP
Write 55-100 words explaining how the game is likely to be decided. Discuss BOTH teams and what each side needs to do. Use current reporting to inform the football analysis, but synthesize it instead of writing outlet-led notes. Focus on concrete factors such as quarterback situation, protection/pass rush, coverage, explosive plays, early-down efficiency, run-game leverage, injuries, coaching changes, travel or weather.

MODEL_RATIONALE — CONTEXT ONLY
Write 18-40 words tying one or two verified football factors to the LevLine side. Do NOT include any number, percentage, spread, projected score, PURE value, MARKET value, model line, the word moneyline, or a final pick sentence.

VOICE
- Human NFL analyst: clear, confident, conversational, specific.
- No database labels, headline dumps, SEO language, TV/live-stream information, or betting-copy filler.
- Do not invent injuries, roster facts, statistics, model inputs, source URLs, or causal claims.
- Paraphrase reporting and avoid unnecessary quotations.
- Use matchup-specific wording rather than stock phrases.

RESEARCH PRIORITY
1. ESPN / ESPN NFL Nation
2. The Athletic / New York Times
3. NFL.com and either club's official team website
4. AP, CBS Sports, Yahoo Sports, NBC Sports, FOX Sports, Sports Illustrated
5. Credible attributable public X/Twitter reporting when accessible
Prefer the last 7 days, and the last 48 hours for injuries/starters/availability.

SOURCE RULES — STRICT
- Return at least TWO independent sources from the approved publishers above.
- Official team reporting is approved and preferred when national coverage is thin.
- Return DIRECT publisher article/report URLs only. Never return news.google.com, bing.com, RSS redirects, nflverse, GitHub, Wikipedia, homepages, search pages, or aggregator/data URLs.
- Open/research the publisher page before returning a URL. Never fabricate a URL.
- Two sources must resolve to different publisher domains.

OUTPUT
Return ONLY one syntactically valid JSON object, with exactly this schema and exactly this game id:
{{"games":{{"{args.game_id}":{{"headline":"matchup-oriented headline","paragraph1":"55-100 word matchup preview","model_rationale":"18-40 words, context only, no numbers","sources":[{{"name":"publisher","title":"article/report title","url":"https://direct.publisher/article"}},{{"name":"second publisher","title":"article/report title","url":"https://direct.second/article"}}]}}}}}}
No Markdown, comments, trailing commas, extra game ids, or commentary.
{feedback}
GAME PACKET
{json.dumps(packet, indent=2)}
"""
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote focused Copilot prompt for {args.game_id} -> {args.prompt_file}")


if __name__ == "__main__":
    main()

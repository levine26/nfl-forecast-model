from __future__ import annotations

"""Build a compact Groq editorial-research prompt for exactly one NFL matchup.

The legacy filename is retained as an internal compatibility contract. The compact
packet is deliberate: Groq Compound systems inherit limits from their underlying
models, so production research should spend tokens on current search results rather
than repeating large deterministic context blobs.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from build_copilot_media_prompt import _packet


def _clip(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _compact_packet(packet: dict) -> dict:
    reporting = []
    for item in packet.get("discovered_reporting") or []:
        if not isinstance(item, dict):
            continue
        reporting.append({
            "name": _clip(item.get("name"), 80),
            "title": _clip(item.get("title"), 180),
            "as_of": _clip(item.get("as_of"), 40),
        })
        if len(reporting) >= 4:
            break

    football = []
    for item in packet.get("verified_football_context") or []:
        if not isinstance(item, dict):
            continue
        football.append({
            "family": _clip(item.get("family"), 50),
            "title": _clip(item.get("title"), 140),
            "summary": _clip(item.get("summary"), 280),
            "advantage_team": _clip(item.get("advantage_team"), 20),
        })
        if len(football) >= 4:
            break

    return {
        "game_id": packet.get("game_id"),
        "date": packet.get("gameday"),
        "away": packet.get("away_team"),
        "home": packet.get("home_team"),
        "selected_side": packet.get("levline_pick"),
        "reporting_leads": reporting,
        "verified_context": football,
    }


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
    packet = _compact_packet(_packet(matches.iloc[0], previews, evidence))

    feedback = ""
    if args.feedback_file and Path(args.feedback_file).exists():
        prior = Path(args.feedback_file).read_text(encoding="utf-8", errors="replace").strip()
        if prior:
            feedback = "\nPrior validator feedback to fix without inventing facts:\n" + prior[-1800:] + "\n"

    prompt = f"""You are Sunday Signal's senior NFL analyst. Use ONE current web search to research this matchup, then return only valid JSON. Deterministic code owns every LevLine number; you own only the human football analysis.

Write:
- headline: matchup-specific football tension, not betting/SEO copy.
- paragraph1: 55-100 words, BOTH teams, concrete mechanism(s) that decide the game. Synthesize recent reporting; do not write an injury-news roundup.
- model_rationale: HARD RANGE 18-40 words of verified football context supporting the selected side. Target 22-28 words and count the words before returning. Do NOT use the word LevLine in this field. No numbers, percentages, spreads, scores, model/PURE/MARKET/F-ST terms, "moneyline", or final-pick wording.
- sources: at least TWO independent DIRECT article/report URLs from different approved publishers returned by your web search.

Research priority: ESPN/The Athletic/NYT; NFL.com/official teams; AP/CBS/Yahoo/NBC/FOX/SI. Prefer last 7 days and last 48 hours for availability. Use packet leads only as leads; newest verified reporting wins. Search broadly enough that one search returns multiple publishers. Do not fabricate URLs, stats, injuries, starters, or causal claims. Standard official status wording may repeat; substantive prose may not.

Return exactly:
{{"games":{{"{args.game_id}":{{"headline":"...","paragraph1":"...","model_rationale":"...","sources":[{{"name":"publisher","title":"report title","url":"https://direct.publisher/article"}},{{"name":"second publisher","title":"report title","url":"https://direct.second/article"}}]}}}}}}
No Markdown or commentary.{feedback}
PACKET:
{json.dumps(packet, separators=(",", ":"))}
"""
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote compact focused Groq prompt for {args.game_id} -> {args.prompt_file} ({len(prompt)} chars)")


if __name__ == "__main__":
    main()

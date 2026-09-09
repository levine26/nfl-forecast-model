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


def _game_packet(row: pd.Series, evidence: dict[str, list[dict]]) -> dict:
    gid = str(row.get("game_id"))
    items = list(evidence.get(gid, []))
    media = []
    football = []
    for item in items:
        family = str((item.get("metadata") or {}).get("family") or item.get("category") or "")
        if family == "media_reporting":
            media.append({
                "title": item.get("title"),
                "source_name": item.get("source_name"),
                "source_url": item.get("source_url"),
                "as_of": item.get("as_of"),
            })
        elif len(football) < 6 and str(item.get("strength") or "") in {"Strong", "Moderate"}:
            football.append({
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
        "levline_home_probability": _num(row.get("final_home_prob")),
        "pure_home_probability": _num(row.get("pure_home_prob")),
        "market_home_probability": _num(row.get("market_home_prob")),
        "projected_score": str(row.get("projected_score") or ""),
        "current_reporting": media[:6],
        "verified_context": football[:6],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--prompt-file", default="/tmp/sunday-signal-media-prompt.txt")
    args = parser.parse_args()
    out = Path(args.output_dir)
    predictions = pd.read_csv(out / "this_week.csv")
    evidence = json.loads((out / "contextual_evidence.json").read_text())
    packets = [_game_packet(row, evidence) for _, row in predictions.iterrows()]

    prompt = """You are the Sunday Signal senior NFL editor. Research and write the public pregame Read for every game in the JSON packet below.

MISSION
Write like a strong human NFL preview writer, not a model explaining itself. Start with the actual football/news story of the matchup. Use the supplied context as a notebook, then verify and improve it with current reporting. LevLine's probability is background context only; do not let a stat or probability become the opening sentence unless the market/model disagreement itself is genuinely the most newsworthy angle.

RESEARCH PRIORITY
1. ESPN / ESPN NFL Nation
2. The Athletic / New York Times
3. NFL.com and official team reporting
4. Associated Press, CBS Sports, Yahoo Sports, NBC Sports, FOX Sports, Sports Illustrated
5. Credible beat reporters and public X posts when accessible and attributable
Prefer reporting from the last 7 days. For injuries, starters, transactions and availability, prefer official/NFL/team or top beat reporting. Use at least two independent current sources per game when reasonably available. Never invent a fact because a source is inaccessible.

WRITING RULES
- 85-145 words per Read, normally 3-5 sentences.
- Natural sportswriter voice: concrete people, decisions, stakes and matchup tension.
- No template openings such as 'start with', 'the cleanest lens', 'the hinge', 'the case for', 'the matchup file', or 'strip away the probability'.
- Do not write the same sentence structure across games.
- Do not dump EPA/sack/explosive rates into the lead. Quantitative context can support one sentence when it genuinely clarifies the story.
- Do not imitate or quote source prose. Paraphrase the reporting in your own words.
- Make clear when something is uncertain, expected, questionable, or a competition rather than settled fact.
- Do not change, recalculate, or recommend changes to LevLine probabilities.
- A short closing clause may mention where LevLine lands, especially when it conflicts with the market or public storyline.

OUTPUT
Return ONLY valid JSON, no Markdown fences and no commentary, using exactly this schema:
{"games":{"GAME_ID":{"headline":"...","read":"...","sources":[{"name":"ESPN","title":"article/report title","url":"https://..."},{"name":"NFL.com","title":"...","url":"https://..."}]}}}
Every game_id in the packet must appear exactly once. Source URLs must be real URLs you actually used.

GAME PACKET
""" + json.dumps({"games": packets}, indent=2)
    Path(args.prompt_file).write_text(prompt, encoding="utf-8")
    print(f"wrote Copilot editorial prompt for {len(packets)} games to {args.prompt_file}")


if __name__ == "__main__":
    main()

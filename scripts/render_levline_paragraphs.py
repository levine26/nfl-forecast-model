from __future__ import annotations

"""Render paragraph 2 from canonical LevLine 3.0 forecast values.

This is an editorial serializer only. It does not calculate or alter LevLine inputs,
probabilities, locks, grades, or model features. The public probability-to-line bridge
is reused directly so the editorial Read cannot contradict the public forecast surface.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from nfl_forecast.editorial_model_read import render_model_paragraph


def _factor(preview: dict, pick: str, opponent: str) -> str:
    for item in preview.get("key_factors") or []:
        if isinstance(item, dict):
            title = re.sub(r"\s+", " ", str(item.get("title") or "")).strip()
            if title:
                return f"Football context: {title}"
    case = re.sub(r"\s+", " ", str(preview.get("case_for_pick") or "")).strip()
    return f"Football context: {case or f'{pick} execution against {opponent}'}"


def render(row: pd.Series, preview: dict, model_rationale: str = "") -> str:
    pick = str(row.get("pick"))
    opponent = str(row.get("away_team")) if pick == str(row.get("home_team")) else str(row.get("home_team"))
    context = re.sub(r"\s+", " ", str(model_rationale or "")).strip()
    if not context:
        context = _factor(preview, pick, opponent)
    return render_model_paragraph(row, context)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--previews", default="outputs/game_previews.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    games = payload.get("games") if isinstance(payload, dict) else None
    if not isinstance(games, dict):
        raise SystemExit("composed payload missing games object")
    predictions = pd.read_csv(args.predictions)
    previews = json.loads(Path(args.previews).read_text(encoding="utf-8"))
    expected = set(predictions["game_id"].astype(str))
    if set(map(str, games)) != expected:
        raise SystemExit("cannot render LevLine paragraphs for incomplete slate")

    for _, row in predictions.iterrows():
        gid = str(row.get("game_id"))
        entry = games[gid]
        entry["paragraph2"] = render(
            row,
            previews.get(gid, {}),
            str(entry.get("model_rationale") or ""),
        )

    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rendered canonical LevLine 3.0 paragraph 2 for {len(expected)} games -> {args.output}")


if __name__ == "__main__":
    main()

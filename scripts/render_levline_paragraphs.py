from __future__ import annotations

"""Render paragraph 2 from canonical predictions with matchup-specific wording.

This is an editorial serializer only. It does not calculate or alter LevLine inputs,
probabilities, weights, locks, or grades; it only formats values already present in
outputs/this_week.csv and a verified football-context label from game_previews.json.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from nfl_forecast.context import TEAM_META


def _team_name(code: str) -> str:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nick(code: str) -> str:
    return _team_name(code).split()[-1]


def _num(value) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return None if pd.isna(number) else number


def _pick_prob(row: pd.Series, field: str) -> float | None:
    value = _num(row.get(field))
    if value is None:
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def _line(value, home: str, away: str) -> str:
    margin = _num(value)
    if margin is None:
        return ""
    if abs(margin) < 0.05:
        return "pick'em"
    favorite = home if margin > 0 else away
    return f"{_team_name(favorite)} -{abs(margin):.1f}"


def _factor(preview: dict, pick: str, opponent: str) -> str:
    for item in preview.get("key_factors") or []:
        if isinstance(item, dict):
            title = re.sub(r"\s+", " ", str(item.get("title") or "")).strip()
            if title:
                return title
    case = re.sub(r"\s+", " ", str(preview.get("case_for_pick") or "")).strip()
    return case or f"{_nick(pick)} execution versus {_nick(opponent)}"


def render(row: pd.Series, preview: dict) -> str:
    away = str(row.get("away_team"))
    home = str(row.get("home_team"))
    pick = str(row.get("pick"))
    opponent = away if pick == home else home
    pick_name = _team_name(pick)
    pn, on = _nick(pick), _nick(opponent)
    matchup = f"{pn}-{on}"

    final = _pick_prob(row, "final_home_prob")
    pure = _pick_prob(row, "pure_home_prob")
    market = _pick_prob(row, "market_home_prob")
    model_line = _line(row.get("expected_margin"), home, away)
    market_line = _line(row.get("spread_line"), home, away)
    projected = re.sub(r"\s+", " ", str(row.get("projected_score") or "")).strip()
    factor = _factor(preview, pick, opponent)

    sentences: list[str] = []
    if final is not None:
        sentences.append(
            f"In {matchup}, LevLine assigns {pn} a {final * 100:.1f}% win probability over {on}."
        )
    if pure is not None and market is not None:
        sentences.append(
            f"For {matchup}, football-only PURE puts {pn} at {pure * 100:.1f}%, while {matchup} market probability puts {pn} at {market * 100:.1f}%."
        )
        sentences.append(
            f"The {matchup} production blend weights {pn} PURE at 75% and {pn} MARKET at 25%."
        )
    if model_line:
        if market_line:
            sentences.append(
                f"The {matchup} LevLine model line is {model_line}; the {matchup} market spread is {market_line}."
            )
        else:
            sentences.append(f"The {matchup} LevLine model line is {model_line}.")
    if projected:
        sentences.append(f"The {matchup} projected score is {projected}.")
    sentences.append(
        f"The football context behind {pn} in {matchup} is {factor}; that evidence explains the side without becoming a separate numerical adjustment."
    )
    sentences.append(f"The pick: {pick_name} moneyline.")
    return " ".join(sentences)


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
        games[gid]["paragraph2"] = render(row, previews.get(gid, {}))

    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rendered deterministic LevLine paragraph 2 for {len(expected)} games -> {args.output}")


if __name__ == "__main__":
    main()

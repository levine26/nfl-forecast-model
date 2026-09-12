from __future__ import annotations

"""Freeze the non-numeric forecast identity used by Groq research.

Groq receives the selected side plus matchup identity, timing, and production-model
identity. If a concurrent forecast refresh changes any of those semantics while the
provider is researching, the already-researched rationale is no longer guaranteed to
apply. Numeric probability/line/score movement is intentionally excluded because the
published model paragraph is deterministically re-rendered after reconciliation.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = 1
CONTRACT_FIELDS = (
    "season",
    "week",
    "gameday",
    "gametime",
    "away_team",
    "home_team",
    "pick",
    "final_probability_strategy",
    "fst_artifact_id",
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    # pandas commonly renders integer-like season/week values as 2026.0/1.0.
    if text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def build_contract(frame: pd.DataFrame) -> dict[str, Any]:
    required = ("game_id", *CONTRACT_FIELDS)
    missing = [field for field in required if field not in frame.columns]
    if missing:
        raise ValueError("canonical predictions missing contract fields: " + ", ".join(missing))

    game_ids = frame["game_id"].map(_clean)
    if (game_ids == "").any():
        raise ValueError("canonical predictions contain a blank game_id")
    duplicates = sorted(game_ids[game_ids.duplicated()].unique())
    if duplicates:
        raise ValueError("canonical predictions contain duplicate game_id values: " + ", ".join(duplicates))

    games: dict[str, dict[str, str]] = {}
    for idx, row in frame.iterrows():
        gid = _clean(row.get("game_id"))
        games[gid] = {field: _clean(row.get(field)) for field in CONTRACT_FIELDS}

    return {
        "schema_version": SCHEMA_VERSION,
        "fields": list(CONTRACT_FIELDS),
        "games": {gid: games[gid] for gid in sorted(games)},
    }


def contract_differences(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    if before.get("schema_version") != SCHEMA_VERSION:
        return [f"unsupported prior contract schema_version={before.get('schema_version')!r}"]
    if tuple(before.get("fields") or ()) != CONTRACT_FIELDS:
        return ["prior contract fields do not match the current governed contract"]

    before_games = before.get("games")
    after_games = after.get("games")
    if not isinstance(before_games, dict) or not isinstance(after_games, dict):
        return ["contract games payload must be an object"]

    differences: list[str] = []
    before_ids = set(map(str, before_games))
    after_ids = set(map(str, after_games))
    for gid in sorted(before_ids - after_ids):
        differences.append(f"{gid}: removed from canonical slate")
    for gid in sorted(after_ids - before_ids):
        differences.append(f"{gid}: added to canonical slate")

    for gid in sorted(before_ids & after_ids):
        old = before_games.get(gid) or {}
        new = after_games.get(gid) or {}
        for field in CONTRACT_FIELDS:
            old_value = _clean(old.get(field))
            new_value = _clean(new.get(field))
            if old_value != new_value:
                differences.append(f"{gid}: {field} changed {old_value!r} -> {new_value!r}")
    return differences


def _read_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("research contract must be a JSON object")
    return payload


def snapshot(predictions: Path, output: Path) -> None:
    contract = build_contract(pd.read_csv(predictions))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"froze Groq research contract for {len(contract['games'])} games -> {output}")


def verify(predictions: Path, contract_path: Path) -> None:
    before = _read_contract(contract_path)
    after = build_contract(pd.read_csv(predictions))
    differences = contract_differences(before, after)
    if differences:
        raise SystemExit(
            "Groq research forecast contract changed during provider research; fresh research is required:\n"
            + "\n".join(f"- {difference}" for difference in differences)
        )
    print(f"Groq research forecast contract unchanged for {len(after['games'])} games.")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    snap = subparsers.add_parser("snapshot")
    snap.add_argument("--predictions", default="outputs/this_week.csv")
    snap.add_argument("--output", required=True)

    check = subparsers.add_parser("verify")
    check.add_argument("--predictions", default="outputs/this_week.csv")
    check.add_argument("--contract", required=True)

    args = parser.parse_args()
    if args.command == "snapshot":
        snapshot(Path(args.predictions), Path(args.output))
    else:
        verify(Path(args.predictions), Path(args.contract))


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Merge one-game Copilot JSON responses into one full-slate candidate payload."""

import argparse
import json
from pathlib import Path

import pandas as pd

from compose_copilot_media_reads import _extract_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    expected = list(pd.read_csv(args.predictions)["game_id"].astype(str))
    root = Path(args.input_dir)
    merged: dict[str, dict] = {}
    for gid in expected:
        path = root / f"{gid}.txt"
        if not path.exists():
            raise SystemExit(f"missing Copilot response for {gid}: {path}")
        payload = _extract_json(path.read_text(encoding="utf-8", errors="replace"))
        games = payload.get("games") if isinstance(payload, dict) else None
        if not isinstance(games, dict) or set(map(str, games)) != {gid}:
            raise SystemExit(f"{gid}: focused response must contain exactly its own game id")
        entry = games.get(gid)
        if not isinstance(entry, dict):
            raise SystemExit(f"{gid}: focused game entry is not an object")
        merged[gid] = entry

    Path(args.output).write_text(
        json.dumps({"games": merged}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"merged {len(merged)} focused Copilot responses -> {args.output}")


if __name__ == "__main__":
    main()

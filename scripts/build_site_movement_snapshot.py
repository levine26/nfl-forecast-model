"""Build a bounded, read-only movement feed for the currently published slate.

The immutable run_history.csv is deliberately left untouched. This script
streams it once on the CI runner instead of forcing mobile browsers to download
and independently parse the entire multi-megabyte research/run ledger.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from pathlib import Path


def build(current: Path, history: Path, output: Path, per_game: int = 24) -> tuple[int, int]:
    if per_game < 1 or per_game > 200:
        raise ValueError("per_game must be between 1 and 200")
    with current.open(newline="", encoding="utf-8-sig") as source:
        current_reader = csv.DictReader(source)
        if not current_reader.fieldnames or "game_id" not in current_reader.fieldnames:
            raise ValueError("current slate missing game_id column")
        game_ids = {row["game_id"].strip() for row in current_reader if row.get("game_id", "").strip()}
    if not game_ids:
        raise ValueError("cannot publish movement snapshot for an empty current slate")

    selected = defaultdict(lambda: deque(maxlen=per_game))
    with history.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames or []
        if "game_id" not in fields:
            raise ValueError("history missing game_id column")
        for row in reader:
            key = row.get("game_id", "").strip()
            if key in game_ids:
                selected[key].append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as dest:
        writer = csv.DictWriter(dest, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        # Keep original row ordering within each matchup. The client sorts
        # its presentation timestamps when necessary.
        for game_id in sorted(game_ids):
            writer.writerows(selected[game_id])
    count = sum(map(len, selected.values()))
    print(f"Movement snapshot: {count} records for {len(game_ids)} scheduled games; max {per_game} per game")
    return len(game_ids), count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-game", type=int, default=24)
    args = parser.parse_args()
    build(args.current, args.history, args.output, args.per_game)


if __name__ == "__main__":
    main()

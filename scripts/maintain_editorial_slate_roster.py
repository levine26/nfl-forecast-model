from __future__ import annotations

"""Maintain a durable per-week Sunday Signal editorial game roster.

The live forecast output may contract as games kick off. This roster is deliberately
separate from regenerated editorial artifacts: within a season/week it can expand when
new current rows appear, but it never shrinks. When the live source advances to a new
season/week, the roster rolls forward to that new slate.
"""

import argparse
import csv
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
GAME_ID_RE = re.compile(r"^(\d{4})_(\d{2})_[A-Z0-9]{2,4}_[A-Z0-9]{2,4}$")


def _read_current(path: Path) -> tuple[tuple[int, int] | None, list[str]]:
    if not path.exists():
        raise RuntimeError(f"Missing current forecast source: {path}")

    identities: set[tuple[int, int]] = set()
    game_ids: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            game_id = str(row.get("game_id") or "").strip()
            if not game_id:
                continue
            season = str(row.get("season") or "").strip()
            week = str(row.get("week") or "").strip()
            if not season or not week:
                raise RuntimeError(f"{game_id}: current row is missing season/week")
            identity = (int(float(season)), int(float(week)))
            identities.add(identity)
            if game_id not in seen:
                game_ids.append(game_id)
                seen.add(game_id)

    if len(identities) > 1:
        raise RuntimeError(f"Current forecast source spans multiple season/weeks: {sorted(identities)}")
    return (next(iter(identities)) if identities else None), game_ids


def _read_existing(path: Path) -> tuple[tuple[int, int] | None, list[str]]:
    if not path.exists():
        return None, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Editorial slate roster must be a JSON object")

    season = payload.get("season")
    week = payload.get("week")
    game_ids = payload.get("game_ids")
    if season is None or week is None or not isinstance(game_ids, list):
        raise RuntimeError("Editorial slate roster requires season, week, and game_ids")

    identity = (int(season), int(week))
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in game_ids:
        game_id = str(raw).strip()
        match = GAME_ID_RE.fullmatch(game_id)
        if match is None:
            raise RuntimeError(f"Invalid editorial roster game_id: {game_id}")
        parsed_identity = (int(match.group(1)), int(match.group(2)))
        if parsed_identity != identity:
            raise RuntimeError(
                f"{game_id}: roster game identity {parsed_identity} does not match {identity}"
            )
        if game_id not in seen:
            normalized.append(game_id)
            seen.add(game_id)
    if not normalized:
        raise RuntimeError("Editorial slate roster contains no games")
    return identity, normalized


def maintain_roster(current: Path, output: Path) -> dict:
    current_identity, current_ids = _read_current(current)
    existing_identity, existing_ids = _read_existing(output)

    if current_identity is None:
        if existing_identity is None:
            raise RuntimeError("Cannot initialize editorial roster from an empty current slate")
        identity = existing_identity
        game_ids = existing_ids
        action = "preserved-empty-current"
    elif existing_identity == current_identity:
        identity = current_identity
        game_ids = list(existing_ids)
        seen = set(game_ids)
        for game_id in current_ids:
            if game_id not in seen:
                game_ids.append(game_id)
                seen.add(game_id)
        action = "preserved-or-expanded"
    else:
        identity = current_identity
        game_ids = current_ids
        action = "rolled-week"

    if not game_ids:
        raise RuntimeError("Editorial roster would be empty")

    payload = {
        "schema_version": 1,
        "season": identity[0],
        "week": identity[1],
        "game_ids": game_ids,
        "policy": "For a fixed season/week, the Sunday Signal editorial roster may expand but must never shrink as games kick off.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(
        f"editorial slate roster OK: season={identity[0]} week={identity[1]} "
        f"games={len(game_ids)} action={action} -> {output}"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain the durable Sunday Signal editorial slate roster.")
    parser.add_argument("--current", type=Path, default=ROOT / "outputs" / "this_week.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "editorial_slate_roster.json")
    args = parser.parse_args()
    maintain_roster(args.current, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

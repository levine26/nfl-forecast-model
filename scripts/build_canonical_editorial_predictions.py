from __future__ import annotations

"""Build the locked-first forecast rows used by Sunday Signal editorial copy.

The public dashboard already resolves each game through the canonical public-forecast
contract: an immutable prediction-history row wins once a T-120 lock exists, otherwise
the current live row is used. Editorial research must consume the same underlying row so
a later market refresh cannot change "The pick:" after the public forecast is locked.

Market refreshes may legitimately shrink outputs/this_week.csv as games kick off. For
failed-game recovery, already-validated Sunday Signal game IDs may therefore need their
immutable rows restored from prediction history before applying the public-forecast
contract.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.public_forecast import build_public_forecasts  # noqa: E402


def _now_utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _active_slate_identity(current_records: list[dict]) -> tuple[int, int]:
    identities: set[tuple[int, int]] = set()
    for row in current_records:
        season = row.get("season")
        week = row.get("week")
        if pd.isna(season) or pd.isna(week):
            raise RuntimeError("Current editorial forecast row is missing season/week")
        identities.add((int(season), int(week)))
    if len(identities) != 1:
        raise RuntimeError(
            "Current editorial forecast source must identify exactly one season/week; "
            f"found {sorted(identities)}"
        )
    return next(iter(identities))


def build_canonical_editorial_predictions(
    current: pd.DataFrame,
    official: pd.DataFrame,
    *,
    now_utc: datetime,
    editorial_game_ids: set[str] | None = None,
) -> pd.DataFrame:
    """Select locked-first rows, restoring only explicitly authorized editorial games."""
    current_records = current.to_dict(orient="records")
    official_records = official.to_dict(orient="records")
    season, week = _active_slate_identity(current_records)

    current_by_game = {
        str(row.get("game_id")): row
        for row in current_records
        if str(row.get("game_id") or "").strip()
    }
    locked_by_game = {
        str(row.get("game_id")): row
        for row in official_records
        if str(row.get("game_id") or "").strip()
        and str(row.get("lock_status") or "").strip().upper() == "LOCKED"
    }

    # outputs/this_week.csv can contract after kickoff. For recovery, restore only
    # immutable games already present in the validated Sunday Signal media roster.
    bridge_records = list(current_records)
    locked_only = [
        row
        for game_id, row in locked_by_game.items()
        if editorial_game_ids is not None
        and game_id in editorial_game_ids
        and game_id not in current_by_game
        and not pd.isna(row.get("season"))
        and not pd.isna(row.get("week"))
        and int(row.get("season")) == season
        and int(row.get("week")) == week
    ]
    locked_only.sort(
        key=lambda row: (
            str(row.get("gameday") or ""),
            str(row.get("gametime") or ""),
            str(row.get("game_id") or ""),
        )
    )
    bridge_records.extend(locked_only)

    if editorial_game_ids is not None:
        bridge_ids = {
            str(row.get("game_id"))
            for row in bridge_records
            if str(row.get("game_id") or "").strip()
        }
        missing_authorized = sorted(editorial_game_ids - bridge_ids)
        if missing_authorized:
            raise RuntimeError(
                "Authorized editorial roster cannot be reconstructed from current/locked rows: "
                f"{missing_authorized}"
            )

    public = build_public_forecasts(bridge_records, official_records, now_utc=now_utc)

    if editorial_game_ids is not None:
        public_ids = {str(game["game_id"]) for game in public["games"]}
        if public_ids != editorial_game_ids:
            raise RuntimeError(
                "Canonical editorial slate does not exactly match the authorized roster: "
                f"missing={sorted(editorial_game_ids - public_ids)} "
                f"extra={sorted(public_ids - editorial_game_ids)}"
            )

    bridge_by_game = {
        str(row.get("game_id")): row
        for row in bridge_records
        if str(row.get("game_id") or "").strip()
    }

    selected: list[dict] = []
    for game in public["games"]:
        game_id = str(game["game_id"])
        if game.get("source_snapshot") == "LOCKED":
            source = locked_by_game.get(game_id)
            if source is None:
                raise RuntimeError(f"{game_id}: canonical public contract selected LOCKED without locked source row")
        else:
            source = bridge_by_game.get(game_id)
            if source is None:
                raise RuntimeError(f"{game_id}: canonical public contract selected LIVE without current source row")
        selected.append(dict(source))

    result = pd.DataFrame(selected)
    if list(result.get("game_id", pd.Series(dtype=str)).astype(str)) != [
        str(game["game_id"]) for game in public["games"]
    ]:
        raise RuntimeError("Canonical editorial source order diverged from public forecast contract")
    return result


GAME_ID_PATTERN = re.compile(r"^\\d{4}_\\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")


def _load_editorial_game_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Editorial roster must be a JSON object")

    games = payload["games"] if "games" in payload else payload
    if isinstance(games, dict):
        game_ids = {
            str(game_id)
            for game_id in games
            if GAME_ID_PATTERN.fullmatch(str(game_id).strip())
        }
    elif isinstance(games, list):
        game_ids = {
            str(game.get("game_id"))
            for game in games
            if isinstance(game, dict)
            and GAME_ID_PATTERN.fullmatch(str(game.get("game_id") or "").strip())
        }
    else:
        raise RuntimeError("Editorial roster games must be an object or list")
    if not game_ids:
        raise RuntimeError("Editorial roster contains no valid game IDs")
    return game_ids


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Sunday Signal editorial predictions from the same locked-first rows as the public forecast contract."
    )
    parser.add_argument("--current", type=Path, default=ROOT / "outputs" / "this_week.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "outputs" / "prediction_history.csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--editorial-roster",
        type=Path,
        help="Optional validated media packet whose game IDs authorize locked-game restoration.",
    )
    parser.add_argument("--now", help="Optional ISO-8601 UTC override for deterministic validation/tests.")
    args = parser.parse_args()

    if not args.current.exists():
        raise SystemExit(f"Missing current forecast source: {args.current}")
    if not args.official.exists():
        raise SystemExit(f"Missing immutable prediction history: {args.official}")

    current = pd.read_csv(args.current)
    official = pd.read_csv(args.official)

    editorial_game_ids: set[str] | None = None
    if args.editorial_roster is not None:
        if not args.editorial_roster.exists():
            raise SystemExit(f"Missing editorial roster: {args.editorial_roster}")
        editorial_game_ids = _load_editorial_game_ids(args.editorial_roster)

    result = build_canonical_editorial_predictions(
        current,
        official,
        now_utc=_now_utc(args.now),
        editorial_game_ids=editorial_game_ids,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)

    locked = int(
        result.get("lock_status", pd.Series(index=result.index, dtype=object))
        .fillna("")
        .astype(str)
        .str.upper()
        .eq("LOCKED")
        .sum()
    )
    print(f"canonical editorial forecast source OK: games={len(result)} locked={locked} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

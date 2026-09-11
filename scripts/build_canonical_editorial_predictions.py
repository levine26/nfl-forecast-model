from __future__ import annotations

"""Build the locked-first forecast rows used by Sunday Signal editorial copy.

The public dashboard already resolves each game through the canonical public-forecast
contract: an immutable prediction-history row wins once a T-120 lock exists, otherwise
the current live row is used. Editorial research must consume the same underlying row so
a later market refresh cannot change "The pick:" after the public forecast is locked.
"""

import argparse
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


def build_canonical_editorial_predictions(
    current: pd.DataFrame,
    official: pd.DataFrame,
    *,
    now_utc: datetime,
) -> pd.DataFrame:
    """Select exactly the same source row the canonical public contract selects."""
    current_records = current.to_dict(orient="records")
    official_records = official.to_dict(orient="records")
    public = build_public_forecasts(current_records, official_records, now_utc=now_utc)

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

    selected: list[dict] = []
    for game in public["games"]:
        game_id = str(game["game_id"])
        if game.get("source_snapshot") == "LOCKED":
            source = locked_by_game.get(game_id)
            if source is None:
                raise RuntimeError(f"{game_id}: canonical public contract selected LOCKED without locked source row")
        else:
            source = current_by_game.get(game_id)
            if source is None:
                raise RuntimeError(f"{game_id}: canonical public contract selected LIVE without current source row")
        selected.append(dict(source))

    result = pd.DataFrame(selected)
    if list(result.get("game_id", pd.Series(dtype=str)).astype(str)) != [
        str(game["game_id"]) for game in public["games"]
    ]:
        raise RuntimeError("Canonical editorial source order diverged from public forecast contract")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Sunday Signal editorial predictions from the same locked-first rows as the public forecast contract."
    )
    parser.add_argument("--current", type=Path, default=ROOT / "outputs" / "this_week.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "outputs" / "prediction_history.csv")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now", help="Optional ISO-8601 UTC override for deterministic validation/tests.")
    args = parser.parse_args()

    if not args.current.exists():
        raise SystemExit(f"Missing current forecast source: {args.current}")
    if not args.official.exists():
        raise SystemExit(f"Missing immutable prediction history: {args.official}")

    current = pd.read_csv(args.current)
    official = pd.read_csv(args.official)
    result = build_canonical_editorial_predictions(current, official, now_utc=_now_utc(args.now))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)

    locked = int(result.get("lock_status", pd.Series(index=result.index, dtype=object)).fillna("").astype(str).str.upper().eq("LOCKED").sum())
    print(f"canonical editorial forecast source OK: games={len(result)} locked={locked} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

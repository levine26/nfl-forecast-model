from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.public_forecast import PublicForecastError, build_public_forecasts  # noqa: E402

ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY = "2026-09-27"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise PublicForecastError(f"required forecast source is missing: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _text(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def _number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _prepare_locked_receipts(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Make dedicated ATS receipt diagnostics authoritative for locked public output.

    Live previews still derive ATS value from the current model and market inputs. Once a
    pick is locked, the immutable ``locked_ats_*`` receipt becomes the contract. For the
    Sep. 27+ policy era, a missing dedicated receipt is an error rather than permission to
    regenerate a bet from generic fields.
    """
    prepared: list[dict[str, str]] = []
    for source in rows:
        row = dict(source)
        if _text(row.get("lock_status")).upper() != "LOCKED":
            prepared.append(row)
            continue

        gameday = _text(row.get("gameday"))[:10]
        status = _text(row.get("locked_ats_status")).upper()
        if not status:
            if gameday and gameday >= ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY:
                raise PublicForecastError(
                    f"{_text(row.get('game_id')) or 'unknown'}: policy-era locked game is missing its dedicated ATS receipt"
                )
            prepared.append(row)
            continue

        if status == "VALUE":
            side = _text(row.get("locked_ats_pick_team"))
            selected_spread = _number(row.get("locked_ats_pick_market_spread"))
            model_margin = _number(row.get("locked_ats_model_margin_home"))
            market_margin = _number(row.get("locked_ats_market_margin_home"))
            if not side or selected_spread is None or model_margin is None or market_margin is None:
                raise PublicForecastError(
                    f"{_text(row.get('game_id')) or 'unknown'}: VALUE ATS receipt is incomplete"
                )
            # The serializer computes presentation fields from these inputs. Replace
            # generic aliases with the immutable receipt diagnostics, then verify below
            # that the resulting selected side/number exactly matches the receipt.
            row["expected_margin"] = str(model_margin)
            row["spread_line"] = str(market_margin)
        elif status == "NO_EDGE":
            model_margin = _number(row.get("locked_ats_model_margin_home"))
            market_margin = _number(row.get("locked_ats_market_margin_home"))
            if model_margin is None or market_margin is None:
                raise PublicForecastError(
                    f"{_text(row.get('game_id')) or 'unknown'}: NO_EDGE ATS receipt is incomplete"
                )
            row["expected_margin"] = str(model_margin)
            row["spread_line"] = str(market_margin)
        elif status == "UNAVAILABLE":
            row["spread_line"] = ""
        else:
            raise PublicForecastError(
                f"{_text(row.get('game_id')) or 'unknown'}: unknown locked ATS status {status!r}"
            )
        prepared.append(row)
    return prepared


def _assert_locked_public_contract(payload: dict, official: list[dict[str, str]]) -> None:
    locked = {
        _text(row.get("game_id")): row
        for row in official
        if _text(row.get("lock_status")).upper() == "LOCKED" and _text(row.get("game_id"))
    }
    for game in payload.get("games", []):
        row = locked.get(_text(game.get("game_id")))
        if row is None:
            continue
        status = _text(row.get("locked_ats_status")).upper()
        if not status:
            continue
        if _text(game.get("ats_status")).upper() != status:
            raise PublicForecastError(f"{game.get('game_id')}: public ATS status diverges from locked receipt")
        if status == "VALUE":
            expected_side = _text(row.get("locked_ats_pick_team"))
            expected_spread = _number(row.get("locked_ats_pick_market_spread"))
            actual_spread = _number(game.get("ats_pick_market_spread"))
            if game.get("ats_pick_team") != expected_side:
                raise PublicForecastError(f"{game.get('game_id')}: public ATS side diverges from locked receipt")
            if expected_spread is None or actual_spread is None or not math.isclose(actual_spread, expected_spread, abs_tol=1e-12):
                raise PublicForecastError(f"{game.get('game_id')}: public ATS spread diverges from locked receipt")
        elif game.get("ats_pick_team") is not None or game.get("ats_pick_market_spread") is not None:
            raise PublicForecastError(f"{game.get('game_id')}: non-VALUE locked receipt must not publish an ATS wager")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate Sunday Signal's canonical public forecast contract.")
    parser.add_argument("--current", type=Path, default=ROOT / "outputs" / "this_week.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "outputs" / "prediction_history.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "public_forecasts.json")
    parser.add_argument("--now", help="Optional ISO-8601 UTC override for deterministic validation/tests.")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.now:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)

    current = _read_csv(args.current)
    official = _prepare_locked_receipts(_read_csv(args.official))
    payload = build_public_forecasts(current, official, now_utc=now)
    _assert_locked_public_contract(payload, official)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"public forecast contract OK: {len(payload['games'])} games -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


NFLVERSE_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
PROBABILITY_TOLERANCE = 1e-10
LEDGER_COLUMNS = (
    "game_id",
    "season",
    "lock_timestamp_utc",
    "locked_home_moneyline",
    "locked_away_moneyline",
    "bet_price_source",
    "bet_price_verified_utc",
)


def american_implied(odds: float) -> float:
    value = float(odds)
    if not np.isfinite(value) or value == 0:
        raise ValueError("American odds must be finite and non-zero")
    if value < 0:
        return (-value) / ((-value) + 100.0)
    return 100.0 / (value + 100.0)


def vig_free_home_probability(home_moneyline: float, away_moneyline: float) -> float:
    home = american_implied(home_moneyline)
    away = american_implied(away_moneyline)
    return home / (home + away)


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    value = float(parsed)
    return value if np.isfinite(value) else None


def _verified_moneyline_pair(receipt: pd.Series, market: pd.Series) -> tuple[float, float] | None:
    locked_probability = _number(receipt.get("market_home_prob"))
    home_moneyline = _number(market.get("home_moneyline"))
    away_moneyline = _number(market.get("away_moneyline"))
    if locked_probability is None or home_moneyline is None or away_moneyline is None:
        return None
    try:
        candidate_probability = vig_free_home_probability(home_moneyline, away_moneyline)
    except ValueError:
        return None
    if abs(candidate_probability - locked_probability) > PROBABILITY_TOLERANCE:
        return None
    return home_moneyline, away_moneyline


def _market_index(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    if "game_id" not in frame.columns:
        return pd.DataFrame()
    current = frame.copy()
    if "season" in current.columns:
        season_values = pd.to_numeric(current["season"], errors="coerce")
        current = current[season_values.eq(int(season))]
    return current.drop_duplicates("game_id", keep="last").set_index("game_id")


def _empty_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=list(LEDGER_COLUMNS))


def enrich_price_ledger(
    history: pd.DataFrame,
    market: pd.DataFrame,
    existing: pd.DataFrame | None = None,
    *,
    season: int = 2026,
    verified_utc: datetime | None = None,
) -> tuple[pd.DataFrame, int]:
    """Append only moneyline pairs that are provably the immutable lock-time pair.

    Older forecast receipts retained the vig-free market home probability but not the
    raw American moneyline pair. A candidate pair is accepted only when converting it
    back to a vig-free home probability reproduces the immutable receipt within a
    tight floating-point tolerance. Later/different prices fail closed.

    Betting prices are kept in a separate append-only ledger so model publishing can
    never rewrite or strip them. Spread juice is not inferred; the site applies its
    documented -110 fallback until a genuine lock-time spread-price source exists.
    """
    ledger = (existing.copy() if existing is not None else _empty_ledger())
    for column in LEDGER_COLUMNS:
        if column not in ledger.columns:
            ledger[column] = ""
    ledger = ledger[list(LEDGER_COLUMNS)]

    market_by_game = _market_index(market, season)
    if market_by_game.empty:
        return ledger, 0

    existing_ids = set(ledger["game_id"].astype(str)) if not ledger.empty else set()
    verified_at = (verified_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    additions: list[dict[str, object]] = []

    for _, receipt in history.iterrows():
        if str(receipt.get("lock_status", "")).strip().upper() != "LOCKED":
            continue
        receipt_season = _number(receipt.get("season"))
        if receipt_season is not None and int(receipt_season) != int(season):
            continue
        game_id = str(receipt.get("game_id", "")).strip()
        if not game_id or game_id in existing_ids or game_id not in market_by_game.index:
            continue

        pair = _verified_moneyline_pair(receipt, market_by_game.loc[game_id])
        if pair is None:
            continue

        additions.append({
            "game_id": game_id,
            "season": int(receipt_season) if receipt_season is not None else int(season),
            "lock_timestamp_utc": str(receipt.get("lock_timestamp_utc", "")),
            "locked_home_moneyline": pair[0],
            "locked_away_moneyline": pair[1],
            "bet_price_source": "nflverse_moneyline_verified_against_locked_market_probability",
            "bet_price_verified_utc": verified_at,
        })
        existing_ids.add(game_id)

    if additions:
        ledger = pd.concat([ledger, pd.DataFrame(additions)], ignore_index=True)
    ledger = ledger.drop_duplicates("game_id", keep="first").sort_values(["season", "game_id"], kind="stable")
    return ledger, len(additions)


def capture(
    history_path: Path,
    ledger_path: Path,
    *,
    season: int = 2026,
    market_source: str = NFLVERSE_GAMES_URL,
) -> int:
    if not history_path.exists():
        raise FileNotFoundError(f"Prediction history not found: {history_path}")
    history = pd.read_csv(history_path)
    market = pd.read_csv(market_source, low_memory=False)
    if ledger_path.exists():
        try:
            existing = pd.read_csv(ledger_path)
        except Exception:
            existing = _empty_ledger()
    else:
        existing = _empty_ledger()
    ledger, changed = enrich_price_ledger(history, market, existing, season=season)
    if changed or not ledger_path.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.to_csv(ledger_path, index=False)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist verified lock-time moneyline prices for Sunday Signal.")
    parser.add_argument("--history", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument("--ledger", type=Path, default=Path("outputs/bet_price_history.csv"))
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--market-source", default=NFLVERSE_GAMES_URL)
    args = parser.parse_args()
    changed = capture(args.history, args.ledger, season=args.season, market_source=args.market_source)
    print(f"Verified moneyline prices added to {changed} betting-price receipt(s).")


if __name__ == "__main__":
    main()

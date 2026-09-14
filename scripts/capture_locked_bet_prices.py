from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


NFLVERSE_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
PROBABILITY_TOLERANCE = 1e-10
NUMERIC_PRICE_COLUMNS = (
    "locked_home_moneyline",
    "locked_away_moneyline",
    "locked_home_spread_price",
    "locked_away_spread_price",
)
TEXT_PRICE_COLUMNS = (
    "bet_price_source",
    "bet_price_verified_utc",
)
PRICE_COLUMNS = NUMERIC_PRICE_COLUMNS + TEXT_PRICE_COLUMNS


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


def enrich_locked_bet_prices(
    history: pd.DataFrame,
    market: pd.DataFrame,
    *,
    season: int = 2026,
    verified_utc: datetime | None = None,
) -> tuple[pd.DataFrame, int]:
    """Add only sportsbook prices that can be verified against a locked market signal.

    Historical receipts store the vig-free market home probability but older rows did
    not retain the raw American moneyline pair. A current nflverse pair is accepted
    only when converting that exact pair back to vig-free probability reproduces the
    immutable receipt within a tight floating-point tolerance. Mismatches fail closed.

    Spread-side juice is intentionally left blank unless an upstream source already
    supplies explicit side prices. The Sunday Signal tracker applies its documented
    -110 fallback when those fields are absent.
    """
    out = history.copy()
    for column in NUMERIC_PRICE_COLUMNS:
        if column not in out.columns:
            out[column] = np.nan
    for column in TEXT_PRICE_COLUMNS:
        if column not in out.columns:
            out[column] = pd.Series("", index=out.index, dtype="object")
        else:
            out[column] = out[column].astype("object")

    market_by_game = _market_index(market, season)
    if market_by_game.empty:
        return out, 0

    verified_at = (verified_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    verified_moneylines = 0

    for index, receipt in out.iterrows():
        if str(receipt.get("lock_status", "")).strip().upper() != "LOCKED":
            continue
        receipt_season = _number(receipt.get("season"))
        if receipt_season is not None and int(receipt_season) != int(season):
            continue
        game_id = str(receipt.get("game_id", "")).strip()
        if not game_id or game_id not in market_by_game.index:
            continue

        market_row = market_by_game.loc[game_id]
        home_existing = _number(receipt.get("locked_home_moneyline"))
        away_existing = _number(receipt.get("locked_away_moneyline"))
        if home_existing is None or away_existing is None:
            pair = _verified_moneyline_pair(receipt, market_row)
            if pair is not None:
                out.at[index, "locked_home_moneyline"] = pair[0]
                out.at[index, "locked_away_moneyline"] = pair[1]
                out.at[index, "bet_price_source"] = "nflverse_moneyline_verified_against_locked_market_probability"
                out.at[index, "bet_price_verified_utc"] = verified_at
                verified_moneylines += 1

        home_spread_price = _number(market_row.get("home_spread_price"))
        away_spread_price = _number(market_row.get("away_spread_price"))
        if home_spread_price is not None and _number(out.at[index, "locked_home_spread_price"]) is None:
            out.at[index, "locked_home_spread_price"] = home_spread_price
        if away_spread_price is not None and _number(out.at[index, "locked_away_spread_price"]) is None:
            out.at[index, "locked_away_spread_price"] = away_spread_price

    return out, verified_moneylines


def capture(
    history_path: Path,
    *,
    season: int = 2026,
    market_source: str = NFLVERSE_GAMES_URL,
) -> int:
    if not history_path.exists():
        raise FileNotFoundError(f"Prediction history not found: {history_path}")
    history = pd.read_csv(history_path)
    market = pd.read_csv(market_source, low_memory=False)
    enriched, changed = enrich_locked_bet_prices(history, market, season=season)
    schema_changed = any(column not in history.columns for column in PRICE_COLUMNS)
    content_changed = not enriched.equals(history.reindex(columns=enriched.columns))
    if schema_changed or content_changed:
        enriched.to_csv(history_path, index=False)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist verified sportsbook prices on immutable LevLine receipts.")
    parser.add_argument("--history", type=Path, default=Path("outputs/prediction_history.csv"))
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--market-source", default=NFLVERSE_GAMES_URL)
    args = parser.parse_args()
    changed = capture(args.history, season=args.season, market_source=args.market_source)
    print(f"Verified moneyline prices added to {changed} locked receipt(s).")


if __name__ == "__main__":
    main()

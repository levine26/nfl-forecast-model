from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


NFLVERSE_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
NFLVERSE_COMMITS_API = "https://api.github.com/repos/nflverse/nfldata/commits"
NFLVERSE_RAW_TEMPLATE = "https://raw.githubusercontent.com/nflverse/nfldata/{sha}/data/games.csv"
PROBABILITY_TOLERANCE = 1e-10
HISTORICAL_COMMIT_LOOKBACK = 6
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
    source_label: str = "nflverse_moneyline_verified_against_locked_market_probability",
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

        candidate = market_by_game.loc[game_id]
        if isinstance(candidate, pd.DataFrame):
            candidate = candidate.iloc[-1]
        pair = _verified_moneyline_pair(receipt, candidate)
        if pair is None:
            continue

        additions.append({
            "game_id": game_id,
            "season": int(receipt_season) if receipt_season is not None else int(season),
            "lock_timestamp_utc": str(receipt.get("lock_timestamp_utc", "")),
            "locked_home_moneyline": pair[0],
            "locked_away_moneyline": pair[1],
            "bet_price_source": source_label,
            "bet_price_verified_utc": verified_at,
        })
        existing_ids.add(game_id)

    if additions:
        ledger = pd.concat([ledger, pd.DataFrame(additions)], ignore_index=True)
    ledger = ledger.drop_duplicates("game_id", keep="first").sort_values(["season", "game_id"], kind="stable")
    return ledger, len(additions)


def _lock_timestamp(value: object) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _nflverse_snapshot_shas_at_or_before(
    lock_utc: datetime,
    timeout: int = 20,
    limit: int = HISTORICAL_COMMIT_LOOKBACK,
) -> list[str]:
    """Return recent games.csv commits at or before the receipt lock, newest first.

    LevLine can consume an nflverse snapshot moments before nflverse publishes a newer
    commit. Looking only at the single latest upstream commit can therefore miss the
    exact pair that generated the immutable market probability. A bounded backward
    walk lets us recover that immediately preceding snapshot while the probability
    equality check remains the authority for accepting a price.
    """
    per_page = max(1, min(int(limit), 100))
    params = urlencode({
        "path": "data/games.csv",
        "until": lock_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "per_page": per_page,
    })
    request = Request(
        f"{NFLVERSE_COMMITS_API}?{params}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "LevLine-Bet-Tracker/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception:
        return []
    if not isinstance(payload, list):
        return []

    shas: list[str] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        sha = str(entry.get("sha", "")).strip()
        if sha and sha not in shas:
            shas.append(sha)
    return shas


def _nflverse_snapshot_sha_at_or_before(lock_utc: datetime, timeout: int = 20) -> str | None:
    shas = _nflverse_snapshot_shas_at_or_before(lock_utc, timeout=timeout, limit=1)
    return shas[0] if shas else None


def _historical_market_snapshot_by_sha(sha: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(NFLVERSE_RAW_TEMPLATE.format(sha=sha), low_memory=False)
    except Exception:
        return None


def _historical_market_snapshot(lock_utc: datetime) -> tuple[pd.DataFrame, str] | None:
    sha = _nflverse_snapshot_sha_at_or_before(lock_utc)
    if not sha:
        return None
    frame = _historical_market_snapshot_by_sha(sha)
    if frame is None:
        return None
    return frame, sha


def _historical_backfill(
    history: pd.DataFrame,
    ledger: pd.DataFrame,
    *,
    season: int,
) -> tuple[pd.DataFrame, int]:
    """Try archived nflverse snapshots for receipts not verifiable from today's file.

    For each immutable lock timestamp, walk a small number of archived games.csv
    commits backward from the lock. This handles upstream publication/consumption lag
    such as a price changing a few minutes before LevLine's receipt was written. Every
    candidate still must reproduce the receipt's exact vig-free probability, so the
    wider search cannot silently substitute a merely nearby market price.
    """
    existing_ids = set(ledger["game_id"].astype(str)) if not ledger.empty else set()
    candidates = history[
        history.get("lock_status", pd.Series("", index=history.index)).astype(str).str.upper().eq("LOCKED")
    ].copy()
    if "season" in candidates.columns:
        candidates = candidates[pd.to_numeric(candidates["season"], errors="coerce").eq(int(season))]
    candidates = candidates[~candidates["game_id"].astype(str).isin(existing_ids)]
    if candidates.empty:
        return ledger, 0

    commit_cache: dict[str, list[str]] = {}
    snapshot_cache: dict[str, pd.DataFrame | None] = {}
    added = 0
    for _, receipt in candidates.iterrows():
        lock_utc = _lock_timestamp(receipt.get("lock_timestamp_utc"))
        if lock_utc is None:
            continue
        cache_key = lock_utc.isoformat()
        if cache_key not in commit_cache:
            commit_cache[cache_key] = _nflverse_snapshot_shas_at_or_before(lock_utc)

        for sha in commit_cache[cache_key]:
            if sha not in snapshot_cache:
                snapshot_cache[sha] = _historical_market_snapshot_by_sha(sha)
            market = snapshot_cache[sha]
            if market is None:
                continue
            one = pd.DataFrame([receipt.to_dict()])
            ledger, changed = enrich_price_ledger(
                one,
                market,
                ledger,
                season=season,
                source_label=f"nflverse_git:{sha}_verified_against_locked_market_probability",
            )
            if changed:
                added += changed
                break
    return ledger, added


def capture(
    history_path: Path,
    ledger_path: Path,
    *,
    season: int = 2026,
    market_source: str = NFLVERSE_GAMES_URL,
    historical_backfill: bool = True,
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

    ledger, current_added = enrich_price_ledger(history, market, existing, season=season)
    historical_added = 0
    if historical_backfill:
        ledger, historical_added = _historical_backfill(history, ledger, season=season)
    changed = current_added + historical_added

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
    parser.add_argument("--no-historical-backfill", action="store_true")
    args = parser.parse_args()
    changed = capture(
        args.history,
        args.ledger,
        season=args.season,
        market_source=args.market_source,
        historical_backfill=not args.no_historical_backfill,
    )
    print(f"Verified moneyline prices added to {changed} betting-price receipt(s).")


if __name__ == "__main__":
    main()

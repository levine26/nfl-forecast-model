from __future__ import annotations

"""Research-only near-kickoff multi-book capture.

The collector is intentionally gated before making a paid/quota-bearing request. It never
writes production outputs and never changes the official lock. Persist its research output
on a dedicated data branch rather than advancing main.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from nfl_forecast.challenger_market_reliance import kickoff_utc
from nfl_forecast.challenger_market_sources import devig_two_way, robust_logit_consensus
from nfl_forecast.fst_production import frozen_fst_probability, load_fst_artifact

API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
TEAM_ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def _fst_probability(pure_probability: float, market_probability: float) -> float:
    artifact = load_fst_artifact()
    probability = frozen_fst_probability(
        np.asarray([market_probability], dtype=float),
        np.asarray([pure_probability], dtype=float),
        artifact,
    )
    return float(probability[0])


def _due_games(
    slate: pd.DataFrame,
    now_utc: datetime,
    *,
    min_minutes: float,
    max_minutes: float,
) -> pd.DataFrame:
    rows = []
    for _, row in slate.iterrows():
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        minutes = (kickoff - now_utc).total_seconds() / 60.0
        if min_minutes <= minutes <= max_minutes:
            item = row.to_dict()
            item["kickoff_utc"] = kickoff.isoformat()
            item["minutes_to_kickoff"] = float(minutes)
            rows.append(item)
    return pd.DataFrame(rows)


def _status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _outcome_price(market: dict, team: str) -> float | None:
    for outcome in market.get("outcomes", []):
        if outcome.get("name") == team:
            try:
                return float(outcome.get("price"))
            except Exception:
                return None
    return None


def capture(
    *,
    slate_path: str = "outputs/this_week.csv",
    history_path: str = "research_outputs/phase2_market_reliance/live_market_history.csv",
    status_path: str = "research_outputs/phase2_market_reliance/live_market_status.json",
    min_minutes: float = 10.0,
    max_minutes: float = 65.0,
    quota_reserve: int = 50,
    now_utc: datetime | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    slate_file = Path(slate_path)
    if not slate_file.exists():
        return {"status": "skipped", "reason": "missing_slate", "external_request_made": False}
    slate = pd.read_csv(slate_file)
    due = _due_games(slate, now, min_minutes=min_minutes, max_minutes=max_minutes)
    if due.empty:
        return {"status": "skipped", "reason": "no_due_games", "external_request_made": False}

    status_file = Path(status_path)
    previous_status = _status(status_file)
    remaining = previous_status.get("quota_remaining")
    if remaining is not None and int(remaining) <= int(quota_reserve):
        return {
            "status": "skipped",
            "reason": "quota_reserve_reached",
            "quota_remaining": int(remaining),
            "external_request_made": False,
        }

    api_key = os.getenv("THE_ODDS_API_KEY", "").strip()
    if not api_key:
        return {"status": "skipped", "reason": "missing_api_key", "external_request_made": False}

    response = requests.get(
        API_URL,
        params={
            "apiKey": api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
        timeout=20,
    )
    response.raise_for_status()
    events = response.json()
    request_timestamp = now.isoformat()
    by_matchup = {
        (str(row.away_team), str(row.home_team)): row
        for _, row in due.iterrows()
    }
    rows: list[dict] = []
    for event in events:
        home_name = str(event.get("home_team", ""))
        away_name = str(event.get("away_team", ""))
        matchup = (TEAM_ABBR.get(away_name), TEAM_ABBR.get(home_name))
        if None in matchup or matchup not in by_matchup:
            continue
        slate_row = by_matchup[matchup]
        source_probabilities: list[float] = []
        source_names: list[str] = []
        source_updates: list[pd.Timestamp] = []
        for bookmaker in event.get("bookmakers", []):
            h2h = next((m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None)
            if not h2h:
                continue
            home_odds = _outcome_price(h2h, home_name)
            away_odds = _outcome_price(h2h, away_name)
            if home_odds is None or away_odds is None:
                continue
            probability = devig_two_way(home_odds, away_odds)
            source_name = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
            last_update = pd.to_datetime(bookmaker.get("last_update"), utc=True, errors="coerce")
            if pd.notna(last_update):
                source_updates.append(last_update)
            source_probabilities.append(probability)
            source_names.append(source_name)
            rows.append(
                {
                    "request_timestamp_utc": request_timestamp,
                    # Information becomes observable to this research ledger at request time;
                    # the provider's own update time is recorded separately for freshness.
                    "snapshot_timestamp_utc": request_timestamp,
                    "game_id": slate_row.game_id,
                    "kickoff_utc": slate_row.kickoff_utc,
                    "minutes_to_kickoff": float(slate_row.minutes_to_kickoff),
                    "source_name": source_name,
                    "source_type": "sportsbook",
                    "source_last_update_utc": bookmaker.get("last_update"),
                    "home_probability": probability,
                    "home_moneyline": home_odds,
                    "away_moneyline": away_odds,
                    "research_levline_home_prob": np.nan,
                    "production_levline_home_prob": slate_row.get("final_home_prob", np.nan),
                    "production_market_home_prob": slate_row.get("market_home_prob", np.nan),
                    "football_home_prob": slate_row.get("fst_pure_home_prob", np.nan),
                    "research_only": True,
                    "production_authorized": False,
                }
            )
        if source_probabilities:
            consensus = robust_logit_consensus(source_probabilities)
            pure = pd.to_numeric(slate_row.get("fst_pure_home_prob"), errors="coerce")
            research_levline = _fst_probability(float(pure), consensus) if pd.notna(pure) else np.nan
            freshest_source_age_minutes = np.nan
            if source_updates:
                freshest = max(source_updates)
                freshest_source_age_minutes = max(
                    0.0, (pd.Timestamp(now) - freshest).total_seconds() / 60.0
                )
            rows.append(
                {
                    "request_timestamp_utc": request_timestamp,
                    "snapshot_timestamp_utc": request_timestamp,
                    "game_id": slate_row.game_id,
                    "kickoff_utc": slate_row.kickoff_utc,
                    "minutes_to_kickoff": float(slate_row.minutes_to_kickoff),
                    "source_name": "sportsbook_consensus",
                    "source_type": "derived_consensus",
                    "source_last_update_utc": request_timestamp,
                    "home_probability": consensus,
                    "home_moneyline": np.nan,
                    "away_moneyline": np.nan,
                    "research_levline_home_prob": research_levline,
                    "production_levline_home_prob": slate_row.get("final_home_prob", np.nan),
                    "production_market_home_prob": slate_row.get("market_home_prob", np.nan),
                    "football_home_prob": pure,
                    "source_count": len(source_probabilities),
                    "source_names": "|".join(sorted(source_names)),
                    "freshest_source_age_minutes": freshest_source_age_minutes,
                    "research_only": True,
                    "production_authorized": False,
                }
            )

    history_file = Path(history_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if history_file.exists():
        try:
            existing = pd.read_csv(history_file)
            new = pd.concat([existing, new], ignore_index=True, sort=False)
        except Exception:
            pass
    if not new.empty:
        new = new.drop_duplicates(
            ["request_timestamp_utc", "game_id", "source_name"], keep="last"
        )
        new.to_csv(history_file, index=False)

    def header_int(name: str) -> int | None:
        value = response.headers.get(name)
        try:
            return int(value) if value is not None else None
        except Exception:
            return None

    result = {
        "status": "captured",
        "request_timestamp_utc": request_timestamp,
        "due_games": int(len(due)),
        "rows_added_this_request": int(len(rows)),
        "external_request_made": True,
        "quota_used": header_int("x-requests-used"),
        "quota_remaining": header_int("x-requests-remaining"),
        "quota_last_request_cost": header_int("x-requests-last"),
        "quota_reserve": int(quota_reserve),
        "research_only": True,
        "production_changed": False,
    }
    status_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", default="outputs/this_week.csv")
    parser.add_argument(
        "--history",
        default="research_outputs/phase2_market_reliance/live_market_history.csv",
    )
    parser.add_argument(
        "--status",
        default="research_outputs/phase2_market_reliance/live_market_status.json",
    )
    parser.add_argument("--min-minutes", type=float, default=10.0)
    parser.add_argument("--max-minutes", type=float, default=65.0)
    parser.add_argument("--quota-reserve", type=int, default=50)
    args = parser.parse_args()
    result = capture(
        slate_path=args.slate,
        history_path=args.history,
        status_path=args.status,
        min_minutes=args.min_minutes,
        max_minutes=args.max_minutes,
        quota_reserve=args.quota_reserve,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

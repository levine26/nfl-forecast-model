from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from research.m1_market_contract_v1 import (
    LATEST_PREKICK,
    MAX_EVENT_KICKOFF_DELTA_MINUTES,
    MIN_COMPLETE_BOOKS,
    PROGRAM_ID,
    due_fixed_horizons,
    latest_prekick_due,
)
from research.m1_market_state_v1 import _complete_book
from research.market_capture_contract_v2 import LEDGER_IDENTITY_COLUMNS
from research.market_capture_v2 import consensus_row, normalize_bookmaker
from research.run_market_capture_v2 import (
    TEAM_ABBR,
    _header_int_any,
    _provider_configs,
    _request_market_events,
    _status,
    kickoff_utc,
)

TEAM_TOKEN_ALIASES = {
    "LAR": "LA",
    "JAC": "JAX",
    "WSH": "WAS",
}


def normalize_team_token(value: Any) -> str | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token in TEAM_ABBR:
        return TEAM_ABBR[token]
    token = TEAM_TOKEN_ALIASES.get(token, token)
    if token in set(TEAM_ABBR.values()):
        return token
    return None


def _parse_provider_kickoff(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def resolve_event(
    events: list[dict[str, Any]],
    *,
    away_team: str,
    home_team: str,
    kickoff_timestamp_utc: datetime,
) -> dict[str, Any] | None:
    """Resolve exactly one provider event; ambiguous or revised-too-far events fail closed."""
    away = normalize_team_token(away_team)
    home = normalize_team_token(home_team)
    if away is None or home is None:
        return None
    target = kickoff_timestamp_utc.astimezone(timezone.utc)
    candidates: list[tuple[float, dict[str, Any]]] = []
    for event in events:
        if normalize_team_token(event.get("away_team")) != away:
            continue
        if normalize_team_token(event.get("home_team")) != home:
            continue
        provider_kickoff = _parse_provider_kickoff(event.get("commence_time"))
        if provider_kickoff is None:
            continue
        delta = abs((provider_kickoff - target).total_seconds()) / 60.0
        if delta <= MAX_EVENT_KICKOFF_DELTA_MINUTES:
            candidates.append((delta, event))
    if len(candidates) != 1:
        return None
    return candidates[0][1]


def _captured_fixed_pairs(path: Path) -> set[tuple[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return set()
    required = {"game_id", "horizon", "row_type", "source_count", "m1_role"}
    if not required.issubset(frame.columns):
        return set()
    source_count = pd.to_numeric(frame["source_count"], errors="coerce")
    frame = frame[
        frame["row_type"].eq("consensus")
        & frame["m1_role"].isin(["predictor", "diagnostic_only"])
        & source_count.ge(MIN_COMPLETE_BOOKS)
        & frame["horizon"].ne(LATEST_PREKICK)
    ]
    return set(zip(frame["game_id"].astype(str), frame["horizon"].astype(str)))


def due_pairs(slate: pd.DataFrame, now_utc: datetime, captured: set[tuple[str, str]]) -> list[dict[str, Any]]:
    due: list[dict[str, Any]] = []
    for _, row in slate.iterrows():
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        game_id = str(row.get("game_id") or "")
        if not game_id:
            continue
        for horizon in due_fixed_horizons(kickoff, now_utc):
            pair = (game_id, horizon["horizon"])
            if pair in captured:
                continue
            due.append(
                {
                    "game_id": game_id,
                    "home_team": str(row.get("home_team")),
                    "away_team": str(row.get("away_team")),
                    "kickoff_timestamp_utc": kickoff,
                    **horizon,
                }
            )
        if latest_prekick_due(kickoff, now_utc):
            due.append(
                {
                    "game_id": game_id,
                    "home_team": str(row.get("home_team")),
                    "away_team": str(row.get("away_team")),
                    "kickoff_timestamp_utc": kickoff,
                    "horizon": LATEST_PREKICK,
                    "role": "diagnostic_only",
                    "target_timestamp_utc": now_utc,
                    "timing_error_minutes": 0.0,
                }
            )
    return due


def capture(
    *,
    slate_path: str = "outputs/this_week.csv",
    ledger_path: str = "research_outputs/m1_market_state_v1/market_snapshots.csv",
    status_path: str = "research_outputs/m1_market_state_v1/status.json",
    quota_reserve: int = 50,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    slate_file = Path(slate_path)
    ledger_file = Path(ledger_path)
    status_file = Path(status_path)

    if not slate_file.exists():
        return {"status": "skipped", "reason": "missing_slate", "external_request_made": False}
    slate = pd.read_csv(slate_file)
    due = due_pairs(slate, now, _captured_fixed_pairs(ledger_file))
    if not due:
        return {"status": "skipped", "reason": "no_uncaptured_m1_horizon_due", "external_request_made": False}

    providers = _provider_configs()
    if not providers:
        return {"status": "skipped", "reason": "missing_market_api_key", "external_request_made": False}

    previous = _status(status_file)
    remaining = previous.get("quota_remaining")
    primary = providers[0]
    if (
        remaining is not None
        and previous.get("market_provider") == primary["name"]
        and int(remaining) < int(quota_reserve) + int(primary["expected_cost"])
    ):
        return {
            "status": "skipped",
            "reason": "free_quota_reserve_reached",
            "market_provider": primary["name"],
            "quota_remaining": int(remaining),
            "external_request_made": False,
        }

    provider_name, response, events, failures, request_cost = _request_market_events(providers)
    rows: list[dict[str, Any]] = []
    missed: list[str] = []
    for item in due:
        event = resolve_event(
            events,
            away_team=item["away_team"],
            home_team=item["home_team"],
            kickoff_timestamp_utc=item["kickoff_timestamp_utc"],
        )
        if event is None:
            missed.append(f"{item['game_id']}:{item['horizon']}:event_identity_unresolved")
            continue

        raw_books: list[dict[str, Any]] = []
        complete_books: list[dict[str, Any]] = []
        for bookmaker in event.get("bookmakers", []):
            row = normalize_bookmaker(
                event=event,
                bookmaker=bookmaker,
                game_id=item["game_id"],
                home_team=item["home_team"],
                away_team=item["away_team"],
                horizon=item["horizon"],
                target_timestamp_utc=item["target_timestamp_utc"],
                request_timestamp_utc=now,
                kickoff_timestamp_utc=item["kickoff_timestamp_utc"],
            )
            if row is None:
                continue
            row.update(
                {
                    "market_provider": provider_name,
                    "program_id": PROGRAM_ID,
                    "m1_role": item["role"],
                    "completed_2026_outcomes_used": 0,
                }
            )
            row["m1_complete_book"] = _complete_book(row)
            raw_books.append(row)
            if row["m1_complete_book"]:
                complete_books.append(row)
        rows.extend(raw_books)

        consensus = consensus_row(complete_books)
        if consensus is None or int(consensus.get("source_count", 0)) < MIN_COMPLETE_BOOKS:
            missed.append(f"{item['game_id']}:{item['horizon']}:insufficient_complete_books")
            continue
        consensus.update(
            {
                "program_id": PROGRAM_ID,
                "m1_role": item["role"],
                "m1_complete_book": True,
                "completed_2026_outcomes_used": 0,
            }
        )
        rows.append(consensus)

    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    combined = pd.DataFrame(rows)
    if ledger_file.exists() and ledger_file.stat().st_size > 0:
        try:
            combined = pd.concat([pd.read_csv(ledger_file), combined], ignore_index=True, sort=False)
        except Exception:
            pass
    if not combined.empty:
        combined = combined.drop_duplicates(list(LEDGER_IDENTITY_COLUMNS), keep="first")
        combined.to_csv(ledger_file, index=False)

    result = {
        "program_id": PROGRAM_ID,
        "status": "captured" if rows else "skipped",
        "reason": None if rows else "no_qualified_market_rows",
        "request_timestamp_utc": now.isoformat(),
        "due_pairs": len(due),
        "rows_added_this_request": len(rows),
        "missed": missed,
        "external_request_made": True,
        "market_provider": provider_name,
        "configured_market_sources": [str(provider["name"]) for provider in providers],
        "provider_failures_before_success": failures,
        "quota_used": _header_int_any(response, ("x-daily-used", "x-requests-used")),
        "quota_remaining": _header_int_any(response, ("x-daily-remaining", "x-requests-remaining")),
        "quota_last_request_cost": _header_int_any(response, ("x-requests-last",)),
        "expected_request_cost": request_cost,
        "quota_reserve": int(quota_reserve),
        "minimum_complete_books": MIN_COMPLETE_BOOKS,
        "historical_endpoint_used": False,
        "research_only": True,
        "production_authorized": False,
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", default="outputs/this_week.csv")
    parser.add_argument("--ledger", default="research_outputs/m1_market_state_v1/market_snapshots.csv")
    parser.add_argument("--status", default="research_outputs/m1_market_state_v1/status.json")
    parser.add_argument("--quota-reserve", type=int, default=50)
    args = parser.parse_args()
    print(
        json.dumps(
            capture(
                slate_path=args.slate,
                ledger_path=args.ledger,
                status_path=args.status,
                quota_reserve=args.quota_reserve,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

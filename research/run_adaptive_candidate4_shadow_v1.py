from __future__ import annotations

"""Create immutable Candidate 4 prospective T-60 research decisions.

This runner has no network access. It combines three already-frozen evidence surfaces:
the official production F-ST lock, the append-only market horizon ledger, and the
Candidate 4 QB-state ledger. It waits for all three surfaces instead of converting an
upstream workflow race into a permanent missing-data decision.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pandas as pd

from research.adaptive_candidate4_shadow_v1 import (
    append_immutable,
    build_candidate4_decisions,
)

PROCESSING_GRACE_MINUTES = 15


def _utc(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _ready_game_ids(
    production_history: pd.DataFrame,
    market_ledger: pd.DataFrame,
    qb_state: pd.DataFrame,
    *,
    now_utc: datetime,
) -> set[str]:
    if production_history.empty or market_ledger.empty or qb_state.empty:
        return set()
    if "game_id" not in qb_state.columns:
        return set()
    qb_ids = set(qb_state["game_id"].astype(str))

    required_market = {"game_id", "horizon", "row_type"}
    if not required_market.issubset(market_ledger.columns):
        return set()
    consensus = market_ledger[
        market_ledger["row_type"].astype(str).eq("consensus")
    ].copy()
    market_ids: set[str] = set()
    for gid, frame in consensus.groupby(consensus["game_id"].astype(str), sort=False):
        horizons = set(frame["horizon"].astype(str))
        if {"T-120m", "T-60m"}.issubset(horizons):
            market_ids.add(str(gid))

    ready: set[str] = set()
    for row in production_history.to_dict("records"):
        gid = str(row.get("game_id") or "")
        if gid not in qb_ids or gid not in market_ids:
            continue
        kickoff = _utc(row.get("kickoff_utc"))
        if kickoff is None:
            continue
        t60 = kickoff - timedelta(minutes=60)
        if now_utc < t60 + timedelta(minutes=PROCESSING_GRACE_MINUTES):
            continue
        if now_utc >= kickoff:
            continue
        ready.add(gid)
    return ready


def run(
    *,
    production_history_path: Path,
    market_ledger_path: Path,
    qb_state_path: Path,
    output_path: Path,
    now_utc: datetime | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    production = _read_csv(production_history_path)
    market = _read_csv(market_ledger_path)
    qb = _read_csv(qb_state_path)
    existing = _read_csv(output_path)

    ready_ids = _ready_game_ids(
        production,
        market,
        qb,
        now_utc=now,
    )
    already = set(existing["game_id"].astype(str)) if "game_id" in existing.columns else set()
    pending = ready_ids - already
    if not pending:
        return {
            "status": "skipped",
            "reason": "no_candidate4_decision_ready",
            "rows_added": 0,
            "ready_games": len(ready_ids),
            "processing_grace_minutes": PROCESSING_GRACE_MINUTES,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    production_subset = production[
        production["game_id"].astype(str).isin(pending)
    ].copy()
    qb_subset = qb[qb["game_id"].astype(str).isin(pending)].copy()

    decisions = build_candidate4_decisions(
        production_subset,
        market,
        qb_subset,
        generated_at_utc=now,
    )
    if decisions.empty:
        return {
            "status": "skipped",
            "reason": "builder_produced_no_rows",
            "rows_added": 0,
            "ready_games": len(ready_ids),
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    combined = append_immutable(existing, decisions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)
    added = len(combined) - len(existing)

    eligible_total = (
        int(combined["eligible"].fillna(False).astype(bool).sum())
        if "eligible" in combined.columns else 0
    )
    switches_total = (
        int(combined["candidate_switch"].fillna(False).astype(bool).sum())
        if "candidate_switch" in combined.columns else 0
    )
    status = {
        "status": "locked" if added else "unchanged",
        "rows_added": int(added),
        "ledger_rows": int(len(combined)),
        "ready_games": int(len(ready_ids)),
        "eligible_rows_total": eligible_total,
        "switches_total": switches_total,
        "processing_grace_minutes": PROCESSING_GRACE_MINUTES,
        "run_timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    output_path.with_name("status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--production-history",
        type=Path,
        default=Path("outputs/prediction_history.csv"),
    )
    parser.add_argument(
        "--market-ledger",
        type=Path,
        default=Path("research_outputs/market_capture_v2/market_snapshots.csv"),
    )
    parser.add_argument(
        "--qb-state",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4/qb_state.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research_outputs/adaptive_candidate4_v1/decision_ledger.csv"),
    )
    args = parser.parse_args()
    result = run(
        production_history_path=args.production_history,
        market_ledger_path=args.market_ledger,
        qb_state_path=args.qb_state,
        output_path=args.output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

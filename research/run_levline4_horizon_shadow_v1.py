from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from research.levline4_horizon_shadow_v1 import build_shadow_ledger


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def run(
    *,
    market_path: str = "research_outputs/market_capture_v2/market_snapshots.csv",
    prediction_history_path: str = "outputs/prediction_history.csv",
    ledger_path: str = "research_outputs/market_capture_v2/levline4_horizon_shadow.csv",
    status_path: str = "research_outputs/market_capture_v2/levline4_horizon_shadow_status.json",
    generated_at_utc: datetime | None = None,
) -> dict:
    market_file = Path(market_path)
    history_file = Path(prediction_history_path)
    ledger_file = Path(ledger_path)
    status_file = Path(status_path)

    market = _read_csv(market_file)
    history = _read_csv(history_file)
    existing = _read_csv(ledger_file)
    before = len(existing)
    generated_at = generated_at_utc or datetime.now(timezone.utc)

    combined = build_shadow_ledger(
        market,
        history,
        existing_ledger=existing,
        generated_at_utc=generated_at,
    )
    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    if not combined.empty:
        combined.to_csv(ledger_file, index=False)

    result = {
        "status": "updated" if len(combined) > before else "unchanged",
        "generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "market_rows_available": int(len(market)),
        "official_lock_rows_available": int(len(history)),
        "shadow_rows_before": int(before),
        "shadow_rows_after": int(len(combined)),
        "shadow_rows_added": int(max(0, len(combined) - before)),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="research_outputs/market_capture_v2/market_snapshots.csv")
    parser.add_argument("--prediction-history", default="outputs/prediction_history.csv")
    parser.add_argument("--ledger", default="research_outputs/market_capture_v2/levline4_horizon_shadow.csv")
    parser.add_argument("--status", default="research_outputs/market_capture_v2/levline4_horizon_shadow_status.json")
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                market_path=args.market,
                prediction_history_path=args.prediction_history,
                ledger_path=args.ledger,
                status_path=args.status,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

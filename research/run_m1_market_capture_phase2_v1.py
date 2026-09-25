from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.m1_market_contract_v1 import PROGRAM_ID
from research.run_m1_market_capture_v1 import capture as _phase1_capture


def _as_utc(value: datetime | None) -> datetime:
    now = value or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _persist_status(path: Path, payload: dict[str, Any], *, now_utc: datetime) -> dict[str, Any]:
    result = {
        "program_id": PROGRAM_ID,
        "phase": "PROSPECTIVE PHASE 2 — LIVE ACCUMULATION AND OPERATIONAL QUALIFICATION",
        "request_timestamp_utc": now_utc.isoformat(),
        "research_only": True,
        "production_authorized": False,
        "production_changed": False,
        "historical_endpoint_used": False,
        "completed_2026_outcomes_used": 0,
        **payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def capture_phase2(
    *,
    slate_path: str = "outputs/this_week.csv",
    ledger_path: str = "research_outputs/m1_market_state_v1/market_snapshots.csv",
    status_path: str = "research_outputs/m1_market_state_v1/status.json",
    quota_reserve: int = 50,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run the frozen Phase-1 collector while making every Phase-2 exit durable.

    This wrapper does not alter due-horizon logic, provider preference, book eligibility,
    feature construction, or any market observation. It only persists the collector's
    operational result so Phase 2 can distinguish quota/key/provider failures from
    scientific missingness without consulting completed-game outcomes.
    """
    now = _as_utc(now_utc)
    status_file = Path(status_path)
    try:
        result = _phase1_capture(
            slate_path=slate_path,
            ledger_path=ledger_path,
            status_path=status_path,
            quota_reserve=quota_reserve,
            now_utc=now,
        )
    except Exception as exc:
        message = str(exc)
        reason = (
            "provider_api_failure"
            if message.startswith("all configured market providers failed")
            else "capture_exception"
        )
        _persist_status(
            status_file,
            {
                "status": "failed",
                "reason": reason,
                "error_type": type(exc).__name__,
                "error_summary": message[:500],
                "external_request_made": reason == "provider_api_failure",
                "quota_reserve": int(quota_reserve),
            },
            now_utc=now,
        )
        raise

    return _persist_status(
        status_file,
        {
            **result,
            "quota_reserve": int(result.get("quota_reserve", quota_reserve)),
        },
        now_utc=now,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slate", default="outputs/this_week.csv")
    parser.add_argument("--ledger", default="research_outputs/m1_market_state_v1/market_snapshots.csv")
    parser.add_argument("--status", default="research_outputs/m1_market_state_v1/status.json")
    parser.add_argument("--quota-reserve", type=int, default=50)
    args = parser.parse_args()
    print(
        json.dumps(
            capture_phase2(
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

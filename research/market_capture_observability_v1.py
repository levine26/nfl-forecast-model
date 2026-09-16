from __future__ import annotations

"""Persist outcome-blind health evidence for the prospective market collector.

The underlying collector intentionally remains the source of market semantics. This wrapper
adds only operational observability: every invoked capture attempt produces a status receipt,
including safe evidence about whether the API credential was configured. It never logs the
credential value and never changes a forecast or market feature.
"""

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
from typing import Callable

from research.run_market_capture_v2 import capture as market_capture

OBSERVABILITY_SCHEMA = "levline-market-capture-observability-v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_receipt(result: dict, *, api_key_configured: bool) -> dict:
    receipt = dict(result)
    receipt.update(
        {
            "observability_schema": OBSERVABILITY_SCHEMA,
            "observed_at_utc": _iso_now(),
            "api_key_configured": bool(api_key_configured),
            "api_key_value_recorded": False,
            "research_only": True,
            "production_authorized": False,
            "probability_feature_authorized": False,
            "official_forecast_mutation_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
    )
    return receipt


def run_observed_capture(
    *,
    status_path: str = "research_outputs/market_capture_v2/status.json",
    quota_reserve: int = 50,
    capture_fn: Callable[..., dict] = market_capture,
) -> tuple[dict, int]:
    status_file = Path(status_path)
    api_key_configured = bool(os.getenv("THE_ODDS_API_KEY", "").strip())
    exit_code = 0

    try:
        result = capture_fn(status_path=status_path, quota_reserve=quota_reserve)
    except Exception as exc:  # preserve evidence before surfacing the original failure
        result = {
            "status": "error",
            "reason": "collector_exception",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "external_request_made": None,
        }
        exit_code = 1

    if result.get("reason") == "missing_api_key":
        exit_code = max(exit_code, 2)

    receipt = _safe_receipt(result, api_key_configured=api_key_configured)
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt, exit_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", default="research_outputs/market_capture_v2/status.json")
    parser.add_argument("--quota-reserve", type=int, default=50)
    args = parser.parse_args()

    receipt, exit_code = run_observed_capture(
        status_path=args.status,
        quota_reserve=args.quota_reserve,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

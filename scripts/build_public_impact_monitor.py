from __future__ import annotations

"""Build the optional public Impact Monitor payload.

Fail-closed publication rules:
- Missing staging input emits an empty payload.
- Non-empty staging input requires an explicit top-level source-governance approval.
- The research compositor performs row-level suppression of unapproved observed statistics.
- The output never authorizes player context as an F-ST probability feature.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from nfl_forecast.player_impact_monitor import build_impact_monitor_payload

APPROVED_REVIEW = "approved_for_publication"


def _read_staging(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None or not path.exists():
        return [], "no_staging_input"

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Impact Monitor staging payload must be a JSON object")

    cards = payload.get("cards") or []
    if not isinstance(cards, list):
        raise ValueError("Impact Monitor staging cards must be a list")
    if not cards:
        return [], "staging_empty"

    if payload.get("source_governance_review_status") != APPROVED_REVIEW:
        raise ValueError(
            "Non-empty Impact Monitor publication requires "
            "source_governance_review_status=approved_for_publication"
        )
    if payload.get("probability_feature_authorized") is True:
        raise ValueError("Impact Monitor publication cannot authorize a probability feature")

    return cards, APPROVED_REVIEW


def run(
    *,
    staging_json: str | None = "outputs/impact_monitor_publication_staging.json",
    output: str = "site/public/data/impact_monitor.json",
    generated_utc: str | None = None,
) -> dict[str, Any]:
    staging_path = Path(staging_json) if staging_json else None
    cards, review_status = _read_staging(staging_path)
    payload = build_impact_monitor_payload(cards, generated_utc=generated_utc)
    payload["source_governance_review_status"] = review_status
    payload["public_game_count"] = len(payload.get("games") or [])
    payload["probability_feature_authorized"] = False

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--staging-json",
        default="outputs/impact_monitor_publication_staging.json",
        help="Optional governance-approved staging payload. Missing input publishes an empty monitor.",
    )
    parser.add_argument("--output", default="site/public/data/impact_monitor.json")
    parser.add_argument("--generated-utc", default=None)
    args = parser.parse_args()
    run(staging_json=args.staging_json, output=args.output, generated_utc=args.generated_utc)


if __name__ == "__main__":
    main()

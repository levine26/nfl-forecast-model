from __future__ import annotations

"""Fail-closed readiness and first-capture acceptance audit for Props 2.2.

Valid states:
- ARMED_AWAITING_FIRST_CAPTURE: no Props 2.2 ledger exists yet, but the frozen grid
  and live workflow hook are correctly wired for the next untouched pregame run.
- FIRST_CAPTURE_VERIFIED: an immutable ledger exists and every source forecast has the
  complete frozen challenger grid with valid chronology, receipt hashes, and research-only
  governance.

This audit never creates or mutates prospective receipts.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from research.props.v22.capture_prospective import CAPTURE_NOT_BEFORE_UTC, read_jsonl
from research.props.v22.challengers import load_grid


class Props22ReadinessError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _receipt_hash(row: Mapping[str, Any]) -> str:
    unsigned = dict(row)
    unsigned.pop("receipt_sha256", None)
    return sha256(_canonical(unsigned).encode("utf-8")).hexdigest()


def _timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise Props22ReadinessError(f"invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise Props22ReadinessError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _validate_live_hook(workflow_text: str) -> dict[str, Any]:
    required = (
        "--allow-empty-postkickoff",
        "postkickoff_noop.json",
        "python research/props/v22/capture_prospective.py",
        "--source-json challenger_outputs/props21/public_challenger.json",
        "--output challenger_outputs/props22/forecast_originals.jsonl",
        "challenger_outputs/props22",
    )
    missing = [marker for marker in required if marker not in workflow_text]
    if missing:
        raise Props22ReadinessError(f"live Props workflow is missing capture markers: {missing}")

    noop_index = workflow_text.find("postkickoff_noop.json")
    capture_index = workflow_text.find("python research/props/v22/capture_prospective.py")
    if noop_index < 0 or capture_index < 0 or capture_index <= noop_index:
        raise Props22ReadinessError(
            "Props 2.2 capture must occur only after the post-kickoff no-op guard"
        )

    return {
        "live_hook_present": True,
        "postkickoff_noop_precedes_capture": True,
    }


def _audit_ledger(
    rows: list[dict[str, Any]],
    *,
    expected_challenger_ids: set[str],
    contract_version: str,
    baseline_model: str,
) -> dict[str, Any]:
    if not rows:
        raise Props22ReadinessError("internal error: ledger audit received no rows")

    by_source: dict[str, set[str]] = defaultdict(set)
    source_ids: dict[str, str] = {}
    identities: set[tuple[str, str]] = set()
    forecast_times: list[datetime] = []
    kickoff_times: list[datetime] = []

    for line_no, row in enumerate(rows, start=1):
        if row.get("contract_version") != contract_version:
            raise Props22ReadinessError(
                f"ledger row {line_no}: contract version drift: {row.get('contract_version')!r}"
            )
        if row.get("research_only") is not True or row.get("production_authorized") is not False:
            raise Props22ReadinessError(
                f"ledger row {line_no}: Props 2.2 receipt escaped research-only governance"
            )
        if row.get("outcome") is not None:
            raise Props22ReadinessError(
                f"ledger row {line_no}: prospective receipt contains outcome data"
            )
        if row.get("source_props21_model_version") != baseline_model:
            raise Props22ReadinessError(
                f"ledger row {line_no}: source baseline mismatch: "
                f"{row.get('source_props21_model_version')!r}"
            )

        source_sha = str(row.get("source_props21_forecast_sha256") or "").strip()
        challenger_id = str(row.get("challenger_id") or "").strip()
        source_id = str(row.get("source_props21_forecast_id") or "").strip()
        receipt_sha = str(row.get("receipt_sha256") or "").strip()

        if len(source_sha) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha.lower()):
            raise Props22ReadinessError(f"ledger row {line_no}: invalid source forecast SHA-256")
        if challenger_id not in expected_challenger_ids:
            raise Props22ReadinessError(
                f"ledger row {line_no}: unknown challenger id {challenger_id!r}"
            )
        if not source_id:
            raise Props22ReadinessError(
                f"ledger row {line_no}: missing source Props 2.1 forecast id"
            )
        if len(receipt_sha) != 64 or receipt_sha != _receipt_hash(row):
            raise Props22ReadinessError(
                f"ledger row {line_no}: immutable receipt SHA-256 mismatch"
            )

        identity = (source_sha, challenger_id)
        if identity in identities:
            raise Props22ReadinessError(
                f"ledger row {line_no}: duplicate immutable identity {identity}"
            )
        identities.add(identity)

        prior_source_id = source_ids.get(source_sha)
        if prior_source_id is not None and prior_source_id != source_id:
            raise Props22ReadinessError(
                f"source SHA {source_sha} maps to multiple Props 2.1 forecast IDs"
            )
        source_ids[source_sha] = source_id
        by_source[source_sha].add(challenger_id)

        forecast_time = _timestamp(row.get("forecast_timestamp_utc"), "forecast_timestamp_utc")
        kickoff_time = _timestamp(row.get("kickoff_utc"), "kickoff_utc")
        if forecast_time < CAPTURE_NOT_BEFORE_UTC:
            raise Props22ReadinessError(
                f"ledger row {line_no}: forecast predates frozen Props 2.2 boundary"
            )
        if forecast_time >= kickoff_time:
            raise Props22ReadinessError(
                f"ledger row {line_no}: forecast is not strictly pre-kickoff"
            )

        chronology = row.get("chronology")
        if not isinstance(chronology, Mapping) or chronology.get("source_chronology_ok") is not True:
            raise Props22ReadinessError(
                f"ledger row {line_no}: source chronology is not valid"
            )

        forecast_times.append(forecast_time)
        kickoff_times.append(kickoff_time)

    incomplete = {
        source_sha: sorted(expected_challenger_ids - challenger_ids)
        for source_sha, challenger_ids in by_source.items()
        if challenger_ids != expected_challenger_ids
    }
    if incomplete:
        raise Props22ReadinessError(
            f"ledger does not contain the complete frozen challenger grid for every source: {incomplete}"
        )

    expected_rows = len(by_source) * len(expected_challenger_ids)
    if len(rows) != expected_rows:
        raise Props22ReadinessError(
            f"ledger row count {len(rows)} != expected complete-grid count {expected_rows}"
        )

    return {
        "state": "FIRST_CAPTURE_VERIFIED",
        "ledger_rows": len(rows),
        "source_forecasts": len(by_source),
        "challengers_per_source": len(expected_challenger_ids),
        "earliest_forecast_utc": min(forecast_times).isoformat(),
        "latest_forecast_utc": max(forecast_times).isoformat(),
        "earliest_kickoff_utc": min(kickoff_times).isoformat(),
        "all_receipt_hashes_valid": True,
        "all_sources_complete_grid": True,
        "all_source_chronology_valid": True,
        "all_receipts_research_only": True,
    }


def audit_readiness(
    *,
    workflow_path: Path,
    ledger_path: Path,
) -> dict[str, Any]:
    grid = load_grid()
    challenger_rows = grid.get("challengers")
    if not isinstance(challenger_rows, list) or not challenger_rows:
        raise Props22ReadinessError("frozen challenger grid is empty")
    challenger_ids = {
        str(row.get("id") or "").strip()
        for row in challenger_rows
        if isinstance(row, Mapping)
    }
    if "" in challenger_ids or len(challenger_ids) != len(challenger_rows):
        raise Props22ReadinessError("frozen challenger grid has missing/duplicate ids")

    hook = _validate_live_hook(workflow_path.read_text(encoding="utf-8"))
    rows = read_jsonl(ledger_path)

    common = {
        "contract_version": grid.get("contract_version"),
        "grid_status": grid.get("status"),
        "baseline_model": grid.get("baseline_model"),
        "capture_not_before_utc": CAPTURE_NOT_BEFORE_UTC.isoformat(),
        "frozen_challenger_count": len(challenger_ids),
        "promotion_candidate_ids": [
            str(row.get("id"))
            for row in challenger_rows
            if isinstance(row, Mapping) and row.get("promotion_eligible") is True
        ],
        **hook,
    }

    if not rows:
        return {
            **common,
            "state": "ARMED_AWAITING_FIRST_CAPTURE",
            "ledger_exists": ledger_path.exists(),
            "ledger_rows": 0,
            "source_forecasts": 0,
            "guardrail": (
                "No prospective Props 2.2 receipts exist yet. This is valid before the first "
                "future untouched pregame live Props publication; do not backfill Week 2."
            ),
        }

    return {
        **common,
        "ledger_exists": True,
        **_audit_ledger(
            rows,
            expected_challenger_ids=challenger_ids,
            contract_version=str(grid.get("contract_version") or ""),
            baseline_model=str(grid.get("baseline_model") or ""),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflow",
        type=Path,
        default=Path(".github/workflows/levline_markets_live.yml"),
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("challenger_outputs/props22/forecast_originals.jsonl"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = audit_readiness(workflow_path=args.workflow, ledger_path=args.ledger)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

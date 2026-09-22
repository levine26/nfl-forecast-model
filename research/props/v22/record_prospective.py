from __future__ import annotations

"""Record immutable, outcome-free Props 2.2 prospective challenger receipts.

This writer is intentionally separate from grading/evaluation. It consumes the exact
Props 2.1 challenger payload generated before kickoff, applies every preregistered
Props 2.2 candidate mechanically, and appends immutable research receipts. It never
reads outcomes and never selects a challenger.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from research.props.v22.challengers import Props22Error, build_slate


P21_CONTRACT = "levline-props-2.1-sunday-challenger-v0.1"
RECEIPT_VERSION = "levline-props22-prospective-original-v0.1"


class Props22CaptureError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise Props22CaptureError(f"{label} must be a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise Props22CaptureError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _sha_ref(value: str, label: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in text):
        raise Props22CaptureError(f"{label} must be a 40/64-character hex SHA")
    return text


def load_props21(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Props22CaptureError("Props 2.1 source must be a JSON object")
    if payload.get("contract_version") != P21_CONTRACT:
        raise Props22CaptureError(
            f"unexpected Props 2.1 contract: {payload.get('contract_version')!r}"
        )
    if payload.get("production_authorized") is not False:
        raise Props22CaptureError("Props 2.1 source must remain research-only")
    rows = payload.get("forecasts")
    if not isinstance(rows, list) or not rows:
        raise Props22CaptureError("Props 2.1 source contains no forecasts")

    generated = _timestamp(payload.get("generated_at"), "generated_at")
    for row in rows:
        if not isinstance(row, Mapping):
            raise Props22CaptureError("Props 2.1 forecasts must be objects")
        if row.get("outcome") is not None:
            raise Props22CaptureError("Props 2.1 source contains outcome-contaminated row")
        forecast = _timestamp(row.get("forecast_timestamp_utc"), "forecast_timestamp_utc")
        kickoff = _timestamp(row.get("kickoff_utc"), "kickoff_utc")
        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping):
            raise Props22CaptureError("Props 2.1 row is missing provenance")
        horizon = _timestamp(provenance.get("source_data_horizon_utc"), "source_data_horizon_utc")
        if not (horizon <= forecast <= generated < kickoff):
            raise Props22CaptureError(
                "Props 2.1 source chronology must satisfy data_horizon <= forecast <= "
                "capture < kickoff"
            )
        if provenance.get("research_only") is not True or provenance.get("production_authorized") is not False:
            raise Props22CaptureError("Props 2.1 row is not research-only")
    return payload


def build_receipts(
    payload: Mapping[str, Any],
    *,
    source_live_run_id: str,
    source_generation_sha: str,
    source_trigger_sha: str,
) -> list[dict[str, Any]]:
    run_id = str(source_live_run_id or "").strip()
    if not run_id:
        raise Props22CaptureError("source live workflow run ID is required")
    generation_sha = _sha_ref(source_generation_sha, "source generation SHA")
    trigger_sha = _sha_ref(source_trigger_sha, "source trigger SHA")

    rows = payload.get("forecasts")
    if not isinstance(rows, list) or not rows:
        raise Props22CaptureError("Props 2.1 source contains no forecasts")
    slate = build_slate(rows)
    generated_at = _timestamp(payload.get("generated_at"), "generated_at").isoformat()

    receipts: list[dict[str, Any]] = []
    for challenger in slate["challengers"]:
        if challenger.get("outcome") is not None:
            raise Props22CaptureError("Props 2.2 challenger unexpectedly contains outcome")
        identity = {
            "source_live_run_id": run_id,
            "source_props21_forecast_id": challenger.get("source_props21_forecast_id"),
            "challenger_id": challenger.get("challenger_id"),
        }
        receipt_id = "p22_" + _sha(identity)[:32]
        receipt = {
            "receipt_version": RECEIPT_VERSION,
            "receipt_id": receipt_id,
            "captured_utc": generated_at,
            "source_live_run_id": run_id,
            "source_generation_sha": generation_sha,
            "source_trigger_sha": trigger_sha,
            "source_props21_payload_sha256": _sha(payload),
            "challenger": challenger,
            "outcome": None,
            "immutable": True,
            "research_only": True,
            "production_authorized": False,
        }
        receipt["receipt_sha256"] = _sha(receipt)
        receipts.append(receipt)

    expected = len(rows) * len({r["challenger"]["challenger_id"] for r in receipts})
    if len(receipts) != expected:
        raise Props22CaptureError(
            f"Props 2.2 receipt count does not reconcile: got {len(receipts)} expected {expected}"
        )
    return receipts


def append_immutable(path: Path, receipts: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rid = str(row.get("receipt_id") or "")
            digest = str(row.get("receipt_sha256") or "")
            if not rid or not digest:
                raise Props22CaptureError("existing Props 2.2 ledger contains malformed receipt")
            if rid in existing and existing[rid] != digest:
                raise Props22CaptureError(f"conflicting duplicate existing receipt: {rid}")
            existing[rid] = digest

    new: list[str] = []
    for receipt in receipts:
        rid = str(receipt["receipt_id"])
        digest = str(receipt["receipt_sha256"])
        if rid in existing:
            if existing[rid] != digest:
                raise Props22CaptureError(f"immutable Props 2.2 receipt conflict: {rid}")
            continue
        new.append(_canonical(receipt))
        existing[rid] = digest

    if new:
        with path.open("a", encoding="utf-8") as handle:
            for line in new:
                handle.write(line + "\n")
    return len(new)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--source-live-run-id", required=True)
    parser.add_argument("--source-generation-sha", required=True)
    parser.add_argument("--source-trigger-sha", required=True)
    args = parser.parse_args()

    payload = load_props21(args.input)
    receipts = build_receipts(
        payload,
        source_live_run_id=args.source_live_run_id,
        source_generation_sha=args.source_generation_sha,
        source_trigger_sha=args.source_trigger_sha,
    )
    appended = append_immutable(args.ledger, receipts)
    challenger_ids = sorted({row["challenger"]["challenger_id"] for row in receipts})
    status = {
        "contract_version": "levline-props22-prospective-capture-v0.1",
        "source_live_run_id": str(args.source_live_run_id),
        "source_props21_forecasts": len(payload["forecasts"]),
        "challenger_ids": challenger_ids,
        "candidate_count": len(challenger_ids),
        "receipt_count_this_source": len(receipts),
        "appended": appended,
        "research_only": True,
        "production_authorized": False,
        "outcomes_used": 0,
        "automatic_promotion_authorized": False,
    }
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

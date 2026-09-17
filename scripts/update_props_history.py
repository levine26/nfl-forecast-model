from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_publication import (  # noqa: E402
    PropsPublicationError,
    append_jsonl_immutable,
    grade_forecast_receipt,
    make_closing_event,
    make_forecast_receipt,
    read_jsonl,
)

HISTORY_DIR = ROOT / "outputs" / "props" / "history"


def _json(path: Path):
    if not path.exists():
        raise PropsPublicationError(f"missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _aware(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PropsPublicationError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def record_forecasts(args) -> int:
    artifact = _json(args.input)
    rows = artifact.get("forecasts") if isinstance(artifact, dict) else None
    if not isinstance(rows, list):
        raise PropsPublicationError("forecast artifact must contain a forecasts list")
    recorded = _aware(args.recorded_utc)
    receipts = [make_forecast_receipt(row, recorded_utc=recorded) for row in rows if isinstance(row, dict)]
    count = append_jsonl_immutable(args.ledger, receipts, identity_key="forecast_id")
    print(f"recorded {count} new immutable forecast originals -> {args.ledger}")
    return 0


def record_closes(args) -> int:
    payload = _json(args.input)
    rows = payload if isinstance(payload, list) else payload.get("closes") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise PropsPublicationError("close input must be a list or contain a closes list")
    receipts = {str(row.get("forecast_id")): row for row in read_jsonl(args.forecast_ledger) if row.get("forecast_id")}
    events = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        forecast_id = str(row.get("forecast_id") or "")
        receipt = receipts.get(forecast_id)
        if receipt is None:
            raise PropsPublicationError(f"cannot attach closing market to unknown forecast_id={forecast_id}")
        original = receipt.get("original_forecast") or {}
        kickoff = _aware(original.get("kickoff_utc"))
        captured_value = row.get("captured_utc") or row.get("captured_at_utc")
        captured = _aware(captured_value)
        if captured > kickoff:
            raise PropsPublicationError(f"closing market timestamp is post-kickoff for forecast_id={forecast_id}")
        events.append(
            make_closing_event(
                forecast_id,
                captured_utc=captured,
                source=row.get("source"),
                line=row.get("line"),
                over_price_american=row.get("over_price_american"),
                under_price_american=row.get("under_price_american"),
                td_price_american=row.get("td_price_american"),
            )
        )
    count = append_jsonl_immutable(args.ledger, events, identity_key="event_id")
    print(f"recorded {count} new closing-market events -> {args.ledger}")
    return 0


def record_grades(args) -> int:
    payload = _json(args.input)
    rows = payload if isinstance(payload, list) else payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise PropsPublicationError("grade input must be a list or contain a results list")
    receipts = {str(row.get("forecast_id")): row for row in read_jsonl(args.forecast_ledger) if row.get("forecast_id")}
    events = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        forecast_id = str(row.get("forecast_id") or "")
        receipt = receipts.get(forecast_id)
        if receipt is None:
            raise PropsPublicationError(f"cannot grade unknown forecast_id={forecast_id}")
        events.append(
            grade_forecast_receipt(
                receipt,
                actual_result=row.get("actual_result"),
                graded_utc=row.get("graded_utc") or row.get("graded_at_utc"),
            )
        )
    count = append_jsonl_immutable(args.ledger, events, identity_key="event_id")
    print(f"recorded {count} new grade events -> {args.ledger}; originals were not rewritten")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Append-only history operations for LevLine Props Research Beta.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Persist original prospective forecast receipts.")
    record.add_argument("--input", type=Path, default=ROOT / "outputs" / "props" / "forecasts.json")
    record.add_argument("--ledger", type=Path, default=HISTORY_DIR / "forecast_originals.jsonl")
    record.add_argument("--recorded-utc")
    record.set_defaults(func=record_forecasts)

    close = sub.add_parser("close", help="Append closing market snapshots without touching originals.")
    close.add_argument("--input", type=Path, required=True)
    close.add_argument("--forecast-ledger", type=Path, default=HISTORY_DIR / "forecast_originals.jsonl")
    close.add_argument("--ledger", type=Path, default=HISTORY_DIR / "market_closes.jsonl")
    close.set_defaults(func=record_closes)

    grade = sub.add_parser("grade", help="Append result/grade events without touching originals.")
    grade.add_argument("--input", type=Path, required=True)
    grade.add_argument("--forecast-ledger", type=Path, default=HISTORY_DIR / "forecast_originals.jsonl")
    grade.add_argument("--ledger", type=Path, default=HISTORY_DIR / "grades.jsonl")
    grade.set_defaults(func=record_grades)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

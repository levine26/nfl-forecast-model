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
    build_history_view,
    build_public_props,
    read_jsonl,
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise PropsPublicationError(f"required Props forecast artifact is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PropsPublicationError("Props forecast artifact must be a JSON object")
    return value


def _parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PropsPublicationError("--now must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LevLine Props Research Beta public/history artifacts.")
    parser.add_argument("--input", type=Path, default=ROOT / "outputs" / "props" / "forecasts.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "props" / "public_props.json")
    parser.add_argument("--site-output", type=Path, default=ROOT / "site" / "public" / "data" / "props_public.json")
    parser.add_argument("--now", help="Timezone-aware ISO-8601 override for deterministic QA.")
    parser.add_argument("--forecast-ledger", type=Path, default=ROOT / "outputs" / "props" / "history" / "forecast_originals.jsonl")
    parser.add_argument("--closing-ledger", type=Path, default=ROOT / "outputs" / "props" / "history" / "market_closes.jsonl")
    parser.add_argument("--grade-ledger", type=Path, default=ROOT / "outputs" / "props" / "history" / "grades.jsonl")
    parser.add_argument("--history-output", type=Path, default=ROOT / "site" / "public" / "data" / "props_history.json")
    args = parser.parse_args()

    artifact = _read_json(args.input)
    public = build_public_props(artifact, now_utc=_parse_now(args.now))
    _write(args.output, public)
    _write(args.site_output, public)

    history = {
        "contract_version": "levline-props-history-view-v0.1",
        "research_label": public["research_label"],
        "records": build_history_view(
            read_jsonl(args.forecast_ledger),
            read_jsonl(args.closing_ledger),
            read_jsonl(args.grade_ledger),
        ),
    }
    _write(args.history_output, history)
    print(
        "props public contract OK: "
        f"{public['summary']['total']} forecasts "
        f"({public['summary']['model_edge']} edge / {public['summary']['watch']} watch / "
        f"{public['summary']['no_signal']} no signal)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

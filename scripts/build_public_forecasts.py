from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.public_forecast import PublicForecastError, build_public_forecasts  # noqa: E402


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise PublicForecastError(f"required forecast source is missing: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate Sunday Signal's canonical public forecast contract.")
    parser.add_argument("--current", type=Path, default=ROOT / "outputs" / "this_week.csv")
    parser.add_argument("--official", type=Path, default=ROOT / "outputs" / "prediction_history.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "public_forecasts.json")
    parser.add_argument("--now", help="Optional ISO-8601 UTC override for deterministic validation/tests.")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.now:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)

    payload = build_public_forecasts(_read_csv(args.current), _read_csv(args.official), now_utc=now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"public forecast contract OK: {len(payload['games'])} games -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

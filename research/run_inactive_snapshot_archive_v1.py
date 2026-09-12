from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from research.inactive_snapshot_archive_v1 import capture_inactives, verify_archive
from research.inactive_snapshot_due_v1 import due_games


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="outputs/this_week.csv")
    parser.add_argument("--output-dir", default="research_outputs/inactive_snapshot_archive_v1")
    parser.add_argument("--force", action="store_true", help="capture even when no game is inside the T-100..T-20 window")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    games = due_games(Path(args.feed), now)
    if not games and not args.force:
        print(json.dumps({"status": "not_due", "captured": False}, sort_keys=True))
        return

    result = capture_inactives(
        output_dir=args.output_dir,
        due_games=games,
        captured_at=now,
    )
    verification = verify_archive(args.output_dir)
    payload = {
        "status": result.observation.get("status"),
        "captured": result.observation.get("status") == "captured_raw",
        "due_games": len(games),
        "integrity_ok": verification["integrity_ok"],
        "raw_body_sha256": result.observation.get("raw_body_sha256"),
        "contains_inactive_reports_label": result.observation.get("contains_inactive_reports_label"),
        "contains_check_back_signal": result.observation.get("contains_check_back_signal"),
    }
    print(json.dumps(payload, sort_keys=True))
    if not verification["integrity_ok"]:
        raise SystemExit("inactive archive integrity verification failed")
    if result.observation.get("status") != "captured_raw":
        raise SystemExit("inactive snapshot capture failed")


if __name__ == "__main__":
    main()

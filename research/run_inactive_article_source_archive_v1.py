from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from research.inactive_article_source_archive_v1 import (
    capture_inactive_articles,
    verify_archive,
)
from research.inactive_snapshot_due_v1 import due_games


def run(
    *,
    feed_path: str = "outputs/this_week.csv",
    output_dir: str = "research_outputs/inactive_article_source_archive_v1",
    force: bool = False,
    now_utc: datetime | None = None,
) -> dict:
    now = now_utc or datetime.now(timezone.utc)
    games = due_games(Path(feed_path), now)
    if not games and not force:
        return {
            "status": "skipped",
            "reason": "no_game_in_inactive_capture_window",
            "research_only": True,
            "production_authorized": False,
        }

    result = capture_inactive_articles(
        output_dir=output_dir,
        due_games=games,
        captured_at=now,
    )
    integrity = verify_archive(output_dir)
    if not integrity["integrity_ok"]:
        raise RuntimeError(f"inactive article archive integrity failure: {integrity['failures']}")
    return {
        "status": result.observation["status"],
        "captured_at_utc": result.observation["captured_at_utc"],
        "due_games": len(games),
        "sources_captured": int(result.sources_captured),
        "discovered_article_urls": len(
            result.observation.get("discovered_inactive_article_urls") or []
        ),
        "integrity_ok": True,
        "player_level_parser_qualified": False,
        "probability_feature_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "research_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="outputs/this_week.csv")
    parser.add_argument(
        "--output-dir",
        default="research_outputs/inactive_article_source_archive_v1",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run(feed_path=args.feed, output_dir=args.output_dir, force=args.force),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

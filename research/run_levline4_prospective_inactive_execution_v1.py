from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from research.levline4_prospective_inactive_execution_v1 import (
    CONTRACT_ID,
    _append_jsonl_unique,
    _latest_due_observation,
    _week_from_due_games,
    execute,
)

EASTERN = ZoneInfo("America/New_York")
SUPPORTED_WEEK = 2


def cohort_is_sunday_eastern(due_games: list[dict[str, Any]]) -> bool:
    if not due_games:
        return False
    weekdays: set[int] = set()
    for game in due_games:
        text = str(game.get("kickoff_utc") or "").strip()
        if not text:
            raise ValueError("due game lacks kickoff_utc")
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("kickoff_utc must be timezone-aware")
        weekdays.add(dt.astimezone(EASTERN).weekday())
    if len(weekdays) != 1:
        raise ValueError(f"due cohort spans multiple Eastern weekdays: {sorted(weekdays)}")
    return weekdays == {6}


def _skip_receipt(
    *,
    output_dir: Path,
    observation: dict[str, Any],
    status: str,
    reason_token: str,
    week: int | None = None,
) -> dict[str, Any]:
    captured_at = str(observation.get("captured_at_utc") or "")
    due_games = list(observation.get("due_games") or [])
    game_ids = sorted(str(game.get("game_id") or "") for game in due_games)
    payload = "|".join(
        [CONTRACT_ID, reason_token, captured_at, ",".join(game_ids)]
    ).encode("utf-8")
    receipt = {
        "schema_version": "levline-2026-prospective-inactive-execution-v1",
        "contract_id": CONTRACT_ID,
        "attempt_id": hashlib.sha256(payload).hexdigest(),
        "status": status,
        "captured_at_utc": captured_at,
        "week": week,
        "due_game_ids": game_ids,
        "resolver_executed": False,
        "global_audit_executed": False,
        "identity_sources_read": False,
        "player_identity_to_gsis_qualified": False,
        "availability_probability_feature_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    _append_jsonl_unique(output_dir / "attempts.jsonl", receipt, key="attempt_id")
    return receipt


def run(
    *,
    archive_dir: Path,
    weekly_projection_path: Path,
    global_projection_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    observation = _latest_due_observation(archive_dir)
    if observation is None:
        return {
            "contract_id": CONTRACT_ID,
            "status": "SKIPPED_NO_DUE_CAPTURE",
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }

    due_games = list(observation.get("due_games") or [])
    week = _week_from_due_games(due_games)
    if week != SUPPORTED_WEEK:
        return _skip_receipt(
            output_dir=output_dir,
            observation=observation,
            status="SKIPPED_OUTSIDE_FROZEN_IDENTITY_SOURCE_WEEK",
            reason_token="unsupported-week-skip",
            week=week,
        )

    if not cohort_is_sunday_eastern(due_games):
        return _skip_receipt(
            output_dir=output_dir,
            observation=observation,
            status="SKIPPED_OUTSIDE_QUALIFIED_SUNDAY_ARTICLE_SEMANTICS",
            reason_token="non-sunday-skip",
            week=week,
        )

    return execute(
        archive_dir=archive_dir,
        weekly_projection_path=weekly_projection_path,
        global_projection_path=global_projection_path,
        output_dir=output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=Path("research_outputs/inactive_article_source_archive_v1"),
    )
    parser.add_argument("--weekly-projection", type=Path, required=True)
    parser.add_argument("--global-projection", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/levline4_prospective_inactive_execution_v1"),
    )
    args = parser.parse_args()
    receipt = run(
        archive_dir=args.archive_dir,
        weekly_projection_path=args.weekly_projection,
        global_projection_path=args.global_projection,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt.get("status") == "FAIL_CROSS_SOURCE_CONTRADICTION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

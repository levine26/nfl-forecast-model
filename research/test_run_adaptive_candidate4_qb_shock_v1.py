from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from research.run_adaptive_candidate4_qb_shock_v1 import candidate_cohorts


def _archive(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": "2026-09-27T15:59:00Z",
        "due_games": [
            {
                "game_id": "2026_03_LAC_BUF",
                "away_team": "LAC",
                "home_team": "BUF",
                "kickoff_utc": "2026-09-27T17:00:00+00:00",
                "minutes_to_kickoff": 61.0,
            }
        ],
        "sources": [],
    }
    (root / "observations.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")


def test_cohort_waits_for_processing_grace(tmp_path) -> None:
    _archive(tmp_path)
    before = candidate_cohorts(
        tmp_path,
        now_utc=datetime(2026, 9, 27, 16, 9, tzinfo=timezone.utc),
        existing_game_ids=set(),
    )
    ready = candidate_cohorts(
        tmp_path,
        now_utc=datetime(2026, 9, 27, 16, 10, tzinfo=timezone.utc),
        existing_game_ids=set(),
    )
    assert before == []
    assert len(ready) == 1
    assert ready[0][0]["game_id"] == "2026_03_LAC_BUF"


def test_existing_game_is_not_reprocessed(tmp_path) -> None:
    _archive(tmp_path)
    ready = candidate_cohorts(
        tmp_path,
        now_utc=datetime(2026, 9, 27, 16, 10, tzinfo=timezone.utc),
        existing_game_ids={"2026_03_LAC_BUF"},
    )
    assert ready == []


def test_non_sunday_game_is_never_candidate4_primary(tmp_path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": "2026-09-24T23:00:00Z",
        "due_games": [
            {
                "game_id": "2026_03_ATL_GB",
                "away_team": "ATL",
                "home_team": "GB",
                "kickoff_utc": "2026-09-25T00:15:00+00:00",
            }
        ],
        "sources": [],
    }
    (tmp_path / "observations.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")
    cohorts = candidate_cohorts(
        tmp_path,
        now_utc=datetime(2026, 9, 24, 23, 25, tzinfo=timezone.utc),
        existing_game_ids=set(),
    )
    assert cohorts == []

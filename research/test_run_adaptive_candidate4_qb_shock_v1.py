from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from research.run_adaptive_candidate4_qb_shock_v1 import candidate_cohorts, run


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


def _qualified_archive(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    html = (
        "<html><body>"
        "<h3>BILLS</h3><ul><li>WR Example Receiver</li></ul>"
        "<h3>CHARGERS</h3><ul><li>QB Justin Herbert</li></ul>"
        "</body></html>"
    ).encode()
    sha = hashlib.sha256(html).hexdigest()
    (root / "raw").mkdir(parents=True, exist_ok=True)
    with gzip.open(root / "raw" / f"{sha}.html.gz", "wb") as handle:
        handle.write(html)
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": "2026-09-27T15:50:00Z",
        "due_games": [
            {
                "game_id": "2026_03_LAC_BUF",
                "away_team": "LAC",
                "home_team": "BUF",
                "kickoff_utc": "2026-09-27T17:00:00+00:00",
            }
        ],
        "sources": [
            {
                "source_kind": "nfl_inactives_news_article",
                "url": "https://www.nfl.com/news/week-3-inactives-test",
                "http_status": 200,
                "raw_body_sha256": sha,
                "raw_object_relpath": f"raw/{sha}.html.gz",
            }
        ],
    }
    (root / "observations.jsonl").write_text(
        json.dumps(observation) + "\n",
        encoding="utf-8",
    )


def _qb1_snapshot(path: Path) -> None:
    pd.DataFrame([
        {
            "schema_version": "adaptive-candidate4-qb1-t120-snapshot-v1",
            "candidate_id": "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1",
            "preregistration_sha": "74ecd303545c09f57593546472d27438e3d8a204",
            "game_id": "2026_03_LAC_BUF",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "home_team": "BUF",
            "away_team": "LAC",
            "kickoff_utc": "2026-09-27T17:00:00Z",
            "t120_target_utc": "2026-09-27T15:00:00Z",
            "captured_at_utc": "2026-09-27T14:59:00Z",
            "capture_timing_error_minutes": -1.0,
            "home_t120_qb1_player_name": "Josh Allen",
            "home_t120_qb1_gsis_id": "00-0034857",
            "home_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "away_t120_qb1_player_name": "Justin Herbert",
            "away_t120_qb1_gsis_id": "00-0036355",
            "away_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "qb1_snapshot_complete": True,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
            "qb1_snapshot_sha256": "d" * 64,
        }
    ]).to_csv(path, index=False)


def test_runner_consumes_frozen_qb1_snapshot_without_live_depth_query(tmp_path) -> None:
    archive = tmp_path / "archive"
    output = tmp_path / "qb_state.csv"
    snapshot = tmp_path / "qb1.csv"
    receipt = tmp_path / "parser_receipt.json"
    _qualified_archive(archive)
    _qb1_snapshot(snapshot)
    receipt.write_text(
        json.dumps({
            "status": "PASS",
            "qualification_passed": True,
            "authority": {
                "player_level_parser_qualified_for_due_cohort_filtering": True
            },
            "completed_2026_outcomes_used": 0,
        }),
        encoding="utf-8",
    )

    status = run(
        archive_dir=archive,
        output_csv=output,
        parser_receipt_path=receipt,
        qb1_snapshot_path=snapshot,
        now_utc=datetime(2026, 9, 27, 16, 10, tzinfo=timezone.utc),
    )
    assert status["rows_added"] == 1
    locked = pd.read_csv(output)
    assert len(locked) == 1
    row = locked.iloc[0]
    assert bool(row["qb_state_complete"]) is True
    assert row["qb_shock_direction"] == 1
    assert row["depth_source"] == "immutable_candidate4_t120_qb1_snapshot"
    assert row["qb1_snapshot_sha256"] == "d" * 64

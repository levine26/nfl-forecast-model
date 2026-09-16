from __future__ import annotations

import json
from pathlib import Path

from research.run_levline4_prospective_inactive_execution_v1 import (
    SUPPORTED_WEEK,
    cohort_is_sunday_eastern,
    run,
)


def test_sunday_gate_uses_eastern_local_day() -> None:
    assert cohort_is_sunday_eastern(
        [{"kickoff_utc": "2026-09-20T17:00:00+00:00"}]
    ) is True
    assert cohort_is_sunday_eastern(
        [{"kickoff_utc": "2026-09-18T00:15:00+00:00"}]
    ) is False
    assert cohort_is_sunday_eastern(
        [{"kickoff_utc": "2026-09-21T00:20:00+00:00"}]
    ) is True


def _write_observation(
    archive: Path,
    *,
    game_id: str,
    away_team: str,
    home_team: str,
    kickoff_utc: str,
    captured_at_utc: str,
) -> None:
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": captured_at_utc,
        "due_games": [
            {
                "game_id": game_id,
                "away_team": away_team,
                "home_team": home_team,
                "kickoff_utc": kickoff_utc,
                "minutes_to_kickoff": 75.0,
            }
        ],
        "sources": [],
    }
    (archive / "observations.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")


def test_non_sunday_capture_skips_before_identity_sources_are_read(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    _write_observation(
        archive,
        game_id="2026_02_BUF_MIA",
        away_team="BUF",
        home_team="MIA",
        kickoff_utc="2026-09-18T00:15:00+00:00",
        captured_at_utc="2026-09-17T23:00:00Z",
    )
    output = tmp_path / "out"
    receipt = run(
        archive_dir=archive,
        weekly_projection_path=tmp_path / "must-not-be-read-weekly.parquet",
        global_projection_path=tmp_path / "must-not-be-read-global.parquet",
        output_dir=output,
    )
    assert receipt["status"] == "SKIPPED_OUTSIDE_QUALIFIED_SUNDAY_ARTICLE_SEMANTICS"
    assert receipt["week"] == 2
    assert receipt["identity_sources_read"] is False
    assert receipt["resolver_executed"] is False
    assert receipt["production_authorized"] is False
    assert (output / "attempts.jsonl").exists()


def test_week3_sunday_skips_before_identity_sources_are_read(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    _write_observation(
        archive,
        game_id="2026_03_ARI_LAR",
        away_team="ARI",
        home_team="LAR",
        kickoff_utc="2026-09-27T20:25:00+00:00",
        captured_at_utc="2026-09-27T19:10:00Z",
    )
    output = tmp_path / "out"
    receipt = run(
        archive_dir=archive,
        weekly_projection_path=tmp_path / "must-not-be-read-weekly.parquet",
        global_projection_path=tmp_path / "must-not-be-read-global.parquet",
        output_dir=output,
    )
    assert SUPPORTED_WEEK == 2
    assert receipt["status"] == "SKIPPED_OUTSIDE_FROZEN_IDENTITY_SOURCE_WEEK"
    assert receipt["week"] == 3
    assert receipt["identity_sources_read"] is False
    assert receipt["resolver_executed"] is False
    assert receipt["production_authorized"] is False
    assert (output / "attempts.jsonl").exists()

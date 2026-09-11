from __future__ import annotations

import json
from pathlib import Path

from research.run_sleeper_archive_capture_v1 import capture_once
from research.sleeper_archive_capture_v1 import (
    build_capture,
    capture_filename,
    read_capture,
    slim_player_state,
    write_capture,
)


def _snapshot() -> dict:
    return {
        "players": {
            "qb1": {
                "full_name": "Quarter Back",
                "team": "ARI",
                "position": "QB",
                "status": "Active",
                "injury_status": "Questionable",
                "practice_participation": "Limited",
                "depth_chart_order": 1,
                "gsis_id": "00-0000001",
                "stats": {"pts": 999},
            },
            "ol1": {
                "full_name": "Offensive Lineman",
                "team": "ARI",
                "position": "OT",
                "status": "Active",
                "injury_status": None,
                "practice_participation": "Full",
                "depth_chart_order": 1,
                "gsis_id": "00-0000002",
                "stats": {"pts": 0},
            },
            "db1": {
                "full_name": "Defensive Back",
                "team": "LAR",
                "position": "CB",
                "status": "Active",
                "injury_status": None,
                "practice_description": "Rest",
                "depth_chart_order": 2,
                "espn_id": 123,
            },
            "def": {"team": "ARI", "position": "DEF", "status": "Active"},
            "retired": {"team": "ARI", "position": "WR", "status": "Retired"},
            "free": {"team": None, "position": "WR", "status": "Active"},
        }
    }


def test_slim_capture_keeps_all_nfl_positions_and_drops_bulk_stats() -> None:
    players, fields = slim_player_state(_snapshot())
    assert set(players) == {"qb1", "ol1", "db1"}
    assert players["ol1"]["position"] == "OT"
    assert players["db1"]["position"] == "CB"
    assert "stats" not in players["qb1"]
    assert "injury_status" in fields
    assert "practice_participation" in fields
    assert "practice_description" in fields
    assert "depth_chart_order" in fields
    assert "gsis_id" in fields


def test_capture_uses_source_commit_as_conservative_availability_bound() -> None:
    payload = build_capture(
        _snapshot(),
        source_commit_sha="a" * 40,
        source_commit_timestamp_utc="2026-09-10T08:05:00Z",
        retrieval_timestamp_utc="2026-09-10T09:30:00Z",
    )
    assert payload["availability_bound"] == "source_git_commit_time"
    assert payload["audit"]["point_in_time_safe"] is True
    assert payload["research_only"] is True
    assert payload["production_authorized"] is False
    assert payload["completed_2026_outcome_selection_authorized"] is False
    assert len(payload["content_sha256"]) == 64
    assert capture_filename(payload).endswith("__aaaaaaaaaaaa.json.gz")


def test_compressed_capture_round_trips(tmp_path: Path) -> None:
    payload = build_capture(
        _snapshot(),
        source_commit_sha="b" * 40,
        source_commit_timestamp_utc="2026-09-10T08:05:00Z",
        retrieval_timestamp_utc="2026-09-10T09:30:00Z",
    )
    path = tmp_path / capture_filename(payload)
    write_capture(path, payload)
    assert path.exists()
    assert read_capture(path) == payload


def test_source_commit_after_retrieval_is_rejected() -> None:
    try:
        build_capture(
            _snapshot(),
            source_commit_sha="c" * 40,
            source_commit_timestamp_utc="2026-09-10T10:00:00Z",
            retrieval_timestamp_utc="2026-09-10T09:30:00Z",
        )
    except ValueError as exc:
        assert "after retrieval time" in str(exc)
    else:
        raise AssertionError("future source commit must fail closed")


def test_capture_runner_is_idempotent_by_upstream_commit(tmp_path: Path) -> None:
    source = tmp_path / "sleeper_players.json"
    source.write_text(json.dumps(_snapshot()), encoding="utf-8")
    output = tmp_path / "snapshots"
    index = tmp_path / "index.json"
    first = capture_once(
        input_path=str(source),
        output_dir=str(output),
        index_path=str(index),
        source_commit_sha="d" * 40,
        source_commit_timestamp_utc="2026-09-10T08:05:00Z",
        retrieval_timestamp_utc="2026-09-10T09:30:00Z",
    )
    second = capture_once(
        input_path=str(source),
        output_dir=str(output),
        index_path=str(index),
        source_commit_sha="d" * 40,
        source_commit_timestamp_utc="2026-09-10T08:05:00Z",
        retrieval_timestamp_utc="2026-09-10T10:30:00Z",
    )
    assert first["status"] == "captured"
    assert second == {
        "status": "skipped",
        "reason": "source_commit_already_captured",
        "source_commit_sha": "d" * 40,
    }
    entries = json.loads(index.read_text(encoding="utf-8"))["captures"]
    assert len(entries) == 1
    assert len(list(output.glob("*.json.gz"))) == 1

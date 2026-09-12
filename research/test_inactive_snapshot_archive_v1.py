from __future__ import annotations

import gzip
from datetime import datetime, timezone
from pathlib import Path

from research.inactive_snapshot_archive_v1 import capture_inactives, verify_archive
from research.inactive_snapshot_due_v1 import due_games


class _Response:
    status_code = 200
    content = b"<html><body><h1>NFL Inactive Reports</h1><p>Example report body</p></body></html>"
    text = content.decode("utf-8")

    def raise_for_status(self) -> None:
        return None


class _Session:
    @staticmethod
    def get(*args, **kwargs):
        return _Response()


def test_due_window_is_pregame_and_includes_t90(tmp_path: Path) -> None:
    feed = tmp_path / "week.csv"
    feed.write_text(
        "game_id,gameday,gametime,away_team,home_team\n"
        "g1,2026-09-13,13:00,AAA,BBB\n",
        encoding="utf-8",
    )
    now = datetime(2026, 9, 13, 15, 30, tzinfo=timezone.utc)  # 11:30 ET, T-90
    games = due_games(feed, now)
    assert len(games) == 1
    assert games[0]["game_id"] == "g1"
    assert abs(float(games[0]["minutes_to_kickoff"]) - 90.0) < 1e-9


def test_capture_preserves_raw_body_and_never_authorizes_probability_use(tmp_path: Path) -> None:
    game = {
        "game_id": "g1",
        "away_team": "AAA",
        "home_team": "BBB",
        "kickoff_utc": "2026-09-13T17:00:00+00:00",
        "minutes_to_kickoff": 60.0,
    }
    result = capture_inactives(
        output_dir=tmp_path,
        due_games=[game],
        captured_at="2026-09-13T16:00:00Z",
        session=_Session,
    )
    observation = result.observation
    assert observation["status"] == "captured_raw"
    assert observation["production_authorized"] is False
    assert observation["probability_feature_authorized"] is False
    assert observation["player_level_parser_qualified"] is False
    assert observation["contains_inactive_reports_label"] is True
    assert result.raw_object_path is not None
    with gzip.open(result.raw_object_path, "rb") as handle:
        assert handle.read() == _Response.content
    verified = verify_archive(tmp_path)
    assert verified["integrity_ok"] is True
    assert verified["unique_raw_objects"] == 1


def test_repeated_identical_source_is_content_addressed(tmp_path: Path) -> None:
    first = capture_inactives(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:30:00Z",
        session=_Session,
    )
    second = capture_inactives(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:35:00Z",
        session=_Session,
    )
    assert first.observation["raw_body_sha256"] == second.observation["raw_body_sha256"]
    assert first.raw_object_created is True
    assert second.raw_object_created is False
    assert verify_archive(tmp_path)["observations"] == 2

from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

import pandas as pd
import pytest

from research.injury_snapshot_archive_v1 import (
    MANIFEST_NAME,
    capture_week,
    verify_archive,
)
from research.run_injury_snapshot_archive_v1 import resolve_current_week


HTML_V1 = """
<html><body>
<h3>Arizona Cardinals</h3>
<table>
<tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr>
<tr><td>Example Tackle</td><td>T</td><td>Knee</td><td>Limited Participation in Practice</td><td></td></tr>
</table>
<h3>Los Angeles Rams</h3>
<table>
<tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr>
<tr><td>Example Corner</td><td>CB</td><td>Hamstring</td><td>Did Not Participate In Practice</td><td>Questionable</td></tr>
</table>
</body></html>
"""
HTML_V2 = HTML_V1.replace("Limited Participation in Practice", "Full Participation in Practice")
MALFORMED_TABLE_HTML = "<html><body><table><tr><th>Nothing useful</th></tr><tr><td>x</td></tr></table></body></html>"


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def get(self, *args, **kwargs):
        return FakeResponse(self.text, self.status_code)


def _manifest(root: Path) -> list[dict]:
    return [json.loads(x) for x in (root / MANIFEST_NAME).read_text().splitlines() if x.strip()]


def test_unchanged_poll_appends_observation_without_duplicate_objects(tmp_path):
    first = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(HTML_V1),
    )
    second = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T21:00:00Z",
        session=FakeSession(HTML_V1),
    )
    rows = _manifest(tmp_path)
    assert len(rows) == 2
    assert first.object_created is True
    assert second.object_created is False
    assert first.raw_object_created is True
    assert second.raw_object_created is False
    assert rows[0]["canonical_snapshot_sha256"] == rows[1]["canonical_snapshot_sha256"]
    assert rows[0]["raw_body_sha256"] == rows[1]["raw_body_sha256"]
    assert len(list((tmp_path / "objects").glob("*.json.gz"))) == 1
    assert len(list((tmp_path / "raw").glob("*.html.gz"))) == 1
    audit = verify_archive(tmp_path)
    assert audit["integrity_ok"] is True
    assert audit["observations"] == 2
    assert audit["unique_snapshot_objects"] == 1
    assert audit["unique_raw_objects"] == 1


def test_changed_report_creates_new_raw_and_canonical_state(tmp_path):
    capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(HTML_V1),
    )
    changed = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T21:00:00Z",
        session=FakeSession(HTML_V2),
    )
    rows = _manifest(tmp_path)
    assert rows[0]["canonical_snapshot_sha256"] != rows[1]["canonical_snapshot_sha256"]
    assert rows[0]["raw_body_sha256"] != rows[1]["raw_body_sha256"]
    assert changed.object_created is True
    assert changed.raw_object_created is True
    audit = verify_archive(tmp_path)
    assert audit["unique_snapshot_objects"] == 2
    assert audit["unique_raw_objects"] == 2


def test_canonical_object_has_no_capture_time_or_model_output_and_raw_is_exact(tmp_path):
    result = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at=datetime(2026, 9, 9, 18, tzinfo=timezone.utc),
        session=FakeSession(HTML_V1),
    )
    assert result.object_path is not None
    assert result.raw_object_path is not None
    with gzip.open(result.object_path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    with gzip.open(result.raw_object_path, "rt", encoding="utf-8") as handle:
        raw_html = handle.read()
    assert raw_html == HTML_V1
    assert "captured_at_utc" not in payload
    assert set(payload) == {"schema_version", "archive_id", "season", "week", "source_name", "source_url", "reports"}
    assert payload["reports"]["ARI"][0]["practice_status"] == "Limited Participation in Practice"
    assert result.observation["completed_2026_outcomes_used"] == 0
    assert result.observation["production_authorized"] is False


def test_failed_http_request_is_preserved_as_observation_and_no_object(tmp_path):
    result = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession("error", status_code=503),
    )
    assert result.observation["status"] == "failed"
    assert result.object_path is None
    assert result.raw_object_path is None
    assert len(_manifest(tmp_path)) == 1
    audit = verify_archive(tmp_path)
    assert audit["integrity_ok"] is True
    assert audit["failed_observations"] == 1


def test_parser_failure_preserves_original_raw_source_for_reaudit(tmp_path):
    result = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(MALFORMED_TABLE_HTML),
    )
    assert result.observation["status"] == "failed"
    assert "no team rows parsed" in result.observation["error"]
    assert result.object_path is None
    assert result.raw_object_path is not None
    assert result.raw_object_path.exists()
    with gzip.open(result.raw_object_path, "rt", encoding="utf-8") as handle:
        assert handle.read() == MALFORMED_TABLE_HTML
    audit = verify_archive(tmp_path)
    assert audit["integrity_ok"] is True
    assert audit["unique_raw_objects"] == 1


def test_duplicate_capture_identity_fails_closed(tmp_path):
    capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(HTML_V1),
    )
    with pytest.raises(ValueError, match="duplicate injury archive observation identity"):
        capture_week(
            season=2026,
            week=1,
            output_dir=tmp_path,
            captured_at="2026-09-09T18:00:00Z",
            session=FakeSession(HTML_V1),
        )


def test_archive_verifier_detects_canonical_and_raw_object_tampering(tmp_path):
    result = capture_week(
        season=2026,
        week=1,
        output_dir=tmp_path,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(HTML_V1),
    )
    assert result.object_path is not None
    result.object_path.write_bytes(b"not-gzip")
    audit = verify_archive(tmp_path)
    assert audit["integrity_ok"] is False
    assert any("canonical object unreadable" in failure for failure in audit["failures"])

    clean = tmp_path / "clean"
    result = capture_week(
        season=2026,
        week=1,
        output_dir=clean,
        captured_at="2026-09-09T18:00:00Z",
        session=FakeSession(HTML_V1),
    )
    assert result.raw_object_path is not None
    result.raw_object_path.write_bytes(b"not-gzip")
    audit = verify_archive(clean)
    assert audit["integrity_ok"] is False
    assert any("raw object unreadable" in failure for failure in audit["failures"])


def test_week_resolution_reads_only_unique_current_season_week(tmp_path):
    path = tmp_path / "this_week.csv"
    pd.DataFrame({"season": [2026, 2026], "week": [1, 1], "unused_score": [99, 0]}).to_csv(path, index=False)
    assert resolve_current_week(path) == (2026, 1)

    pd.DataFrame({"season": [2026, 2026], "week": [1, 2]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="exactly one current season/week"):
        resolve_current_week(path)

from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

from research.inactive_article_source_archive_v1 import (
    ARCHIVE_ID,
    capture_inactive_articles,
    discover_inactive_article_urls,
    verify_archive,
)


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, **kwargs):
        self.calls.append(url)
        if url not in self.responses:
            raise RuntimeError(f"unexpected URL {url}")
        return self.responses[url]


def test_discovery_accepts_generic_and_matchup_inactive_articles_only() -> None:
    html = """
    <html><body>
      <a href="/news/nfl-week-1-inactives-players-ruled-out-for-sunday-games">NFL Week 1 inactives: Players ruled out</a>
      <a href="/news/nfl-kickoff-game-inactives-new-england-patriots-at-seattle-seahawks">Kickoff Game Inactives</a>
      <a href="/news/injuries-week-1">NFL Week 1 injury report</a>
      <a href="https://evil.example/news/inactives">Inactives mirror</a>
      <a href="/videos/week-1-inactives">Video inactives</a>
      <a href="/news/nfl-week-1-inactives-players-ruled-out-for-sunday-games?foo=bar">duplicate</a>
    </body></html>
    """
    urls = discover_inactive_article_urls(html)
    assert urls == [
        "https://www.nfl.com/news/nfl-week-1-inactives-players-ruled-out-for-sunday-games",
        "https://www.nfl.com/news/nfl-kickoff-game-inactives-new-england-patriots-at-seattle-seahawks",
    ]


def test_capture_preserves_news_index_and_discovered_article_bytes(tmp_path: Path) -> None:
    news_url = "https://www.nfl.com/news/"
    article_url = "https://www.nfl.com/news/nfl-week-1-inactives-sunday-games"
    news_html = f'<a href="{article_url}">NFL Week 1 inactives</a>'
    article_html = "<h1>NFL Week 1 inactives</h1><h3>BEARS</h3><li>QB Example Player</li>"
    session = FakeSession(
        {
            news_url: FakeResponse(news_html),
            article_url: FakeResponse(article_html),
        }
    )
    result = capture_inactive_articles(
        output_dir=tmp_path,
        due_games=[
            {
                "game_id": "2026_01_CHI_CAR",
                "away_team": "CHI",
                "home_team": "CAR",
                "kickoff_utc": "2026-09-13T17:00:00+00:00",
                "minutes_to_kickoff": 90.0,
            }
        ],
        captured_at=datetime(2026, 9, 13, 15, 30, tzinfo=timezone.utc),
        session=session,
    )
    assert result.sources_captured == 2
    assert session.calls == [news_url, article_url]
    observation = result.observation
    assert observation["archive_id"] == ARCHIVE_ID
    assert observation["status"] == "captured_raw_sources"
    assert observation["player_level_parser_qualified"] is False
    assert observation["probability_feature_authorized"] is False
    assert observation["production_authorized"] is False
    assert observation["completed_2026_outcomes_used"] == 0
    assert observation["discovered_inactive_article_urls"] == [article_url]
    assert {source["source_kind"] for source in observation["sources"]} == {
        "nfl_news_index",
        "nfl_inactives_news_article",
    }
    verified = verify_archive(tmp_path)
    assert verified["integrity_ok"] is True
    assert verified["unique_raw_objects"] == 2


def test_news_index_is_preserved_even_when_no_article_is_discoverable(tmp_path: Path) -> None:
    news_url = "https://www.nfl.com/news/"
    session = FakeSession({news_url: FakeResponse("<a href='/news/foo'>Other news</a>")})
    result = capture_inactive_articles(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:30:00Z",
        session=session,
    )
    assert result.sources_captured == 1
    assert result.observation["discovered_inactive_article_urls"] == []
    assert result.observation["sources"][0]["source_kind"] == "nfl_news_index"
    assert verify_archive(tmp_path)["integrity_ok"] is True


def test_http_error_body_is_still_preserved_as_evidence(tmp_path: Path) -> None:
    news_url = "https://www.nfl.com/news/"
    result = capture_inactive_articles(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:35:00Z",
        session=FakeSession({news_url: FakeResponse("temporarily unavailable", 503)}),
    )
    assert result.sources_captured == 0
    assert result.observation["status"] == "failed"
    assert result.observation["sources"][0]["http_status"] == 503
    relpath = result.observation["sources"][0]["raw_object_relpath"]
    with gzip.open(tmp_path / relpath, "rb") as handle:
        assert handle.read() == b"temporarily unavailable"
    assert verify_archive(tmp_path)["integrity_ok"] is True


def test_archive_integrity_detects_raw_tampering(tmp_path: Path) -> None:
    news_url = "https://www.nfl.com/news/"
    result = capture_inactive_articles(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:40:00Z",
        session=FakeSession({news_url: FakeResponse("<html>news</html>")}),
    )
    relpath = result.observation["sources"][0]["raw_object_relpath"]
    with gzip.open(tmp_path / relpath, "wb") as handle:
        handle.write(b"tampered")
    verified = verify_archive(tmp_path)
    assert verified["integrity_ok"] is False
    assert any("SHA mismatch" in failure for failure in verified["failures"])


def test_manifest_is_append_only_by_capture_timestamp(tmp_path: Path) -> None:
    news_url = "https://www.nfl.com/news/"
    session = FakeSession({news_url: FakeResponse("<html>news</html>")})
    capture_inactive_articles(
        output_dir=tmp_path,
        due_games=[],
        captured_at="2026-09-13T15:45:00Z",
        session=session,
    )
    try:
        capture_inactive_articles(
            output_dir=tmp_path,
            due_games=[],
            captured_at="2026-09-13T15:45:00Z",
            session=session,
        )
        raised = False
    except ValueError as exc:
        raised = "duplicate inactive article capture identity" in str(exc)
    assert raised is True
    rows = [json.loads(line) for line in (tmp_path / "observations.jsonl").read_text().splitlines()]
    assert len(rows) == 1

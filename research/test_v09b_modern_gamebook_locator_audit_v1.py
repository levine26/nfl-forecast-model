from __future__ import annotations

from research.v09b_modern_gamebook_locator_audit_v1 import (
    extract_game_center_links,
    extract_gamebook_evidence,
    extract_gamebook_links,
    game_center_url,
    is_allowed_document_url,
    team_slug,
    week_schedule_url,
)


def test_game_center_url_is_deterministic() -> None:
    assert game_center_url(season=2019, week=12, away_team="NYG", home_team="CHI") == (
        "https://www.nfl.com/games/giants-at-bears-2019-reg-12"
    )


def test_week_schedule_url_is_first_party_and_deterministic() -> None:
    assert week_schedule_url(season=2020, week=4) == (
        "https://www.nfl.com/schedules/2020/by-week/week-4"
    )


def test_washington_slug_is_season_specific() -> None:
    assert team_slug("WAS", 2019) == "redskins"
    assert team_slug("WAS", 2020) == "football-team"
    assert team_slug("WAS", 2021) == "football-team"


def test_extracts_exact_suffixed_game_center_from_first_party_schedule() -> None:
    html = """
    <html><body>
      <a href='/games/colts-at-bears-2020-reg-4-x4464'>Colts at Bears</a>
      <a href='/games/buccaneers-at-bears-2020-reg-5'>Other game</a>
    </body></html>
    """
    links = extract_game_center_links(
        html,
        schedule_url="https://www.nfl.com/schedules/2020/by-week/week-4",
        season=2020,
        week=4,
        away_team="IND",
        home_team="CHI",
    )
    assert links == ["https://www.nfl.com/games/colts-at-bears-2020-reg-4-x4464"]


def test_schedule_resolver_rejects_third_party_and_wrong_matchup() -> None:
    html = """
    <html><body>
      <a href='https://example.com/games/colts-at-bears-2020-reg-4-x4464'>Wrong host</a>
      <a href='/games/colts-at-lions-2020-reg-4-x9999'>Wrong opponent</a>
    </body></html>
    """
    assert extract_game_center_links(
        html,
        schedule_url="https://www.nfl.com/schedules/2020/by-week/week-4",
        season=2020,
        week=4,
        away_team="IND",
        home_team="CHI",
    ) == []


def test_extracts_only_download_game_book_anchor_and_deduplicates() -> None:
    html = """
    <html><body>
      <a href='/other.pdf'>Other PDF</a>
      <a href='https://static.www.nfl.com/image/upload/gamecenter/book.pdf'>Download Game Book (PDF)</a>
      <a href='https://static.www.nfl.com/image/upload/gamecenter/book.pdf'><span>Download Game Book</span></a>
    </body></html>
    """
    links = extract_gamebook_links(html, "https://www.nfl.com/games/example")
    assert links == ["https://static.www.nfl.com/image/upload/gamecenter/book.pdf"]


def test_visible_download_anchor_has_precedence_over_unrelated_embedded_pdfs() -> None:
    html = """
    <html><body>
      <a href='https://static.www.nfl.com/image/upload/gamecenter/correct.pdf'>Download Game Book</a>
      <script>
        window.__DATA__ = {
          "other1": "https://static.www.nfl.com/image/upload/gamecenter/unrelated1.pdf",
          "other2": "https://static.www.nfl.com/image/upload/gamecenter/unrelated2.pdf"
        };
      </script>
    </body></html>
    """
    links, method = extract_gamebook_evidence(html, "https://www.nfl.com/games/example")
    assert links == ["https://static.www.nfl.com/image/upload/gamecenter/correct.pdf"]
    assert method == "download_anchor"


def test_extracts_embedded_first_party_gamecenter_pdf_when_anchor_is_not_rendered() -> None:
    html = (
        '<script>window.__DATA__={"gameBook":"https:\\/\\/static.www.nfl.com\\/image\\/upload'
        '\\/v1\\/gamecenter\\/abc123.pdf"}</script>'
    )
    links, method = extract_gamebook_evidence(html, "https://www.nfl.com/games/example")
    assert links == ["https://static.www.nfl.com/image/upload/v1/gamecenter/abc123.pdf"]
    assert method == "embedded_first_party_pdf"


def test_embedded_extractor_ignores_non_gamecenter_pdf() -> None:
    html = '<script>{"doc":"https://static.www.nfl.com/rulebook.pdf"}</script>'
    links, method = extract_gamebook_evidence(html, "https://www.nfl.com/games/example")
    assert links == []
    assert method == "none"


def test_document_host_must_be_first_party_static_nfl() -> None:
    assert is_allowed_document_url("https://static.www.nfl.com/image/upload/gamecenter/book.pdf") is True
    assert is_allowed_document_url("http://static.www.nfl.com/image/upload/gamecenter/book.pdf") is False
    assert is_allowed_document_url("https://example.com/gamebook.pdf") is False
    assert is_allowed_document_url("https://static.clubs.nfl.com/gamebook.pdf") is False

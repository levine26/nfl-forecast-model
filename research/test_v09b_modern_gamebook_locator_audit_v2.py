from __future__ import annotations

from research.v09b_modern_gamebook_locator_audit_v2 import (
    extract_gamebook_evidence,
    redirect_target_allowed,
)


def test_explicit_download_anchor_has_precedence_over_embedded_page_pdfs() -> None:
    html = """
    <html><body>
      <a href='https://static.www.nfl.com/image/upload/gamecenter/correct.pdf'>Download Game Book (PDF)</a>
      <script>
        {"other":"https://static.www.nfl.com/image/upload/gamecenter/unrelated-a.pdf",
         "other2":"https://static.www.nfl.com/image/upload/gamecenter/unrelated-b.pdf"}
      </script>
    </body></html>
    """
    links, method = extract_gamebook_evidence(html, "https://www.nfl.com/games/example")
    assert links == ["https://static.www.nfl.com/image/upload/gamecenter/correct.pdf"]
    assert method == "download_anchor"


def test_embedded_first_party_pdf_is_fallback_only_when_anchor_absent() -> None:
    html = (
        '<script>{"gameBook":"https:\\/\\/static.www.nfl.com\\/image\\/upload'
        '\\/v1\\/gamecenter\\/abc123.pdf"}</script>'
    )
    links, method = extract_gamebook_evidence(html, "https://www.nfl.com/games/example")
    assert links == ["https://static.www.nfl.com/image/upload/v1/gamecenter/abc123.pdf"]
    assert method == "embedded_first_party_pdf"


def test_no_authorized_evidence_fails_closed() -> None:
    links, method = extract_gamebook_evidence(
        '<a href="https://example.com/book.pdf">Other PDF</a>',
        "https://www.nfl.com/games/example",
    )
    assert links == []
    assert method == "none"


def test_game_center_redirects_may_stay_within_nfl_hosts() -> None:
    assert redirect_target_allowed(
        "https://www.nfl.com/games/example",
        "https://nfl.com/games/example",
    ) is True
    assert redirect_target_allowed(
        "https://nfl.com/schedules/2020/by-week/week-4",
        "https://www.nfl.com/schedules/2020/by-week/week-4",
    ) is True


def test_document_redirect_must_remain_on_static_nfl_host() -> None:
    assert redirect_target_allowed(
        "https://static.www.nfl.com/image/upload/gamecenter/book.pdf",
        "https://static.www.nfl.com/image/upload/v2/gamecenter/book.pdf",
    ) is True
    assert redirect_target_allowed(
        "https://static.www.nfl.com/image/upload/gamecenter/book.pdf",
        "https://example.com/book.pdf",
    ) is False


def test_discovery_redirect_to_third_party_or_http_fails_closed() -> None:
    assert redirect_target_allowed(
        "https://www.nfl.com/games/example",
        "https://example.com/games/example",
    ) is False
    assert redirect_target_allowed(
        "https://www.nfl.com/games/example",
        "http://www.nfl.com/games/example",
    ) is False
    assert redirect_target_allowed(
        "https://example.com/games/example",
        "https://www.nfl.com/games/example",
    ) is False

from __future__ import annotations

"""Provenance-only article-content acquisition for the editorial shadow path.

Article existence, identity, fetched bytes, and literal quote location can be
verified mechanically. **Neither quote location nor a plausible source URL is
proof that an analytical football claim is true.** A distinct trusted claim
reviewer must attest entailment before an accepted HUMAN Read is published.
"""

from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

from nfl_forecast.source_policy import is_direct_media_report_url, media_domain_family


MAX_ARTICLE_BYTES = 1_000_000
MIN_ARTICLE_WORDS = 60
GENERIC_REPORT_TITLE = re.compile(
    r"\b(?:how to watch|where to watch|live stream|tv channel|"
    r"game picks|sportsbook|best bets|parlay|daily fantasy|dfs picks|"
    r"week \d+ odds|gametracker|full schedule)\b", re.I
)
TOKEN = re.compile(r"[a-z0-9]+", re.I)
STOP = {"the", "and", "from", "the", "for", "with", "vs", "on",
        "this", "that", "week", "2026", "news", "football", "nfl"}


class ArticleCaptureError(ValueError):
    pass


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _tokens(value: object) -> set[str]:
    return {word.lower() for word in TOKEN.findall(str(value or "")) if word.lower() not in STOP}


def _safe_article_url(value: str) -> str:
    url = str(value or "").strip()
    try:
        parts = urlparse(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ArticleCaptureError("invalid direct publisher HTTPS URL")
        if parts.port not in (None, 443):
            raise ArticleCaptureError("publisher URL uses an unapproved port")
        if not is_direct_media_report_url(url):
            raise ArticleCaptureError("URL is not an approved direct publisher report")
    except ValueError as exc:
        if isinstance(exc, ArticleCaptureError):
            raise
        raise ArticleCaptureError("invalid publisher URL") from exc
    return url


def _article_text(soup: BeautifulSoup) -> str:
    # A headline can name both teams while the article body concerns a
    # different matchup. Team coverage must be established by reporting text,
    # never by the title or a surrounding navigation/link shell.
    for element in soup(["script", "style", "nav", "header", "footer", "aside", "form", "h1"]):
        element.decompose()
    root = soup.find("article") or soup.find("main") or soup.find("body")
    return _clean(root.get_text(" ", strip=True) if root else "")


def _page_title(soup: BeautifulSoup) -> str:
    # Publisher sites often include a branding H1 before the story H1.
    # The article-scoped heading (or OpenGraph title) is the source identity.
    article = soup.find("article")
    h1 = article.find("h1") if article is not None else None
    if h1 and h1.get_text(" ", strip=True):
        return _clean(h1.get_text(" ", strip=True))
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        return _clean(meta["content"])
    h1 = soup.find("h1")
    if h1 and h1.get_text(" ", strip=True):
        return _clean(h1.get_text(" ", strip=True))
    title = soup.find("title")
    return _clean(title.get_text(" ", strip=True) if title else "")


def _published(soup: BeautifulSoup) -> str | None:
    for attrs in (
        {"property": "article:published_time"}, {"name": "datePublished"},
        {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return _clean(tag["content"])
    first = soup.find("time")
    if first and first.get("datetime"):
        return _clean(first["datetime"])
    return None


def capture_report(
    url: str,
    *,
    expected_title: str,
    away_name: str,
    home_name: str,
    session: Any = requests,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch one allowed report and generate an auditable evidence receipt.

    Network redirects are rejected rather than silently following to unexpected
    publishers. Callers can qualify a canonical redirected URL separately.
    Response content and title are untrusted page data; no LLM output is trusted.
    """
    url = _safe_article_url(url)
    try:
        response = session.get(url, timeout=9, allow_redirects=False)
    except requests.RequestException as exc:
        raise ArticleCaptureError(f"source could not be retrieved: {type(exc).__name__}") from exc
    status = int(response.status_code)
    if status != 200:
        raise ArticleCaptureError(f"source HTTP status {status}, not article success")
    kind = str(response.headers.get("content-type") or "").lower()
    if "text/html" not in kind:
        raise ArticleCaptureError("source did not return HTML reporting")
    content = response.content
    if not isinstance(content, bytes) or not content or len(content) > MAX_ARTICLE_BYTES:
        raise ArticleCaptureError("article body missing or exceeds bounded response size")
    soup = BeautifulSoup(content, "html.parser")
    title = _page_title(soup)
    if len(title) < 12 or GENERIC_REPORT_TITLE.search(title):
        raise ArticleCaptureError("generic or missing article title")
    actual = _tokens(title)
    asserted = _tokens(expected_title)
    if len(actual & asserted) < 2 or len(actual & asserted) / max(1, len(asserted)) < 0.40:
        raise ArticleCaptureError("article title contradicts cited title")
    body = _article_text(soup)
    if len(TOKEN.findall(body)) < MIN_ARTICLE_WORDS:
        raise ArticleCaptureError("source is a navigation shell, not substantial reporting")
    for team in (away_name, home_name):
        nickname = _clean(team).split(" ")[-1]
        if not nickname or not re.search(r"\b" + re.escape(nickname) + r"\b", body, re.I):
            raise ArticleCaptureError(f"article text does not cover matchup team {team}")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return {
        "url": url,
        "publisher_family": media_domain_family(url),
        "article_title": title,
        "published_or_updated_raw": _published(soup),
        "retrieved_utc": timestamp,
        "content_sha256": sha256(content).hexdigest(),
        "extracted_body_sha256": sha256(body.encode("utf-8")).hexdigest(),
        "article_resolution_verified": True,
        "quote_location_verified": False,
        "claim_entailment_verified": False,
        "matchup_teams": [away_name, home_name],
        "body_text": body,
    }


def locate_quote(report: dict[str, Any], *, quote: str) -> dict[str, str]:
    """Create a literal-text pointer, NOT a trusted claim-truth assertion."""
    if report.get("article_resolution_verified") is not True or not report.get("body_text"):
        raise ArticleCaptureError("cannot match quotes against unverified article content")
    excerpt = _clean(quote)
    if len(excerpt) < 18:
        raise ArticleCaptureError("source quote is too short to support review")
    normalized_body = _clean(report["body_text"]).casefold()
    if excerpt.casefold() not in normalized_body:
        raise ArticleCaptureError("claimed supporting quote not present in retrieved article")
    return {
        "quote": excerpt,
        "quote_sha256": sha256(excerpt.encode("utf-8")).hexdigest(),
        "content_sha256": str(report["content_sha256"]),
        "verification_status": "quote_located_entailment_unverified",
    }


def require_independent_publishers(reports: list[dict[str, Any]]) -> None:
    if len(reports) < 2:
        raise ArticleCaptureError("fewer than two source-content receipts")
    verified = [r for r in reports if r.get("article_resolution_verified") is True]
    if len({r.get("publisher_family") for r in verified}) < 2:
        raise ArticleCaptureError("two independently verified publisher families required")

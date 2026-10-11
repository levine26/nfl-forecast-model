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
        # Stream with a hard byte cap. Accessing response.content before checking its
        # size would download arbitrarily large pages into memory.
        response = session.get(url, timeout=9, allow_redirects=False, stream=True)
    except requests.RequestException as exc:
        raise ArticleCaptureError(f"source could not be retrieved: {type(exc).__name__}") from exc
    try:
        status = int(response.status_code)
        if status != 200:
            raise ArticleCaptureError(f"source HTTP status {status}, not article success")
        kind = str(response.headers.get("content-type") or "").lower()
        if "text/html" not in kind:
            raise ArticleCaptureError("source did not return HTML reporting")
        declared = response.headers.get("content-length")
        if declared:
            try:
                if int(declared) > MAX_ARTICLE_BYTES:
                    raise ArticleCaptureError("article body exceeds bounded response size")
            except ValueError as exc:
                if isinstance(exc, ArticleCaptureError):
                    raise
                raise ArticleCaptureError("invalid article content length") from exc
        parts: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not isinstance(chunk, bytes):
                raise ArticleCaptureError("article download returned non-byte content")
            size += len(chunk)
            if size > MAX_ARTICLE_BYTES:
                raise ArticleCaptureError("article body missing or exceeds bounded response size")
            parts.append(chunk)
        content = b"".join(parts)
        if not content:
            raise ArticleCaptureError("article body missing or exceeds bounded response size")
    except requests.RequestException as exc:
        raise ArticleCaptureError(f"source interrupted during retrieval: {type(exc).__name__}") from exc
    finally:
        response.close()
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
    # A first-party personnel report may cover only one side; full matchup
    # coverage is enforced across independent verified sources at the slate gate.
    reported_teams = []
    for team in (away_name, home_name):
        nickname = _clean(team).split(" ")[-1]
        if nickname and re.search(r"\b" + re.escape(nickname) + r"\b", body, re.I):
            reported_teams.append(team)
    if not reported_teams:
        raise ArticleCaptureError("article text does not cover either matchup team")
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
        "reported_teams": reported_teams,
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


def require_independent_publishers(
    reports: list[dict[str, Any]], *, expected_teams: list[str] | None = None,
) -> None:
    """Only verify independent retrieval and combined team coverage, never entailment."""
    if len(reports) < 2:
        raise ArticleCaptureError("fewer than two source-content receipts")
    verified = [r for r in reports if r.get("article_resolution_verified") is True]
    if len(verified) != len(reports) or len({r.get("publisher_family") for r in verified}) < 2:
        raise ArticleCaptureError("two independently verified publisher families required")
    if expected_teams:
        covered = set().union(*(set(r.get("reported_teams") or []) for r in verified))
        if not set(expected_teams).issubset(covered):
            raise ArticleCaptureError("two-source reporting packet does not cover both matchup teams")


def capture_and_verify_source(
    *,
    game_id: str,
    url: str,
    expected_title: str,
    team_aliases: dict[str, list[str]],
    claims: list[dict[str, str]],
    session: Any = requests,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Combine real HTTP acquisition with the ONE shadow evidence verifier.

    The source verifier audits title/URL/article identity and literal quotations.
    Its result is expressly NOT a semantic factual attestation and may not be
    passed to the editorial acceptance ledger as article_claims_verified=True.
    """
    from nfl_forecast.editorial_source_receipts_shadow import verify_retrieved_article

    parts = game_id.split("_")
    if len(parts) != 4 or set(team_aliases) != {parts[2], parts[3]}:
        raise ArticleCaptureError("team aliases must match canonical game identity")
    for code in (parts[2], parts[3]):
        if not isinstance(team_aliases[code], list) or not team_aliases[code]:
            raise ArticleCaptureError("missing trusted canonical team aliases")
    report = capture_report(
        url,
        expected_title=expected_title,
        away_name=team_aliases[parts[2]][0],
        home_name=team_aliases[parts[3]][0],
        session=session,
        now=now,
    )
    raw_timestamp = report.get("published_or_updated_raw")
    published: str | None = None
    if raw_timestamp:
        try:
            parsed = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                published = parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass  # Keep unparseable time as raw metadata; do not fabricate.
    receipt = verify_retrieved_article(
        game_id=game_id,
        candidate_url=url,
        candidate_title=expected_title,
        fetched={
            "status_code": 200,
            "final_url": report["url"],
            "title": report["article_title"],
            "article_text": report["body_text"],
            "retrieved_utc": report["retrieved_utc"],
            "published_utc": published,
        },
        claims=claims,
        team_aliases=team_aliases,
    )
    receipt["http_content_sha256"] = report["content_sha256"]
    receipt["extracted_body_sha256"] = report["extracted_body_sha256"]
    receipt["published_or_updated_raw"] = raw_timestamp
    return receipt

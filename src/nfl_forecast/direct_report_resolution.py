from __future__ import annotations

"""Resolve news-discovery redirects to *candidate* original publisher URLs.

Only approved HTTPS news gateways can be fetched. Every intermediate HTTP
redirect is validated before requesting it; an arbitrary RSS URL or redirects
to an unknown/internal host are never fetched. Resolution is NOT fact checking:
a later article-content/claim evidence gate must still verify the article.
"""

from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests

from nfl_forecast.source_policy import is_direct_media_report_url

_DISCOVERY_HOSTS = frozenset({"news.google.com", "bing.com", "www.bing.com"})
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


def _url_identity(url: str) -> tuple[str, str]:
    """Return restricted URL kind and canonical input, or reject."""
    raw = str(url or "").strip()
    try:
        parsed = urlparse(raw)
    except (TypeError, ValueError):
        return "", ""
    if parsed.scheme != "https" or not parsed.hostname:
        return "", ""
    try:
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            return "", ""
    except ValueError:
        return "", ""
    host = parsed.hostname.lower().rstrip(".")
    if host in _DISCOVERY_HOSTS:
        return "gateway", raw
    if is_direct_media_report_url(raw):
        return "publisher_candidate", raw
    return "", ""


def resolve_original_report_url(
    raw: str,
    *,
    session=requests,
    timeout: int = 5,
    max_redirects: int = 4,
) -> tuple[str, str]:
    """Return (direct_publisher_url, diagnostic) without trusting gateway prose.

    This intentionally does not claim that an article exists or supports a
    football fact. It simply prevents a search intermediary from being used
    as the displayed article URL. Network failures return an empty candidate.
    """
    kind, current = _url_identity(raw)
    if kind == "publisher_candidate":
        return current, "direct_url_candidate"
    if kind != "gateway":
        return "", "unapproved_discovery_url"

    parsed = urlparse(current)
    # Some Bing links include the actual publisher URL as an explicit argument.
    # Never follow an arbitrary embedded URL.
    if parsed.hostname in {"bing.com", "www.bing.com"}:
        for key in ("url",):
            target = unquote((parse_qs(parsed.query).get(key) or [""])[0])
            target_kind, clean = _url_identity(target)
            if target_kind == "publisher_candidate":
                return clean, "gateway_embedded_publisher_candidate"

    visited: set[str] = set()
    for _ in range(max(1, min(int(max_redirects), 6))):
        kind, safe = _url_identity(current)
        if kind == "publisher_candidate":
            return safe, "gateway_redirect_publisher_candidate"
        if kind != "gateway" or safe in visited:
            return "", "unsafe_or_cyclic_redirect"
        visited.add(safe)

        try:
            # allow_redirects=False makes the destination of every hop auditable.
            response = session.get(
                safe,
                timeout=max(1, min(int(timeout), 10)),
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "Sunday-Signal/1.0 (editorial source verification)"},
            )
        except (requests.RequestException, OSError, ValueError):
            return "", "gateway_resolution_unavailable"

        try:
            status = int(getattr(response, "status_code", 0))
            location = response.headers.get("Location") if getattr(response, "headers", None) else None
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

        if status not in _REDIRECT_CODES or not location:
            return "", "gateway_without_direct_redirect"
        candidate = urljoin(safe, location)
        target_kind, clean = _url_identity(candidate)
        if not target_kind:
            return "", "unapproved_redirect_destination"
        current = clean
    return "", "redirect_limit_exceeded"

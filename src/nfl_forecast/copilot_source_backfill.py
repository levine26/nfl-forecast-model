from __future__ import annotations

"""Direct approved-source backfill for Copilot-written Sunday Signal Reads.

The human writer is asked to research every matchup, but a single full-slate LLM
request can occasionally return fewer than two direct article URLs for a game.
This module closes only that provenance gap by querying Bing News RSS against
approved publisher domains. It never creates a source URL, never accepts an
aggregator URL as public provenance, and never touches LevLine inputs or output.
"""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from nfl_forecast.context import TEAM_META
from nfl_forecast.source_policy import (
    APPROVED_MEDIA_DOMAINS,
    OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE,
)


BING_NEWS_RSS = "https://www.bing.com/news/search"

# Official team publishers are tried first because they are both authoritative and
# highly likely to publish opponent-specific Week coverage. National publishers
# provide a second deterministic search tier when team-site coverage is sparse.
NATIONAL_BACKFILL_DOMAINS = (
    "nfl.com",
    "espn.com",
    "cbssports.com",
    "sports.yahoo.com",
    "nbcsports.com",
    "foxsports.com",
    "si.com",
)

BETTING_TERMS = (
    "odds",
    "best bet",
    "betting",
    "parlay",
    "prop bet",
    "against the spread",
    "ats pick",
    "moneyline pick",
)


def _team_code(value: object) -> str:
    code = str(value or "").upper()
    return "JAX" if code == "JAC" else code


def _team_name(code: str) -> str:
    key = _team_code(code)
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nickname(code: str) -> str:
    return _team_name(code).split()[-1]


def _clean(value: object) -> str:
    text = BeautifulSoup(unescape(str(value or "")), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""


def _domain_allowed(url: str) -> bool:
    host = _host(url)
    return any(host == domain or host.endswith("." + domain) for domain in APPROVED_MEDIA_DOMAINS)


def domain_family(url: str) -> str:
    host = _host(url)
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("sports.yahoo.com"):
        return "yahoo.com"
    return host


def canonical_direct_url(url: str) -> str:
    """Return an approved direct article URL, including resolvable Bing targets."""
    raw = str(url or "").strip()
    if _domain_allowed(raw):
        parsed = urlparse(raw)
        return raw if parsed.path.strip("/") else ""

    parsed = urlparse(raw)
    if parsed.hostname and parsed.hostname.lower().endswith("bing.com"):
        target = (parse_qs(parsed.query).get("url") or [""])[0]
        target = unquote(target)
        if _domain_allowed(target) and urlparse(target).path.strip("/"):
            return target
    return ""


def _parse_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _rss_rows(xml_text: str) -> list[dict[str, str | datetime | None]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str | datetime | None]] = []
    for item in root.findall(".//item"):
        source_node = item.find("source")
        source_name = _clean(source_node.text if source_node is not None else "")
        publisher_url = _clean(source_node.attrib.get("url") if source_node is not None else "")
        title = _clean(item.findtext("title"))
        summary = _clean(item.findtext("description"))
        link = _clean(item.findtext("link") or item.findtext("guid"))
        if not title or not link:
            continue
        rows.append(
            {
                "name": source_name,
                "publisher_url": publisher_url,
                "title": title,
                "summary": summary,
                "url": link,
                "published": _parse_date(item.findtext("pubDate")),
            }
        )
    return rows


def _mentions(text: str, code: str) -> bool:
    lowered = str(text or "").lower()
    full = _team_name(code).lower()
    nick = _nickname(code).lower()
    return full in lowered or re.search(rf"\b{re.escape(nick)}\b", lowered) is not None


def _matchup_relevant(text: str, away: str, home: str, domain: str) -> bool:
    official_away = OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE.get(away)
    official_home = OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE.get(home)
    if domain == official_away:
        return _mentions(text, home)
    if domain == official_home:
        return _mentions(text, away)
    return _mentions(text, away) and _mentions(text, home)


def _search_domain(
    *,
    away: str,
    home: str,
    domain: str,
    session,
    timeout: int,
    lookback_days: int,
) -> list[dict[str, str]]:
    query = f'site:{domain} "{_nickname(away)}" "{_nickname(home)}" NFL'
    url = f"{BING_NEWS_RSS}?q={quote_plus(query)}&format=rss&mkt=en-US"
    try:
        response = session.get(url, timeout=timeout, headers={"User-Agent": "Sunday-Signal/1.0 (+public NFL research)"})
        response.raise_for_status()
        rows = _rss_rows(response.text)
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    out: list[dict[str, str]] = []
    for row in rows:
        published = row.get("published")
        if isinstance(published, datetime) and published < cutoff:
            continue
        title = str(row.get("title") or "").strip()
        summary = str(row.get("summary") or "").strip()
        text = f"{title} {summary}"
        if any(term in text.lower() for term in BETTING_TERMS):
            continue
        direct = canonical_direct_url(str(row.get("url") or ""))
        if not direct or domain_family(direct) != domain_family(f"https://{domain}/"):
            continue
        if not _matchup_relevant(text, away, home, domain):
            continue
        name = str(row.get("name") or "").strip() or domain
        out.append({"name": name, "title": title, "url": direct})
    return out


def backfill_direct_sources(
    row,
    existing_sources: list[dict],
    *,
    session=requests,
    timeout: int = 7,
    lookback_days: int = 14,
    minimum_sources: int = 2,
    maximum_sources: int = 4,
) -> list[dict]:
    """Add direct approved article URLs until the two-independent-source gate is met.

    Failure remains fail-closed: if approved direct reporting cannot be found, this
    function simply returns fewer than ``minimum_sources`` and the existing
    publication validator rejects the Read.
    """
    away = _team_code(row.get("away_team"))
    home = _team_code(row.get("home_team"))
    selected = [dict(source) for source in existing_sources if isinstance(source, dict)]
    families = {domain_family(str(source.get("url") or "")) for source in selected}
    titles = {re.sub(r"[^a-z0-9]+", " ", str(source.get("title") or "").lower()).strip() for source in selected}

    domains: list[str] = []
    for code in (away, home):
        domain = OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE.get(code)
        if domain and domain not in domains:
            domains.append(domain)
    for domain in NATIONAL_BACKFILL_DOMAINS:
        if domain not in domains:
            domains.append(domain)

    for domain in domains:
        if len(families) >= minimum_sources or len(selected) >= maximum_sources:
            break
        if domain_family(f"https://{domain}/") in families:
            continue
        for candidate in _search_domain(
            away=away,
            home=home,
            domain=domain,
            session=session,
            timeout=timeout,
            lookback_days=lookback_days,
        ):
            family = domain_family(candidate["url"])
            title_key = re.sub(r"[^a-z0-9]+", " ", candidate["title"].lower()).strip()
            if not family or family in families or title_key in titles:
                continue
            selected.append(candidate)
            families.add(family)
            titles.add(title_key)
            break

    return selected[:maximum_sources]

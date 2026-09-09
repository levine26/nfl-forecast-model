from __future__ import annotations

"""Best-effort current reporting for human game previews.

This layer is editorial only. It discovers fresh public reporting from major outlets
and optional X/Twitter signals, ranks it by source quality/recency/relevance, and
returns compact metadata for the Sunday Signal Read. Nothing here is imported by
LevLine's numerical pipeline.
"""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import os
import re
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from bs4 import BeautifulSoup

from nfl_forecast.context import TEAM_META

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
BING_NEWS_RSS = "https://www.bing.com/news/search"
X_RECENT_SEARCH = "https://api.x.com/2/tweets/search/recent"

SOURCE_PRIORITY = {
    "espn": 100,
    "the athletic": 98,
    "new york times": 97,
    "nytimes": 97,
    "associated press": 96,
    "ap news": 96,
    "nfl.com": 94,
    "nfl network": 94,
    "cbs sports": 90,
    "fox sports": 88,
    "nbc sports": 88,
    "yahoo sports": 86,
    "usa today": 84,
    "sports illustrated": 80,
}

HIGH_SIGNAL_WORDS = {
    "injury", "injured", "questionable", "doubtful", "out", "return", "returns",
    "start", "starter", "expected", "practice", "limited", "debut", "trade", "traded",
    "coordinator", "play-caller", "playcaller", "scheme", "preview", "matchup", "week 1",
    "week one", "lineup", "inactive", "suspended", "available", "availability",
}

LOW_SIGNAL_WORDS = {"odds", "parlay", "prop bet", "best bet", "dfs", "fantasy", "same-game"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _team_name(code: Any) -> str:
    key = "JAX" if str(code or "").upper() == "JAC" else str(code or "").upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _clean_html(value: Any) -> str:
    text = BeautifulSoup(unescape(str(value or "")), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: Any, source_name: str = "") -> str:
    title = _clean_html(value)
    for suffix in [source_name, source_name.replace(".com", "")]:
        if suffix:
            title = re.sub(rf"\s+(?:-|\||—)\s+{re.escape(suffix)}\s*$", "", title, flags=re.I)
    return title.strip(" -|—")


def _parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        try:
            parsed = pd.to_datetime(text, utc=True, errors="raise")
            return parsed.to_pydatetime()
        except Exception:
            return None


def _children_text(item: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for child in list(item):
        key = child.tag.split("}")[-1].lower()
        value = "".join(child.itertext()).strip()
        if value and key not in out:
            out[key] = value
        if key == "source" and child.attrib.get("url"):
            out["source_url"] = child.attrib["url"]
    return out


def _source_priority(name: str) -> int:
    lowered = str(name or "").lower()
    for needle, value in SOURCE_PRIORITY.items():
        if needle in lowered:
            return value
    # Local beat outlets are useful but should not outrank national/league reporting
    # simply because a generic feed happens to surface them first.
    return 72


def _relevance_score(title: str, summary: str, away_name: str, home_name: str, source: str, published: datetime | None) -> float:
    text = f"{title} {summary}".lower()
    score = float(_source_priority(source))
    for team in (away_name, home_name):
        nickname = team.split()[-1].lower()
        if team.lower() in text:
            score += 12
        elif nickname in text:
            score += 8
    if any(word in text for word in HIGH_SIGNAL_WORDS):
        score += 12
    if any(word in text for word in LOW_SIGNAL_WORDS):
        score -= 22
    if published is not None:
        age_hours = max(0.0, (_now() - published).total_seconds() / 3600.0)
        score += max(0.0, 12.0 - age_hours / 12.0)
    return score


def _parse_rss(xml_text: str, provider: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        fields = _children_text(item)
        source = fields.get("source") or fields.get("provider") or fields.get("publisher") or "Unknown source"
        title = _clean_title(fields.get("title"), source)
        if not title:
            continue
        summary = _clean_html(fields.get("description") or fields.get("summary"))
        link = fields.get("link") or fields.get("guid") or fields.get("source_url") or ""
        published = _parse_date(fields.get("pubdate") or fields.get("date") or fields.get("published"))
        rows.append({
            "title": title,
            "summary": summary,
            "source_name": source,
            "source_url": link,
            "publisher_url": fields.get("source_url"),
            "published": published,
            "provider": provider,
        })
    return rows


def _fetch_feed(session, url: str, provider: str, timeout: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = session.get(url, timeout=timeout, headers={"User-Agent": "Sunday-Signal/1.0 (+public NFL research)"})
        response.raise_for_status()
        return _parse_rss(response.text, provider), None
    except Exception as exc:
        return [], str(exc)[:220]


def _fetch_x(session, away_name: str, home_name: str, timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    token = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        return [], {"status": "unavailable", "note": "Set X_BEARER_TOKEN to enable optional recent public X signals."}
    query = f'("{away_name}" OR "{home_name}") NFL -is:retweet lang:en'
    try:
        response = session.get(
            X_RECENT_SEARCH,
            params={
                "query": query,
                "max_results": 10,
                "tweet.fields": "created_at,author_id",
                "expansions": "author_id",
                "user.fields": "username,name,verified",
            },
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}", "User-Agent": "Sunday-Signal/1.0"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return [], {"status": "degraded", "error": str(exc)[:220]}
    users = {str(user.get("id")): user for user in (data.get("includes", {}).get("users") or [])}
    rows = []
    for tweet in data.get("data") or []:
        user = users.get(str(tweet.get("author_id")), {})
        username = str(user.get("username") or "unknown")
        text = re.sub(r"\s+", " ", str(tweet.get("text") or "")).strip()
        if not text:
            continue
        rows.append({
            "title": text[:180],
            "summary": text,
            "source_name": f"X / @{username}",
            "source_url": f"https://x.com/{username}/status/{tweet.get('id')}",
            "publisher_url": f"https://x.com/{username}",
            "published": _parse_date(tweet.get("created_at")),
            "provider": "x",
            "social_verified": bool(user.get("verified")),
        })
    return rows, {"status": "healthy", "signals": len(rows)}


def _dedupe_and_rank(rows: list[dict[str, Any]], away_name: str, home_name: str, lookback_days: int, max_items: int) -> list[dict[str, Any]]:
    cutoff = _now() - timedelta(days=lookback_days)
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        published = row.get("published")
        if published is not None and published < cutoff:
            continue
        title = str(row.get("title") or "").strip()
        summary = str(row.get("summary") or "").strip()
        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if not key or key in seen:
            continue
        score = _relevance_score(title, summary, away_name, home_name, str(row.get("source_name") or ""), published)
        if row.get("provider") == "x" and not row.get("social_verified"):
            score -= 18
        row = dict(row)
        row["score"] = round(score, 3)
        ranked.append(row)
        seen.add(key)
    ranked.sort(key=lambda item: (float(item.get("score") or 0), item.get("published") or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return ranked[:max_items]


def _as_editorial_item(row: dict[str, Any]) -> dict[str, Any]:
    published = row.get("published")
    return {
        "category": "reported_angle",
        "title": str(row.get("title") or "").strip(),
        "summary": str(row.get("summary") or "").strip()[:500],
        "strength": "Strong" if float(row.get("score") or 0) >= 105 else "Moderate",
        "source_name": str(row.get("source_name") or "Unknown source"),
        "source_url": str(row.get("source_url") or row.get("publisher_url") or ""),
        "as_of": published.isoformat() if isinstance(published, datetime) else _now().isoformat(),
        "side": "neutral",
        "relevance": "Fresh external reporting used to choose the human preview angle; editorial only.",
        "metadata": {
            "family": "reported_angle",
            "provider": row.get("provider"),
            "source_priority": _source_priority(str(row.get("source_name") or "")),
            "editorial_score": float(row.get("score") or 0),
            "publisher_url": row.get("publisher_url"),
            "published_utc": published.isoformat() if isinstance(published, datetime) else None,
            "social_verified": row.get("social_verified"),
            "promoted_to_model": False,
        },
    }


def fetch_media_context(
    predictions: pd.DataFrame,
    session=requests,
    lookback_days: int = 14,
    max_items_per_game: int = 4,
    timeout: int = 15,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Discover fresh reporting for every matchup without making it a hard dependency."""
    out: dict[str, list[dict[str, Any]]] = {}
    provider_errors: dict[str, int] = {"google_news": 0, "bing_news": 0}
    x_states: list[str] = []
    games_with_reporting = 0
    total_items = 0

    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        away_name = _team_name(game.get("away_team"))
        home_name = _team_name(game.get("home_team"))
        query = f'"{away_name}" "{home_name}" NFL'
        encoded = quote_plus(query)
        google_url = f"{GOOGLE_NEWS_RSS}?q={encoded}+when:{int(lookback_days)}d&hl=en-US&gl=US&ceid=US:en"
        bing_url = f"{BING_NEWS_RSS}?q={encoded}&format=rss&mkt=en-US"
        rows: list[dict[str, Any]] = []
        google_rows, google_error = _fetch_feed(session, google_url, "google_news", timeout)
        bing_rows, bing_error = _fetch_feed(session, bing_url, "bing_news", timeout)
        rows.extend(google_rows)
        rows.extend(bing_rows)
        if google_error:
            provider_errors["google_news"] += 1
        if bing_error:
            provider_errors["bing_news"] += 1

        x_rows, x_status = _fetch_x(session, away_name, home_name, timeout)
        rows.extend(x_rows)
        x_states.append(str(x_status.get("status") or "unknown"))

        ranked = _dedupe_and_rank(rows, away_name, home_name, lookback_days, max_items_per_game)
        if ranked:
            out[gid] = [_as_editorial_item(row) for row in ranked]
            games_with_reporting += 1
            total_items += len(ranked)

    status_name = "healthy" if games_with_reporting == len(predictions) and len(predictions) else "partial" if games_with_reporting else "degraded"
    return out, {
        "status": status_name,
        "as_of": _now().isoformat(),
        "games": int(len(predictions)),
        "games_with_reporting": games_with_reporting,
        "signals": total_items,
        "providers": {
            "google_news_rss": {"errors": provider_errors["google_news"]},
            "bing_news_rss": {"errors": provider_errors["bing_news"]},
            "x_recent_search": {"status": "healthy" if "healthy" in x_states else ("degraded" if "degraded" in x_states else "unavailable")},
        },
        "source_policy": "Major current reporting chooses the editorial angle. X is optional and never outranks verified mainstream reporting by default. No media signal moves LevLine numerically.",
    }

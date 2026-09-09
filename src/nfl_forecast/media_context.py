from __future__ import annotations

"""Current-reporting context for human-first Sunday Signal previews.

This module is editorial only. It can add sourced reporting to game files and can
supply a curated, source-backed Read for the current slate. Nothing here is read
by LevLine's numerical feature/model pipeline.
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from xml.etree import ElementTree
import json
import re
from typing import Any

import pandas as pd
import requests

from nfl_forecast.context import TEAM_META

ESPN_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=100"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

# Editorial discovery only. A source can inform prose without becoming a model input.
SOURCE_PRIORITY = {
    "ESPN": 100,
    "The Athletic": 98,
    "The New York Times": 98,
    "NFL.com": 96,
    "Associated Press": 94,
    "CBS Sports": 90,
    "Yahoo Sports": 88,
    "NBC Sports": 86,
    "FOX Sports": 84,
    "Sports Illustrated": 80,
}

TEAM_NICK = {
    "ARI":"cardinals", "ATL":"falcons", "BAL":"ravens", "BUF":"bills", "CAR":"panthers", "CHI":"bears",
    "CIN":"bengals", "CLE":"browns", "DAL":"cowboys", "DEN":"broncos", "DET":"lions", "GB":"packers",
    "HOU":"texans", "IND":"colts", "JAX":"jaguars", "JAC":"jaguars", "KC":"chiefs", "LA":"rams",
    "LAC":"chargers", "LV":"raiders", "MIA":"dolphins", "MIN":"vikings", "NE":"patriots", "NO":"saints",
    "NYG":"giants", "NYJ":"jets", "PHI":"eagles", "PIT":"steelers", "SEA":"seahawks", "SF":"49ers",
    "TB":"buccaneers", "TEN":"titans", "WAS":"commanders",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(team: Any) -> str:
    value = str(team or "").upper()
    return "JAX" if value == "JAC" else value


def _team_name(team: str) -> str:
    return str((TEAM_META.get(_norm(team)) or {}).get("name") or TEAM_NICK.get(_norm(team)) or team)


def _source_from_title(title: str) -> str:
    if " - " in title:
        candidate = title.rsplit(" - ", 1)[-1].strip()
        if candidate:
            return candidate
    return "Public reporting"


def _match_text(text: str, away: str, home: str) -> bool:
    low = str(text or "").lower()
    a = TEAM_NICK.get(_norm(away), _norm(away).lower())
    h = TEAM_NICK.get(_norm(home), _norm(home).lower())
    return a in low and h in low


def _load_curated_reads(season: int, week: int, config_dir: str | Path = "config") -> dict[str, dict[str, Any]]:
    path = Path(config_dir) / f"media_editorial_seeds_{season}_w{week}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    games = payload.get("games") if isinstance(payload, dict) else None
    return games if isinstance(games, dict) else {}


def _fetch_espn_articles(session=requests) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    as_of = _now()
    try:
        response = session.get(ESPN_NEWS_URL, timeout=20, headers={"User-Agent":"sunday-signal/1.0"})
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return [], {"status":"degraded", "source":"ESPN", "error":str(exc)[:220], "as_of":as_of}
    rows: list[dict[str, Any]] = []
    for article in data.get("articles", []) or []:
        headline = str(article.get("headline") or "").strip()
        description = str(article.get("description") or "").strip()
        href = ""
        links = article.get("links") or {}
        if isinstance(links, dict):
            web = links.get("web") or {}
            if isinstance(web, dict):
                href = str(web.get("href") or "")
        if headline:
            rows.append({
                "headline": headline,
                "description": description,
                "url": href,
                "source_name": "ESPN",
                "published": article.get("published"),
            })
    return rows, {"status":"healthy", "source":"ESPN", "articles":len(rows), "as_of":as_of}


def _fetch_google_headlines(away: str, home: str, session=requests, limit: int = 6) -> list[dict[str, Any]]:
    query = f'"{_team_name(away)}" "{_team_name(home)}" NFL'
    url = f"{GOOGLE_NEWS_RSS}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        response = session.get(url, timeout=15, headers={"User-Agent":"sunday-signal/1.0"})
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        title = str(item.findtext("title") or "").strip()
        link = str(item.findtext("link") or "").strip()
        if not title or not _match_text(title, away, home):
            continue
        source = _source_from_title(title)
        rows.append({"headline":title, "description":"", "url":link, "source_name":source, "published":item.findtext("pubDate")})
    return rows


def _reporting_item(article: dict[str, Any], away: str, home: str) -> dict[str, Any]:
    headline = re.sub(r"\s+", " ", str(article.get("headline") or "")).strip()
    source = str(article.get("source_name") or "Public reporting")
    return {
        "category": "reporting",
        "title": headline,
        # Do not republish article copy. The headline is a discovery signal; source
        # links remain attached for the editor and reader to inspect directly.
        "summary": f"Current {source} reporting flags this as a live {away}-{home} storyline.",
        "strength": "Strong" if source in SOURCE_PRIORITY else "Moderate",
        "source_name": source,
        "source_url": str(article.get("url") or ""),
        "as_of": str(article.get("published") or _now()),
        "side": "neutral",
        "relevance": "Current external reporting used to choose the human story angle; never a numerical model input.",
        "metadata": {
            "family":"media_reporting",
            "source_priority":SOURCE_PRIORITY.get(source, 50),
            "reported_headline":headline,
            "promoted_to_model":False,
            "provenance_grade":"B",
        },
    }


def add_media_context(
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    season: int,
    week: int,
    config_dir: str | Path = "config",
    session=requests,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Attach current reporting and source-backed editorial Reads to each game."""
    out = {str(k): list(v) for k, v in (evidence or {}).items()}
    curated = _load_curated_reads(season, week, config_dir)
    espn, espn_status = _fetch_espn_articles(session=session)
    games_with_curated = 0
    games_with_reporting = 0

    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        away, home = _norm(game.get("away_team")), _norm(game.get("home_team"))
        items = out.setdefault(gid, [])

        seed = curated.get(gid)
        if isinstance(seed, dict) and seed.get("read"):
            games_with_curated += 1
            items.append({
                "category":"reporting",
                "title":str(seed.get("headline") or f"{away}-{home} preview").strip(),
                "summary":str(seed.get("read") or "").strip(),
                "strength":"Strong",
                "source_name":str(seed.get("source_name") or "Curated current reporting"),
                "source_url":str(seed.get("source_url") or ""),
                "as_of":_now(),
                "side":"neutral",
                "relevance":"Human-written synthesis of current matchup reporting; editorial only.",
                "metadata":{
                    "family":"media_reporting",
                    "direct_read":True,
                    "editorial_seed":True,
                    "source_priority":110,
                    "promoted_to_model":False,
                    "provenance_grade":"A",
                },
            })

        matching = [a for a in espn if _match_text(f"{a.get('headline','')} {a.get('description','')}", away, home)]
        if len(matching) < 2:
            matching.extend(_fetch_google_headlines(away, home, session=session, limit=6))
        seen: set[str] = set()
        added = 0
        for article in sorted(matching, key=lambda a: SOURCE_PRIORITY.get(str(a.get("source_name") or ""), 50), reverse=True):
            headline = str(article.get("headline") or "").strip()
            key = headline.lower()
            if not headline or key in seen:
                continue
            seen.add(key)
            items.append(_reporting_item(article, away, home))
            added += 1
            if added >= 3:
                break
        if added:
            games_with_reporting += 1

    status = {
        "status":"healthy" if games_with_curated or games_with_reporting else "degraded",
        "as_of":_now(),
        "games_with_curated_read":games_with_curated,
        "games_with_live_reporting":games_with_reporting,
        "espn":espn_status,
        "discovery":"ESPN API + Google News RSS headlines; curated source-backed Read takes precedence when present.",
        "guardrail":"Media context is editorial only and cannot change LevLine probabilities or features.",
    }
    return out, status


def apply_source_first_reads(
    previews: dict[str, dict[str, Any]],
    evidence: dict[str, list[dict[str, Any]]],
    predictions: pd.DataFrame | None = None,
) -> dict[str, dict[str, Any]]:
    """Make a direct, source-backed media Read the public lead when available.

    This runs at the last editorial stage so older story-desk/template code cannot
    overwrite the reporting-led paragraph. Quantitative factor cards, market copy,
    cases and model output remain intact below the lead.
    """
    rows = {}
    if predictions is not None and not predictions.empty and "game_id" in predictions.columns:
        rows = {str(row.game_id): row for _, row in predictions.iterrows()}

    for game_id, preview in previews.items():
        items = list((evidence or {}).get(str(game_id), []))
        direct = [
            item for item in items
            if (item.get("metadata") or {}).get("family") == "media_reporting"
            and bool((item.get("metadata") or {}).get("direct_read"))
            and str(item.get("summary") or "").strip()
        ]
        direct.sort(
            key=lambda item: int((item.get("metadata") or {}).get("source_priority") or 0),
            reverse=True,
        )
        if not direct:
            continue
        lead = direct[0]
        headline = str(lead.get("title") or "").strip()
        read = str(lead.get("summary") or "").strip()
        if headline:
            preview["headline"] = headline
        paragraphs = list(preview.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = read
        else:
            paragraphs = [read]
        preview["paragraphs"] = paragraphs

        reporting = [
            item for item in items
            if (item.get("metadata") or {}).get("family") == "media_reporting"
        ]
        reporting.sort(
            key=lambda item: int((item.get("metadata") or {}).get("source_priority") or 0),
            reverse=True,
        )
        preview["reporting_sources"] = [
            {
                "title": str(item.get("title") or ""),
                "source_name": item.get("source_name"),
                "source_url": item.get("source_url"),
                "as_of": item.get("as_of"),
            }
            for item in reporting[:4]
            if item.get("title")
        ]
        voice = dict(preview.get("editorial_voice") or {})
        voice.update({
            "evidence_led": True,
            "game_specific": True,
            "slate_aware": True,
            "source_first_reporting": True,
            "lead_source": lead.get("source_name"),
            "lead_source_url": lead.get("source_url"),
            "lead_items": [headline] if headline else [],
        })
        preview["editorial_voice"] = voice
        spine = dict(preview.get("story_spine") or {})
        spine.update({
            "primary_family":"media_reporting",
            "primary_title":headline,
            "primary_mode":"reported_storyline",
        })
        preview["story_spine"] = spine
        preview["editorial_version"] = "source-first-v1"

        row = rows.get(str(game_id))
        if row is not None:
            preview["source_first_guardrail"] = (
                "Current reporting chooses and explains the story angle only; "
                "LevLine probabilities remain generated by the numerical model."
            )
    return previews

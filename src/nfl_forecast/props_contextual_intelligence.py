from __future__ import annotations

"""Shared LevLine contextual-intelligence adapter for Props Research Beta.

This module consumes the already-validated Sunday Signal media artifact instead of
running a second news-research stack. It is deliberately narrow: only explicit,
point-in-time quarterback starter reporting may override the timestamped depth chart.

The adapter never parses betting recommendations, probabilities, or completed-game
outcomes. Ambiguous/stale reporting fails closed.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Any, Mapping
from urllib.parse import quote_plus, urlparse

import pandas as pd
import requests

from .media_context import (
    BING_NEWS_RSS,
    GOOGLE_NEWS_RSS,
    _fetch_feed as _levline_fetch_feed,
    _is_low_trust_source as _levline_is_low_trust_source,
    _source_priority as _levline_source_priority,
    _team_name as _levline_team_name,
)
from .props_player_state import normalize_player_name, normalize_team_code
from .source_policy import OFFICIAL_TEAM_MEDIA_DOMAINS

MAX_MEDIA_AGE_HOURS = 6.0
MAX_LIVE_STARTER_REPORT_AGE_HOURS = 72.0

_CONFIRMED_PATTERNS = (
    r"\bwill start\b",
    r"\bis starting\b",
    r"\bwill be (?:the )?(?:starting quarterback|starter)\b",
    r"\bnamed (?:the )?(?:starting quarterback|starting qb|starter)\b",
    r"\bconfirmed (?:that )?.{0,40}\b(?:will start|is starting)\b",
)

_EXPECTED_PATTERNS = (
    r"\bexpected to start\b",
    r"\bset to start\b",
    r"\bslated to start\b",
    r"\blikely to start\b",
    r"\bprojected to start\b",
    r"\bwill take over\b",
    r"\bexpected to take over\b",
)

_UNCERTAIN_PATTERNS = (
    r"\bnot yet named\b",
    r"\bhas not yet named\b",
    r"\buncertain\b",
    r"\bcompetition\b",
    r"\bcould start\b",
    r"\bmay start\b",
    r"\bif .{0,30}\bstarts\b",
)


def _utc(value: object) -> pd.Timestamp | None:
    try:
        parsed = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(parsed) or parsed.tzinfo is None:
        return None
    return parsed.tz_convert("UTC")


def _host(url: object) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""


def _source_support(entry: Mapping[str, Any], player_name: str) -> tuple[bool, list[str]]:
    sources = entry.get("sources")
    if not isinstance(sources, list):
        return False, []
    last = str(player_name).strip().split()[-1].lower() if str(player_name).strip() else ""
    urls: list[str] = []
    title_support = False
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        url = str(source.get("url") or "").strip()
        title = re.sub(r"\s+", " ", str(source.get("title") or "")).strip().lower()
        if not url or not _host(url):
            continue
        urls.append(url)
        if last and last in title and any(
            token in title
            for token in ("start", "starter", "starting", "quarterback", "qb", "take over")
        ):
            title_support = True
    return title_support, urls


def _claim_strength(text: str, player_name: str) -> str | None:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean or not player_name:
        return None
    match = re.search(re.escape(player_name), clean, flags=re.I)
    if match is None:
        return None

    # Bind starter language to the named player instead of accepting any starter
    # phrase in a symmetric context window. This avoids misreading constructions such
    # as "Drew Lock expected to start after Sam Darnold was ruled out" as a starter
    # claim about Darnold.
    after = clean[match.start(): min(len(clean), match.end() + 120)].lower()
    before = clean[max(0, match.start() - 80): match.start()].lower()
    local = (before + clean[match.start(): min(len(clean), match.end() + 80)]).lower()

    if any(re.search(pattern, after, flags=re.I) for pattern in _UNCERTAIN_PATTERNS):
        return None

    name = re.escape(player_name.lower())
    if any(re.search(rf"{name}.{{0,55}}{pattern}", after, flags=re.I) for pattern in _CONFIRMED_PATTERNS):
        return "confirmed"
    if re.search(r"\bnamed\b.{0,45}$", before, flags=re.I) and re.search(
        r"\b(?:the )?(?:starter|starting quarterback)\b",
        after,
        flags=re.I,
    ):
        return "confirmed"
    if any(re.search(rf"{name}.{{0,55}}{pattern}", after, flags=re.I) for pattern in _EXPECTED_PATTERNS):
        return "expected"
    if any(re.search(pattern, local, flags=re.I) for pattern in _UNCERTAIN_PATTERNS):
        return None
    return None


def _qb_rows(player_state: pd.DataFrame, game_id: str) -> pd.DataFrame:
    rows = player_state[
        player_state["game_id"].astype(str).eq(str(game_id))
        & player_state["position"].astype("string").fillna("").str.upper().eq("QB")
    ].copy()
    if rows.empty:
        raise ValueError(f"player_state has no quarterback rows for game={game_id}")
    rows["_team"] = rows["team"].map(normalize_team_code)
    return rows


def resolve_primary_qbs_from_levline_media(
    media_payload: Mapping[str, Any] | None,
    player_state: pd.DataFrame,
    *,
    game_id: str,
    forecast_timestamp: object,
    max_age_hours: float = MAX_MEDIA_AGE_HOURS,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Resolve explicit starter-QB reporting from the shared LevLine media artifact.

    Qualified reporting overrides the depth chart only when:
    - the media entry exists for the same game;
    - its generated timestamp is timezone-aware, no later than the forecast, and fresh;
    - exactly one roster QB on a team is explicitly reported as confirmed/expected starter;
    - the candidate is not already marked OUT;
    - expected (not confirmed) claims have either title-level source support or a
      material competing-QB absence (OUT/DOUBTFUL).

    This is a point-in-time source handoff, not a learned/tuned model.
    """

    audit: dict[str, Any] = {
        "status": "missing",
        "game_id": str(game_id),
        "max_age_hours": float(max_age_hours),
        "generated_utc": None,
        "age_hours": None,
        "teams_resolved": 0,
        "teams_ambiguous": [],
        "teams_unresolved": [],
        "claims": [],
        "completed_game_outcomes_used": False,
        "betting_fields_used": False,
    }
    if not isinstance(media_payload, Mapping):
        return {}, audit

    games = media_payload.get("games")
    if not isinstance(games, Mapping):
        audit["status"] = "unusable_missing_games"
        return {}, audit
    entry = games.get(str(game_id))
    if not isinstance(entry, Mapping):
        audit["status"] = "unavailable_game_entry"
        return {}, audit

    generated = _utc(entry.get("generated_utc") or media_payload.get("generated_utc"))
    if generated is None:
        audit["status"] = "unusable_missing_timestamp"
        return {}, audit
    forecast = _utc(forecast_timestamp)
    if forecast is None:
        raise ValueError("forecast_timestamp must be timezone-aware")
    audit["generated_utc"] = generated.isoformat()
    age_hours = (forecast - generated).total_seconds() / 3600.0
    audit["age_hours"] = float(age_hours)
    if age_hours < -1e-6:
        audit["status"] = "unusable_future_media"
        return {}, audit
    if age_hours > float(max_age_hours):
        audit["status"] = "stale"
        return {}, audit

    paragraph = str(entry.get("paragraph1") or entry.get("read") or "")
    if not paragraph.strip():
        audit["status"] = "unusable_missing_reporting_text"
        return {}, audit

    qbs = _qb_rows(player_state, str(game_id))
    resolved: dict[str, dict[str, str]] = {}

    for team, group in qbs.groupby("_team", sort=True):
        candidates: list[dict[str, Any]] = []
        for _, row in group.iterrows():
            player_name = str(row.get("player_name") or "").strip()
            player_id = str(row.get("player_id") or "").strip()
            if not player_name or not player_id:
                continue
            active_state = str(row.get("expected_active_state") or "UNKNOWN").upper()
            if active_state == "OUT":
                continue
            strength = _claim_strength(paragraph, player_name)
            if strength is None:
                continue

            title_support, source_urls = _source_support(entry, player_name)
            other_states = {
                str(other.get("expected_active_state") or "UNKNOWN").upper()
                for _, other in group.iterrows()
                if str(other.get("player_id") or "") != player_id
            }
            material_competitor_absence = bool(
                {"OUT", "DOUBTFUL"}.intersection(other_states)
            )
            if strength == "expected" and not (
                title_support or material_competitor_absence
            ):
                audit["claims"].append(
                    {
                        "team": str(team),
                        "player_id": player_id,
                        "player_name": player_name,
                        "strength": strength,
                        "accepted": False,
                        "reason": "expected_claim_lacks_corroboration",
                    }
                )
                continue

            candidates.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "strength": strength,
                    "source_urls": source_urls,
                    "title_support": title_support,
                    "material_competitor_absence": material_competitor_absence,
                }
            )

        if len(candidates) != 1:
            if len(candidates) > 1:
                audit["teams_ambiguous"].append(
                    {
                        "team": str(team),
                        "candidate_ids": sorted(row["player_id"] for row in candidates),
                    }
                )
            else:
                audit["teams_unresolved"].append(str(team))
            continue

        candidate = candidates[0]
        source_urls = candidate["source_urls"][:4]
        resolved[str(team)] = {
            "player_id": candidate["player_id"],
            "provenance": (
                "levline_shared_media:"
                f"{generated.isoformat()}:{candidate['strength']}:"
                + "|".join(source_urls)
            ),
        }
        audit["claims"].append(
            {
                "team": str(team),
                "player_id": candidate["player_id"],
                "player_name": candidate["player_name"],
                "strength": candidate["strength"],
                "accepted": True,
                "title_support": bool(candidate["title_support"]),
                "material_competitor_absence": bool(
                    candidate["material_competitor_absence"]
                ),
                "source_urls": source_urls,
            }
        )

    audit["teams_resolved"] = len(resolved)
    audit["status"] = "qualified" if resolved else "no_qualified_starter_claim"
    return resolved, audit



def _team_mentioned(text: str, team_name: str) -> bool:
    lowered = str(text or "").lower()
    full = str(team_name or "").lower()
    nickname = full.split()[-1] if full else ""
    return bool(full and (full in lowered or (nickname and nickname in lowered)))


def _official_report_source(row: Mapping[str, Any]) -> bool:
    candidates = (
        row.get("publisher_url"),
        row.get("source_url"),
    )
    for raw in candidates:
        host = _host(raw)
        if host.startswith("www."):
            host = host[4:]
        if not host:
            continue
        if host == "nfl.com" or host.endswith(".nfl.com"):
            return True
        if any(
            host == domain or host.endswith("." + domain)
            for domain in OFFICIAL_TEAM_MEDIA_DOMAINS
        ):
            return True
    return False


def _starter_report_row(
    row: Mapping[str, Any],
    *,
    game_id: str,
    away_name: str,
    home_name: str,
    captured_at: datetime,
    max_age_hours: float,
) -> dict[str, Any] | None:
    published = row.get("published")
    if not isinstance(published, datetime):
        return None
    if published.tzinfo is None:
        return None
    published = published.astimezone(timezone.utc)
    age_hours = (captured_at - published).total_seconds() / 3600.0
    if age_hours < -0.1 or age_hours > float(max_age_hours):
        return None

    title = re.sub(r"\s+", " ", str(row.get("title") or "")).strip()
    summary = re.sub(r"\s+", " ", str(row.get("summary") or "")).strip()
    text = f"{title} {summary}".strip()
    lowered = text.lower()
    if not title:
        return None
    if not _team_mentioned(text, away_name) or not _team_mentioned(text, home_name):
        return None
    if not any(
        token in lowered
        for token in (
            "will start",
            "is starting",
            "expected to start",
            "set to start",
            "slated to start",
            "likely to start",
            "named starting",
            "named the starter",
            "starting qb",
            "starting quarterback",
        )
    ):
        return None

    source_name = str(row.get("source_name") or "").strip()
    source_priority = int(_levline_source_priority(source_name))
    official_source = _official_report_source(row)
    if _levline_is_low_trust_source(source_name):
        return None
    if not official_source and source_priority < 82:
        return None

    return {
        "game_id": str(game_id),
        "title": title,
        "summary": summary[:700],
        "source_name": source_name or "Unknown source",
        "source_url": str(row.get("source_url") or "").strip(),
        "publisher_url": str(row.get("publisher_url") or "").strip(),
        "published_utc": published.isoformat(),
        "provider": str(row.get("provider") or ""),
        "source_priority": source_priority,
        "official_source": bool(official_source),
        "captured_at_utc": captured_at.isoformat(),
    }


def fetch_live_qb_starter_reports(
    schedules: pd.DataFrame,
    *,
    season: int,
    week: int,
    session=requests,
    timeout: int = 8,
    max_age_hours: float = MAX_LIVE_STARTER_REPORT_AGE_HOURS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch current starter-QB reporting through LevLine's existing media sources.

    This deliberately reuses the same Google News/Bing RSS fetch/parsing and source
    priority policy as Sunday Signal. It does not introduce a separate media provider.
    Only fresh, trusted reports that mention both teams and explicit starter language
    survive into the handoff.
    """

    required = {"game_id", "season", "week", "away_team", "home_team"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule source missing starter-reporting fields: {sorted(missing)}")

    work = schedules.copy()
    work = work[
        pd.to_numeric(work["season"], errors="coerce").eq(int(season))
        & pd.to_numeric(work["week"], errors="coerce").eq(int(week))
    ].copy()
    if work.empty:
        raise ValueError(
            f"schedule source has no starter-reporting rows for season={season}, week={week}"
        )

    lookback_days = max(1, int(math.ceil(float(max_age_hours) / 24.0)))
    captured_at = datetime.now(timezone.utc)

    def fetch_game(row: pd.Series) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
        game_id = str(row.get("game_id") or "").strip()
        away_name = _levline_team_name(row.get("away_team"))
        home_name = _levline_team_name(row.get("home_team"))
        query = f'"{away_name}" "{home_name}" quarterback starter'
        encoded = quote_plus(query)
        google_url = (
            f"{GOOGLE_NEWS_RSS}?q={encoded}+when:{lookback_days}d"
            "&hl=en-US&gl=US&ceid=US:en"
        )
        bing_url = f"{BING_NEWS_RSS}?q={encoded}&format=rss&mkt=en-US"
        google_rows, google_error = _levline_fetch_feed(
            session, google_url, "google_news", timeout
        )
        bing_rows, bing_error = _levline_fetch_feed(
            session, bing_url, "bing_news", timeout
        )

        accepted: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source_row in google_rows + bing_rows:
            item = _starter_report_row(
                source_row,
                game_id=game_id,
                away_name=away_name,
                home_name=home_name,
                captured_at=captured_at,
                max_age_hours=max_age_hours,
            )
            if item is None:
                continue
            key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            accepted.append(item)

        accepted.sort(
            key=lambda item: (
                str(item.get("published_utc") or ""),
                bool(item.get("official_source")),
                int(item.get("source_priority") or 0),
            ),
            reverse=True,
        )
        return game_id, accepted, {
            "google_errors": int(bool(google_error)),
            "bing_errors": int(bool(bing_error)),
        }

    games: dict[str, list[dict[str, Any]]] = {}
    google_errors = 0
    bing_errors = 0
    rows = [row for _, row in work.iterrows()]
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(rows)))) as pool:
        futures = [pool.submit(fetch_game, row) for row in rows]
        for future in as_completed(futures):
            try:
                game_id, reports, errors = future.result()
            except Exception:
                continue
            if reports:
                games[game_id] = reports
            google_errors += int(errors["google_errors"])
            bing_errors += int(errors["bing_errors"])

    payload = {
        "contract_version": "levline-props-live-starter-reporting-v1",
        "captured_at_utc": captured_at.isoformat(),
        "max_age_hours": float(max_age_hours),
        "games": games,
    }
    audit = {
        "status": "qualified" if games else "no_qualified_starter_reports",
        "captured_at_utc": captured_at.isoformat(),
        "games_requested": int(len(rows)),
        "games_with_reports": int(len(games)),
        "report_count": int(sum(len(items) for items in games.values())),
        "google_news_errors": int(google_errors),
        "bing_news_errors": int(bing_errors),
        "source_stack": "Sunday Signal Google News RSS + Bing News RSS source policy",
        "completed_game_outcomes_used": False,
        "betting_fields_used": False,
    }
    return payload, audit


def resolve_primary_qbs_from_live_reports(
    report_payload: Mapping[str, Any] | None,
    player_state: pd.DataFrame,
    *,
    game_id: str,
    forecast_timestamp: object,
    max_age_hours: float = MAX_LIVE_STARTER_REPORT_AGE_HOURS,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Resolve current QB starter declarations from structured live LevLine reporting."""

    audit: dict[str, Any] = {
        "status": "missing",
        "game_id": str(game_id),
        "max_age_hours": float(max_age_hours),
        "teams_resolved": 0,
        "teams_ambiguous": [],
        "teams_unresolved": [],
        "claims": [],
        "completed_game_outcomes_used": False,
        "betting_fields_used": False,
    }
    if not isinstance(report_payload, Mapping):
        return {}, audit
    games = report_payload.get("games")
    if not isinstance(games, Mapping):
        audit["status"] = "unusable_missing_games"
        return {}, audit
    reports = games.get(str(game_id))
    if not isinstance(reports, list) or not reports:
        audit["status"] = "unavailable_game_entry"
        return {}, audit

    forecast = _utc(forecast_timestamp)
    if forecast is None:
        raise ValueError("forecast_timestamp must be timezone-aware")
    qbs = _qb_rows(player_state, str(game_id))
    resolved: dict[str, dict[str, str]] = {}

    for team, group in qbs.groupby("_team", sort=True):
        accepted: list[dict[str, Any]] = []
        for _, row in group.iterrows():
            player_name = str(row.get("player_name") or "").strip()
            player_id = str(row.get("player_id") or "").strip()
            if not player_name or not player_id:
                continue
            if str(row.get("expected_active_state") or "UNKNOWN").upper() == "OUT":
                continue

            other_states = {
                str(other.get("expected_active_state") or "UNKNOWN").upper()
                for _, other in group.iterrows()
                if str(other.get("player_id") or "") != player_id
            }
            material_competitor_absence = bool(
                {"OUT", "DOUBTFUL"}.intersection(other_states)
            )

            for report in reports:
                if not isinstance(report, Mapping):
                    continue
                published = _utc(report.get("published_utc"))
                if published is None:
                    continue
                age_hours = (forecast - published).total_seconds() / 3600.0
                if age_hours < -0.1 or age_hours > float(max_age_hours):
                    continue
                title = str(report.get("title") or "")
                summary = str(report.get("summary") or "")
                strength = _claim_strength(f"{title}. {summary}", player_name)
                if strength is None:
                    continue

                title_support = _claim_strength(title, player_name) is not None
                if strength == "expected" and not (
                    title_support or material_competitor_absence
                ):
                    audit["claims"].append(
                        {
                            "team": str(team),
                            "player_id": player_id,
                            "player_name": player_name,
                            "strength": strength,
                            "accepted": False,
                            "reason": "expected_claim_lacks_corroboration",
                            "published_utc": published.isoformat(),
                        }
                    )
                    continue

                source_urls = [
                    str(value).strip()
                    for value in (
                        report.get("source_url"),
                        report.get("publisher_url"),
                    )
                    if str(value or "").strip()
                ]
                accepted.append(
                    {
                        "team": str(team),
                        "player_id": player_id,
                        "player_name": player_name,
                        "strength": strength,
                        "published": published,
                        "published_utc": published.isoformat(),
                        "official_source": bool(report.get("official_source")),
                        "source_priority": int(report.get("source_priority") or 0),
                        "source_name": str(report.get("source_name") or ""),
                        "source_urls": source_urls,
                        "title": title,
                        "material_competitor_absence": material_competitor_absence,
                    }
                )

        if not accepted:
            audit["teams_unresolved"].append(str(team))
            continue

        best_by_player: dict[str, dict[str, Any]] = {}
        for claim in accepted:
            current = best_by_player.get(claim["player_id"])
            rank = (
                claim["published"].value,
                int(claim["strength"] == "confirmed"),
                int(claim["official_source"]),
                int(claim["source_priority"]),
            )
            if current is None:
                best_by_player[claim["player_id"]] = claim
                continue
            current_rank = (
                current["published"].value,
                int(current["strength"] == "confirmed"),
                int(current["official_source"]),
                int(current["source_priority"]),
            )
            if rank > current_rank:
                best_by_player[claim["player_id"]] = claim

        ranked = sorted(
            best_by_player.values(),
            key=lambda claim: (
                claim["published"].value,
                int(claim["strength"] == "confirmed"),
                int(claim["official_source"]),
                int(claim["source_priority"]),
            ),
            reverse=True,
        )
        top = ranked[0]
        if len(ranked) > 1:
            second = ranked[1]
            separation_hours = (
                top["published"] - second["published"]
            ).total_seconds() / 3600.0
            if separation_hours < 1.0:
                audit["teams_ambiguous"].append(
                    {
                        "team": str(team),
                        "candidate_ids": [top["player_id"], second["player_id"]],
                        "reason": "conflicting_recent_starter_reports",
                    }
                )
                continue

        source_urls = top["source_urls"][:4]
        resolved[str(team)] = {
            "player_id": top["player_id"],
            "provenance": (
                "levline_live_reporting:"
                f"{top['published_utc']}:{top['strength']}:"
                + "|".join(source_urls)
            ),
        }
        audit["claims"].append(
            {
                **{
                    key: value
                    for key, value in top.items()
                    if key not in {"published", "source_urls"}
                },
                "accepted": True,
                "source_urls": source_urls,
            }
        )

    audit["teams_resolved"] = len(resolved)
    audit["status"] = "qualified" if resolved else "no_qualified_starter_claim"
    return resolved, audit

def load_levline_media_payload(path: object) -> dict[str, Any] | None:
    """Load the shared media artifact from disk without treating absence as healthy."""

    from pathlib import Path
    import json

    source = Path(path)
    if not source.exists():
        return None
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None

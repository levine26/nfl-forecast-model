from __future__ import annotations

"""Shared LevLine contextual-intelligence adapter for Props Research Beta.

This module consumes the already-validated Sunday Signal media artifact instead of
running a second news-research stack. It is deliberately narrow: only explicit,
point-in-time quarterback starter reporting may override the timestamped depth chart.

The adapter never parses betting recommendations, probabilities, or completed-game
outcomes. Ambiguous/stale reporting fails closed.
"""

from datetime import datetime, timezone
import re
from typing import Any, Mapping
from urllib.parse import urlparse

import pandas as pd

from .props_player_state import normalize_player_name, normalize_team_code

MAX_MEDIA_AGE_HOURS = 6.0

_CONFIRMED_PATTERNS = (
    r"\bwill start\b",
    r"\bis starting\b",
    r"\bwill be (?:the )?(?:starting quarterback|starter)\b",
    r"\bnamed (?:the )?(?:starting quarterback|starter)\b",
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


MAX_CURRENT_REPORT_AGE_HOURS = 48.0


def _current_source_claim_strength(title: str, player_name: str) -> str | None:
    """Resolve starter language in a source headline and bind it to one named QB."""

    clean = re.sub(r"\s+", " ", str(title or "")).strip()
    if not clean or not player_name:
        return None
    match = re.search(re.escape(player_name), clean, flags=re.I)
    if match is None:
        return None

    base = _claim_strength(clean, player_name)
    if base is not None:
        return base

    before = clean[max(0, match.start() - 70): match.start()].lower()
    after = clean[match.end(): min(len(clean), match.end() + 90)].lower()
    local = clean[max(0, match.start() - 60): min(len(clean), match.end() + 90)].lower()
    if any(re.search(pattern, local, flags=re.I) for pattern in _UNCERTAIN_PATTERNS):
        return None

    if re.search(r"\b(?:name|names|named)\b.{0,45}$", before, flags=re.I) and re.search(
        r"\b(?:starter|starting quarterback|starting qb)\b",
        after,
        flags=re.I,
    ):
        return "confirmed"
    if re.search(r"\b(?:to start|starts|will start)\b", after, flags=re.I):
        return "confirmed"
    if re.search(r"\bwith (?:a )?start (?:at|against)\b", after, flags=re.I):
        return "confirmed"
    if re.search(r"\b(?:starter|starting quarterback|starting qb)\b.{0,35}$", before, flags=re.I):
        return "confirmed"
    return None


def resolve_primary_qbs_from_current_reporting(
    previews_payload: Mapping[str, Any] | None,
    player_state: pd.DataFrame,
    *,
    game_id: str,
    forecast_timestamp: object,
    max_age_hours: float = MAX_CURRENT_REPORT_AGE_HOURS,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Resolve QB starters from LevLine's persisted current-reporting source list.

    current_reported_sources is produced by the same ranked Google/Bing/team-source
    media pass used by Sunday Signal, before any provider/Copilot presentation overlay.
    Each source must be timestamped at or before the forecast and recent enough for the
    weekly starter decision. Conflicting older claims lose to a newer qualified claim;
    an exact-time conflict fails closed.
    """

    audit: dict[str, Any] = {
        "status": "missing",
        "game_id": str(game_id),
        "max_age_hours": float(max_age_hours),
        "sources_received": 0,
        "sources_qualified": 0,
        "sources_future_discarded": 0,
        "sources_stale_discarded": 0,
        "sources_missing_timestamp": 0,
        "teams_resolved": 0,
        "teams_ambiguous": [],
        "teams_unresolved": [],
        "claims": [],
        "completed_game_outcomes_used": False,
        "betting_fields_used": False,
    }
    if not isinstance(previews_payload, Mapping):
        return {}, audit

    games = previews_payload.get("games")
    game_map = games if isinstance(games, Mapping) else previews_payload
    preview = game_map.get(str(game_id)) if isinstance(game_map, Mapping) else None
    if not isinstance(preview, Mapping):
        audit["status"] = "unavailable_game_entry"
        return {}, audit

    raw_sources = preview.get("current_reported_sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        audit["status"] = "unavailable_current_reporting"
        return {}, audit
    audit["sources_received"] = len(raw_sources)

    forecast = _utc(forecast_timestamp)
    if forecast is None:
        raise ValueError("forecast_timestamp must be timezone-aware")

    qualified_sources: list[dict[str, Any]] = []
    for source in raw_sources:
        if not isinstance(source, Mapping):
            continue
        stamp = _utc(source.get("as_of"))
        if stamp is None:
            audit["sources_missing_timestamp"] += 1
            continue
        age_hours = (forecast - stamp).total_seconds() / 3600.0
        if age_hours < -1e-6:
            audit["sources_future_discarded"] += 1
            continue
        if age_hours > float(max_age_hours):
            audit["sources_stale_discarded"] += 1
            continue
        title = re.sub(r"\s+", " ", str(source.get("title") or "")).strip()
        url = str(source.get("source_url") or source.get("url") or "").strip()
        if not title or not url or not _host(url):
            continue
        qualified_sources.append(
            {
                "title": title,
                "source_name": str(source.get("source_name") or source.get("name") or "").strip(),
                "source_url": url,
                "as_of": stamp,
            }
        )

    audit["sources_qualified"] = len(qualified_sources)
    if not qualified_sources:
        audit["status"] = "no_qualified_current_reporting"
        return {}, audit

    qbs = _qb_rows(player_state, str(game_id))
    resolved: dict[str, dict[str, str]] = {}

    for team, group in qbs.groupby("_team", sort=True):
        team_claims: list[dict[str, Any]] = []
        for _, row in group.iterrows():
            player_name = str(row.get("player_name") or "").strip()
            player_id = str(row.get("player_id") or "").strip()
            if not player_name or not player_id:
                continue
            if str(row.get("expected_active_state") or "UNKNOWN").upper() == "OUT":
                continue
            for source in qualified_sources:
                strength = _current_source_claim_strength(source["title"], player_name)
                if strength is None:
                    continue
                claim = {
                    "team": str(team),
                    "player_id": player_id,
                    "player_name": player_name,
                    "strength": strength,
                    "as_of": source["as_of"],
                    "source_name": source["source_name"],
                    "source_url": source["source_url"],
                    "title": source["title"],
                }
                team_claims.append(claim)
                audit["claims"].append(
                    {
                        **{k: v for k, v in claim.items() if k != "as_of"},
                        "as_of": source["as_of"].isoformat(),
                        "accepted": False,
                    }
                )

        if not team_claims:
            audit["teams_unresolved"].append(str(team))
            continue

        newest = max(claim["as_of"] for claim in team_claims)
        newest_claims = [claim for claim in team_claims if claim["as_of"] == newest]
        newest_ids = sorted({claim["player_id"] for claim in newest_claims})
        if len(newest_ids) != 1:
            audit["teams_ambiguous"].append(
                {
                    "team": str(team),
                    "as_of": newest.isoformat(),
                    "candidate_ids": newest_ids,
                }
            )
            continue

        player_id = newest_ids[0]
        candidate_claims = [claim for claim in newest_claims if claim["player_id"] == player_id]
        candidate_claims.sort(
            key=lambda claim: (claim["strength"] == "confirmed", bool(claim["source_name"])),
            reverse=True,
        )
        winner = candidate_claims[0]
        resolved[str(team)] = {
            "player_id": player_id,
            "provenance": (
                "levline_current_reporting:"
                f"{winner['as_of'].isoformat()}:{winner['strength']}:"
                f"{winner['source_url']}"
            ),
        }
        for claim in audit["claims"]:
            if (
                claim.get("team") == str(team)
                and claim.get("player_id") == player_id
                and claim.get("as_of") == winner["as_of"].isoformat()
                and claim.get("source_url") == winner["source_url"]
            ):
                claim["accepted"] = True
                break

    audit["teams_resolved"] = len(resolved)
    audit["status"] = "qualified" if resolved else "no_qualified_starter_claim"
    return resolved, audit


def load_levline_game_previews(path: object) -> dict[str, Any] | None:
    """Load Sunday Signal game previews with persisted current reporting."""

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

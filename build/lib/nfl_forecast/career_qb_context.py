from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any

import nflreadpy as nfl
import pandas as pd


PLAYER_STATS_URL = "https://nflreadr.nflverse.com/articles/dictionary_player_stats.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _norm_name(value: Any) -> str:
    return re.sub(r"[^a-z]", "", str(value or "").lower())


def _norm_team(value: Any) -> str:
    team = str(value or "").upper()
    return "JAX" if team == "JAC" else team


def _pandas(frame: Any) -> pd.DataFrame:
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    try:
        return frame.to_pandas()
    except Exception:
        return pd.DataFrame()


def _targets(evidence: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    targets = []
    for game_id, items in evidence.items():
        for item in items:
            meta = item.get("metadata") or {}
            if meta.get("family") != "qb_opponent_history":
                continue
            title = str(item.get("title") or "")
            if " vs " not in title:
                continue
            qb, rest = title.split(" vs ", 1)
            opponent = rest.split(":", 1)[0].strip()
            meaningful = list(meta.get("meetings") or [])
            recent_ids = {
                str(row.get("game_id")) for row in meaningful
                if (_num(row.get("dropbacks")) or 0) >= 10 and row.get("game_id")
            }
            targets.append({
                "game_id": str(game_id),
                "item": item,
                "qb": qb.strip(),
                "opponent": _norm_team(opponent),
                "side": str(item.get("side") or "neutral"),
                "recent_ids": recent_ids,
            })
    return targets


def _career_start_season(targets: list[dict[str, Any]], players: pd.DataFrame, season: int) -> int:
    if players.empty or "display_name" not in players.columns:
        return max(1999, season - 18)
    p = players.copy()
    p["_name"] = p["display_name"].map(_norm_name)
    names = {_norm_name(t["qb"]) for t in targets}
    p = p[p["_name"].isin(names)]
    for field in ("draft_year", "rookie_year", "entry_year"):
        if field in p.columns:
            years = pd.to_numeric(p[field], errors="coerce").dropna()
            years = years[(years >= 1999) & (years < season)]
            if not years.empty:
                return int(years.min())
    return max(1999, season - 18)


def add_career_qb_ledgers(
    evidence: dict[str, list[dict[str, Any]]],
    season: int,
    player_stats: Any | None = None,
    players: Any | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    """Cross-check recent PBP histories against the full weekly player-stat ledger.

    Public wording deliberately says "meaningful passing games" rather than
    starts. A game enters the career ledger only when the quarterback logged at
    least 10 official pass attempts, preventing a two-pass relief cameo from
    being presented as equivalent to a start.
    """
    targets = _targets(evidence)
    as_of = _now()
    if not targets:
        return evidence, [], {"status":"healthy", "as_of":as_of, "targets":0, "evidence_items_added":0}

    try:
        player_frame = _pandas(players if players is not None else nfl.load_players())
        start = _career_start_season(targets, player_frame, season)
        stats_frame = _pandas(player_stats if player_stats is not None else nfl.load_player_stats(list(range(start, season)), summary_level="week"))
    except Exception as exc:
        return evidence, [], {
            "status":"degraded", "as_of":as_of, "source":"nflverse weekly player stats", "source_url":PLAYER_STATS_URL,
            "error":str(exc)[:220], "guardrail":"Career ledger is optional explanatory verification and never changes LevLine.",
        }

    required = {"player_display_name", "opponent_team", "attempts", "game_id"}
    if stats_frame.empty or not required.issubset(stats_frame.columns):
        return evidence, [], {
            "status":"degraded", "as_of":as_of, "source":"nflverse weekly player stats", "source_url":PLAYER_STATS_URL,
            "error":f"Missing required player-stat fields: {sorted(required - set(stats_frame.columns))}",
            "guardrail":"Career ledger is optional explanatory verification and never changes LevLine.",
        }

    s = stats_frame.copy()
    s["_name"] = s["player_display_name"].map(_norm_name)
    s["_opp"] = s["opponent_team"].map(_norm_team)
    s["attempts"] = pd.to_numeric(s["attempts"], errors="coerce").fillna(0)
    s = s[s["attempts"].ge(10)].copy()
    if "season" in s.columns:
        s["season"] = pd.to_numeric(s["season"], errors="coerce")
        s = s[s["season"].lt(season)]

    audit = []
    added = 0
    conflicts = 0
    for target in targets:
        rows = s[s["_name"].eq(_norm_name(target["qb"])) & s["_opp"].eq(target["opponent"])].copy()
        rows = rows.drop_duplicates("game_id", keep="last")
        career_ids = set(rows["game_id"].astype(str))
        missing_recent = sorted(target["recent_ids"] - career_ids)
        grade = "HOLD" if missing_recent else "B"
        if missing_recent:
            conflicts += 1
            audit.append({
                "game_id":target["game_id"], "quarterback":target["qb"], "opponent":target["opponent"],
                "status":"conflict", "provenance_grade":"HOLD", "recent_pbp_games_missing_from_weekly_ledger":missing_recent,
            })
            continue
        if rows.empty:
            audit.append({
                "game_id":target["game_id"], "quarterback":target["qb"], "opponent":target["opponent"],
                "status":"no_meaningful_games", "provenance_grade":"B",
            })
            continue

        reg = int(rows["season_type"].astype(str).str.upper().eq("REG").sum()) if "season_type" in rows.columns else None
        post = int(len(rows) - reg) if reg is not None else None
        attempts = int(rows["attempts"].sum())
        yards = int(pd.to_numeric(rows.get("passing_yards"), errors="coerce").fillna(0).sum()) if "passing_yards" in rows.columns else None
        tds = int(pd.to_numeric(rows.get("passing_tds"), errors="coerce").fillna(0).sum()) if "passing_tds" in rows.columns else None
        ints = int(pd.to_numeric(rows.get("passing_interceptions"), errors="coerce").fillna(0).sum()) if "passing_interceptions" in rows.columns else None
        seasons = pd.to_numeric(rows.get("season"), errors="coerce").dropna() if "season" in rows.columns else pd.Series(dtype=float)
        start = int(seasons.min()) if not seasons.empty else None
        end = int(seasons.max()) if not seasons.empty else None
        breakdown = f" ({reg} regular season, {post} postseason)" if reg is not None else ""
        statline = []
        if yards is not None:
            statline.append(f"{yards:,} passing yards")
        if tds is not None and ints is not None:
            statline.append(f"{tds} TD, {ints} INT")
        stat_text = f" Across those games: {attempts} attempts" + (", " + ", ".join(statline) if statline else "") + "."
        sample_text = f" from {start} through {end}" if start is not None and end is not None else ""
        summary = (
            f"The full nflverse weekly player-stat ledger{sample_text} contains {len(rows)} meaningful passing games for {target['qb']} against {target['opponent']}{breakdown}."
            + stat_text
            + " A game must include at least 10 pass attempts to count here, so brief relief cameos are excluded. The recent play-by-play sample is cross-checked against this ledger."
        )
        title = f"{target['qb']} vs {target['opponent']}: career game ledger"
        items = evidence[target["game_id"]]
        if title not in {str(item.get("title")) for item in items}:
            items.append({
                "category":"history", "title":title, "summary":summary,
                "strength":"Strong" if len(rows) >= 5 else "Moderate" if len(rows) >= 3 else "Weak",
                "source_name":"nflverse weekly player stats", "source_url":PLAYER_STATS_URL, "as_of":as_of,
                "side":target["side"], "sample_size":int(len(rows)), "relevance":"Full-career opponent ledger cross-check for the current starting quarterback",
                "promoted_to_model":False,
                "metadata":{
                    "family":"career_qb_opponent_ledger", "meaningful_games":int(len(rows)), "regular_season_games":reg,
                    "postseason_games":post, "attempt_threshold":10, "career_game_ids":sorted(career_ids),
                    "recent_pbp_game_ids":sorted(target["recent_ids"]), "recent_overlap_verified":True,
                    "provenance_grade":grade, "scope":"career_weekly_stats_meaningful_passing_games_not_starts",
                },
            })
            added += 1
        audit.append({
            "game_id":target["game_id"], "quarterback":target["qb"], "opponent":target["opponent"],
            "status":"verified", "meaningful_games":int(len(rows)), "regular_season_games":reg, "postseason_games":post,
            "recent_overlap_verified":True, "provenance_grade":grade,
        })

    return evidence, audit, {
        "status":"healthy" if conflicts == 0 else "degraded",
        "as_of":as_of, "source":"nflverse weekly player stats", "source_url":PLAYER_STATS_URL,
        "seasons_loaded_start":int(pd.to_numeric(stats_frame.get('season'), errors='coerce').min()) if 'season' in stats_frame.columns else None,
        "seasons_loaded_end":int(pd.to_numeric(stats_frame.get('season'), errors='coerce').max()) if 'season' in stats_frame.columns else None,
        "targets":len(targets), "verified":sum(1 for row in audit if row.get('status') == 'verified'),
        "conflicts":conflicts, "evidence_items_added":added,
        "guardrail":"Career facts come from full weekly player stats with a 10-attempt meaningful-game threshold and are cross-checked against the recent PBP game IDs; conflicts fail closed and are not published.",
    }

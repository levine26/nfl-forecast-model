from __future__ import annotations

import re
from typing import Any

import pandas as pd

from nfl_forecast.context import PBP_SOURCE_URL, utc_now


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _norm_name(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


def _latest_complete_season(pbp: pd.DataFrame | None, season: int) -> int | None:
    if pbp is None or pbp.empty or "season" not in pbp.columns:
        return None
    years = pd.to_numeric(pbp["season"], errors="coerce").dropna().astype(int)
    years = years[years < int(season)]
    return int(years.max()) if len(years) else None


def build_player_usage(
    pbp: pd.DataFrame | None,
    season: int,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    """Summarize prior-season opportunity shares for players on the injury report.

    This is explanatory context only. Opportunity share is intentionally not converted
    into a point-value injury adjustment.
    """
    latest = _latest_complete_season(pbp, season)
    if latest is None or pbp is None:
        return {}, {"status": "degraded", "error": "No prior complete PBP season available"}

    p = pbp[pd.to_numeric(pbp.get("season"), errors="coerce").eq(latest)].copy()
    if p.empty or "posteam" not in p.columns:
        return {}, {"status": "degraded", "error": "Prior-season offensive PBP unavailable"}

    usage: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_team, group in p.groupby("posteam", dropna=True):
        team = _norm_team(raw_team)
        target_names = group.get("receiver_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)
        rush_names = group.get("rusher_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)
        pass_names = group.get("passer_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)

        target_counts = target_names.map(_norm_name).value_counts()
        rush_counts = rush_names.map(_norm_name).value_counts()
        pass_counts = pass_names.map(_norm_name).value_counts()
        total_targets = int(target_counts.sum())
        total_rushes = int(rush_counts.sum())
        total_dropbacks = int(pass_counts.sum())

        names = set(target_counts.index) | set(rush_counts.index) | set(pass_counts.index)
        for player in names:
            if not player:
                continue
            targets = int(target_counts.get(player, 0))
            rushes = int(rush_counts.get(player, 0))
            dropbacks = int(pass_counts.get(player, 0))
            usage[(team, player)] = {
                "season": latest,
                "targets": targets,
                "target_share": targets / total_targets if total_targets else 0.0,
                "rushes": rushes,
                "rush_share": rushes / total_rushes if total_rushes else 0.0,
                "dropbacks": dropbacks,
                "dropback_share": dropbacks / total_dropbacks if total_dropbacks else 0.0,
            }

    return usage, {
        "status": "healthy",
        "source": "nflverse play-by-play",
        "source_url": PBP_SOURCE_URL,
        "season": latest,
        "players": len(usage),
    }


def _usage_sentence(position: str, row: dict[str, Any]) -> str | None:
    pos = str(position or "").upper()
    season = row.get("season")
    target_share = float(row.get("target_share") or 0)
    rush_share = float(row.get("rush_share") or 0)
    dropback_share = float(row.get("dropback_share") or 0)
    targets = int(row.get("targets") or 0)
    rushes = int(row.get("rushes") or 0)
    dropbacks = int(row.get("dropbacks") or 0)

    if pos == "QB" and dropbacks >= 75 and dropback_share >= .25:
        return f"In {season}, that player handled {dropback_share:.0%} of the team's recorded quarterback dropbacks ({dropbacks})."
    if pos in {"WR", "TE"} and targets >= 20 and target_share >= .08:
        sentence = f"In {season}, that role accounted for {target_share:.0%} of the team's recorded targets ({targets})."
        if rushes >= 10 and rush_share >= .05:
            sentence += f" It also carried {rush_share:.0%} of team rushes ({rushes})."
        return sentence
    if pos == "RB" and (rushes >= 25 or targets >= 15):
        parts = []
        if rushes >= 25 and rush_share >= .08:
            parts.append(f"{rush_share:.0%} of team rushes ({rushes})")
        if targets >= 15 and target_share >= .05:
            parts.append(f"{target_share:.0%} of team targets ({targets})")
        if parts:
            return f"In {season}, that role represented " + " and ".join(parts) + "."
    return None


def enrich_personnel_usage(
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    injuries: dict[str, list[dict[str, Any]]],
    pbp: pd.DataFrame | None,
    season: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    usage, usage_status = build_player_usage(pbp, season)
    if usage_status.get("status") != "healthy":
        return evidence, {**usage_status, "matched_injured_players": 0, "evidence_items_enriched": 0}

    matched_players = 0
    enriched = 0
    seen: set[tuple[str, str, str]] = set()
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items = evidence.get(gid, [])
        for raw_team in [str(game.get("away_team")), str(game.get("home_team"))]:
            team = _norm_team(raw_team)
            for injury in injuries.get(team, []):
                name = str(injury.get("name") or "")
                normalized = _norm_name(name)
                if not normalized:
                    continue
                usage_row = usage.get((team, normalized))
                if not usage_row:
                    continue
                sentence = _usage_sentence(str(injury.get("position") or ""), usage_row)
                if not sentence:
                    continue
                matched_players += 1
                key = (gid, team, normalized)
                if key in seen:
                    continue
                seen.add(key)

                target = None
                for item in items:
                    if str(item.get("category") or "").lower() != "personnel":
                        continue
                    if normalized and normalized in _norm_name(item.get("title")):
                        target = item
                        break
                if target is None:
                    continue

                summary = str(target.get("summary") or "").strip()
                if sentence not in summary:
                    target["summary"] = (summary + " " + sentence + " Usage is context for the role at risk, not an automatic forecast adjustment.").strip()
                source_name = str(target.get("source_name") or "NFL.com official injury report")
                if "nflverse" not in source_name.lower():
                    target["source_name"] = source_name + " + nflverse usage"
                metadata = dict(target.get("metadata") or {})
                metadata["usage_context"] = usage_row
                metadata["supporting_sources"] = list(dict.fromkeys([
                    target.get("source_url"), PBP_SOURCE_URL,
                ]))
                metadata["usage_as_of"] = utc_now()
                target["metadata"] = metadata
                enriched += 1

    return evidence, {
        "status": "healthy",
        "source": "NFL.com official injury report + nflverse PBP usage",
        "source_url": PBP_SOURCE_URL,
        "season": usage_status.get("season"),
        "matched_injured_players": matched_players,
        "evidence_items_enriched": enriched,
        "guardrail": "Prior usage clarifies role importance but is not converted into an unvalidated point-value injury adjustment.",
    }

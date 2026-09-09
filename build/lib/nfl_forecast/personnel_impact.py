from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

import pandas as pd

from nfl_forecast.context import PBP_SOURCE_URL, utc_now


SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _name_tokens(name: str | None) -> list[str]:
    tokens = [token.lower() for token in re.findall(r"[A-Za-z]+", str(name or ""))]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return tokens


def _person_key(name: str | None) -> str:
    """Map full NFL.com names and nflverse abbreviations onto a conservative key.

    nflverse play-by-play commonly stores names as `A.Receiver`, while the official
    injury report uses `Alpha Receiver`. First-initial + final surname token bridges
    those formats without general fuzzy matching.
    """
    tokens = _name_tokens(name)
    if len(tokens) < 2:
        return ""
    return f"{tokens[0][0]}{tokens[-1]}"


def _norm_name(name: str | None) -> str:
    return "".join(_name_tokens(name))


def _latest_complete_season(pbp: pd.DataFrame | None, season: int) -> int | None:
    if pbp is None or pbp.empty or "season" not in pbp.columns:
        return None
    years = pd.to_numeric(pbp["season"], errors="coerce").dropna().astype(int)
    years = years[years < int(season)]
    return int(years.max()) if len(years) else None


def _safe_counts(series: pd.Series) -> tuple[pd.Series, set[str]]:
    """Count abbreviated player keys and identify ambiguous team-local keys."""
    if series.empty:
        return pd.Series(dtype="int64"), set()
    frame = pd.DataFrame({"raw": series.astype(str)})
    frame["key"] = frame["raw"].map(_person_key)
    frame["raw_norm"] = frame["raw"].map(_norm_name)
    frame = frame[frame["key"].astype(bool)]
    if frame.empty:
        return pd.Series(dtype="int64"), set()
    raw_variants = frame.groupby("key")["raw_norm"].nunique()
    ambiguous = set(raw_variants[raw_variants > 1].index)
    counts = frame[~frame["key"].isin(ambiguous)]["key"].value_counts()
    return counts, ambiguous


def build_player_usage(
    pbp: pd.DataFrame | None,
    season: int,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    """Summarize prior-season opportunity shares for players on the injury report.

    This is explanatory context only. Opportunity share is intentionally not converted
    into a point-value injury adjustment. Ambiguous team-local abbreviated names are
    discarded instead of riskily attaching usage to the wrong player.
    """
    latest = _latest_complete_season(pbp, season)
    if latest is None or pbp is None:
        return {}, {"status": "degraded", "error": "No prior complete PBP season available"}

    p = pbp[pd.to_numeric(pbp.get("season"), errors="coerce").eq(latest)].copy()
    if p.empty or "posteam" not in p.columns:
        return {}, {"status": "degraded", "error": "Prior-season offensive PBP unavailable"}

    usage: dict[tuple[str, str], dict[str, Any]] = {}
    ambiguous_keys = 0
    for raw_team, group in p.groupby("posteam", dropna=True):
        team = _norm_team(raw_team)
        target_names = group.get("receiver_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)
        rush_names = group.get("rusher_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)
        pass_names = group.get("passer_player_name", pd.Series(index=group.index, dtype=object)).dropna().astype(str)

        target_counts, target_ambiguous = _safe_counts(target_names)
        rush_counts, rush_ambiguous = _safe_counts(rush_names)
        pass_counts, pass_ambiguous = _safe_counts(pass_names)
        ambiguous = target_ambiguous | rush_ambiguous | pass_ambiguous
        ambiguous_keys += len(ambiguous)
        total_targets = int(len(target_names))
        total_rushes = int(len(rush_names))
        total_dropbacks = int(len(pass_names))

        names = (set(target_counts.index) | set(rush_counts.index) | set(pass_counts.index)) - ambiguous
        for player in names:
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
        "ambiguous_player_keys_discarded": ambiguous_keys,
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
        return f"In {season}, he handled {dropback_share:.0%} of the team's recorded quarterback dropbacks ({dropbacks})."
    if pos in {"WR", "TE"} and targets >= 20 and target_share >= .08:
        sentence = f"In {season}, he accounted for {target_share:.0%} of the team's recorded targets ({targets})."
        if rushes >= 10 and rush_share >= .05:
            sentence += f" He also carried {rush_share:.0%} of team rushes ({rushes})."
        return sentence
    if pos == "RB" and (rushes >= 25 or targets >= 15):
        parts = []
        if rushes >= 25 and rush_share >= .08:
            parts.append(f"{rush_share:.0%} of team rushes ({rushes})")
        if targets >= 15 and target_share >= .05:
            parts.append(f"{target_share:.0%} of team targets ({targets})")
        if parts:
            return f"In {season}, he represented " + " and ".join(parts) + "."
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
    eligible_skill_injuries = 0
    seen: set[tuple[str, str, str]] = set()
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items = evidence.get(gid, [])
        for raw_team in [str(game.get("away_team")), str(game.get("home_team"))]:
            team = _norm_team(raw_team)
            for injury in injuries.get(team, []):
                name = str(injury.get("name") or "")
                person_key = _person_key(name)
                if not person_key:
                    continue
                if str(injury.get("position") or "").upper() in {"QB", "RB", "WR", "TE"}:
                    eligible_skill_injuries += 1
                usage_row = usage.get((team, person_key))
                if not usage_row:
                    continue
                sentence = _usage_sentence(str(injury.get("position") or ""), usage_row)
                if not sentence:
                    continue
                matched_players += 1
                key = (gid, team, person_key)
                if key in seen:
                    continue
                seen.add(key)

                target = None
                full_norm = _norm_name(name)
                for item in items:
                    if str(item.get("category") or "").lower() != "personnel":
                        continue
                    title = str(item.get("title") or "")
                    if full_norm and full_norm in _norm_name(title):
                        target = item
                        break
                    if person_key and _person_key(title.split("—", 1)[0].split(":", 1)[-1]) == person_key:
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
                metadata["person_key"] = person_key
                metadata["supporting_sources"] = list(dict.fromkeys(filter(None, [
                    target.get("source_url"), PBP_SOURCE_URL,
                ])))
                metadata["usage_as_of"] = utc_now()
                target["metadata"] = metadata
                enriched += 1

    return evidence, {
        "status": "healthy",
        "source": "NFL.com official injury report + nflverse PBP usage",
        "source_url": PBP_SOURCE_URL,
        "season": usage_status.get("season"),
        "eligible_skill_injuries": eligible_skill_injuries,
        "matched_injured_players": matched_players,
        "evidence_items_enriched": enriched,
        "ambiguous_player_keys_discarded": usage_status.get("ambiguous_player_keys_discarded", 0),
        "guardrail": "Prior usage clarifies role importance but is not converted into an unvalidated point-value injury adjustment; ambiguous abbreviated-name matches are discarded.",
    }

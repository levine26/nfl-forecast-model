from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import pandas as pd

from nfl_forecast.context import Evidence, FTN_SOURCE_URL, PBP_SOURCE_URL, utc_now
from nfl_forecast.staff_impact import (
    DEFENSE_METRICS,
    IMPACT_TEXT,
    OFFENSE_METRICS,
    _format_metric,
    _norm_name,
    _norm_team,
    _num,
    _weighted_profile,
    build_team_season_profiles,
)


def load_staff_lineage(season: int, config_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(config_path or f"config/staff_lineage_{season}.json")
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [row for row in rows if isinstance(row, dict) and int(row.get("season", -1)) == int(season)]


def _existing_staff_impact(items: list[dict[str, Any]], coordinator: str) -> bool:
    needle = _norm_name(coordinator)
    return any(
        (item.get("metadata") or {}).get("family") == "staff_impact"
        and _norm_name((item.get("metadata") or {}).get("coordinator")) == needle
        for item in items
    )


def _lineage_stints(entry: dict[str, Any]) -> list[dict[str, Any]]:
    team = _norm_team(str(entry.get("prior_team") or ""))
    years = [int(year) for year in entry.get("prior_seasons", []) if str(year).isdigit()]
    return [
        {
            "team": team,
            "season": year,
            "source_url": entry.get("source_url"),
            "matched_role": entry.get("prior_role"),
            "lineage": True,
        }
        for year in years if team
    ]


def add_staff_lineage_impact(
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    coaching_history: dict[str, dict[int, dict[str, Any]]],
    ftn: pd.DataFrame | None,
    pbp: pd.DataFrame | None,
    season: int,
    config_path: str | Path | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Use official-team lineage only when direct coordinator history is unavailable.

    This is intentionally a fallback. A first-time coordinator's prior team is not
    treated as a coordinator sample; the rates describe the football environment the
    coach came from, and the copy explicitly preserves that distinction.
    """
    entries = load_staff_lineage(season, config_path)
    if not entries:
        return evidence, {
            "status": "healthy",
            "entries": 0,
            "matched_current_staff": 0,
            "impacts_added": 0,
            "note": "No seasonal official-source lineage fallbacks configured.",
        }

    offense, defense, profile_status = build_team_season_profiles(ftn, pbp)
    if profile_status.get("status") != "healthy":
        return evidence, {
            "status": "degraded",
            "entries": len(entries),
            "matched_current_staff": 0,
            "impacts_added": 0,
            "profile_status": profile_status,
        }

    game_by_team: dict[str, tuple[str, str]] = {}
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        game_by_team[_norm_team(str(game.get("away_team")))] = (gid, "away")
        game_by_team[_norm_team(str(game.get("home_team")))] = (gid, "home")

    matched = 0
    impacts = 0
    skipped_direct = 0
    unresolved = []
    for entry in entries:
        team = _norm_team(str(entry.get("team") or ""))
        role = str(entry.get("role") or "")
        name = str(entry.get("name") or "")
        if team not in game_by_team or role not in {"off_coach", "def_coach"} or not name:
            continue
        current = coaching_history.get(team, {}).get(season, {})
        current_name = str(current.get(role) or "")
        if _norm_name(current_name) != _norm_name(name):
            unresolved.append({"team": team, "role": role, "name": name, "reason": "current staff did not match official lineage entry"})
            continue
        matched += 1
        gid, side = game_by_team[team]
        if _existing_staff_impact(evidence.get(gid, []), name):
            skipped_direct += 1
            continue

        profiles = offense if role == "off_coach" else defense
        metric_spec = OFFENSE_METRICS if role == "off_coach" else DEFENSE_METRICS
        baseline = profiles.get((team, season - 1), {})
        stints = _lineage_stints(entry)
        profile, sample_plays, used_stints = _weighted_profile(stints, profiles)
        if not baseline or not profile:
            unresolved.append({"team": team, "role": role, "name": name, "reason": "lineage team-season profile unavailable"})
            continue

        changes = []
        for metric, (label, threshold) in metric_spec.items():
            lineage_value = _num(profile.get(metric))
            old_value = _num(baseline.get(metric))
            if lineage_value is None or old_value is None:
                continue
            diff = lineage_value - old_value
            if abs(diff) >= threshold:
                changes.append((abs(diff) / threshold, metric, label, lineage_value, old_value, diff))
        changes.sort(reverse=True)

        role_label = "offensive coordinator" if role == "off_coach" else "defensive coordinator"
        prior_role = str(entry.get("prior_role") or "prior staff role")
        source_name = str(entry.get("source_name") or "Official team source")
        source_url = str(entry.get("source_url") or "")
        continuity = str(entry.get("continuity_note") or "").strip()
        prior_places = ", ".join(f"{stint['team']} {stint['season']}" for stint in stints[-3:])

        if changes:
            clauses = []
            implications = []
            for _, metric, label, lineage_value, old_value, diff in changes[:2]:
                direction = "more" if diff > 0 else "less"
                clauses.append(
                    f"{direction} {label} ({_format_metric(metric, lineage_value)} in {prior_places} versus {_format_metric(metric, old_value)} for {team} last season)"
                )
                implications.append(IMPACT_TEXT.get(metric, "That is a structural difference worth watching."))
            comparison = " The tracked differences worth watching are " + "; ".join(clauses) + ". " + " ".join(dict.fromkeys(implications))
        else:
            comparison = " Across the tracked tendency families, that prior-team environment does not create a large enough difference from last year's team baseline to justify calling this an overhaul before the new offense shows it on the field."

        summary = (
            (continuity + " " if continuity else "")
            + f"For context, {name}'s prior role was {prior_role}; the {prior_places} rates describe the environment he came from, not plays he personally called."
            + comparison
            + " This is lineage evidence for the matchup writeup only, not a numerical LevLine adjustment."
        ).strip()

        evidence.setdefault(gid, []).append(Evidence(
            category="coaching",
            title=f"What {name}'s coaching lineage suggests for {team}",
            summary=summary,
            strength="Moderate" if sample_plays >= 350 else "Weak",
            source_name=f"{source_name} + FTN/nflverse historical tendencies",
            source_url=source_url or FTN_SOURCE_URL,
            as_of=utc_now(),
            side=side,
            sample_size=sample_plays,
            relevance="Official current-staff lineage paired with prior-team tendency data; used only when direct coordinator history is unavailable",
            metadata={
                "family": "staff_impact",
                "role": role,
                "coordinator": name,
                "lineage_fallback": True,
                "prior_role": prior_role,
                "prior_stints": stints,
                "prior_profile": profile,
                "team_baseline": baseline,
                "supporting_sources": [source_url, FTN_SOURCE_URL, PBP_SOURCE_URL],
                "inference": "coaching lineage projection; not coordinator causality",
            },
        ).to_dict())
        impacts += 1

    return evidence, {
        "status": "healthy",
        "entries": len(entries),
        "matched_current_staff": matched,
        "direct_profiles_preferred": skipped_direct,
        "impacts_added": impacts,
        "unresolved": unresolved,
        "source": "Official club coaching reports + FTN charting + nflverse PBP",
        "guardrail": "First-time-coordinator lineage describes the prior football environment and never attributes team rates causally to a position coach or alters LevLine numerically.",
        "profile_status": profile_status,
    }

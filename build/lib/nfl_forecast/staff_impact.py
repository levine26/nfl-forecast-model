from __future__ import annotations

from collections import defaultdict
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from nfl_forecast.context import Evidence, FTN_SOURCE_URL, PBP_SOURCE_URL, utc_now


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _norm_name(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


def _num(value) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _bool_rate(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns or frame.empty:
        return None
    values = frame[column].fillna(False).astype(bool)
    return float(values.mean()) if len(values) else None


def build_team_season_profiles(
    ftn: pd.DataFrame | None,
    pbp: pd.DataFrame | None,
) -> tuple[dict[tuple[str, int], dict[str, float]], dict[tuple[str, int], dict[str, float]], dict[str, Any]]:
    """Build team-season tendency profiles used only for explanatory staff projections.

    These profiles are intentionally kept outside LevLine's numerical feature pipeline.
    They describe how a coordinator's prior teams tended to play; they do not assume
    the new team will copy those rates exactly.
    """
    if ftn is None or pbp is None or ftn.empty or pbp.empty:
        return {}, {}, {"status": "degraded", "error": "FTN or PBP unavailable"}

    f = ftn.copy()
    p = pbp.copy()
    game_col = "nflverse_game_id" if "nflverse_game_id" in f.columns else "game_id"
    play_col = "nflverse_play_id" if "nflverse_play_id" in f.columns else "play_id"
    required = {"game_id", "play_id", "season", "posteam", "defteam", "epa"}
    if not required.issubset(p.columns) or game_col not in f.columns or play_col not in f.columns:
        return {}, {}, {"status": "degraded", "error": "Required charting/PBP join fields unavailable"}

    keep = [
        c for c in [
            "game_id", "play_id", "season", "posteam", "defteam", "epa", "down",
            "pass_attempt", "rush_attempt",
        ] if c in p.columns
    ]
    p2 = p[keep].drop_duplicates(["game_id", "play_id"], keep="last")
    merged = f.merge(
        p2,
        left_on=[game_col, play_col],
        right_on=["game_id", "play_id"],
        how="left",
        suffixes=("", "_pbp"),
    )
    if "season" not in merged.columns and "season_pbp" in merged.columns:
        merged["season"] = merged["season_pbp"]
    merged["season"] = pd.to_numeric(merged.get("season"), errors="coerce")
    merged = merged[merged["season"].notna()].copy()
    if merged.empty:
        return {}, {}, {"status": "degraded", "error": "No charted seasons after merge"}

    merged["shotgun"] = merged.get("qb_location", pd.Series(index=merged.index, dtype=object)).astype(str).eq("S")
    merged["blitz"] = pd.to_numeric(merged.get("n_blitzers"), errors="coerce").fillna(0).gt(0)
    for source, target in [
        ("is_motion", "motion"), ("is_play_action", "play_action"),
        ("is_rpo", "rpo"), ("is_screen_pass", "screen"),
    ]:
        merged[target] = merged.get(source, pd.Series(False, index=merged.index)).fillna(False).astype(bool)

    offense: dict[tuple[str, int], dict[str, float]] = {}
    defense: dict[tuple[str, int], dict[str, float]] = {}

    for (season, team), group in merged.groupby(["season", "posteam"], dropna=True):
        team = _norm_team(team)
        year = int(season)
        row: dict[str, float] = {
            "plays": float(len(group)),
            "epa_per_play": float(pd.to_numeric(group.get("epa"), errors="coerce").mean()),
            "motion_rate": _bool_rate(group, "motion"),
            "play_action_rate": _bool_rate(group, "play_action"),
            "rpo_rate": _bool_rate(group, "rpo"),
            "screen_rate": _bool_rate(group, "screen"),
            "shotgun_rate": _bool_rate(group, "shotgun"),
        }
        if {"pass_attempt", "rush_attempt"}.issubset(group.columns):
            passes = pd.to_numeric(group["pass_attempt"], errors="coerce").fillna(0).gt(0)
            rushes = pd.to_numeric(group["rush_attempt"], errors="coerce").fillna(0).gt(0)
            plays = passes | rushes
            if plays.any():
                row["pass_rate"] = float(passes[plays].mean())
            if "down" in group.columns:
                early = plays & pd.to_numeric(group["down"], errors="coerce").isin([1, 2])
                if early.any():
                    row["early_down_pass_rate"] = float(passes[early].mean())
        offense[(team, year)] = {k: v for k, v in row.items() if v is not None and np.isfinite(v)}

    for (season, team), group in merged.groupby(["season", "defteam"], dropna=True):
        team = _norm_team(team)
        year = int(season)
        row = {
            "plays": float(len(group)),
            "blitz_rate": _bool_rate(group, "blitz"),
            "box_avg": _num(pd.to_numeric(group.get("n_defense_box"), errors="coerce").mean()),
            "epa_allowed": _num(pd.to_numeric(group.get("epa"), errors="coerce").mean()),
        }
        defense[(team, year)] = {k: v for k, v in row.items() if v is not None and np.isfinite(v)}

    seasons = sorted({year for _, year in offense} | {year for _, year in defense})
    return offense, defense, {
        "status": "healthy",
        "source": "FTN charting + nflverse PBP",
        "seasons": seasons,
        "team_seasons": len(set(offense) | set(defense)),
    }


def _prior_stints(
    coaches: dict[str, dict[int, dict[str, Any]]],
    coordinator: str,
    role: str,
    season: int,
) -> list[dict[str, Any]]:
    needle = _norm_name(coordinator)
    stints = []
    if not needle:
        return stints
    for raw_team, seasons in coaches.items():
        team = _norm_team(raw_team)
        for year, staff in seasons.items():
            if int(year) >= int(season):
                continue
            if _norm_name((staff or {}).get(role)) != needle:
                continue
            stints.append({
                "team": team,
                "season": int(year),
                "source_url": (staff or {}).get("source_url"),
            })
    return sorted(stints, key=lambda item: (item["season"], item["team"]))


def _weighted_profile(stints: list[dict[str, Any]], profiles: dict[tuple[str, int], dict[str, float]]) -> tuple[dict[str, float], int, int]:
    numerators: dict[str, float] = defaultdict(float)
    denominators: dict[str, float] = defaultdict(float)
    total_plays = 0
    used = 0
    for stint in stints:
        profile = profiles.get((stint["team"], int(stint["season"])))
        if not profile:
            continue
        weight = max(1.0, float(profile.get("plays", 1.0)))
        total_plays += int(weight)
        used += 1
        for key, value in profile.items():
            if key == "plays" or value is None:
                continue
            numerators[key] += float(value) * weight
            denominators[key] += weight
    out = {key: numerators[key] / denominators[key] for key in numerators if denominators[key] > 0}
    return out, total_plays, used


OFFENSE_METRICS = {
    "motion_rate": ("pre-snap motion", .04),
    "play_action_rate": ("play action", .04),
    "rpo_rate": ("RPO usage", .03),
    "screen_rate": ("screen usage", .025),
    "shotgun_rate": ("shotgun usage", .05),
    "pass_rate": ("overall pass rate", .045),
    "early_down_pass_rate": ("early-down pass rate", .045),
}
DEFENSE_METRICS = {
    "blitz_rate": ("blitz rate", .04),
    "box_avg": ("average box count", .35),
}

IMPACT_TEXT = {
    "motion_rate": "That can force coverage declarations earlier and create leverage before the snap.",
    "play_action_rate": "That would put more stress on linebackers and safeties before the throw.",
    "rpo_rate": "That changes the conflict rules for second-level defenders.",
    "screen_rate": "That can punish aggressive rush plans and manufacture easier touches.",
    "shotgun_rate": "That changes the protection and play-action picture defenses see most often.",
    "pass_rate": "That would change how aggressively defenses can play the run across the full game script.",
    "early_down_pass_rate": "That matters because first and second down dictate how often a defense gets obvious passing situations.",
    "blitz_rate": "That changes the quarterback's protection calls and hot-read burden.",
    "box_avg": "That can change the numbers an offense sees in the run game before the snap.",
}


def _format_metric(metric: str, value: float) -> str:
    if metric == "box_avg":
        return f"{value:.1f} defenders in the box"
    return f"{value:.0%}"


def _impact_evidence_for_team(
    team: str,
    side: str,
    season: int,
    coaches: dict[str, dict[int, dict[str, Any]]],
    offense_profiles: dict[tuple[str, int], dict[str, float]],
    defense_profiles: dict[tuple[str, int], dict[str, float]],
) -> tuple[list[Evidence], dict[str, int]]:
    team = _norm_team(team)
    current = coaches.get(team, {}).get(season, {})
    prior = coaches.get(team, {}).get(season - 1, {})
    if not current:
        return [], {"new_roles": 0, "profiled_roles": 0}

    items: list[Evidence] = []
    counts = {"new_roles": 0, "profiled_roles": 0}
    for role, role_label, profiles, metric_spec in [
        ("off_coach", "offensive coordinator", offense_profiles, OFFENSE_METRICS),
        ("def_coach", "defensive coordinator", defense_profiles, DEFENSE_METRICS),
    ]:
        coordinator = current.get(role)
        if not coordinator:
            continue
        if prior and _norm_name(prior.get(role)) == _norm_name(coordinator):
            continue
        counts["new_roles"] += 1
        stints = _prior_stints(coaches, coordinator, role, season)
        profile, sample_plays, used_stints = _weighted_profile(stints, profiles)
        baseline = profiles.get((team, season - 1), {})
        if not profile or not baseline:
            continue

        changes = []
        for metric, (label, threshold) in metric_spec.items():
            new_value = _num(profile.get(metric))
            old_value = _num(baseline.get(metric))
            if new_value is None or old_value is None:
                continue
            diff = new_value - old_value
            if abs(diff) < threshold:
                continue
            changes.append((abs(diff) / threshold, metric, label, new_value, old_value, diff))
        if not changes:
            continue
        changes.sort(reverse=True)
        top = changes[:2]
        counts["profiled_roles"] += 1

        prior_places = []
        for stint in stints:
            label = f"{stint['team']} {stint['season']}"
            if label not in prior_places and (stint["team"], stint["season"]) in profiles:
                prior_places.append(label)
        prior_label = ", ".join(prior_places[-3:]) if prior_places else "prior NFL stops"

        clauses = []
        impacts = []
        for _, metric, label, new_value, old_value, diff in top:
            direction = "more" if diff > 0 else "less"
            clauses.append(
                f"{direction} {label} ({_format_metric(metric, new_value)} across {prior_label} versus {_format_metric(metric, old_value)} for {team} last season)"
            )
            impacts.append(IMPACT_TEXT.get(metric, "That is a meaningful structural difference to watch."))

        summary = (
            f"{team}'s new {role_label}, {coordinator}, arrives with a verifiable prior-team tendency profile: "
            + "; ".join(clauses)
            + ". " + " ".join(dict.fromkeys(impacts))
            + " This is a historical tendency projection, not a claim that the new playbook will copy the old rates or an unvalidated numerical adjustment to LevLine."
        )
        strength = "Strong" if sample_plays >= 900 and used_stints >= 2 else "Moderate" if sample_plays >= 350 else "Weak"
        items.append(Evidence(
            category="coaching",
            title=f"What {coordinator} could change in {team}",
            summary=summary,
            strength=strength,
            source_name="Staff records + FTN/nflverse historical tendencies",
            source_url=current.get("source_url") or FTN_SOURCE_URL,
            as_of=utc_now(),
            side=side,
            sample_size=sample_plays,
            relevance="New coordinator's prior NFL tendency profile compared with the new team's most recent complete-season baseline",
            metadata={
                "family": "staff_impact",
                "role": role,
                "coordinator": coordinator,
                "prior_stints": stints,
                "prior_profile": profile,
                "team_baseline": baseline,
                "supporting_sources": [current.get("source_url"), FTN_SOURCE_URL, PBP_SOURCE_URL],
                "inference": "historical tendency projection",
            },
        ))
    return items, counts


def add_staff_impact(
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    coaching_history: dict[str, dict[int, dict[str, Any]]],
    ftn: pd.DataFrame | None,
    pbp: pd.DataFrame | None,
    season: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    offense, defense, profile_status = build_team_season_profiles(ftn, pbp)
    if profile_status.get("status") != "healthy":
        return evidence, {"status": "degraded", **profile_status, "impacts_added": 0}

    new_roles = 0
    profiled_roles = 0
    impacts_added = 0
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        additions: list[Evidence] = []
        for raw_team, side in [(str(game.get("away_team")), "away"), (str(game.get("home_team")), "home")]:
            team_items, counts = _impact_evidence_for_team(
                raw_team, side, season, coaching_history, offense, defense,
            )
            additions.extend(team_items)
            new_roles += counts["new_roles"]
            profiled_roles += counts["profiled_roles"]
        if additions:
            evidence.setdefault(gid, []).extend(item.to_dict() for item in additions)
            impacts_added += len(additions)

    return evidence, {
        "status": "healthy",
        "source": "Wikipedia rendered staff records + FTN charting + nflverse PBP",
        "new_coordinator_roles": new_roles,
        "roles_with_verified_prior_tendency_profile": profiled_roles,
        "impacts_added": impacts_added,
        "guardrail": "Coordinator impact is a historical tendency projection for explanation only; it does not alter LevLine unless separately validated out of sample.",
        "profile_status": profile_status,
    }

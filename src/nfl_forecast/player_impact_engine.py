from __future__ import annotations

"""Research-only expected-lineup impact and explainability engine.

This module does not alter game probabilities.  It converts explicitly supplied pregame
player value, role, availability, replacement, and uncertainty inputs into modeled lineup
and unit context.  Availability is never inferred from actual participation or snaps.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

ENGINE_VERSION = "player-impact-explainability-v1"
UNITS = ("qb", "skill", "ol", "pass_rush", "run_defense", "secondary")
AVAILABILITY_SOURCE_STATES = ("qualified", "prospective_unqualified", "unknown")

REQUIRED_PLAYER_COLUMNS = {
    "game_id",
    "season",
    "week",
    "team",
    "player_id",
    "player_name",
    "unit",
    "role",
    "modeled_player_value",
    "replacement_value",
    "expected_role_share",
    "availability_probability",
    "value_uncertainty",
    "availability_uncertainty",
    "feature_data_horizon",
    "availability_source_status",
}

PROHIBITED_RETROSPECTIVE_COLUMNS = {
    "actual_current_game_snaps",
    "actual_snap_count",
    "actual_snap_share",
    "actual_participation",
    "final_inactive_learned_post_kickoff",
    "postgame_player_value",
    "home_win",
    "actual_home_score",
    "actual_away_score",
}


@dataclass(frozen=True)
class PlayerImpactBuild:
    player_impacts: pd.DataFrame
    unit_impacts: pd.DataFrame
    team_impacts: pd.DataFrame
    audit: dict


def _number(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _require_columns(frame: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing required fields: {sorted(missing)}")


def validate_expected_lineup_inputs(frame: pd.DataFrame) -> None:
    _require_columns(frame, REQUIRED_PLAYER_COLUMNS, "expected lineup")
    retrospective = PROHIBITED_RETROSPECTIVE_COLUMNS.intersection(frame.columns)
    if retrospective:
        raise ValueError(
            "Expected-lineup engine refuses retrospective/current-game outcome fields: "
            f"{sorted(retrospective)}"
        )
    if frame.empty:
        raise ValueError("Expected-lineup engine requires at least one player row")

    stable_id = frame.player_id.astype("string").fillna("").str.strip()
    if stable_id.eq("").any() or stable_id.str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Stable player_id is required; ambiguous identity fails closed")
    if frame.duplicated(["game_id", "team", "player_id", "unit", "role"]).any():
        raise ValueError("Duplicate expected-lineup player identity")

    units = set(frame.unit.astype(str).str.lower())
    invalid_units = units - set(UNITS)
    if invalid_units:
        raise ValueError(f"Unregistered player-impact units: {sorted(invalid_units)}")

    source_states = set(frame.availability_source_status.astype(str))
    invalid_sources = source_states - set(AVAILABILITY_SOURCE_STATES)
    if invalid_sources:
        raise ValueError(f"Invalid availability source status: {sorted(invalid_sources)}")

    for column in ("modeled_player_value", "replacement_value", "expected_role_share", "availability_probability", "value_uncertainty", "availability_uncertainty"):
        values = _number(frame, column)
        if values.isna().any():
            raise ValueError(f"Expected-lineup numeric field is incomplete: {column}")
    for column in ("expected_role_share", "availability_probability"):
        values = _number(frame, column)
        if values.lt(0).any() or values.gt(1).any():
            raise ValueError(f"{column} must be within [0, 1]")
    for column in ("value_uncertainty", "availability_uncertainty"):
        if _number(frame, column).lt(0).any():
            raise ValueError(f"{column} must be non-negative")


def build_player_impacts(expected_lineup: pd.DataFrame) -> pd.DataFrame:
    """Estimate expected value relative to explicit replacement, with uncertainty.

    The scale is a LevLine research/explainability scale.  It is not an official NFL
    statistic and is not interpreted as a direct change in win probability.
    """
    validate_expected_lineup_inputs(expected_lineup)
    out = expected_lineup.copy()
    out["unit"] = out.unit.astype(str).str.lower()
    value = _number(out, "modeled_player_value")
    replacement = _number(out, "replacement_value")
    role_share = _number(out, "expected_role_share")
    p_active = _number(out, "availability_probability")
    value_uncertainty = _number(out, "value_uncertainty")
    availability_uncertainty = _number(out, "availability_uncertainty")

    gap = value - replacement
    positive_gap = np.maximum(gap, 0.0)
    out["value_over_replacement"] = gap
    out["expected_available_role_share"] = p_active * role_share
    out["full_availability_value_over_replacement"] = role_share * gap
    out["expected_value_over_replacement"] = p_active * role_share * gap
    out["expected_lineup_value_lost"] = (1.0 - p_active) * role_share * positive_gap
    out["expected_lineup_value_gained"] = p_active * role_share * positive_gap
    out["expected_replacement_burden"] = (1.0 - p_active) * role_share * positive_gap
    out["impact_uncertainty"] = np.sqrt(
        (p_active * role_share * value_uncertainty) ** 2
        + (role_share * gap * availability_uncertainty) ** 2
    )
    out["engine_version"] = ENGINE_VERSION
    out["research_only"] = True
    out["probability_feature_authorized"] = False
    return out


def build_unit_impacts(player_impacts: pd.DataFrame) -> pd.DataFrame:
    _require_columns(
        player_impacts,
        {
            "game_id", "season", "week", "team", "unit", "player_id",
            "expected_role_share", "availability_probability", "replacement_value",
            "expected_value_over_replacement", "expected_lineup_value_lost",
            "expected_lineup_value_gained", "expected_replacement_burden",
            "impact_uncertainty", "availability_source_status",
        },
        "player impacts",
    )
    work = player_impacts.copy()
    work["uncertainty_sq"] = _number(work, "impact_uncertainty") ** 2
    work["replacement_weight"] = _number(work, "expected_role_share")
    work["weighted_replacement_value"] = (
        _number(work, "replacement_value") * work.replacement_weight
    )
    work["availability_weight"] = _number(work, "expected_role_share")
    work["weighted_availability"] = (
        _number(work, "availability_probability") * work.availability_weight
    )
    work["qualified_availability"] = work.availability_source_status.eq("qualified")

    rows = []
    keys = ["game_id", "season", "week", "team", "unit"]
    for key, part in work.groupby(keys, sort=True, dropna=False):
        role_weight = float(part.replacement_weight.sum())
        availability_weight = float(part.availability_weight.sum())
        rows.append({
            **dict(zip(keys, key)),
            "players": int(part.player_id.nunique()),
            "expected_value_over_replacement": float(part.expected_value_over_replacement.sum()),
            "expected_lineup_value_lost": float(part.expected_lineup_value_lost.sum()),
            "expected_lineup_value_gained": float(part.expected_lineup_value_gained.sum()),
            "expected_replacement_burden": float(part.expected_replacement_burden.sum()),
            "replacement_quality": (
                float(part.weighted_replacement_value.sum() / role_weight)
                if role_weight > 0 else np.nan
            ),
            "expected_availability": (
                float(part.weighted_availability.sum() / availability_weight)
                if availability_weight > 0 else np.nan
            ),
            "impact_uncertainty": float(np.sqrt(part.uncertainty_sq.sum())),
            "qualified_availability_rows": int(part.qualified_availability.sum()),
            "unqualified_or_unknown_availability_rows": int((~part.qualified_availability).sum()),
            "engine_version": ENGINE_VERSION,
            "research_only": True,
            "probability_feature_authorized": False,
        })
    return pd.DataFrame(rows)


def build_team_impacts(unit_impacts: pd.DataFrame) -> pd.DataFrame:
    _require_columns(
        unit_impacts,
        {
            "game_id", "season", "week", "team", "unit",
            "expected_value_over_replacement", "expected_lineup_value_lost",
            "expected_lineup_value_gained", "expected_replacement_burden",
            "impact_uncertainty", "unqualified_or_unknown_availability_rows",
        },
        "unit impacts",
    )
    work = unit_impacts.copy()
    work["uncertainty_sq"] = _number(work, "impact_uncertainty") ** 2
    rows = []
    keys = ["game_id", "season", "week", "team"]
    for key, part in work.groupby(keys, sort=True, dropna=False):
        unit_map = part.set_index("unit")

        def unit_value(unit: str, column: str = "expected_value_over_replacement") -> float:
            if unit not in unit_map.index:
                return 0.0
            value = unit_map.loc[unit, column]
            if isinstance(value, pd.Series):
                value = value.sum()
            return float(value)

        rows.append({
            **dict(zip(keys, key)),
            "expected_lineup_value_over_replacement": float(part.expected_value_over_replacement.sum()),
            "expected_lineup_value_lost": float(part.expected_lineup_value_lost.sum()),
            "expected_lineup_value_gained": float(part.expected_lineup_value_gained.sum()),
            "expected_replacement_burden": float(part.expected_replacement_burden.sum()),
            "lineup_impact_uncertainty": float(np.sqrt(part.uncertainty_sq.sum())),
            "qb_impact": unit_value("qb"),
            "skill_impact": unit_value("skill"),
            "ol_impact": unit_value("ol"),
            "pass_rush_impact": unit_value("pass_rush"),
            "run_defense_impact": unit_value("run_defense"),
            "secondary_impact": unit_value("secondary"),
            "unqualified_or_unknown_availability_rows": int(part.unqualified_or_unknown_availability_rows.sum()),
            "engine_version": ENGINE_VERSION,
            "research_only": True,
            "probability_feature_authorized": False,
        })
    return pd.DataFrame(rows)


def build_game_matchup_context(
    schedules: pd.DataFrame,
    team_impacts: pd.DataFrame,
) -> pd.DataFrame:
    """Build signed matchup-risk diagnostics without converting them to win probability."""
    _require_columns(schedules, {"game_id", "home_team", "away_team"}, "schedules")
    _require_columns(
        team_impacts,
        {
            "game_id", "team", "qb_impact", "skill_impact", "ol_impact",
            "pass_rush_impact", "run_defense_impact", "secondary_impact",
            "lineup_impact_uncertainty", "expected_lineup_value_lost",
        },
        "team impacts",
    )
    home = team_impacts.add_prefix("home_").rename(columns={"home_game_id": "game_id", "home_team": "home_team"})
    away = team_impacts.add_prefix("away_").rename(columns={"away_game_id": "game_id", "away_team": "away_team"})
    games = schedules.copy()
    games = games.merge(home, on=["game_id", "home_team"], how="left", validate="one_to_one")
    games = games.merge(away, on=["game_id", "away_team"], how="left", validate="one_to_one")

    for column in (
        "home_qb_impact", "home_skill_impact", "home_ol_impact", "home_pass_rush_impact",
        "home_run_defense_impact", "home_secondary_impact", "away_qb_impact",
        "away_skill_impact", "away_ol_impact", "away_pass_rush_impact",
        "away_run_defense_impact", "away_secondary_impact",
    ):
        games[column] = pd.to_numeric(games[column], errors="coerce")

    games["home_pass_protection_risk"] = games.away_pass_rush_impact - games.home_ol_impact
    games["away_pass_protection_risk"] = games.home_pass_rush_impact - games.away_ol_impact
    games["home_receiving_matchup_risk"] = games.away_secondary_impact - games.home_skill_impact
    games["away_receiving_matchup_risk"] = games.home_secondary_impact - games.away_skill_impact
    games["home_run_matchup_risk"] = games.away_run_defense_impact - games.home_skill_impact
    games["away_run_matchup_risk"] = games.home_run_defense_impact - games.away_skill_impact
    games["research_only"] = True
    games["probability_feature_authorized"] = False
    games["engine_version"] = ENGINE_VERSION
    return games


def build_expected_lineup_impacts(expected_lineup: pd.DataFrame) -> PlayerImpactBuild:
    players = build_player_impacts(expected_lineup)
    units = build_unit_impacts(players)
    teams = build_team_impacts(units)
    audit = {
        "engine_version": ENGINE_VERSION,
        "research_only": True,
        "probability_feature_authorized": False,
        "player_rows": int(len(players)),
        "unit_rows": int(len(units)),
        "team_rows": int(len(teams)),
        "stable_player_ids": int(players.player_id.nunique()),
        "qualified_availability_rows": int(players.availability_source_status.eq("qualified").sum()),
        "prospective_unqualified_availability_rows": int(players.availability_source_status.eq("prospective_unqualified").sum()),
        "unknown_availability_rows": int(players.availability_source_status.eq("unknown").sum()),
        "retrospective_snap_imputation_used": 0,
        "outcomes_used": 0,
    }
    return PlayerImpactBuild(players, units, teams, audit)

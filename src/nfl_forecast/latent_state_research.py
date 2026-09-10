from __future__ import annotations

"""Research-only dynamic latent team-strength state for F-LS-01.

For every game in week W, the attached latent state is frozen after week W-1. The
recursion is updated only in a batch after the whole week, so same-week ordering cannot
leak information. This module is not imported by the production forecast path.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

STATE_GAIN = 0.20
HALF_GAIN = STATE_GAIN / 2.0
OFFSEASON_CARRY = 0.50
HISTORICAL_END = 2025
LATENT_FEATURES = (
    "latent_diff_offense_state",
    "latent_home_defensive_advantage",
)


@dataclass(frozen=True)
class LatentStateBuild:
    pregame_state: pd.DataFrame
    terminal_state: pd.DataFrame
    audit: dict[str, Any]


def _opponent(frame: pd.DataFrame) -> pd.Series:
    is_home = frame["team"].eq(frame["home_team"])
    return pd.Series(
        np.where(is_home, frame["away_team"], frame["home_team"]),
        index=frame.index,
        dtype="object",
    )


def _center(state: dict[str, float], teams: list[str]) -> float:
    if not teams:
        return 0.0
    mean = float(np.mean([float(state.get(team, 0.0)) for team in teams]))
    for team in teams:
        state[team] = float(state.get(team, 0.0) - mean)
    return mean


def build_latent_team_state(team_games: pd.DataFrame) -> LatentStateBuild:
    """Build weekly-frozen offense and defense-weakness latent states.

    Expected neutral EPA for team T against opponent O is
    ``offense_state[T] + defense_weakness_state[O]``. A completed observation updates
    each side by HALF_GAIN times the residual. States are mean-centered after each
    weekly batch for identifiability, and the next season starts from 50% of the prior
    terminal state for returning teams.
    """

    required = {
        "game_id",
        "season",
        "week",
        "team",
        "home_team",
        "away_team",
        "neutral_epa",
    }
    missing = required - set(team_games.columns)
    if missing:
        raise ValueError(f"team_games missing latent-state fields: {sorted(missing)}")

    work = team_games.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["neutral_epa"] = pd.to_numeric(work["neutral_epa"], errors="coerce")
    work = work[
        work["season"].notna()
        & work["week"].notna()
        & work["team"].notna()
        & work["game_id"].notna()
        & work["neutral_epa"].notna()
    ].copy()
    if work.empty:
        raise ValueError("No completed team-game neutral EPA rows for latent-state research")
    work["season"] = work["season"].astype(int)
    work["week"] = work["week"].astype(int)
    if int(work["season"].max()) > HISTORICAL_END:
        raise ValueError("F-LS-01 may not consume outcomes after 2025")

    work["team"] = work["team"].astype(str)
    work["home_team"] = work["home_team"].astype(str)
    work["away_team"] = work["away_team"].astype(str)
    work["opponent"] = _opponent(work).astype(str)
    work = work.sort_values(["season", "week", "game_id", "team"]).reset_index(drop=True)

    prior_terminal_offense: dict[str, float] = {}
    prior_terminal_defense: dict[str, float] = {}
    pregame_records: list[dict[str, Any]] = []
    terminal_records: list[dict[str, Any]] = []
    weekly_center_rows: list[dict[str, Any]] = []

    for season in sorted(work["season"].unique()):
        season_rows = work[work["season"].eq(season)]
        teams = sorted(set(season_rows["team"]) | set(season_rows["opponent"]))
        offense = {
            team: OFFSEASON_CARRY * float(prior_terminal_offense.get(team, 0.0))
            for team in teams
        }
        defense = {
            team: OFFSEASON_CARRY * float(prior_terminal_defense.get(team, 0.0))
            for team in teams
        }
        # Previous terminal states are already centered, but returning subsets can have
        # non-zero mean; re-center before Week 1 so only relative strength carries over.
        _center(offense, teams)
        _center(defense, teams)

        for week in sorted(season_rows["week"].unique()):
            week_rows = season_rows[season_rows["week"].eq(week)].copy()
            offense_delta = {team: 0.0 for team in teams}
            defense_delta = {team: 0.0 for team in teams}

            for row in week_rows.itertuples(index=False):
                team = str(row.team)
                opponent = str(row.opponent)
                pregame_records.append(
                    {
                        "game_id": str(row.game_id),
                        "season": int(season),
                        "week": int(week),
                        "team": team,
                        "opponent": opponent,
                        "latent_offense_state": float(offense.get(team, 0.0)),
                        "latent_defense_weakness_state": float(defense.get(team, 0.0)),
                    }
                )
                expected = float(offense.get(team, 0.0) + defense.get(opponent, 0.0))
                residual = float(row.neutral_epa - expected)
                offense_delta[team] = float(offense_delta.get(team, 0.0) + HALF_GAIN * residual)
                defense_delta[opponent] = float(
                    defense_delta.get(opponent, 0.0) + HALF_GAIN * residual
                )

            # Batch update after every row in the week has been scored from the same
            # frozen state. This is the core anti-leakage/order-invariance contract.
            for team in teams:
                offense[team] = float(offense.get(team, 0.0) + offense_delta.get(team, 0.0))
                defense[team] = float(defense.get(team, 0.0) + defense_delta.get(team, 0.0))
            offense_mean_removed = _center(offense, teams)
            defense_mean_removed = _center(defense, teams)
            weekly_center_rows.append(
                {
                    "season": int(season),
                    "week": int(week),
                    "offense_mean_removed": offense_mean_removed,
                    "defense_mean_removed": defense_mean_removed,
                    "post_center_offense_mean": float(np.mean([offense[t] for t in teams])),
                    "post_center_defense_mean": float(np.mean([defense[t] for t in teams])),
                }
            )

        for team in teams:
            terminal_records.append(
                {
                    "season": int(season),
                    "team": team,
                    "latent_offense_state": float(offense[team]),
                    "latent_defense_weakness_state": float(defense[team]),
                }
            )
        prior_terminal_offense = offense.copy()
        prior_terminal_defense = defense.copy()

    pregame = pd.DataFrame(pregame_records).sort_values(
        ["season", "week", "game_id", "team"]
    ).reset_index(drop=True)
    terminal = pd.DataFrame(terminal_records).sort_values(["season", "team"]).reset_index(drop=True)
    center = pd.DataFrame(weekly_center_rows)
    max_center_error = 0.0
    if not center.empty:
        max_center_error = float(
            max(
                center["post_center_offense_mean"].abs().max(),
                center["post_center_defense_mean"].abs().max(),
            )
        )
    audit = {
        "state_gain": STATE_GAIN,
        "half_gain_per_component": HALF_GAIN,
        "offseason_carry": OFFSEASON_CARRY,
        "pregame_rows": int(len(pregame)),
        "terminal_rows": int(len(terminal)),
        "seasons": sorted(int(s) for s in work["season"].unique()),
        "weekly_batches": int(len(center)),
        "max_abs_post_center_mean": max_center_error,
        "same_week_updates_used_for_same_week_features": 0,
        "2026_outcomes_used": 0,
        "hyperparameter_search_performed": False,
    }
    return LatentStateBuild(pregame_state=pregame, terminal_state=terminal, audit=audit)


def build_game_latent_features(
    games: pd.DataFrame,
    pregame_state: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the fixed two-feature F-LS-01 vector to game rows."""
    required = {"game_id", "home_team", "away_team"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"games missing latent matchup keys: {sorted(missing)}")
    state_required = {
        "game_id",
        "team",
        "latent_offense_state",
        "latent_defense_weakness_state",
    }
    state_missing = state_required - set(pregame_state.columns)
    if state_missing:
        raise ValueError(f"pregame state missing fields: {sorted(state_missing)}")

    out = games.copy()
    state = pregame_state[list(state_required)].drop_duplicates(["game_id", "team"], keep="last")
    home = state.rename(
        columns={
            "team": "home_team",
            "latent_offense_state": "home_latent_offense_state",
            "latent_defense_weakness_state": "home_latent_defense_weakness_state",
        }
    )
    away = state.rename(
        columns={
            "team": "away_team",
            "latent_offense_state": "away_latent_offense_state",
            "latent_defense_weakness_state": "away_latent_defense_weakness_state",
        }
    )
    out = out.merge(home, on=["game_id", "home_team"], how="left", validate="one_to_one")
    out = out.merge(away, on=["game_id", "away_team"], how="left", validate="one_to_one")
    out["latent_diff_offense_state"] = (
        pd.to_numeric(out["home_latent_offense_state"], errors="coerce")
        - pd.to_numeric(out["away_latent_offense_state"], errors="coerce")
    )
    out["latent_home_defensive_advantage"] = (
        pd.to_numeric(out["away_latent_defense_weakness_state"], errors="coerce")
        - pd.to_numeric(out["home_latent_defense_weakness_state"], errors="coerce")
    )
    return out


def latent_feature_columns(frame: pd.DataFrame) -> list[str]:
    columns = [column for column in LATENT_FEATURES if column in frame.columns]
    if len(columns) != len(LATENT_FEATURES):
        raise RuntimeError(f"Expected exactly two F-LS-01 features; found {columns}")
    return columns

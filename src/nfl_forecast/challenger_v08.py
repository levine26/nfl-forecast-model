from __future__ import annotations

"""Research-only quarterback starter quality/continuity features.

The schedule's home/away QB identifiers provide the starter identity available for the
pregame matchup. Quarterback performance is built only from completed prior starts:
all rolling quality, experience, and continuity variables are shifted before the current
row. Unplayed schedule rows never increment history, so future listed starters cannot
manufacture experience.

Production forecasting does not import this module.
"""

import math

import numpy as np
import pandas as pd

QB_ALPHA = 0.20


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def aggregate_qb_games(pbp: pd.DataFrame) -> pd.DataFrame:
    """One row per quarterback/team/game using dropback EPA and success.

    Pass attempts and sacks define the stable dropback sample. Relief appearances are
    retained here, but the starter scaffold later selects only the scheduled starter's
    performance for starter-history features.
    """
    required = {"game_id", "season", "week", "posteam", "epa", "passer_player_id"}
    missing = required - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing quarterback columns: {sorted(missing)}")

    plays = pbp.copy()
    if "season_type" in plays.columns:
        plays = plays[plays.season_type.eq("REG")].copy()
    pass_attempt = _numeric(plays, "pass_attempt").fillna(0).eq(1)
    sack = _numeric(plays, "sack").fillna(0).eq(1)
    dropback = pass_attempt | sack
    plays = plays[
        dropback
        & plays.posteam.notna()
        & plays.passer_player_id.notna()
        & pd.to_numeric(plays.epa, errors="coerce").notna()
    ].copy()
    plays["epa_num"] = pd.to_numeric(plays.epa, errors="coerce")
    if "success" in plays.columns:
        plays["success_num"] = pd.to_numeric(plays.success, errors="coerce")
    else:
        plays["success_num"] = plays.epa_num.gt(0).astype(float)
    if "cpoe" in plays.columns:
        plays["cpoe_num"] = pd.to_numeric(plays.cpoe, errors="coerce")
    else:
        plays["cpoe_num"] = np.nan

    name_col = "passer_player_name" if "passer_player_name" in plays.columns else None
    group_cols = ["game_id", "season", "week", "posteam", "passer_player_id"]
    if name_col:
        group_cols.append(name_col)
    grouped = plays.groupby(group_cols, observed=True, dropna=False)
    out = grouped.agg(
        qb_dropbacks=("epa_num", "size"),
        qb_epa_per_dropback=("epa_num", "mean"),
        qb_success_rate=("success_num", "mean"),
        qb_cpoe=("cpoe_num", "mean"),
    ).reset_index()
    out = out.rename(columns={"posteam": "team", "passer_player_id": "qb_id"})
    if name_col:
        out = out.rename(columns={name_col: "qb_name"})
    else:
        out["qb_name"] = pd.NA
    return out


def build_starter_scaffold(schedules: pd.DataFrame) -> pd.DataFrame:
    """Two rows per regular-season game: scheduled home and away starter."""
    required = {"game_id", "season", "week", "gameday", "home_team", "away_team"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"Schedules missing quarterback scaffold columns: {sorted(missing)}")
    if not {"home_qb_id", "away_qb_id"}.issubset(schedules.columns):
        raise ValueError("Schedules do not provide home_qb_id/away_qb_id")

    sched = schedules.copy()
    if "game_type" in sched.columns:
        sched = sched[sched.game_type.eq("REG")].copy()

    common = [c for c in ["game_id", "season", "week", "gameday", "gametime", "home_score", "away_score"] if c in sched.columns]
    home = sched[common + ["home_team", "home_qb_id"] + (["home_qb_name"] if "home_qb_name" in sched.columns else [])].copy()
    home = home.rename(columns={"home_team": "team", "home_qb_id": "qb_id", "home_qb_name": "qb_name"})
    home["is_home"] = 1.0

    away = sched[common + ["away_team", "away_qb_id"] + (["away_qb_name"] if "away_qb_name" in sched.columns else [])].copy()
    away = away.rename(columns={"away_team": "team", "away_qb_id": "qb_id", "away_qb_name": "qb_name"})
    away["is_home"] = 0.0

    starters = pd.concat([home, away], ignore_index=True)
    if "qb_name" not in starters.columns:
        starters["qb_name"] = pd.NA
    starters["completed"] = False
    if {"home_score", "away_score"}.issubset(starters.columns):
        starters["completed"] = starters.home_score.notna() & starters.away_score.notna()
    return starters


def _shifted_ewma(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame.groupby("qb_id", sort=False)[column].transform(
        lambda s: s.shift(1).ewm(alpha=QB_ALPHA, adjust=False, min_periods=1).mean()
    )


def _prior_completed_count(frame: pd.DataFrame) -> pd.Series:
    return frame.groupby("qb_id", sort=False)["completed"].transform(
        lambda s: s.shift(1).fillna(False).astype(int).cumsum()
    )


def _prior_dropbacks(frame: pd.DataFrame) -> pd.Series:
    return frame.groupby("qb_id", sort=False)["qb_dropbacks"].transform(
        lambda s: pd.to_numeric(s, errors="coerce").shift(1).fillna(0.0).cumsum()
    )


def _team_continuity_prior(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Prior consecutive completed starts and prior-starter change flag."""
    continuity = pd.Series(0.0, index=frame.index, dtype=float)
    changed = pd.Series(0.0, index=frame.index, dtype=float)
    for _, group in frame.groupby("team", sort=False):
        last_qb = None
        streak = 0
        for idx, row in group.iterrows():
            qb = row.get("qb_id")
            known = pd.notna(qb)
            same = known and last_qb is not None and str(qb) == str(last_qb)
            continuity.at[idx] = float(streak if same else 0)
            changed.at[idx] = float(last_qb is not None and known and not same)
            if bool(row.get("completed", False)) and known:
                if same:
                    streak += 1
                else:
                    last_qb = qb
                    streak = 1
    return continuity, changed


def build_qb_starter_team_features(pbp: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    """Pregame QB features on the team/game starter scaffold."""
    qb_games = aggregate_qb_games(pbp)
    starters = build_starter_scaffold(schedules)

    # String normalization avoids schedule/PBP dtype mismatches without inventing IDs.
    starters["qb_key"] = starters.qb_id.where(starters.qb_id.notna(), pd.NA).astype("string")
    qb_games["qb_key"] = qb_games.qb_id.where(qb_games.qb_id.notna(), pd.NA).astype("string")
    metrics = qb_games[[
        "game_id", "team", "qb_key", "qb_dropbacks", "qb_epa_per_dropback",
        "qb_success_rate", "qb_cpoe",
    ]].copy()
    starters = starters.merge(
        metrics,
        on=["game_id", "team", "qb_key"],
        how="left",
        validate="one_to_one",
    )
    starters = starters.sort_values(
        ["qb_key", "season", "week", "gameday", "gametime", "game_id"],
        na_position="last",
    ).copy()

    # Grouping by qb_key: unknown starters intentionally remain missing-quality rows.
    starters["qb_id"] = starters["qb_key"]
    starters["qb_epa_ewma"] = _shifted_ewma(starters, "qb_epa_per_dropback")
    starters["qb_success_ewma"] = _shifted_ewma(starters, "qb_success_rate")
    starters["qb_cpoe_ewma"] = _shifted_ewma(starters, "qb_cpoe")
    starters["qb_prior_starts"] = _prior_completed_count(starters)
    starters["qb_prior_dropbacks"] = _prior_dropbacks(starters)
    starters["qb_log_prior_starts"] = np.log1p(starters.qb_prior_starts.astype(float))
    starters["qb_log_prior_dropbacks"] = np.log1p(starters.qb_prior_dropbacks.astype(float))
    starters["qb_quality_missing"] = starters.qb_epa_ewma.isna().astype(float)
    starters["qb_new_starter"] = starters.qb_prior_starts.eq(0).astype(float)

    # Team continuity must be calculated in team chronology, not QB chronology.
    team_order = starters.sort_values(
        ["team", "season", "week", "gameday", "gametime", "game_id"],
        na_position="last",
    ).copy()
    continuity, changed = _team_continuity_prior(team_order)
    team_order["qb_continuity_starts_prior"] = continuity
    team_order["qb_starter_changed"] = changed

    keep = [
        "game_id", "team", "qb_id", "qb_name", "is_home",
        "qb_epa_ewma", "qb_success_ewma", "qb_cpoe_ewma",
        "qb_log_prior_starts", "qb_log_prior_dropbacks",
        "qb_continuity_starts_prior", "qb_starter_changed",
        "qb_quality_missing", "qb_new_starter",
    ]
    return team_order[keep].copy()


def build_qb_matchup_features(
    pbp: pd.DataFrame,
    schedules: pd.DataFrame,
    base_games: pd.DataFrame,
) -> pd.DataFrame:
    """Append research-only QB starter features to a game-level frame."""
    team = build_qb_starter_team_features(pbp, schedules)
    numeric = [
        "qb_epa_ewma", "qb_success_ewma", "qb_cpoe_ewma",
        "qb_log_prior_starts", "qb_log_prior_dropbacks",
        "qb_continuity_starts_prior", "qb_starter_changed",
        "qb_quality_missing", "qb_new_starter",
    ]
    home = team[team.is_home.eq(1.0)][["game_id", *numeric]].copy().rename(
        columns={c: f"home_{c}" for c in numeric}
    )
    away = team[team.is_home.eq(0.0)][["game_id", *numeric]].copy().rename(
        columns={c: f"away_{c}" for c in numeric}
    )
    matchup = home.merge(away, on="game_id", how="outer", validate="one_to_one")

    continuous = [
        "qb_epa_ewma", "qb_success_ewma", "qb_cpoe_ewma",
        "qb_log_prior_starts", "qb_log_prior_dropbacks", "qb_continuity_starts_prior",
    ]
    for column in continuous:
        matchup[f"diff_{column}"] = matchup[f"home_{column}"] - matchup[f"away_{column}"]

    # Preserve both sides for binary availability/change information: a difference
    # alone cannot distinguish "both changed" from "neither changed".
    binary = ["qb_starter_changed", "qb_quality_missing", "qb_new_starter"]
    keep = ["game_id"] + [f"diff_{c}" for c in continuous]
    for column in binary:
        keep.extend([f"home_{column}", f"away_{column}"])

    return base_games.merge(matchup[keep], on="game_id", how="left", validate="one_to_one")


def qb_feature_columns(frame: pd.DataFrame) -> list[str]:
    prefixes = (
        "diff_qb_",
        "home_qb_starter_changed", "away_qb_starter_changed",
        "home_qb_quality_missing", "away_qb_quality_missing",
        "home_qb_new_starter", "away_qb_new_starter",
    )
    return sorted(c for c in frame.columns if c.startswith(prefixes))

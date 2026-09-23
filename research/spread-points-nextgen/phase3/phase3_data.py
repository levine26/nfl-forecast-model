from __future__ import annotations

"""Chronology-safe data construction shared by Phase 3 A0/B0/C0.

No 2025 or 2026 rows are loaded. All pregame process states are shifted by one
completed team game and carry across seasons inside the frozen 2016-2024 history.
"""

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from nfl_forecast.data import load_core_data
from nfl_forecast.features import aggregate_team_games, add_game_results

from .phase3_scaffold import (
    EWMA_HALF_LIFE,
    RZ_PRIOR_STRENGTH,
    TRAINING_FLOOR,
    assert_phase3_loaded_universe,
    canonical_targets,
    shifted_ewma,
)


@dataclass
class Phase3Data:
    schedules: pd.DataFrame
    pbp: pd.DataFrame
    team_states: pd.DataFrame
    a0_team_rows: pd.DataFrame
    drives: pd.DataFrame
    b0_team_rows: pd.DataFrame
    b0_outcome_rows: pd.DataFrame
    rare_points: pd.DataFrame


def _regular_schedule(schedules: pd.DataFrame) -> pd.DataFrame:
    df = schedules.copy()
    if "game_type" in df.columns:
        df = df[df["game_type"].eq("REG")].copy()
    elif "season_type" in df.columns:
        df = df[df["season_type"].eq("REG")].copy()
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df = df[df["season"].between(TRAINING_FLOOR, 2024, inclusive="both")].copy()
    assert_phase3_loaded_universe(df)
    if "gameday" in df.columns:
        df["gameday"] = pd.to_datetime(df["gameday"], errors="coerce")
    return canonical_targets(df)


def load_phase3_source_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Absolute Phase 3 firewall: the loader is never asked for 2025 or 2026.
    seasons = list(range(TRAINING_FLOOR, 2025))
    bundle = load_core_data(seasons)
    schedules = _regular_schedule(bundle.schedules)
    pbp = bundle.pbp.copy()
    if "season_type" in pbp.columns:
        pbp = pbp[pbp["season_type"].eq("REG")].copy()
    pbp["season"] = pd.to_numeric(pbp["season"], errors="coerce")
    pbp = pbp[pbp["season"].between(TRAINING_FLOOR, 2024, inclusive="both")].copy()
    assert_phase3_loaded_universe(pbp)
    return schedules, pbp


def _schedule_team_scaffold(schedules: pd.DataFrame) -> pd.DataFrame:
    cols = [
        c
        for c in (
            "game_id",
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "home_rest",
            "away_rest",
            "spread_line",
            "total_line",
        )
        if c in schedules.columns
    ]
    sched = schedules[cols].drop_duplicates("game_id").copy()
    home = sched.copy()
    home["team"] = home["home_team"]
    home["opponent"] = home["away_team"]
    home["home_indicator"] = 1.0
    home["points_for"] = pd.to_numeric(home.get("home_score"), errors="coerce")
    home["points_against"] = pd.to_numeric(home.get("away_score"), errors="coerce")
    home["team_rest"] = pd.to_numeric(home.get("home_rest"), errors="coerce")
    home["opponent_rest"] = pd.to_numeric(home.get("away_rest"), errors="coerce")

    away = sched.copy()
    away["team"] = away["away_team"]
    away["opponent"] = away["home_team"]
    away["home_indicator"] = 0.0
    away["points_for"] = pd.to_numeric(away.get("away_score"), errors="coerce")
    away["points_against"] = pd.to_numeric(away.get("home_score"), errors="coerce")
    away["team_rest"] = pd.to_numeric(away.get("away_rest"), errors="coerce")
    away["opponent_rest"] = pd.to_numeric(away.get("home_rest"), errors="coerce")

    out = pd.concat([home, away], ignore_index=True)
    out["rest_diff_team"] = out["team_rest"] - out["opponent_rest"]
    return out


def build_team_states(pbp: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    observed = aggregate_team_games(pbp)
    observed = add_game_results(observed, schedules)
    observed_cols = [
        c
        for c in (
            "game_id",
            "team",
            "off_epa",
            "pass_epa",
            "rush_epa",
            "success_rate",
            "def_epa_allowed",
            "def_pass_epa_allowed",
            "def_rush_epa_allowed",
            "def_success_allowed",
        )
        if c in observed.columns
    ]
    observed = observed[observed_cols].drop_duplicates(["game_id", "team"], keep="last")

    scaffold = _schedule_team_scaffold(schedules)
    df = scaffold.merge(observed, on=["game_id", "team"], how="left")
    df = df.sort_values(["team", "gameday", "season", "week", "game_id"]).copy()

    state_metrics = [
        "off_epa",
        "pass_epa",
        "rush_epa",
        "success_rate",
        "def_epa_allowed",
        "def_pass_epa_allowed",
        "def_rush_epa_allowed",
        "def_success_allowed",
        "points_for",
        "points_against",
    ]
    for col in state_metrics:
        if col not in df.columns:
            df[col] = np.nan
        df[f"{col}_state"] = df.groupby("team", sort=False)[col].transform(
            lambda s: shifted_ewma(pd.to_numeric(s, errors="coerce"), EWMA_HALF_LIFE)
        )

    # Team game index is historical identity only; current target outcome is never used.
    df["team_game_index"] = df.groupby("team", sort=False).cumcount().astype(int)
    return df.sort_values(["season", "week", "gameday", "game_id", "home_indicator"], ascending=[True, True, True, True, False]).reset_index(drop=True)


def build_a0_team_rows(team_states: pd.DataFrame) -> pd.DataFrame:
    own_cols = [
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
        "team",
        "opponent",
        "home_indicator",
        "points_for",
        "points_against",
        "rest_diff_team",
        "team_game_index",
        "off_epa_state",
        "pass_epa_state",
        "success_rate_state",
        "def_epa_allowed_state",
        "def_pass_epa_allowed_state",
        "def_success_allowed_state",
        "points_for_state",
        "points_against_state",
    ]
    base = team_states[[c for c in own_cols if c in team_states.columns]].copy()
    opp = team_states[
        [
            "game_id",
            "team",
            "def_epa_allowed_state",
            "def_pass_epa_allowed_state",
            "def_success_allowed_state",
            "off_epa_state",
            "pass_epa_state",
            "success_rate_state",
            "points_for_state",
            "points_against_state",
        ]
    ].copy()
    opp = opp.rename(
        columns={
            "team": "opponent",
            "def_epa_allowed_state": "opp_def_epa_allowed_state",
            "def_pass_epa_allowed_state": "opp_def_pass_epa_allowed_state",
            "def_success_allowed_state": "opp_def_success_allowed_state",
            "off_epa_state": "opp_off_epa_state",
            "pass_epa_state": "opp_pass_epa_state",
            "success_rate_state": "opp_success_rate_state",
            "points_for_state": "opp_points_for_state",
            "points_against_state": "opp_points_against_state",
        }
    )
    out = base.merge(opp, on=["game_id", "opponent"], how="left", validate="many_to_one")
    out["offense_team"] = out["team"]
    out["defense_team"] = out["opponent"]
    return out


def _first_text(group: pd.DataFrame, candidates: Iterable[str]) -> str:
    for col in candidates:
        if col in group.columns:
            vals = group[col].dropna().astype(str)
            if len(vals):
                return vals.iloc[-1]
    return ""


def _drive_outcome(result: str) -> str:
    text = str(result).strip().lower()
    if "touchdown" in text:
        return "TD"
    if "field goal" in text and not any(x in text for x in ("miss", "blocked", "no good")):
        return "FG"
    return "EMPTY"


def build_drive_table(pbp: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    plays = pbp.copy()
    plays = plays[plays["game_id"].notna() & plays["posteam"].notna()].copy()
    drive_col = "fixed_drive" if "fixed_drive" in plays.columns and plays["fixed_drive"].notna().any() else "drive"
    if drive_col not in plays.columns:
        raise ValueError("PBP has neither fixed_drive nor drive")
    plays = plays[plays[drive_col].notna()].copy()
    plays["_drive"] = plays[drive_col].astype(str)

    sched_cols = [
        c
        for c in (
            "game_id",
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
            "home_rest",
            "away_rest",
        )
        if c in schedules.columns
    ]
    sched = schedules[sched_cols].drop_duplicates("game_id")
    # PBP releases may already carry schedule identity/context columns. Drop any
    # overlapping schedule-owned fields before the canonical join so pandas does
    # not suffix home_team/away_team/gameday/rest columns into _x/_y variants.
    # This is an engineering normalization only; schedule remains authoritative.
    schedule_owned = [c for c in sched_cols if c != "game_id" and c in plays.columns]
    if schedule_owned:
        plays = plays.drop(columns=schedule_owned)
    plays = plays.merge(sched, on="game_id", how="inner", validate="many_to_one")

    if "epa" in plays.columns:
        plays["_is_off_play"] = pd.to_numeric(plays["epa"], errors="coerce").notna()
    else:
        plays["_is_off_play"] = True
    plays["_success"] = (
        pd.to_numeric(plays["success"], errors="coerce")
        if "success" in plays.columns
        else (pd.to_numeric(plays.get("epa"), errors="coerce") > 0).astype(float)
    )
    interception = pd.to_numeric(plays.get("interception", 0), errors="coerce").fillna(0)
    fumble_lost = pd.to_numeric(plays.get("fumble_lost", 0), errors="coerce").fillna(0)
    plays["_turnover"] = (interception.gt(0) | fumble_lost.gt(0)).astype(float)
    yards = pd.to_numeric(plays.get("yards_gained"), errors="coerce")
    plays["_explosive"] = (yards.ge(20) & plays["_is_off_play"]).astype(float)
    yardline = pd.to_numeric(plays.get("yardline_100"), errors="coerce")
    plays["_redzone"] = yardline.le(20) & plays["_is_off_play"]

    if {"posteam_score", "posteam_score_post"}.issubset(plays.columns):
        delta = (
            pd.to_numeric(plays["posteam_score_post"], errors="coerce")
            - pd.to_numeric(plays["posteam_score"], errors="coerce")
        )
        plays["_score_increment"] = delta.clip(lower=0).fillna(0.0)
    else:
        plays["_score_increment"] = 0.0

    rows: list[dict] = []
    group_cols = ["game_id", "posteam", "_drive"]
    for (game_id, offense, drive_id), g in plays.groupby(group_cols, sort=False, observed=True):
        g_off = g[g["_is_off_play"]]
        if g_off.empty:
            continue
        result = _first_text(g, ("fixed_drive_result", "drive_result"))
        outcome = _drive_outcome(result)
        defense_vals = g["defteam"].dropna().astype(str) if "defteam" in g.columns else pd.Series(dtype=str)
        defense = defense_vals.iloc[0] if len(defense_vals) else None
        play_count = int(g_off["_is_off_play"].sum())
        epa = pd.to_numeric(g_off.get("epa"), errors="coerce")
        success = pd.to_numeric(g_off["_success"], errors="coerce")
        td_points = float(g["_score_increment"].sum())
        if outcome == "TD" and td_points not in (6.0, 7.0, 8.0):
            td_points = 7.0
        rows.append(
            {
                "game_id": str(game_id),
                "season": int(pd.to_numeric(g["season"], errors="coerce").dropna().iloc[0]),
                "week": int(pd.to_numeric(g["week"], errors="coerce").dropna().iloc[0]),
                "gameday": g["gameday"].dropna().iloc[0] if g["gameday"].notna().any() else pd.NaT,
                "home_team": g["home_team"].dropna().astype(str).iloc[0],
                "away_team": g["away_team"].dropna().astype(str).iloc[0],
                "offense_team": str(offense),
                "defense_team": str(defense) if defense is not None else None,
                "drive_id": str(drive_id),
                "outcome": outcome,
                "plays": play_count,
                "epa_per_play": float(epa.mean()) if epa.notna().any() else np.nan,
                "success_rate": float(success.mean()) if success.notna().any() else np.nan,
                "turnover": float(g["_turnover"].max()),
                "explosive_plays": float(g["_explosive"].sum()),
                "explosive_rate": float(g["_explosive"].sum() / max(play_count, 1)),
                "redzone_drive": float(g["_redzone"].any()),
                "redzone_td": float(g["_redzone"].any() and outcome == "TD"),
                "td_points": td_points if outcome == "TD" else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("drive construction produced zero drives")
    assert_phase3_loaded_universe(out)
    return out.sort_values(["season", "week", "gameday", "game_id", "offense_team", "drive_id"]).reset_index(drop=True)


def build_rare_points(pbp: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    work = pbp[pbp["game_id"].notna()].copy()
    if "safety" in work.columns and "defteam" in work.columns:
        safe = work[pd.to_numeric(work["safety"], errors="coerce").fillna(0).gt(0)]
        for _, r in safe.iterrows():
            if pd.notna(r.get("defteam")):
                rows.append({"game_id": str(r["game_id"]), "team": str(r["defteam"]), "rare_points": 2.0})
    if "touchdown" in work.columns and "td_team" in work.columns and "posteam" in work.columns:
        td = work[pd.to_numeric(work["touchdown"], errors="coerce").fillna(0).gt(0)].copy()
        td = td[td["td_team"].notna() & td["posteam"].notna()]
        td = td[td["td_team"].astype(str).ne(td["posteam"].astype(str))]
        for _, r in td.iterrows():
            rows.append({"game_id": str(r["game_id"]), "team": str(r["td_team"]), "rare_points": 7.0})

    scaffold = _schedule_team_scaffold(schedules)[["game_id", "team", "season", "week"]].copy()
    scaffold["game_id"] = scaffold["game_id"].astype(str)
    if rows:
        rare = pd.DataFrame(rows).groupby(["game_id", "team"], as_index=False)["rare_points"].sum()
        out = scaffold.merge(rare, on=["game_id", "team"], how="left")
        out["rare_points"] = out["rare_points"].fillna(0.0)
    else:
        out = scaffold.assign(rare_points=0.0)
    return out


def _league_redzone_prior(team_games: pd.DataFrame) -> pd.DataFrame:
    game = (
        team_games.groupby(["game_id", "season", "week", "gameday"], as_index=False)
        .agg(game_rz_drives=("rz_drives", "sum"), game_rz_td=("rz_td", "sum"))
        .sort_values(["gameday", "season", "week", "game_id"])
    )
    game["prior_league_rz_drives"] = game["game_rz_drives"].cumsum().shift(1).fillna(0.0)
    game["prior_league_rz_td"] = game["game_rz_td"].cumsum().shift(1).fillna(0.0)
    denom = game["prior_league_rz_drives"].to_numpy(dtype=float)
    numer = game["prior_league_rz_td"].to_numpy(dtype=float)
    rate = np.divide(numer, denom, out=np.full(len(game), 0.5), where=denom > 0)
    game["prior_league_rz_rate"] = rate
    return game[["game_id", "prior_league_rz_rate"]]


def build_b0_frames(
    drives: pd.DataFrame,
    team_states: pd.DataFrame,
    schedules: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    offense = (
        drives.groupby(["game_id", "offense_team"], as_index=False)
        .agg(
            drive_count=("drive_id", "nunique"),
            plays_total=("plays", "sum"),
            plays_per_drive=("plays", "mean"),
            turnover_per_drive=("turnover", "mean"),
            explosive_plays=("explosive_plays", "sum"),
            rz_drives=("redzone_drive", "sum"),
            rz_td=("redzone_td", "sum"),
        )
        .rename(columns={"offense_team": "team"})
    )
    offense["explosive_rate"] = offense["explosive_plays"] / offense["plays_total"].clip(lower=1)

    defense = (
        drives[drives["defense_team"].notna()]
        .groupby(["game_id", "defense_team"], as_index=False)
        .agg(
            drive_count_allowed=("drive_id", "nunique"),
            plays_allowed_total=("plays", "sum"),
            plays_per_drive_allowed=("plays", "mean"),
            takeaway_per_drive=("turnover", "mean"),
            explosive_plays_allowed=("explosive_plays", "sum"),
            rz_drives_allowed=("redzone_drive", "sum"),
            rz_td_allowed=("redzone_td", "sum"),
        )
        .rename(columns={"defense_team": "team"})
    )
    defense["explosive_rate_allowed"] = defense["explosive_plays_allowed"] / defense["plays_allowed_total"].clip(lower=1)

    base_cols = [
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
        "team",
        "opponent",
        "home_indicator",
        "rest_diff_team",
        "off_epa_state",
        "success_rate_state",
        "def_epa_allowed_state",
        "def_success_allowed_state",
    ]
    team = team_states[[c for c in base_cols if c in team_states.columns]].copy()
    team = team.merge(offense, on=["game_id", "team"], how="left").merge(defense, on=["game_id", "team"], how="left")
    team = team.sort_values(["team", "gameday", "season", "week", "game_id"]).copy()

    ewma_cols = [
        "drive_count",
        "plays_per_drive",
        "turnover_per_drive",
        "explosive_rate",
        "drive_count_allowed",
        "plays_per_drive_allowed",
        "takeaway_per_drive",
        "explosive_rate_allowed",
    ]
    for col in ewma_cols:
        team[f"{col}_state"] = team.groupby("team", sort=False)[col].transform(
            lambda s: shifted_ewma(pd.to_numeric(s, errors="coerce"), EWMA_HALF_LIFE)
        )

    # Prior-team red-zone cumulative counts.
    team["prior_team_rz_drives"] = team.groupby("team", sort=False)["rz_drives"].transform(
        lambda s: pd.to_numeric(s, errors="coerce").fillna(0).cumsum().shift(1)
    ).fillna(0.0)
    team["prior_team_rz_td"] = team.groupby("team", sort=False)["rz_td"].transform(
        lambda s: pd.to_numeric(s, errors="coerce").fillna(0).cumsum().shift(1)
    ).fillna(0.0)
    team["prior_team_rz_drives_allowed"] = team.groupby("team", sort=False)["rz_drives_allowed"].transform(
        lambda s: pd.to_numeric(s, errors="coerce").fillna(0).cumsum().shift(1)
    ).fillna(0.0)
    team["prior_team_rz_td_allowed"] = team.groupby("team", sort=False)["rz_td_allowed"].transform(
        lambda s: pd.to_numeric(s, errors="coerce").fillna(0).cumsum().shift(1)
    ).fillna(0.0)

    league_prior = _league_redzone_prior(team)
    team = team.merge(league_prior, on="game_id", how="left", validate="many_to_one")
    rate = pd.to_numeric(team["prior_league_rz_rate"], errors="coerce").fillna(0.5)
    k = float(RZ_PRIOR_STRENGTH)
    team["rz_td_state"] = (
        team["prior_team_rz_td"] + k * rate
    ) / (team["prior_team_rz_drives"] + k)
    team["rz_td_allowed_state"] = (
        team["prior_team_rz_td_allowed"] + k * rate
    ) / (team["prior_team_rz_drives_allowed"] + k)

    opponent_cols = [
        "game_id",
        "team",
        "drive_count_allowed_state",
        "plays_per_drive_allowed_state",
        "takeaway_per_drive_state",
        "explosive_rate_allowed_state",
        "def_epa_allowed_state",
        "def_success_allowed_state",
        "rz_td_allowed_state",
    ]
    opp = team[[c for c in opponent_cols if c in team.columns]].copy().rename(
        columns={
            "team": "opponent",
            "drive_count_allowed_state": "opp_drive_count_allowed_state",
            "plays_per_drive_allowed_state": "opp_plays_per_drive_allowed_state",
            "takeaway_per_drive_state": "opp_takeaway_per_drive_state",
            "explosive_rate_allowed_state": "opp_explosive_rate_allowed_state",
            "def_epa_allowed_state": "opp_def_epa_allowed_state",
            "def_success_allowed_state": "opp_def_success_allowed_state",
            "rz_td_allowed_state": "opp_rz_td_allowed_state",
        }
    )
    team = team.merge(opp, on=["game_id", "opponent"], how="left", validate="many_to_one")
    team["offense_team"] = team["team"]
    team["defense_team"] = team["opponent"]

    outcome_state_cols = [
        "game_id",
        "team",
        "offense_team",
        "defense_team",
        "home_indicator",
        "rest_diff_team",
        "off_epa_state",
        "opp_def_epa_allowed_state",
        "success_rate_state",
        "opp_def_success_allowed_state",
        "turnover_per_drive_state",
        "opp_takeaway_per_drive_state",
        "explosive_rate_state",
        "opp_explosive_rate_allowed_state",
        "rz_td_state",
        "opp_rz_td_allowed_state",
    ]
    state = team[[c for c in outcome_state_cols if c in team.columns]].copy()
    outcome_rows = drives.merge(
        state,
        left_on=["game_id", "offense_team"],
        right_on=["game_id", "team"],
        how="inner",
        suffixes=("", "_statekey"),
        validate="many_to_one",
    )
    if "team" in outcome_rows.columns:
        outcome_rows = outcome_rows.drop(columns=["team"])

    return (
        team.sort_values(["season", "week", "gameday", "game_id", "home_indicator"], ascending=[True, True, True, True, False]).reset_index(drop=True),
        outcome_rows.sort_values(["season", "week", "gameday", "game_id", "offense_team", "drive_id"]).reset_index(drop=True),
    )


def build_phase3_data() -> Phase3Data:
    schedules, pbp = load_phase3_source_data()
    team_states = build_team_states(pbp, schedules)
    a0_team_rows = build_a0_team_rows(team_states)
    drives = build_drive_table(pbp, schedules)
    b0_team_rows, b0_outcome_rows = build_b0_frames(drives, team_states, schedules)
    rare_points = build_rare_points(pbp, schedules)
    return Phase3Data(
        schedules=schedules,
        pbp=pbp,
        team_states=team_states,
        a0_team_rows=a0_team_rows,
        drives=drives,
        b0_team_rows=b0_team_rows,
        b0_outcome_rows=b0_outcome_rows,
        rare_points=rare_points,
    )

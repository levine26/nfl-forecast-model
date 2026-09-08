from __future__ import annotations

import numpy as np
import pandas as pd


PBP_REQUIRED = {"game_id", "season", "week", "posteam", "defteam", "epa", "home_team", "away_team"}


def _safe_mean(s: pd.Series) -> float:
    return float(s.mean()) if len(s) else np.nan


def aggregate_team_games(pbp: pd.DataFrame, wp_low: float = 0.05, wp_high: float = 0.95) -> pd.DataFrame:
    missing = PBP_REQUIRED - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing required columns: {sorted(missing)}")

    plays = pbp[pbp["posteam"].notna() & pbp["defteam"].notna() & pbp["epa"].notna()].copy()
    if "season_type" in plays.columns:
        plays = plays[plays["season_type"].eq("REG")]

    plays["is_pass"] = plays.get("pass_attempt", 0).fillna(0).astype(float).eq(1)
    plays["is_rush"] = plays.get("rush_attempt", 0).fillna(0).astype(float).eq(1)
    if "success" in plays.columns:
        plays["success_num"] = pd.to_numeric(plays["success"], errors="coerce")
    else:
        plays["success_num"] = (plays["epa"] > 0).astype(float)

    if "wp" in plays.columns:
        plays["neutral"] = plays["wp"].between(wp_low, wp_high, inclusive="both")
    else:
        plays["neutral"] = True

    def agg(group: pd.DataFrame) -> pd.Series:
        pass_plays = group[group["is_pass"]]
        rush_plays = group[group["is_rush"]]
        neutral = group[group["neutral"]]
        return pd.Series({
            "off_epa": _safe_mean(group["epa"]),
            "pass_epa": _safe_mean(pass_plays["epa"]),
            "rush_epa": _safe_mean(rush_plays["epa"]),
            "success_rate": _safe_mean(group["success_num"]),
            "neutral_epa": _safe_mean(neutral["epa"]),
            "off_plays": len(group),
        })

    offense = plays.groupby(["game_id", "season", "week", "posteam"], observed=True).apply(agg).reset_index()
    offense = offense.rename(columns={"posteam": "team"})

    defense = plays.groupby(["game_id", "season", "week", "defteam"], observed=True).apply(agg).reset_index()
    defense = defense.rename(columns={
        "defteam": "team", "off_epa": "def_epa_allowed", "pass_epa": "def_pass_epa_allowed",
        "rush_epa": "def_rush_epa_allowed", "success_rate": "def_success_allowed",
        "neutral_epa": "def_neutral_epa_allowed", "off_plays": "def_plays"
    })

    return offense.merge(defense, on=["game_id", "season", "week", "team"], how="outer")


def add_game_results(team_games: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    sched = schedules[[c for c in ["game_id","home_team","away_team","home_score","away_score","gameday"] if c in schedules.columns]].copy()
    df = team_games.merge(sched, on="game_id", how="left")
    df["is_home"] = df["team"].eq(df["home_team"])
    df["points_for"] = np.where(df["is_home"], df["home_score"], df["away_score"])
    df["points_against"] = np.where(df["is_home"], df["away_score"], df["home_score"])
    df["win"] = np.where(df["points_for"].notna(), (df["points_for"] > df["points_against"]).astype(float), np.nan)
    return df


def _ewma_shifted(s: pd.Series, alpha: float) -> pd.Series:
    return s.shift(1).ewm(alpha=alpha, adjust=False, min_periods=1).mean()


def add_pregame_rolling(team_games: pd.DataFrame, windows=(3,5,8), alpha=0.15) -> pd.DataFrame:
    df = team_games.sort_values(["team", "season", "week", "gameday"], na_position="last").copy()
    base = [
        "off_epa","pass_epa","rush_epa","success_rate","neutral_epa",
        "def_epa_allowed","def_pass_epa_allowed","def_rush_epa_allowed","def_success_allowed","win"
    ]
    for col in [c for c in base if c in df.columns]:
        g = df.groupby("team", group_keys=False)[col]
        df[f"{col}_ewma"] = g.apply(lambda s: _ewma_shifted(s, alpha)).reset_index(level=0, drop=True)
        for w in windows:
            df[f"{col}_l{w}"] = g.apply(lambda s: s.shift(1).rolling(w, min_periods=1).mean()).reset_index(level=0, drop=True)
    return df


def build_matchup_features(team_games: pd.DataFrame, schedules: pd.DataFrame, elo: pd.DataFrame) -> pd.DataFrame:
    schedule_cols = [c for c in ["game_id", "season", "week", "gameday", "gametime", "home_team", "away_team"] if c in schedules.columns]
    sched = schedules[schedule_cols + (["game_type"] if "game_type" in schedules.columns else [])].copy()
    if "game_type" in sched.columns:
        sched = sched[sched["game_type"].eq("REG")].copy()

    home_scaffold = sched[[c for c in ["game_id", "season", "week", "gameday", "gametime", "home_team"] if c in sched.columns]].copy()
    home_scaffold = home_scaffold.rename(columns={"home_team": "team"})
    away_scaffold = sched[[c for c in ["game_id", "season", "week", "gameday", "gametime", "away_team"] if c in sched.columns]].copy()
    away_scaffold = away_scaffold.rename(columns={"away_team": "team"})
    scaffold = pd.concat([home_scaffold, away_scaffold], ignore_index=True)

    metric_cols = [c for c in team_games.columns if c not in {"season", "week", "gameday", "gametime", "home_team", "away_team"}]
    observed = team_games[metric_cols].drop_duplicates(["game_id", "team"], keep="last")
    team_schedule = scaffold.merge(observed, on=["game_id", "team"], how="left")
    pre = add_pregame_rolling(team_schedule)

    feature_cols = [c for c in pre.columns if c.endswith("_ewma") or any(c.endswith(f"_l{w}") for w in (3,5,8))]
    latest = pre[["game_id", "team"] + feature_cols].copy()

    home = latest.rename(columns={"team":"home_team", **{c:f"home_{c}" for c in feature_cols}})
    away = latest.rename(columns={"team":"away_team", **{c:f"away_{c}" for c in feature_cols}})

    keep = [c for c in ["game_id","season","week","gameday","gametime","game_type","home_team","away_team","home_score","away_score","home_rest","away_rest","spread_line","total_line","home_moneyline","away_moneyline"] if c in schedules.columns]
    games = schedules[keep].copy()
    if "game_type" in games.columns:
        games = games[games["game_type"].eq("REG")].copy()
    games = games.merge(home, on=["game_id","home_team"], how="left").merge(away, on=["game_id","away_team"], how="left")
    games = games.merge(elo, on="game_id", how="left")

    for c in feature_cols:
        hc, ac = f"home_{c}", f"away_{c}"
        if hc in games and ac in games:
            games[f"diff_{c}"] = games[hc] - games[ac]

    if "home_rest" in games and "away_rest" in games:
        games["rest_diff"] = games["home_rest"] - games["away_rest"]
    games["home_win"] = np.where(games["home_score"].notna(), (games["home_score"] > games["away_score"]).astype(float), np.nan)
    games["margin"] = games["home_score"] - games["away_score"]
    games["game_total"] = games["home_score"] + games["away_score"]
    return games


def sujar_baseline_columns(df: pd.DataFrame) -> list[str]:
    candidates = [
        "home_elo", "away_elo", "elo_home_prob", "rest_diff",
        "diff_win_ewma", "diff_off_epa_ewma", "diff_def_epa_allowed_ewma",
    ]
    return [c for c in candidates if c in df.columns]


def core_columns(df: pd.DataFrame) -> list[str]:
    cols = [c for c in df.columns if c.startswith("diff_")]
    extras = [c for c in ["home_elo","away_elo","elo_home_prob","rest_diff"] if c in df.columns]
    return sorted(set(cols + extras))

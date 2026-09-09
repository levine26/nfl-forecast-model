from __future__ import annotations

"""Research-only football features for the LevLine challenger.

Every feature in this module is built from games completed *before* the game
being predicted.  The production feature matrix is not modified.
"""

import numpy as np
import pandas as pd


EXTRA_RAW_METRICS = (
    "explosive_rate",
    "turnover_rate",
    "sack_rate",
    "qb_hit_rate",
    "early_down_epa",
    "early_down_success",
    "early_down_pass_epa",
    "redzone_epa",
    "redzone_success",
    "third_down_success",
)


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _safe_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").mean()
    return float(value) if pd.notna(value) else np.nan


def _safe_rate(numerator: pd.Series, denominator: pd.Series | None = None) -> float:
    if denominator is None:
        value = pd.to_numeric(numerator, errors="coerce").mean()
        return float(value) if pd.notna(value) else np.nan
    den = float(pd.to_numeric(denominator, errors="coerce").sum())
    if den <= 0:
        return np.nan
    return float(pd.to_numeric(numerator, errors="coerce").sum() / den)


def aggregate_advanced_team_games(pbp: pd.DataFrame) -> pd.DataFrame:
    """Create compact per-game team metrics from public play-by-play.

    These are deliberately stable, interpretable rate/efficiency signals rather
    than high-dimensional play-level features.  Missing nflverse fields degrade
    to NaN instead of inventing information.
    """
    required = {"game_id", "season", "week", "posteam", "defteam", "epa"}
    missing = required - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing challenger columns: {sorted(missing)}")

    plays = pbp[
        pbp.posteam.notna() & pbp.defteam.notna() & pd.to_numeric(pbp.epa, errors="coerce").notna()
    ].copy()
    if "season_type" in plays.columns:
        plays = plays[plays.season_type.eq("REG")].copy()

    plays["epa_num"] = pd.to_numeric(plays.epa, errors="coerce")
    plays["pass_num"] = _numeric(plays, "pass_attempt")
    plays["rush_num"] = _numeric(plays, "rush_attempt")
    plays["sack_num"] = _numeric(plays, "sack")
    plays["qb_hit_num"] = _numeric(plays, "qb_hit")
    plays["interception_num"] = _numeric(plays, "interception")
    plays["fumble_lost_num"] = _numeric(plays, "fumble_lost")
    plays["yards_num"] = _numeric(plays, "yards_gained")
    plays["down_num"] = _numeric(plays, "down", default=np.nan)
    plays["yardline_num"] = _numeric(plays, "yardline_100", default=np.nan)
    if "success" in plays.columns:
        plays["success_num"] = pd.to_numeric(plays.success, errors="coerce")
    else:
        plays["success_num"] = plays.epa_num.gt(0).astype(float)

    # nflverse may code a sack as a pass attempt or separately.  This definition
    # remains stable either way and avoids a zero denominator.
    plays["dropback_num"] = ((plays.pass_num > 0) | (plays.sack_num > 0)).astype(float)
    plays["turnover_num"] = (
        plays.interception_num.clip(lower=0) + plays.fumble_lost_num.clip(lower=0)
    ).clip(upper=1)
    plays["offensive_play_num"] = ((plays.pass_num > 0) | (plays.rush_num > 0) | (plays.sack_num > 0)).astype(float)
    plays["explosive_num"] = (
        ((plays.pass_num > 0) & (plays.yards_num >= 20))
        | ((plays.rush_num > 0) & (plays.yards_num >= 10))
    ).astype(float)
    plays["early_down"] = plays.down_num.isin([1.0, 2.0])
    plays["early_down_pass"] = plays.early_down & (plays.pass_num > 0)
    plays["redzone"] = plays.yardline_num.between(1, 20, inclusive="both")
    plays["third_down"] = plays.down_num.eq(3.0)

    def aggregate(group: pd.DataFrame) -> pd.Series:
        offensive = group[group.offensive_play_num > 0]
        dropbacks = group[group.dropback_num > 0]
        early = group[group.early_down]
        early_pass = group[group.early_down_pass]
        redzone = group[group.redzone]
        third = group[group.third_down]
        return pd.Series({
            "explosive_rate": _safe_rate(offensive.explosive_num),
            "turnover_rate": _safe_rate(offensive.turnover_num),
            "sack_rate": _safe_rate(dropbacks.sack_num),
            "qb_hit_rate": _safe_rate(dropbacks.qb_hit_num),
            "early_down_epa": _safe_mean(early.epa_num),
            "early_down_success": _safe_mean(early.success_num),
            "early_down_pass_epa": _safe_mean(early_pass.epa_num),
            "redzone_epa": _safe_mean(redzone.epa_num),
            "redzone_success": _safe_mean(redzone.success_num),
            "third_down_success": _safe_mean(third.success_num),
        })

    offense = (
        plays.groupby(["game_id", "season", "week", "posteam"], observed=True)
        .apply(aggregate, include_groups=False)
        .reset_index()
        .rename(columns={"posteam": "team"})
    )
    defense = (
        plays.groupby(["game_id", "season", "week", "defteam"], observed=True)
        .apply(aggregate, include_groups=False)
        .reset_index()
        .rename(columns={"defteam": "team"})
    )
    defense = defense.rename(
        columns={metric: f"def_{metric}_allowed" for metric in EXTRA_RAW_METRICS}
    )
    return offense.merge(defense, on=["game_id", "season", "week", "team"], how="outer")


def _rolling(series: pd.Series, alpha: float, windows: tuple[int, ...]) -> dict[str, pd.Series]:
    shifted = series.shift(1)
    out = {"ewma": shifted.ewm(alpha=alpha, adjust=False, min_periods=1).mean()}
    for window in windows:
        out[f"l{window}"] = shifted.rolling(window, min_periods=1).mean()
    return out


def build_advanced_matchup_features(
    pbp: pd.DataFrame,
    schedules: pd.DataFrame,
    elo: pd.DataFrame,
    *,
    windows: tuple[int, ...] = (3, 5, 8),
    alpha: float = 0.15,
) -> pd.DataFrame:
    """Return one row per game with leakage-safe challenger differentials."""
    observed = aggregate_advanced_team_games(pbp)

    schedule_cols = [
        c for c in ["game_id", "season", "week", "gameday", "gametime", "game_type", "home_team", "away_team"]
        if c in schedules.columns
    ]
    sched = schedules[schedule_cols].copy()
    if "game_type" in sched.columns:
        sched = sched[sched.game_type.eq("REG")].copy()

    home = sched[["game_id", "season", "week", "gameday", "home_team", "away_team"]].copy()
    home = home.rename(columns={"home_team": "team", "away_team": "opponent"})
    home["is_home"] = 1
    away = sched[["game_id", "season", "week", "gameday", "home_team", "away_team"]].copy()
    away = away.rename(columns={"away_team": "team", "home_team": "opponent"})
    away["is_home"] = 0
    scaffold = pd.concat([home, away], ignore_index=True)

    raw_cols = [c for c in observed.columns if c not in {"season", "week"}]
    team_schedule = scaffold.merge(
        observed[raw_cols].drop_duplicates(["game_id", "team"], keep="last"),
        on=["game_id", "team"],
        how="left",
    )

    # Add opponent pregame Elo as a schedule-strength signal.  For each game this
    # is known pregame, and its rolling form is shifted before the target game.
    elo_cols = [c for c in ["game_id", "home_elo", "away_elo"] if c in elo.columns]
    if len(elo_cols) == 3:
        team_schedule = team_schedule.merge(elo[elo_cols], on="game_id", how="left")
        team_schedule["opponent_elo"] = np.where(
            team_schedule.is_home.eq(1), team_schedule.away_elo, team_schedule.home_elo
        )
    else:
        team_schedule["opponent_elo"] = np.nan

    metric_cols = [c for c in observed.columns if c not in {"game_id", "season", "week", "team"}]
    metric_cols.append("opponent_elo")
    team_schedule = team_schedule.sort_values(
        ["team", "season", "week", "gameday", "game_id"], na_position="last"
    ).copy()

    produced: list[str] = []
    for metric in metric_cols:
        numeric = pd.to_numeric(team_schedule[metric], errors="coerce")
        grouped = numeric.groupby(team_schedule.team)
        for suffix in ["ewma", *[f"l{w}" for w in windows]]:
            if suffix == "ewma":
                values = grouped.transform(
                    lambda s: s.shift(1).ewm(alpha=alpha, adjust=False, min_periods=1).mean()
                )
            else:
                window = int(suffix[1:])
                values = grouped.transform(
                    lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
                )
            col = f"ch_{metric}_{suffix}"
            team_schedule[col] = values
            produced.append(col)

    latest = team_schedule[["game_id", "team"] + produced]
    home_features = latest.rename(
        columns={"team": "home_team", **{c: f"home_{c}" for c in produced}}
    )
    away_features = latest.rename(
        columns={"team": "away_team", **{c: f"away_{c}" for c in produced}}
    )
    games = sched[["game_id", "home_team", "away_team"]].copy()
    games = games.merge(home_features, on=["game_id", "home_team"], how="left")
    games = games.merge(away_features, on=["game_id", "away_team"], how="left")
    for col in produced:
        games[f"diff_{col}"] = games[f"home_{col}"] - games[f"away_{col}"]

    keep = ["game_id"] + [c for c in games.columns if c.startswith("diff_ch_")]
    return games[keep]


def enriched_columns(frame: pd.DataFrame, production_columns: list[str]) -> list[str]:
    extras = sorted(c for c in frame.columns if c.startswith("diff_ch_"))
    return sorted(set(production_columns + extras))

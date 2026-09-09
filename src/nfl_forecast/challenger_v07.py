from __future__ import annotations

"""Research-only opponent-adjusted football features for LevLine challengers.

The adjustment is deliberately two-stage and leakage-safe:

1. For each completed team-game, score the observed offensive/defensive performance
   relative to the opponent's *pregame* EWMA strength. The opponent baseline is
   already shifted one game by ``add_pregame_rolling``.
2. Roll those opponent-adjusted residuals forward with another one-game shift before
   they are attached to a matchup.

Therefore a game's own EPA can never influence its pregame feature row. Production
feature generation does not import this module.
"""

import numpy as np
import pandas as pd

from .features import add_pregame_rolling

WINDOWS = (3, 5, 8)
ALPHA = 0.15

# observed team metric -> opponent pregame metric used as the expectation
OFFENSE_EXPECTATIONS = {
    "off_epa": "def_epa_allowed",
    "pass_epa": "def_pass_epa_allowed",
    "rush_epa": "def_rush_epa_allowed",
    "success_rate": "def_success_allowed",
}
DEFENSE_EXPECTATIONS = {
    "def_epa_allowed": "off_epa",
    "def_pass_epa_allowed": "pass_epa",
    "def_rush_epa_allowed": "rush_epa",
    "def_success_allowed": "success_rate",
}


def opponent_adjusted_raw_columns() -> list[str]:
    return [f"opp_adj_{c}" for c in [*OFFENSE_EXPECTATIONS, *DEFENSE_EXPECTATIONS]]


def _opponent_column(frame: pd.DataFrame) -> pd.Series:
    is_home = frame["team"].eq(frame["home_team"])
    return pd.Series(
        np.where(is_home, frame["away_team"], frame["home_team"]),
        index=frame.index,
        dtype="object",
    )


def add_opponent_adjusted_game_residuals(team_games: pd.DataFrame) -> pd.DataFrame:
    """Add one-game opponent-adjusted residuals without using same-game opponent data.

    Example: ``opp_adj_off_epa`` is the offense's observed EPA minus the opponent
    defense's pregame ``def_epa_allowed_ewma``. For defense, lower residuals remain
    better: ``def_epa_allowed - opponent_off_epa_ewma``.
    """
    required = {"game_id", "team", "home_team", "away_team", "season", "week", "gameday"}
    missing = required - set(team_games.columns)
    if missing:
        raise ValueError(f"team_games missing opponent-adjustment columns: {sorted(missing)}")

    pre = add_pregame_rolling(team_games, windows=WINDOWS, alpha=ALPHA)
    pre["opponent"] = _opponent_column(pre)

    expected_metrics = sorted(set(OFFENSE_EXPECTATIONS.values()) | set(DEFENSE_EXPECTATIONS.values()))
    baseline_cols = [f"{metric}_ewma" for metric in expected_metrics]
    missing_baselines = [c for c in baseline_cols if c not in pre.columns]
    if missing_baselines:
        raise ValueError(f"pregame opponent baselines unavailable: {missing_baselines}")

    opponent = pre[["game_id", "team", *baseline_cols]].copy()
    opponent = opponent.rename(
        columns={
            "team": "opponent",
            **{c: f"opponent_{c}" for c in baseline_cols},
        }
    )
    work = pre.merge(opponent, on=["game_id", "opponent"], how="left", validate="many_to_one")

    for observed, expected in OFFENSE_EXPECTATIONS.items():
        if observed not in work.columns:
            work[f"opp_adj_{observed}"] = np.nan
            continue
        work[f"opp_adj_{observed}"] = (
            pd.to_numeric(work[observed], errors="coerce")
            - pd.to_numeric(work[f"opponent_{expected}_ewma"], errors="coerce")
        )

    for observed, expected in DEFENSE_EXPECTATIONS.items():
        if observed not in work.columns:
            work[f"opp_adj_{observed}"] = np.nan
            continue
        work[f"opp_adj_{observed}"] = (
            pd.to_numeric(work[observed], errors="coerce")
            - pd.to_numeric(work[f"opponent_{expected}_ewma"], errors="coerce")
        )

    keep = list(team_games.columns)
    return work[[*keep, *opponent_adjusted_raw_columns()]].copy()


def _shifted_roll(frame: pd.DataFrame, column: str, *, window: int | None = None) -> pd.Series:
    grouped = frame.groupby("team", sort=False)[column]
    if window is None:
        return grouped.transform(
            lambda s: s.shift(1).ewm(alpha=ALPHA, adjust=False, min_periods=1).mean()
        )
    return grouped.transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())


def build_opponent_adjusted_matchup_features(
    team_games: pd.DataFrame,
    schedules: pd.DataFrame,
    base_games: pd.DataFrame,
) -> pd.DataFrame:
    """Append leakage-safe opponent-adjusted home-minus-away matchup features.

    ``base_games`` is normally the output of ``build_matchup_features``. The returned
    frame preserves every existing production-compatible column and adds only
    ``diff_opp_adj_*`` research columns.
    """
    adjusted = add_opponent_adjusted_game_residuals(team_games)
    residual_cols = opponent_adjusted_raw_columns()

    schedule_cols = [
        c for c in ["game_id", "season", "week", "gameday", "gametime", "home_team", "away_team"]
        if c in schedules.columns
    ]
    sched = schedules[schedule_cols + (["game_type"] if "game_type" in schedules.columns else [])].copy()
    if "game_type" in sched.columns:
        sched = sched[sched["game_type"].eq("REG")].copy()

    home = sched[[c for c in ["game_id", "season", "week", "gameday", "gametime", "home_team"] if c in sched]].copy()
    home = home.rename(columns={"home_team": "team"})
    away = sched[[c for c in ["game_id", "season", "week", "gameday", "gametime", "away_team"] if c in sched]].copy()
    away = away.rename(columns={"away_team": "team"})
    scaffold = pd.concat([home, away], ignore_index=True)

    observed = adjusted[["game_id", "team", *residual_cols]].drop_duplicates(
        ["game_id", "team"], keep="last"
    )
    team_schedule = scaffold.merge(observed, on=["game_id", "team"], how="left")
    team_schedule = team_schedule.sort_values(
        ["team", "season", "week", "gameday", "game_id"], na_position="last"
    ).copy()

    rolled_cols: list[str] = []
    for column in residual_cols:
        ewma = f"{column}_ewma"
        team_schedule[ewma] = _shifted_roll(team_schedule, column)
        rolled_cols.append(ewma)
        for window in WINDOWS:
            name = f"{column}_l{window}"
            team_schedule[name] = _shifted_roll(team_schedule, column, window=window)
            rolled_cols.append(name)

    latest = team_schedule[["game_id", "team", *rolled_cols]].copy()
    home_latest = latest.rename(
        columns={"team": "home_team", **{c: f"home_{c}" for c in rolled_cols}}
    )
    away_latest = latest.rename(
        columns={"team": "away_team", **{c: f"away_{c}" for c in rolled_cols}}
    )

    matchup = sched[["game_id", "home_team", "away_team"]].copy()
    matchup = matchup.merge(home_latest, on=["game_id", "home_team"], how="left")
    matchup = matchup.merge(away_latest, on=["game_id", "away_team"], how="left")

    diff_cols: list[str] = []
    for column in rolled_cols:
        name = f"diff_{column}"
        matchup[name] = matchup[f"home_{column}"] - matchup[f"away_{column}"]
        diff_cols.append(name)

    out = base_games.merge(matchup[["game_id", *diff_cols]], on="game_id", how="left", validate="one_to_one")
    return out


def opponent_adjusted_feature_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(c for c in frame.columns if c.startswith("diff_opp_adj_"))

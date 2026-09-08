from __future__ import annotations

import math
import pandas as pd


def expected(home_elo: float, away_elo: float, home_advantage: float = 45.0) -> float:
    return 1.0 / (1.0 + 10 ** (-(home_elo + home_advantage - away_elo) / 400.0))


def build_pregame_elo(
    schedules: pd.DataFrame,
    initial: float = 1500.0,
    k_factor: float = 20.0,
    home_advantage: float = 45.0,
    offseason_regression: float = 0.33,
) -> pd.DataFrame:
    """Sequential Elo. Each row contains ratings as they existed before kickoff."""
    df = schedules.copy()
    if "game_type" in df.columns:
        df = df[df["game_type"].eq("REG")].copy()
    sort_cols = [c for c in ["season", "week", "gameday", "gametime"] if c in df.columns]
    df = df.sort_values(sort_cols).reset_index(drop=True)
    ratings: dict[str, float] = {}
    last_season = None
    out = []

    for _, row in df.iterrows():
        season = int(row["season"])
        if last_season is not None and season != last_season:
            for team, rating in list(ratings.items()):
                ratings[team] = initial + (rating - initial) * (1.0 - offseason_regression)
        last_season = season

        home, away = row["home_team"], row["away_team"]
        h = ratings.get(home, initial)
        a = ratings.get(away, initial)
        p_home = expected(h, a, home_advantage)
        out.append({"game_id": row["game_id"], "home_elo": h, "away_elo": a, "elo_home_prob": p_home})

        hs, as_ = row.get("home_score"), row.get("away_score")
        if pd.notna(hs) and pd.notna(as_):
            actual = 1.0 if hs > as_ else 0.0 if hs < as_ else 0.5
            mov = abs(float(hs) - float(as_))
            mov_mult = math.log(mov + 1.0) * (2.2 / ((abs(h - a) * 0.001) + 2.2)) if mov else 1.0
            delta = k_factor * mov_mult * (actual - p_home)
            ratings[home] = h + delta
            ratings[away] = a - delta

    return pd.DataFrame(out)

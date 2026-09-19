from __future__ import annotations

"""Opponent defensive-efficiency residual research for LevLine Props 2.0.

This module evaluates conditional yardage efficiency with actual event count held fixed.
It is a component-isolation study, not a pregame player-prop forecast.
"""

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

CONTRACT_VERSION = "levline-props-v2-defensive-efficiency-v0.1.0"
EVENT_TYPES = ("rushing", "receiving")
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
PLAYER_PRIOR_STRENGTH = {"rushing": 65.0, "receiving": 45.0}
DEFENSE_PRIOR_EVENTS = 80.0
DEFENSE_LOOKBACK_GAMES = 8
RIDGE_ALPHA = 25.0
EPS = 1e-9


class DefensiveEfficiencyError(ValueError):
    pass


@dataclass(frozen=True)
class ResidualFit:
    event_type: str
    trained_through_season: int
    n_rows: int
    x_mean: float
    x_sd: float
    intercept: float
    beta_standardized: float
    ridge_alpha: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()
    return text.ne("") & text.ne("<NA>") & text.str.lower().ne("nan")


def build_event_rows(
    pbp: pd.DataFrame,
    player_positions: dict[str, str],
) -> pd.DataFrame:
    required = {"game_id", "season", "week", "posteam", "defteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise DefensiveEfficiencyError(f"PBP missing fields: {sorted(missing)}")
    work = pbp.copy()
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    elif "game_type" in work.columns:
        work = work[work["game_type"].astype(str).str.upper().eq("REG")].copy()

    rush_attempt = pd.to_numeric(work.get("rush_attempt", 0), errors="coerce").fillna(0).eq(1)
    complete = pd.to_numeric(work.get("complete_pass", 0), errors="coerce").fillna(0).eq(1)
    rusher_col = next((c for c in ("rusher_player_id", "rusher_id") if c in work.columns), None)
    receiver_col = next((c for c in ("receiver_player_id", "receiver_id") if c in work.columns), None)
    if rusher_col is None or receiver_col is None:
        raise DefensiveEfficiencyError("PBP missing stable rusher/receiver IDs")

    rushing_yards = pd.to_numeric(
        work["rushing_yards"] if "rushing_yards" in work.columns else work.get("yards_gained"),
        errors="coerce",
    )
    receiving_yards = pd.to_numeric(
        work["receiving_yards"] if "receiving_yards" in work.columns else work.get("yards_gained"),
        errors="coerce",
    )

    pieces = []
    rusher = work[rusher_col].astype("string").fillna("").str.strip()
    rmask = rush_attempt & _valid_text(rusher) & rushing_yards.notna()
    if rmask.any():
        frame = work.loc[rmask, ["game_id", "season", "week", "posteam", "defteam"]].copy()
        frame["player_id"] = rusher.loc[rmask].astype(str).to_numpy()
        frame["event_type"] = "rushing"
        frame["yards"] = rushing_yards.loc[rmask].astype(float).to_numpy()
        pieces.append(frame)

    receiver = work[receiver_col].astype("string").fillna("").str.strip()
    recmask = complete & _valid_text(receiver) & receiving_yards.notna()
    if recmask.any():
        frame = work.loc[recmask, ["game_id", "season", "week", "posteam", "defteam"]].copy()
        frame["player_id"] = receiver.loc[recmask].astype(str).to_numpy()
        frame["event_type"] = "receiving"
        frame["yards"] = receiving_yards.loc[recmask].astype(float).to_numpy()
        pieces.append(frame)

    if not pieces:
        raise DefensiveEfficiencyError("no supported efficiency event rows")
    out = pd.concat(pieces, ignore_index=True)
    out["season"] = pd.to_numeric(out["season"], errors="coerce").astype(int)
    out["week"] = pd.to_numeric(out["week"], errors="coerce").astype(int)
    out["posteam"] = out["posteam"].astype("string").fillna("").str.upper().str.strip()
    out["defteam"] = out["defteam"].astype("string").fillna("").str.upper().str.strip()
    out["position"] = (
        out["player_id"].map(player_positions).astype("string").fillna("").str.upper().str.strip()
    )
    out = out[
        out["position"].isin(SUPPORTED_POSITIONS)
        & out["posteam"].ne("")
        & out["defteam"].ne("")
    ].copy()
    return out.reset_index(drop=True)


def _season_position_priors(events: pd.DataFrame) -> dict[tuple[int, str, str], float]:
    priors: dict[tuple[int, str, str], float] = {}
    seasons = sorted(events["season"].astype(int).unique())
    for season in seasons:
        train = events[events["season"].astype(int).lt(int(season))]
        for event_type in EVENT_TYPES:
            event_rows = train[train["event_type"].eq(event_type)]
            if event_rows.empty:
                continue
            pooled_mean = float(event_rows["yards"].mean())
            for position in sorted(SUPPORTED_POSITIONS):
                rows = event_rows[event_rows["position"].eq(position)]
                priors[(int(season), event_type, position)] = (
                    float(rows["yards"].mean()) if not rows.empty else pooled_mean
                )
    return priors


def build_component_rows(events: pd.DataFrame) -> pd.DataFrame:
    """Build strict-prior-week player-game efficiency rows.

    Same-week outcomes do not update baselines for later games in that week. This is intentionally
    conservative and matches the Props STRICT_PRIOR_WEEK historical boundary.
    """
    required = {
        "game_id", "season", "week", "defteam", "player_id", "position", "event_type", "yards"
    }
    missing = required - set(events.columns)
    if missing:
        raise DefensiveEfficiencyError(f"event rows missing fields: {sorted(missing)}")

    priors = _season_position_priors(events)
    player_sum: dict[tuple[str, str], float] = defaultdict(float)
    player_n: dict[tuple[str, str], int] = defaultdict(int)
    defense_games: dict[tuple[str, str], deque[tuple[float, int]]] = defaultdict(
        lambda: deque(maxlen=DEFENSE_LOOKBACK_GAMES)
    )
    prior_event_sum: dict[str, float] = defaultdict(float)
    prior_event_n: dict[str, int] = defaultdict(int)

    rows: list[dict[str, Any]] = []
    for (season, week), week_events in events.sort_values(
        ["season", "week", "game_id"]
    ).groupby(["season", "week"], sort=True):
        season = int(season)
        week = int(week)
        league_mean = {
            event_type: (
                prior_event_sum[event_type] / prior_event_n[event_type]
                if prior_event_n[event_type] > 0
                else math.nan
            )
            for event_type in EVENT_TYPES
        }

        group_cols = ["game_id", "defteam", "player_id", "position", "event_type"]
        for key, group in week_events.groupby(group_cols, sort=False):
            game_id, defense, player_id, position, event_type = key
            position_prior = priors.get((season, str(event_type), str(position)))
            league = league_mean.get(str(event_type), math.nan)
            if position_prior is None or not math.isfinite(float(position_prior)):
                continue
            if not math.isfinite(float(league)):
                continue

            pkey = (str(player_id), str(event_type))
            p_n = int(player_n[pkey])
            p_sum = float(player_sum[pkey])
            strength = float(PLAYER_PRIOR_STRENGTH[str(event_type)])
            player_baseline = (p_sum + strength * float(position_prior)) / (p_n + strength)

            dkey = (str(defense), str(event_type))
            prior_games = list(defense_games[dkey])
            d_yards = float(sum(item[0] for item in prior_games))
            d_events = int(sum(item[1] for item in prior_games))
            defense_baseline = (
                d_yards + DEFENSE_PRIOR_EVENTS * float(league)
            ) / (d_events + DEFENSE_PRIOR_EVENTS)
            defense_delta = float(defense_baseline - league)

            actual_count = int(len(group))
            actual_yards = float(pd.to_numeric(group["yards"], errors="coerce").sum())
            actual_eff = actual_yards / actual_count
            rows.append({
                "contract_version": CONTRACT_VERSION,
                "season": season,
                "week": week,
                "game_id": str(game_id),
                "defteam": str(defense),
                "player_id": str(player_id),
                "position": str(position),
                "event_type": str(event_type),
                "actual_event_count": actual_count,
                "actual_total_yards": actual_yards,
                "actual_yards_per_event": actual_eff,
                "player_baseline_yards_per_event": float(player_baseline),
                "player_prior_event_count": p_n,
                "position_prior_yards_per_event": float(position_prior),
                "opponent_defense_yards_per_event": float(defense_baseline),
                "league_yards_per_event": float(league),
                "opponent_defense_delta": defense_delta,
                "opponent_prior_games": len(prior_games),
                "opponent_prior_events": d_events,
                "same_week_outcomes_used": 0,
            })

        # Update all histories only after the entire week has been forecast.
        for (player_id, event_type), group in week_events.groupby(
            ["player_id", "event_type"], sort=False
        ):
            vals = pd.to_numeric(group["yards"], errors="coerce").dropna()
            player_sum[(str(player_id), str(event_type))] += float(vals.sum())
            player_n[(str(player_id), str(event_type))] += int(len(vals))
        for (game_id, defense, event_type), group in week_events.groupby(
            ["game_id", "defteam", "event_type"], sort=False
        ):
            vals = pd.to_numeric(group["yards"], errors="coerce").dropna()
            defense_games[(str(defense), str(event_type))].append(
                (float(vals.sum()), int(len(vals)))
            )
        for event_type, group in week_events.groupby("event_type", sort=False):
            vals = pd.to_numeric(group["yards"], errors="coerce").dropna()
            prior_event_sum[str(event_type)] += float(vals.sum())
            prior_event_n[str(event_type)] += int(len(vals))

    return pd.DataFrame(rows)


def fit_residual(
    rows: pd.DataFrame,
    *,
    event_type: str,
    trained_through_season: int,
) -> ResidualFit:
    if int(trained_through_season) > 2025:
        raise DefensiveEfficiencyError("completed 2026 outcomes are prohibited")
    train = rows[
        rows["event_type"].eq(str(event_type))
        & rows["season"].astype(int).le(int(trained_through_season))
    ].copy()
    if train.empty:
        raise DefensiveEfficiencyError("empty defensive-efficiency training set")
    x = pd.to_numeric(train["opponent_defense_delta"], errors="coerce").to_numpy(dtype=float)
    y = (
        pd.to_numeric(train["actual_yards_per_event"], errors="coerce")
        - pd.to_numeric(train["player_baseline_yards_per_event"], errors="coerce")
    ).to_numpy(dtype=float)
    w = pd.to_numeric(train["actual_event_count"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    x, y, w = x[mask], y[mask], w[mask]
    if len(x) < 100:
        raise DefensiveEfficiencyError("insufficient residual training rows")
    wsum = float(w.sum())
    x_mean = float(np.sum(w * x) / wsum)
    x_var = float(np.sum(w * (x - x_mean) ** 2) / wsum)
    x_sd = float(max(math.sqrt(x_var), 1e-6))
    z = (x - x_mean) / x_sd
    y_mean = float(np.sum(w * y) / wsum)
    numerator = float(np.sum(w * z * (y - y_mean)))
    denominator = float(np.sum(w * z * z) + RIDGE_ALPHA)
    beta = numerator / denominator
    return ResidualFit(
        event_type=str(event_type),
        trained_through_season=int(trained_through_season),
        n_rows=int(len(x)),
        x_mean=x_mean,
        x_sd=x_sd,
        intercept=y_mean,
        beta_standardized=float(beta),
        ridge_alpha=RIDGE_ALPHA,
    )


def score_season(
    rows: pd.DataFrame,
    *,
    event_type: str,
    evaluation_season: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fit = fit_residual(
        rows,
        event_type=event_type,
        trained_through_season=int(evaluation_season) - 1,
    )
    test = rows[
        rows["event_type"].eq(str(event_type))
        & rows["season"].astype(int).eq(int(evaluation_season))
    ].copy()
    if test.empty:
        raise DefensiveEfficiencyError(f"no {event_type} rows for {evaluation_season}")
    z = (
        pd.to_numeric(test["opponent_defense_delta"], errors="coerce") - fit.x_mean
    ) / fit.x_sd
    correction = fit.intercept + fit.beta_standardized * z
    test["challenger_yards_per_event"] = (
        pd.to_numeric(test["player_baseline_yards_per_event"], errors="coerce") + correction
    )
    count = pd.to_numeric(test["actual_event_count"], errors="coerce")
    actual = pd.to_numeric(test["actual_total_yards"], errors="coerce")
    test["baseline_total_yards_prediction"] = (
        count * pd.to_numeric(test["player_baseline_yards_per_event"], errors="coerce")
    )
    test["challenger_total_yards_prediction"] = count * test["challenger_yards_per_event"]
    test["baseline_abs_error"] = (test["baseline_total_yards_prediction"] - actual).abs()
    test["challenger_abs_error"] = (test["challenger_total_yards_prediction"] - actual).abs()
    test["baseline_efficiency_abs_error"] = (
        pd.to_numeric(test["player_baseline_yards_per_event"], errors="coerce")
        - pd.to_numeric(test["actual_yards_per_event"], errors="coerce")
    ).abs()
    test["challenger_efficiency_abs_error"] = (
        test["challenger_yards_per_event"]
        - pd.to_numeric(test["actual_yards_per_event"], errors="coerce")
    ).abs()
    return test, {
        "contract_version": CONTRACT_VERSION,
        "event_type": str(event_type),
        "evaluation_season": int(evaluation_season),
        "trained_through_season": int(evaluation_season) - 1,
        "n": int(len(test)),
        "unique_games": int(test["game_id"].astype(str).nunique()),
        "unique_players": int(test["player_id"].astype(str).nunique()),
        "baseline_conditional_total_mae": float(test["baseline_abs_error"].mean()),
        "challenger_conditional_total_mae": float(test["challenger_abs_error"].mean()),
        "challenger_minus_baseline_total_mae": float(
            (test["challenger_abs_error"] - test["baseline_abs_error"]).mean()
        ),
        "baseline_efficiency_mae": float(test["baseline_efficiency_abs_error"].mean()),
        "challenger_efficiency_mae": float(test["challenger_efficiency_abs_error"].mean()),
        "fit": fit.to_dict(),
        "conditioned_on_actual_event_count": True,
        "pregame_prop_forecast": False,
        "prop_lines_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
    }


def clustered_mae_difference_ci(
    frame: pd.DataFrame,
    *,
    replicates: int = 3000,
    seed: int = 20260918,
) -> list[float | None]:
    games = np.asarray(sorted(frame["game_id"].astype(str).unique()))
    if len(games) < 2:
        return [None, None]
    grouped = {game: frame[frame["game_id"].astype(str).eq(game)] for game in games}
    rng = np.random.default_rng(seed)
    values = np.empty(int(replicates), dtype=float)
    for index in range(int(replicates)):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[game] for game in sampled], ignore_index=True)
        values[index] = float(
            (boot["challenger_abs_error"] - boot["baseline_abs_error"]).mean()
        )
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]

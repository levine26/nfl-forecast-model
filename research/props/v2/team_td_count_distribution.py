from __future__ import annotations

"""Team offensive touchdown count-distribution research for LevLine Props 2.0.

This component isolates the count distribution. Poisson and Gamma-Poisson challengers receive the
same strictly lagged expected touchdown mean for every team-game.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

CONTRACT_VERSION = "levline-props-v2-team-td-count-v0.1.0"
LEAGUE_PRIOR_GAMES = 8.0
TEAM_LOOKBACK_GAMES = 16
MAX_SUPPORT = 14
EPS = 1e-12


class TeamTDCountError(ValueError):
    pass


@dataclass(frozen=True)
class DispersionFit:
    trained_through_season: int
    n_rows: int
    alpha: float
    method: str = "pearson_moments"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_team_game_td_counts(pbp: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "season", "week", "posteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise TeamTDCountError(f"PBP missing fields: {sorted(missing)}")
    work = pbp.copy()
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    elif "game_type" in work.columns:
        work = work[work["game_type"].astype(str).str.upper().eq("REG")].copy()

    pass_td = pd.to_numeric(work.get("pass_touchdown", 0), errors="coerce").fillna(0).eq(1)
    rush_td = pd.to_numeric(work.get("rush_touchdown", 0), errors="coerce").fillna(0).eq(1)
    offense_td = (pass_td | rush_td).astype(int)
    work["offensive_td"] = offense_td

    teams = work["posteam"].astype("string").fillna("").str.upper().str.strip()
    work["team"] = teams
    work = work[work["team"].ne("")].copy()
    if work.empty:
        raise TeamTDCountError("no offensive team rows")

    counts = (
        work.groupby(["game_id", "season", "week", "team"], as_index=False, sort=True)
        .agg(offensive_tds=("offensive_td", "sum"))
    )
    counts["season"] = pd.to_numeric(counts["season"], errors="coerce").astype(int)
    counts["week"] = pd.to_numeric(counts["week"], errors="coerce").astype(int)
    counts["offensive_tds"] = pd.to_numeric(counts["offensive_tds"], errors="coerce").astype(int)
    return counts.sort_values(["season", "week", "game_id", "team"]).reset_index(drop=True)


def build_strict_prior_means(team_games: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "season", "week", "team", "offensive_tds"}
    missing = required - set(team_games.columns)
    if missing:
        raise TeamTDCountError(f"team-game rows missing fields: {sorted(missing)}")

    history: dict[str, list[float]] = {}
    league_sum = 0.0
    league_n = 0
    rows: list[dict[str, Any]] = []

    ordered = team_games.sort_values(["season", "week", "game_id", "team"])
    for (season, week), week_rows in ordered.groupby(["season", "week"], sort=True):
        league_mean = league_sum / league_n if league_n > 0 else math.nan
        for row in week_rows.itertuples(index=False):
            team_history = history.get(str(row.team), [])
            if not math.isfinite(league_mean):
                continue
            recent = team_history[-TEAM_LOOKBACK_GAMES:]
            team_sum = float(sum(recent))
            team_n = len(recent)
            mean = (
                team_sum + LEAGUE_PRIOR_GAMES * league_mean
            ) / (team_n + LEAGUE_PRIOR_GAMES)
            rows.append({
                "contract_version": CONTRACT_VERSION,
                "game_id": str(row.game_id),
                "season": int(row.season),
                "week": int(row.week),
                "team": str(row.team),
                "actual_offensive_tds": int(row.offensive_tds),
                "expected_offensive_tds": float(mean),
                "prior_team_games": int(team_n),
                "prior_league_games": int(league_n),
                "same_week_outcomes_used": 0,
            })

        # Strict prior-week update: all teams in the week update only after predictions for the week.
        for row in week_rows.itertuples(index=False):
            history.setdefault(str(row.team), []).append(float(row.offensive_tds))
            league_sum += float(row.offensive_tds)
            league_n += 1

    return pd.DataFrame(rows)


def fit_dispersion(rows: pd.DataFrame, *, trained_through_season: int) -> DispersionFit:
    if int(trained_through_season) > 2025:
        raise TeamTDCountError("completed 2026 outcomes are prohibited")
    train = rows[rows["season"].astype(int).le(int(trained_through_season))].copy()
    if len(train) < 200:
        raise TeamTDCountError("insufficient team-game rows for dispersion fit")
    y = pd.to_numeric(train["actual_offensive_tds"], errors="coerce").to_numpy(dtype=float)
    mu = pd.to_numeric(train["expected_offensive_tds"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(y) & np.isfinite(mu) & (mu > 0)
    y, mu = y[mask], mu[mask]
    if len(y) < 200:
        raise TeamTDCountError("insufficient finite team-game rows for dispersion fit")

    numerator = float(np.sum((y - mu) ** 2 - y))
    denominator = float(np.sum(mu ** 2))
    alpha = max(0.0, numerator / max(denominator, EPS))
    return DispersionFit(
        trained_through_season=int(trained_through_season),
        n_rows=int(len(y)),
        alpha=float(alpha),
    )


def poisson_pmf(mu: float, max_support: int = MAX_SUPPORT) -> np.ndarray:
    mu = max(float(mu), EPS)
    probs = np.empty(max_support + 1, dtype=float)
    probs[0] = math.exp(-mu)
    for k in range(1, max_support):
        probs[k] = probs[k - 1] * mu / k
    probs[max_support] = max(0.0, 1.0 - probs[:max_support].sum())
    probs /= probs.sum()
    return probs


def negative_binomial_pmf(mu: float, alpha: float, max_support: int = MAX_SUPPORT) -> np.ndarray:
    mu = max(float(mu), EPS)
    alpha = max(float(alpha), 0.0)
    if alpha <= 1e-10:
        return poisson_pmf(mu, max_support=max_support)
    r = 1.0 / alpha
    p = r / (r + mu)
    probs = np.empty(max_support + 1, dtype=float)
    probs[0] = math.exp(r * math.log(p))
    for k in range(1, max_support):
        probs[k] = probs[k - 1] * ((k - 1 + r) / k) * (1.0 - p)
    probs[max_support] = max(0.0, 1.0 - probs[:max_support].sum())
    probs /= probs.sum()
    return probs


def discrete_crps(probs: np.ndarray, observation: int) -> float:
    p = np.asarray(probs, dtype=float)
    cdf = np.cumsum(p)
    support = np.arange(len(p))
    obs_cdf = (support >= int(observation)).astype(float)
    return float(np.sum((cdf - obs_cdf) ** 2))


def log_loss(probs: np.ndarray, observation: int) -> float:
    index = min(max(int(observation), 0), len(probs) - 1)
    return float(-math.log(max(float(probs[index]), EPS)))


def central_interval(probs: np.ndarray, level: float = 0.80) -> tuple[int, int, bool]:
    cdf = np.cumsum(np.asarray(probs, dtype=float))
    alpha = 1.0 - float(level)
    lo = int(np.searchsorted(cdf, alpha / 2.0, side="left"))
    hi = int(np.searchsorted(cdf, 1.0 - alpha / 2.0, side="left"))
    return lo, hi, True


def score_season(
    rows: pd.DataFrame,
    *,
    evaluation_season: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fit = fit_dispersion(rows, trained_through_season=int(evaluation_season) - 1)
    test = rows[rows["season"].astype(int).eq(int(evaluation_season))].copy()
    if test.empty:
        raise TeamTDCountError(f"no team-game rows for {evaluation_season}")

    records = []
    for row in test.itertuples(index=False):
        mu = float(row.expected_offensive_tds)
        actual = int(row.actual_offensive_tds)
        poi = poisson_pmf(mu)
        nb = negative_binomial_pmf(mu, fit.alpha)
        poi_lo, poi_hi, _ = central_interval(poi)
        nb_lo, nb_hi, _ = central_interval(nb)
        records.append({
            **row._asdict(),
            "dispersion_alpha": fit.alpha,
            "poisson_crps": discrete_crps(poi, actual),
            "nb_crps": discrete_crps(nb, actual),
            "poisson_log_loss": log_loss(poi, actual),
            "nb_log_loss": log_loss(nb, actual),
            "poisson_interval_low_80": poi_lo,
            "poisson_interval_high_80": poi_hi,
            "nb_interval_low_80": nb_lo,
            "nb_interval_high_80": nb_hi,
            "poisson_covered_80": bool(poi_lo <= actual <= poi_hi),
            "nb_covered_80": bool(nb_lo <= actual <= nb_hi),
        })
    scored = pd.DataFrame(records)
    summary = {
        "contract_version": CONTRACT_VERSION,
        "evaluation_season": int(evaluation_season),
        "trained_through_season": int(evaluation_season) - 1,
        "n": int(len(scored)),
        "unique_games": int(scored["game_id"].astype(str).nunique()),
        "poisson_crps": float(scored["poisson_crps"].mean()),
        "nb_crps": float(scored["nb_crps"].mean()),
        "nb_minus_poisson_crps": float((scored["nb_crps"] - scored["poisson_crps"]).mean()),
        "poisson_log_loss": float(scored["poisson_log_loss"].mean()),
        "nb_log_loss": float(scored["nb_log_loss"].mean()),
        "nb_minus_poisson_log_loss": float(
            (scored["nb_log_loss"] - scored["poisson_log_loss"]).mean()
        ),
        "poisson_coverage_80": float(scored["poisson_covered_80"].mean()),
        "nb_coverage_80": float(scored["nb_covered_80"].mean()),
        "dispersion_fit": fit.to_dict(),
        "same_expected_mean_for_both_models": True,
        "player_prop_outcomes_used": 0,
        "sportsbook_data_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
    }
    return scored, summary


def clustered_crps_difference_ci(
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
    for i in range(int(replicates)):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sampled], ignore_index=True)
        values[i] = float((boot["nb_crps"] - boot["poisson_crps"]).mean())
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]

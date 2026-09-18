from __future__ import annotations

"""Research-beta opportunity model for LevLine Props.

The module models *volume before efficiency*. Its simulator contract follows the
football hierarchy

    team plays -> dropbacks vs designed rushes -> dropback outcome
    -> carries / routes -> targets -> receptions.

All historical inputs must be point-in-time safe. The model uses conjugate shrinkage
(Gamma-Poisson, Beta-Binomial and Dirichlet-Multinomial) so every forecast carries
explicit uncertainty and can be sampled without inventing a Gaussian error term.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

ENGINE_VERSION = "props-opportunity-v1"
RESEARCH_LABEL = "LEVLINE PROPS RESEARCH BETA"

TEAM_REQUIRED = {"game_id", "season", "week", "team"}
PLAYER_REQUIRED = {
    "game_id",
    "season",
    "week",
    "team",
    "player_id",
    "position",
    "designed_carries",
    "routes",
    "targets",
    "receptions",
}
CURRENT_PLAYER_REQUIRED = {
    "player_id",
    "player_name",
    "position",
    "availability_probability",
}
PROHIBITED_CURRENT_COLUMNS = {
    "actual_current_game_snaps",
    "actual_snap_count",
    "actual_snap_share",
    "actual_participation",
    "postgame_player_value",
    "home_win",
    "actual_home_score",
    "actual_away_score",
    "final_inactive_learned_post_kickoff",
}

DEFAULT_TEAM_PLAY_PRIOR_MEAN = 64.0
DEFAULT_TEAM_PLAY_PRIOR_GAMES = 3.0
DEFAULT_RATE_PRIOR_TRIALS = 96.0
DEFAULT_ALLOCATION_PSEUDOCOUNT = 0.50
DEFAULT_ROLE_MIN_EVIDENCE = 1.0


@dataclass(frozen=True)
class ForecastContext:
    game_id: str
    season: int
    week: int
    team: str
    opponent: str
    forecast_timestamp: str
    data_horizon: str
    play_volume_multiplier: float = 1.0
    play_volume_uncertainty_multiplier: float = 1.0
    dropback_logit_delta: float = 0.0
    scramble_logit_delta: float = 0.0
    targetable_attempt_logit_delta: float = 0.0
    adjustments_provenance: str = "none"


@dataclass(frozen=True)
class OpportunityProjection:
    metadata: dict[str, Any]
    hierarchy: dict[str, Any]
    marginals: dict[str, Any]
    players: list[dict[str, Any]]
    redistribution: dict[str, Any]
    audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _logit(p: float) -> float:
    p = min(1.0 - 1e-9, max(1e-9, p))
    return math.log(p / (1.0 - p))


def _inv_logit(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _effective_weights(n: int, half_life_games: float) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    if half_life_games <= 0:
        return np.ones(n, dtype=float)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return np.power(0.5, age / half_life_games)


def _weighted_sum(values: pd.Series, weights: np.ndarray) -> float:
    x = pd.to_numeric(values, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    if len(x) != len(weights):
        raise ValueError("Weight alignment failure")
    return float(np.dot(x, weights))


def _beta(alpha: float, beta: float, *, label: str) -> dict[str, Any]:
    alpha = max(float(alpha), 1e-6)
    beta = max(float(beta), 1e-6)
    total = alpha + beta
    mean = alpha / total
    var = alpha * beta / (total * total * (total + 1.0))
    return {
        "label": label,
        "family": "beta",
        "alpha": alpha,
        "beta": beta,
        "mean": mean,
        "variance": var,
        "sd": math.sqrt(max(var, 0.0)),
        "effective_sample_size": total,
        "support": [0.0, 1.0],
    }


def _degenerate_share(value: float, *, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "family": "degenerate",
        "value": float(value),
        "mean": float(value),
        "variance": 0.0,
        "sd": 0.0,
        "support": [float(value), float(value)],
    }


def _gamma_poisson(shape: float, rate: float, *, label: str) -> dict[str, Any]:
    shape = max(float(shape), 1e-6)
    rate = max(float(rate), 1e-6)
    mean = shape / rate
    latent_var = shape / (rate * rate)
    pred_var = mean + latent_var
    p = rate / (rate + 1.0)
    return {
        "label": label,
        "family": "gamma_poisson",
        "gamma_shape": shape,
        "gamma_rate": rate,
        "mean": mean,
        "variance": pred_var,
        "sd": math.sqrt(max(pred_var, 0.0)),
        "negative_binomial_r": shape,
        "negative_binomial_p": p,
        "support": "nonnegative_integer",
    }


def _moment_count(mean: float, variance: float, *, label: str) -> dict[str, Any]:
    mean = max(float(mean), 0.0)
    variance = max(float(variance), mean)
    if mean <= 0:
        return {
            "label": label,
            "family": "degenerate",
            "value": 0,
            "mean": 0.0,
            "variance": 0.0,
            "sd": 0.0,
            "support": "nonnegative_integer",
            "approximation": True,
        }
    if variance <= mean * (1.0 + 1e-9):
        return {
            "label": label,
            "family": "poisson_moment_approximation",
            "lambda": mean,
            "mean": mean,
            "variance": mean,
            "sd": math.sqrt(mean),
            "support": "nonnegative_integer",
            "approximation": True,
        }
    r = mean * mean / (variance - mean)
    p = r / (r + mean)
    return {
        "label": label,
        "family": "negative_binomial_moment_approximation",
        "r": r,
        "p": p,
        "mean": mean,
        "variance": variance,
        "sd": math.sqrt(variance),
        "support": "nonnegative_integer",
        "approximation": True,
    }


def _dirichlet(player_ids: list[str], alpha: np.ndarray, *, label: str) -> dict[str, Any]:
    if len(player_ids) != len(alpha) or not player_ids:
        raise ValueError(f"{label} Dirichlet requires aligned non-empty players")
    alpha = np.asarray(alpha, dtype=float)
    if np.any(~np.isfinite(alpha)) or np.any(alpha <= 0):
        raise ValueError(f"{label} Dirichlet concentrations must be positive")
    total = float(alpha.sum())
    means = alpha / total
    variances = alpha * (total - alpha) / (total * total * (total + 1.0))
    return {
        "label": label,
        "family": "dirichlet",
        "player_ids": player_ids,
        "concentration": {pid: float(a) for pid, a in zip(player_ids, alpha)},
        "mean_share": {pid: float(m) for pid, m in zip(player_ids, means)},
        "variance": {pid: float(v) for pid, v in zip(player_ids, variances)},
        "concentration_total": total,
        "simplex_sum": 1.0,
    }


def _thinned_count_moments(
    count_mean: float,
    count_var: float,
    share_mean: float,
    share_var: float,
) -> tuple[float, float]:
    """Moments for Y | N,p ~ Binomial(N,p), with independent N and random p."""
    en = max(count_mean, 0.0)
    vn = max(count_var, 0.0)
    ep = _clip01(share_mean)
    vp = max(share_var, 0.0)
    ep2 = min(1.0, vp + ep * ep)
    en2 = vn + en * en
    mean = en * ep
    var = en * max(ep - ep2, 0.0) + en2 * ep2 - mean * mean
    return mean, max(var, mean * 0.25)


def _apply_beta_logit_delta(dist: dict[str, Any], delta: float, *, label: str) -> dict[str, Any]:
    delta = _finite(delta)
    if abs(delta) < 1e-12:
        return {**dist, "label": label, "logit_delta": 0.0}
    base_mean = float(dist["mean"])
    new_mean = _inv_logit(_logit(base_mean) + delta)
    strength = max(float(dist["effective_sample_size"]), 2.0)
    return {
        **_beta(new_mean * strength, (1.0 - new_mean) * strength, label=label),
        "logit_delta": delta,
        "pre_adjustment_mean": base_mean,
    }


def _normalize_team_history(team_history: pd.DataFrame, player_history: pd.DataFrame) -> pd.DataFrame:
    missing = TEAM_REQUIRED - set(team_history.columns)
    if missing:
        raise ValueError(f"team_history missing required fields: {sorted(missing)}")
    out = team_history.copy()
    for col in ("season", "week"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[["season", "week"]].isna().any().any():
        raise ValueError("team_history has invalid season/week")

    numeric = (
        "offensive_plays",
        "dropbacks",
        "pass_attempts",
        "sacks",
        "qb_scrambles",
        "designed_rush_attempts",
        "team_rush_attempts",
        "team_targets",
    )
    for col in numeric:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    player_targets = None
    if not player_history.empty and {"game_id", "team", "targets"}.issubset(player_history.columns):
        ph = player_history.copy()
        ph["targets"] = pd.to_numeric(ph["targets"], errors="coerce").fillna(0.0)
        player_targets = (
            ph.groupby(["game_id", "team"], as_index=False, sort=False)["targets"]
            .sum()
            .rename(columns={"targets": "_player_targets"})
        )
        out = out.merge(player_targets, on=["game_id", "team"], how="left", validate="one_to_one")

    if "pass_attempts" not in out.columns:
        raise ValueError("team_history requires pass_attempts")
    if "sacks" not in out.columns:
        out["sacks"] = 0.0
    if "qb_scrambles" not in out.columns:
        out["qb_scrambles"] = 0.0
    if "dropbacks" not in out.columns:
        out["dropbacks"] = out["pass_attempts"] + out["sacks"] + out["qb_scrambles"]
    else:
        derived = out["pass_attempts"] + out["sacks"] + out["qb_scrambles"]
        out["dropbacks"] = out["dropbacks"].where(out["dropbacks"].notna(), derived)

    if "designed_rush_attempts" not in out.columns:
        if "team_rush_attempts" in out.columns:
            out["designed_rush_attempts"] = (out["team_rush_attempts"] - out["qb_scrambles"]).clip(lower=0)
        else:
            raise ValueError("team_history requires designed_rush_attempts or team_rush_attempts")
    if "offensive_plays" not in out.columns:
        out["offensive_plays"] = out["dropbacks"] + out["designed_rush_attempts"]

    if "team_targets" not in out.columns:
        if player_targets is None:
            raise ValueError("team_targets unavailable: provide team_targets or player target history")
        out["team_targets"] = out["_player_targets"]
    elif "_player_targets" in out.columns:
        out["team_targets"] = out["team_targets"].where(out["team_targets"].notna(), out["_player_targets"])

    required_numeric = [
        "offensive_plays",
        "dropbacks",
        "pass_attempts",
        "sacks",
        "qb_scrambles",
        "designed_rush_attempts",
        "team_targets",
    ]
    if out[required_numeric].isna().any().any():
        bad = [c for c in required_numeric if out[c].isna().any()]
        raise ValueError(f"team_history has incomplete opportunity counts: {bad}")
    if (out[required_numeric] < 0).any().any():
        raise ValueError("team_history opportunity counts must be non-negative")

    if (out["dropbacks"] > out["offensive_plays"] + 1e-9).any():
        raise ValueError("dropbacks cannot exceed offensive_plays")
    dropback_outcomes = out["pass_attempts"] + out["sacks"] + out["qb_scrambles"]
    if (dropback_outcomes > out["dropbacks"] + 1e-9).any():
        raise ValueError("pass_attempts + sacks + qb_scrambles cannot exceed dropbacks")
    if (out["team_targets"] > out["pass_attempts"] + 1e-9).any():
        raise ValueError("team_targets cannot exceed pass_attempts")
    return out


def _normalize_player_history(player_history: pd.DataFrame) -> pd.DataFrame:
    missing = PLAYER_REQUIRED - set(player_history.columns)
    if missing:
        raise ValueError(f"player_history missing required fields: {sorted(missing)}")
    out = player_history.copy()
    out["player_id"] = out["player_id"].astype("string").fillna("").str.strip()
    if out["player_id"].eq("").any() or out["player_id"].str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Stable player_id is required in player_history")
    out["position"] = out["position"].astype(str).str.upper()
    for col in ("season", "week", "designed_carries", "routes", "targets", "receptions"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[
        ["season", "week", "designed_carries", "routes", "targets", "receptions"]
    ].isna().any().any():
        raise ValueError("player_history contains invalid opportunity counts")
    if (out[["designed_carries", "routes", "targets", "receptions"]] < 0).any().any():
        raise ValueError("player_history opportunity counts must be non-negative")
    if (out["receptions"] > out["targets"] + 1e-9).any():
        raise ValueError("receptions cannot exceed targets")
    for optional in ("red_zone_opportunities", "goal_line_opportunities"):
        if optional in out.columns:
            out[optional] = pd.to_numeric(out[optional], errors="coerce")
            if out[optional].isna().any() or (out[optional] < 0).any():
                raise ValueError(f"{optional} must be non-negative when supplied")
    return out


def _normalize_current_players(current_players: pd.DataFrame) -> pd.DataFrame:
    missing = CURRENT_PLAYER_REQUIRED - set(current_players.columns)
    if missing:
        raise ValueError(f"current_players missing required fields: {sorted(missing)}")
    retrospective = PROHIBITED_CURRENT_COLUMNS.intersection(current_players.columns)
    if retrospective:
        raise ValueError(
            "Current-player inputs refuse retrospective/current-game fields: "
            f"{sorted(retrospective)}"
        )
    out = current_players.copy()
    out["player_id"] = out["player_id"].astype("string").fillna("").str.strip()
    if out["player_id"].eq("").any() or out["player_id"].str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Stable player_id is required; ambiguous identity fails closed")
    if out["player_id"].duplicated().any():
        raise ValueError("Duplicate current player_id")
    out["position"] = out["position"].astype(str).str.upper()
    out["availability_probability"] = pd.to_numeric(out["availability_probability"], errors="coerce")
    if out["availability_probability"].isna().any() or not out["availability_probability"].between(0, 1).all():
        raise ValueError("availability_probability must be complete and within [0, 1]")
    if "availability_uncertainty" not in out.columns:
        out["availability_uncertainty"] = np.sqrt(
            out["availability_probability"] * (1.0 - out["availability_probability"])
        )
    else:
        out["availability_uncertainty"] = pd.to_numeric(out["availability_uncertainty"], errors="coerce")
        if out["availability_uncertainty"].isna().any() or (out["availability_uncertainty"] < 0).any():
            raise ValueError("availability_uncertainty must be non-negative")
    for col in ("role_multiplier", "carry_role_multiplier", "target_role_multiplier", "route_role_multiplier"):
        if col not in out.columns:
            out[col] = 1.0
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            if out[col].isna().any() or (out[col] < 0).any():
                raise ValueError(f"{col} must be non-negative")
    if "is_primary_qb" not in out.columns:
        out["is_primary_qb"] = False
    out["is_primary_qb"] = out["is_primary_qb"].map(
        lambda value: bool(value) if pd.notna(value) else False
    )
    return out


def _validate_history_horizon(frame: pd.DataFrame, context: ForecastContext, *, label: str) -> None:
    season = pd.to_numeric(frame["season"], errors="coerce")
    week = pd.to_numeric(frame["week"], errors="coerce")
    unsafe = (season > context.season) | ((season == context.season) & (week >= context.week))
    if unsafe.any():
        rows = frame.loc[
            unsafe,
            [c for c in ("game_id", "season", "week", "team") if c in frame.columns],
        ]
        raise ValueError(
            f"{label} contains current/future-week rows beyond the forecast horizon: "
            f"{rows.head(5).to_dict('records')}"
        )
    if context.game_id in set(frame["game_id"].astype(str)):
        raise ValueError(f"{label} contains the forecast game_id")


def _primary_qb(players: pd.DataFrame) -> str:
    explicit = players[players["is_primary_qb"] & players["position"].eq("QB")]
    if len(explicit) == 1:
        return str(explicit.iloc[0]["player_id"])
    if len(explicit) > 1:
        raise ValueError("Multiple players marked is_primary_qb")
    likely = players[players["position"].eq("QB") & players["availability_probability"].gt(0.5)]
    if len(likely) == 1:
        return str(likely.iloc[0]["player_id"])
    raise ValueError("Primary QB identity is ambiguous; mark exactly one is_primary_qb")


def _league_rate_prior(
    frame: pd.DataFrame,
    success_col: str,
    trial_col: str,
    *,
    prior_trials: float,
) -> tuple[float, float]:
    successes = float(pd.to_numeric(frame[success_col], errors="coerce").fillna(0).sum())
    trials = float(pd.to_numeric(frame[trial_col], errors="coerce").fillna(0).sum())
    mean = successes / trials if trials > 0 else 0.5
    mean = min(1.0 - 1e-6, max(1e-6, mean))
    return mean * prior_trials, (1.0 - mean) * prior_trials


def _team_beta_posterior(
    all_history: pd.DataFrame,
    team_rows: pd.DataFrame,
    success_col: str,
    trial_col: str,
    *,
    label: str,
    half_life_games: float,
    prior_trials: float = DEFAULT_RATE_PRIOR_TRIALS,
) -> dict[str, Any]:
    a0, b0 = _league_rate_prior(all_history, success_col, trial_col, prior_trials=prior_trials)
    rows = team_rows.sort_values(["season", "week", "game_id"]).copy()
    w = _effective_weights(len(rows), half_life_games)
    success = _weighted_sum(rows[success_col], w)
    trials = _weighted_sum(rows[trial_col], w)
    failures = max(trials - success, 0.0)
    return _beta(a0 + success, b0 + failures, label=label)


def _team_plays_posterior(
    all_history: pd.DataFrame,
    team_rows: pd.DataFrame,
    *,
    half_life_games: float,
) -> dict[str, Any]:
    league = pd.to_numeric(all_history["offensive_plays"], errors="coerce").dropna()
    league_mean = float(league.mean()) if len(league) else DEFAULT_TEAM_PLAY_PRIOR_MEAN
    league_mean = max(league_mean, 1.0)
    shape0 = league_mean * DEFAULT_TEAM_PLAY_PRIOR_GAMES
    rate0 = DEFAULT_TEAM_PLAY_PRIOR_GAMES
    rows = team_rows.sort_values(["season", "week", "game_id"]).copy()
    w = _effective_weights(len(rows), half_life_games)
    weighted_plays = _weighted_sum(rows["offensive_plays"], w)
    exposure = float(w.sum())
    return _gamma_poisson(shape0 + weighted_plays, rate0 + exposure, label="team_offensive_plays")


def _dropback_outcome_posterior(
    all_history: pd.DataFrame,
    team_rows: pd.DataFrame,
    *,
    half_life_games: float,
    prior_dropbacks: float = 160.0,
) -> dict[str, Any]:
    cats = ["pass_attempts", "sacks", "qb_scrambles"]
    league = np.array([float(all_history[c].sum()) for c in cats], dtype=float)
    if league.sum() <= 0:
        league = np.array([0.90, 0.07, 0.03], dtype=float)
    else:
        league = league / league.sum()
    alpha0 = np.maximum(league * prior_dropbacks, 0.5)
    rows = team_rows.sort_values(["season", "week", "game_id"]).copy()
    w = _effective_weights(len(rows), half_life_games)
    obs = np.array([_weighted_sum(rows[c], w) for c in cats], dtype=float)
    alpha = alpha0 + obs
    total = float(alpha.sum())
    mean = alpha / total
    return {
        "label": "dropback_outcome",
        "family": "dirichlet_categorical",
        "categories": cats,
        "concentration": {c: float(a) for c, a in zip(cats, alpha)},
        "mean_probability": {c: float(m) for c, m in zip(cats, mean)},
        "concentration_total": total,
    }


def _adjust_dropback_outcomes(
    outcome: dict[str, Any],
    *,
    scramble_logit_delta: float,
) -> dict[str, Any]:
    delta = _finite(scramble_logit_delta)
    if abs(delta) < 1e-12:
        return {**outcome, "scramble_logit_delta": 0.0}
    cats = list(outcome["categories"])
    probs = dict(outcome["mean_probability"])
    scramble = probs["qb_scrambles"]
    new_scramble = _inv_logit(_logit(scramble) + delta)
    remaining_old = max(1.0 - scramble, 1e-9)
    remaining_new = 1.0 - new_scramble
    for c in ("pass_attempts", "sacks"):
        probs[c] = probs[c] / remaining_old * remaining_new
    probs["qb_scrambles"] = new_scramble
    total = float(outcome["concentration_total"])
    alpha = np.array([max(probs[c] * total, 1e-6) for c in cats], dtype=float)
    return {
        **outcome,
        "concentration": {c: float(a) for c, a in zip(cats, alpha)},
        "mean_probability": {c: float(a / alpha.sum()) for c, a in zip(cats, alpha)},
        "concentration_total": float(alpha.sum()),
        "scramble_logit_delta": delta,
        "pre_adjustment_scramble_probability": scramble,
    }


def _position_prior_rate(
    player_history: pd.DataFrame,
    team_history: pd.DataFrame,
    *,
    position: str,
    numerator: str,
    denominator: str,
    default_mean: float,
    prior_strength: float,
) -> tuple[float, float]:
    hist = player_history[player_history["position"].eq(position)].copy()
    if hist.empty:
        mean = default_mean
    else:
        if denominator in hist.columns:
            den = pd.to_numeric(hist[denominator], errors="coerce").fillna(0.0)
        else:
            den_frame = team_history[["game_id", "team", denominator]].drop_duplicates(
                ["game_id", "team"]
            )
            hist = hist.merge(den_frame, on=["game_id", "team"], how="left", validate="many_to_one")
            den = pd.to_numeric(hist[denominator], errors="coerce").fillna(0.0)
        num = pd.to_numeric(hist[numerator], errors="coerce").fillna(0.0)
        denom = float(den.sum())
        mean = float(num.sum() / denom) if denom > 0 else default_mean
    mean = min(1.0 - 1e-6, max(1e-6, mean))
    return mean * prior_strength, (1.0 - mean) * prior_strength


def _player_beta_posterior(
    player_history: pd.DataFrame,
    team_history: pd.DataFrame,
    player_id: str,
    position: str,
    *,
    numerator: str,
    denominator: str,
    default_mean: float,
    prior_strength: float,
    half_life_games: float,
    label: str,
    prior_mean_column: str | None = None,
) -> tuple[dict[str, Any], float]:
    hist = player_history[player_history["player_id"].astype(str).eq(str(player_id))].copy()
    prior_mean_override: float | None = None
    if prior_mean_column and prior_mean_column in hist.columns:
        values = pd.to_numeric(hist[prior_mean_column], errors="coerce").dropna().unique()
        if len(values) > 1:
            raise ValueError(
                f"{prior_mean_column} must be constant per player when supplied"
            )
        if len(values) == 1:
            prior_mean_override = float(values[0])
            if not 0 < prior_mean_override < 1:
                raise ValueError(f"{prior_mean_column} must be strictly within (0, 1)")
    if prior_mean_override is None:
        a0, b0 = _position_prior_rate(
            player_history,
            team_history,
            position=position,
            numerator=numerator,
            denominator=denominator,
            default_mean=default_mean,
            prior_strength=prior_strength,
        )
    else:
        a0 = prior_mean_override * prior_strength
        b0 = (1.0 - prior_mean_override) * prior_strength
    hist = hist.sort_values(["season", "week", "game_id"])
    if denominator not in hist.columns:
        den_frame = team_history[["game_id", "team", denominator]].drop_duplicates(["game_id", "team"])
        hist = hist.merge(den_frame, on=["game_id", "team"], how="left", validate="many_to_one")
    w = _effective_weights(len(hist), half_life_games)
    successes = _weighted_sum(hist[numerator], w) if len(hist) else 0.0
    trials = _weighted_sum(hist[denominator], w) if len(hist) else 0.0
    failures = max(trials - successes, 0.0)
    return _beta(a0 + successes, b0 + failures, label=label), trials


def _channel_base_alpha(
    player_history: pd.DataFrame,
    players: pd.DataFrame,
    *,
    channel: str,
    half_life_games: float,
) -> tuple[np.ndarray, np.ndarray]:
    ids = players["player_id"].astype(str).tolist()
    alpha = np.full(len(ids), DEFAULT_ALLOCATION_PSEUDOCOUNT, dtype=float)
    evidence = np.zeros(len(ids), dtype=float)
    for i, pid in enumerate(ids):
        hist = player_history[player_history["player_id"].astype(str).eq(pid)].sort_values(
            ["season", "week", "game_id"]
        )
        if hist.empty or channel not in hist.columns:
            continue
        w = _effective_weights(len(hist), half_life_games)
        val = _weighted_sum(hist[channel], w)
        alpha[i] += val
        evidence[i] = val
    return alpha, evidence


def _availability_adjusted_allocation(
    players: pd.DataFrame,
    base_alpha: np.ndarray,
    *,
    label: str,
    multiplier_column: str,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray]:
    ids = players["player_id"].astype(str).tolist()
    base_total = float(base_alpha.sum())
    base_share = base_alpha / base_total
    availability = players["availability_probability"].to_numpy(dtype=float)
    multipliers = (
        players["role_multiplier"].to_numpy(dtype=float)
        * players[multiplier_column].to_numpy(dtype=float)
    )
    raw = base_alpha * availability * multipliers
    active = raw > 1e-9
    if not active.any():
        raise ValueError(f"No available players remain for {label}")

    avail_unc = players["availability_uncertainty"].to_numpy(dtype=float)
    uncertainty_index = float(np.average(avail_unc, weights=np.maximum(base_share, 1e-9)))
    concentration_scale = 1.0 / (1.0 + 4.0 * uncertainty_index)

    active_ids = [ids[i] for i in np.flatnonzero(active)]
    active_alpha = np.maximum(raw[active] * concentration_scale, 0.05)
    dist = _dirichlet(active_ids, active_alpha, label=label)
    after_share = np.zeros(len(ids), dtype=float)
    for i in np.flatnonzero(active):
        after_share[i] = dist["mean_share"][ids[i]]

    redistribution = {
        "channel": label,
        "baseline_share": {pid: float(s) for pid, s in zip(ids, base_share)},
        "post_availability_share": {pid: float(s) for pid, s in zip(ids, after_share)},
        "share_delta": {pid: float(a - b) for pid, a, b in zip(ids, after_share, base_share)},
        "missing_baseline_mass": float(np.sum(base_share[~active])),
        "availability_uncertainty_index": uncertainty_index,
        "concentration_scale": concentration_scale,
        "rule": (
            "Remove/dampen unavailable or demoted role concentration, then redistribute "
            "over all remaining eligible players in proportion to their shrunk historical "
            "role concentration and explicit role multipliers; never hard-assign all volume "
            "to one depth-chart successor."
        ),
    }
    return dist, redistribution, after_share


def _route_redistribution(
    players: pd.DataFrame,
    base_means: np.ndarray,
    base_strength: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any], np.ndarray]:
    availability = players["availability_probability"].to_numpy(dtype=float)
    mult = (
        players["role_multiplier"].to_numpy(dtype=float)
        * players["route_role_multiplier"].to_numpy(dtype=float)
    )
    adjusted = np.clip(base_means * availability * mult, 0.0, 1.0)
    target_total = float(base_means.sum())
    missing = max(target_total - float(adjusted.sum()), 0.0)

    for _ in range(8):
        if missing <= 1e-10:
            break
        spare = np.maximum(1.0 - adjusted, 0.0) * (availability > 1e-9)
        if spare.sum() <= 1e-10:
            break
        evidence_weight = np.maximum(base_means, 0.05) * np.maximum(availability, 0.0)
        weights = spare * evidence_weight
        if weights.sum() <= 0:
            weights = spare
        addition = missing * weights / weights.sum()
        addition = np.minimum(addition, spare)
        adjusted += addition
        used = float(addition.sum())
        if used <= 1e-12:
            break
        missing -= used

    route_rows: list[dict[str, Any]] = []
    avail_unc = players["availability_uncertainty"].to_numpy(dtype=float)
    for i, row in players.reset_index(drop=True).iterrows():
        mean = float(adjusted[i])
        if mean <= 1e-12 or row["availability_probability"] <= 1e-12:
            dist = _degenerate_share(0.0, label=f"route_participation:{row.player_id}")
        elif mean >= 1.0 - 1e-12:
            dist = _degenerate_share(1.0, label=f"route_participation:{row.player_id}")
        else:
            strength = max(2.0, float(base_strength[i]) / (1.0 + 4.0 * float(avail_unc[i])))
            dist = _beta(
                mean * strength,
                (1.0 - mean) * strength,
                label=f"route_participation:{row.player_id}",
            )
        route_rows.append(dist)

    info = {
        "channel": "route_participation",
        "baseline_total_route_slots_per_dropback": target_total,
        "post_availability_total_route_slots_per_dropback": float(adjusted.sum()),
        "unfilled_route_slots_per_dropback": float(max(missing, 0.0)),
        "baseline_participation": {
            pid: float(v) for pid, v in zip(players["player_id"].astype(str), base_means)
        },
        "post_availability_participation": {
            pid: float(v) for pid, v in zip(players["player_id"].astype(str), adjusted)
        },
        "rule": (
            "Vacated route participation is redistributed across active pass-catchers "
            "proportionally to shrunk historical participation and remaining <=1 capacity."
        ),
    }
    return route_rows, info, adjusted


def _allocation_channel(
    player_history: pd.DataFrame,
    eligible_players: pd.DataFrame,
    *,
    history_column: str,
    label: str,
    multiplier_column: str,
    half_life_games: float,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, np.ndarray]:
    base_alpha, evidence = _channel_base_alpha(
        player_history,
        eligible_players,
        channel=history_column,
        half_life_games=half_life_games,
    )
    dist, redistribution, shares = _availability_adjusted_allocation(
        eligible_players,
        base_alpha,
        label=label,
        multiplier_column=multiplier_column,
    )
    return dist, redistribution, shares, evidence


def build_opportunity_projection(
    team_history: pd.DataFrame,
    player_history: pd.DataFrame,
    current_players: pd.DataFrame,
    context: ForecastContext,
    *,
    half_life_games: float = 8.0,
) -> OpportunityProjection:
    """Build a point-in-time-safe simulator contract for one offense/game.

    Historical rows may include completed 2026 games only when they precede the
    forecast horizon. They update the live state; they are not used here to choose
    architecture, weights or hyperparameters.
    """
    if half_life_games <= 0:
        raise ValueError("half_life_games must be positive")
    has_context_adjustment = any(
        abs(_finite(value, default)) > 1e-12
        for value, default in (
            (context.play_volume_multiplier - 1.0, 0.0),
            (context.play_volume_uncertainty_multiplier - 1.0, 0.0),
            (context.dropback_logit_delta, 0.0),
            (context.scramble_logit_delta, 0.0),
            (context.targetable_attempt_logit_delta, 0.0),
        )
    )
    if has_context_adjustment and str(context.adjustments_provenance).strip().lower() in {
        "",
        "none",
        "unknown",
    }:
        raise ValueError("Non-neutral context adjustments require explicit adjustments_provenance")

    team_hist = _normalize_team_history(team_history, player_history)
    player_hist = _normalize_player_history(player_history)
    players = _normalize_current_players(current_players)
    _validate_history_horizon(team_hist, context, label="team_history")
    _validate_history_horizon(player_hist, context, label="player_history")

    team_hist["team"] = team_hist["team"].astype(str).str.upper().replace({"JAC": "JAX"})
    player_hist["team"] = player_hist["team"].astype(str).str.upper().replace({"JAC": "JAX"})
    team = str(context.team).upper().replace("JAC", "JAX")
    team_rows = team_hist[team_hist["team"].eq(team)].copy()
    if team_rows.empty:
        raise ValueError(f"No historical team opportunity rows for {team}")

    primary_qb = _primary_qb(players)

    plays = _team_plays_posterior(team_hist, team_rows, half_life_games=half_life_games)
    volume_multiplier = _finite(context.play_volume_multiplier, 1.0)
    uncertainty_multiplier = _finite(context.play_volume_uncertainty_multiplier, 1.0)
    if volume_multiplier <= 0 or uncertainty_multiplier < 1.0:
        raise ValueError("play volume multiplier must be >0 and uncertainty multiplier must be >=1")
    if abs(volume_multiplier - 1.0) > 1e-12 or uncertainty_multiplier > 1.0:
        base_shape = float(plays["gamma_shape"])
        base_rate = float(plays["gamma_rate"])
        scaled_rate = base_rate / volume_multiplier
        uncertainty_sq = uncertainty_multiplier**2
        sampling_shape = base_shape / uncertainty_sq
        sampling_rate = scaled_rate / uncertainty_sq
        adjusted = _gamma_poisson(
            sampling_shape,
            sampling_rate,
            label="team_offensive_plays",
        )
        plays = {
            **adjusted,
            "play_volume_multiplier": volume_multiplier,
            "uncertainty_multiplier": uncertainty_multiplier,
            "pre_adjustment_mean": float(base_shape / base_rate),
            "pre_uncertainty_gamma_shape": base_shape,
            "pre_uncertainty_gamma_rate": scaled_rate,
        }

    dropback = _team_beta_posterior(
        team_hist,
        team_rows,
        "dropbacks",
        "offensive_plays",
        label="dropback_rate",
        half_life_games=half_life_games,
    )
    dropback = _apply_beta_logit_delta(
        dropback,
        context.dropback_logit_delta,
        label="dropback_rate",
    )

    outcomes = _dropback_outcome_posterior(
        team_hist,
        team_rows,
        half_life_games=half_life_games,
    )
    outcomes = _adjust_dropback_outcomes(
        outcomes,
        scramble_logit_delta=context.scramble_logit_delta,
    )

    targetable = _team_beta_posterior(
        team_hist,
        team_rows,
        "team_targets",
        "pass_attempts",
        label="targetable_attempt_rate",
        half_life_games=half_life_games,
    )
    targetable = _apply_beta_logit_delta(
        targetable,
        context.targetable_attempt_logit_delta,
        label="targetable_attempt_rate",
    )

    carry_eligible = players[
        players["position"].isin(["QB", "RB", "FB", "WR"])
    ].copy().reset_index(drop=True)
    receive_eligible = players[
        players["position"].isin(["RB", "FB", "WR", "TE"])
    ].copy().reset_index(drop=True)
    if carry_eligible.empty or receive_eligible.empty:
        raise ValueError("Current roster lacks carry or receiving-eligible players")

    carry_dist, carry_redist, carry_shares, carry_evidence = _allocation_channel(
        player_hist,
        carry_eligible,
        history_column="designed_carries",
        label="designed_carry_share",
        multiplier_column="carry_role_multiplier",
        half_life_games=half_life_games,
    )
    target_dist, target_redist, target_shares, target_evidence = _allocation_channel(
        player_hist,
        receive_eligible,
        history_column="targets",
        label="target_share",
        multiplier_column="target_role_multiplier",
        half_life_games=half_life_games,
    )

    route_base = []
    route_strength = []
    route_evidence = []
    catch_dists: dict[str, dict[str, Any]] = {}
    catch_evidence: dict[str, float] = {}
    for _, row in receive_eligible.iterrows():
        route_dist, route_trials = _player_beta_posterior(
            player_hist,
            team_hist,
            str(row.player_id),
            str(row.position),
            numerator="routes",
            denominator="dropbacks",
            default_mean=0.45,
            prior_strength=24.0,
            half_life_games=half_life_games,
            label=f"route_participation:{row.player_id}",
            prior_mean_column="route_prior_mean",
        )
        route_base.append(route_dist["mean"])
        route_strength.append(route_dist["effective_sample_size"])
        route_evidence.append(route_trials)
        catch_dist, catch_trials = _player_beta_posterior(
            player_hist,
            team_hist,
            str(row.player_id),
            str(row.position),
            numerator="receptions",
            denominator="targets",
            default_mean=0.66,
            prior_strength=16.0,
            half_life_games=half_life_games,
            label=f"reception_probability_given_target:{row.player_id}",
        )
        catch_dists[str(row.player_id)] = catch_dist
        catch_evidence[str(row.player_id)] = catch_trials

    route_dists, route_redist, route_means = _route_redistribution(
        receive_eligible,
        np.asarray(route_base, dtype=float),
        np.asarray(route_strength, dtype=float),
    )

    optional_redistribution: dict[str, Any] = {}
    optional_allocations: dict[str, Any] = {}
    for col, label in (
        ("red_zone_opportunities", "red_zone_opportunity_share"),
        ("goal_line_opportunities", "goal_line_opportunity_share"),
    ):
        if col not in player_hist.columns or float(player_hist[col].sum()) <= 0:
            optional_redistribution[label] = {
                "status": "unavailable",
                "reason": f"{col} not supplied with historical evidence",
            }
            continue
        dist, redist, _, _ = _allocation_channel(
            player_hist,
            receive_eligible,
            history_column=col,
            label=label,
            multiplier_column="target_role_multiplier",
            half_life_games=half_life_games,
        )
        optional_allocations[label] = dist
        optional_redistribution[label] = redist

    n_mean = float(plays["mean"])
    n_var = float(plays["variance"])
    d_mean, d_var = _thinned_count_moments(
        n_mean,
        n_var,
        float(dropback["mean"]),
        float(dropback["variance"]),
    )
    designed_mean, designed_var = _thinned_count_moments(
        n_mean,
        n_var,
        1.0 - float(dropback["mean"]),
        float(dropback["variance"]),
    )

    out_alpha = outcomes["concentration"]
    out_total = float(outcomes["concentration_total"])
    pass_p = float(outcomes["mean_probability"]["pass_attempts"])
    pass_var_p = (
        out_alpha["pass_attempts"] * (out_total - out_alpha["pass_attempts"])
    ) / (out_total * out_total * (out_total + 1.0))
    scramble_p = float(outcomes["mean_probability"]["qb_scrambles"])
    scramble_var_p = (
        out_alpha["qb_scrambles"] * (out_total - out_alpha["qb_scrambles"])
    ) / (out_total * out_total * (out_total + 1.0))
    pa_mean, pa_var = _thinned_count_moments(d_mean, d_var, pass_p, pass_var_p)
    scr_mean, scr_var = _thinned_count_moments(d_mean, d_var, scramble_p, scramble_var_p)
    rush_mean = designed_mean + scr_mean
    rush_var = max(designed_var + scr_var, rush_mean)

    qb_carry_share = 0.0
    qb_carry_var = 0.0
    if primary_qb in carry_dist["mean_share"]:
        qb_carry_share = float(carry_dist["mean_share"][primary_qb])
        qb_carry_var = float(carry_dist["variance"][primary_qb])
    qb_designed_mean, qb_designed_var = _thinned_count_moments(
        designed_mean,
        designed_var,
        qb_carry_share,
        qb_carry_var,
    )
    qb_rush_mean = qb_designed_mean + scr_mean
    qb_rush_var = max(qb_designed_var + scr_var, qb_rush_mean)

    team_target_mean, team_target_var = _thinned_count_moments(
        pa_mean,
        pa_var,
        float(targetable["mean"]),
        float(targetable["variance"]),
    )

    player_rows: list[dict[str, Any]] = []
    carry_index = {pid: i for i, pid in enumerate(carry_eligible["player_id"].astype(str))}
    recv_index = {pid: i for i, pid in enumerate(receive_eligible["player_id"].astype(str))}
    route_dist_map = {
        str(pid): dist
        for pid, dist in zip(receive_eligible["player_id"].astype(str), route_dists)
    }
    for _, row in players.iterrows():
        pid = str(row.player_id)
        entry: dict[str, Any] = {
            "player_id": pid,
            "player_name": str(row.player_name),
            "position": str(row.position),
            "availability_probability": float(row.availability_probability),
            "availability_uncertainty": float(row.availability_uncertainty),
            "is_primary_qb": pid == primary_qb,
        }
        if pid in carry_index:
            i = carry_index[pid]
            share = float(carry_shares[i])
            share_var = float(carry_dist["variance"].get(pid, 0.0))
            cmean, cvar = _thinned_count_moments(designed_mean, designed_var, share, share_var)
            entry.update(
                {
                    "designed_carry_share_mean": share,
                    "designed_carry_share_variance": share_var,
                    "designed_carries_mean": cmean,
                    "designed_carries_variance": cvar,
                    "carry_history_effective_opportunities": float(carry_evidence[i]),
                }
            )
            if pid == primary_qb:
                entry["qb_scrambles_mean"] = scr_mean
                entry["qb_rush_opportunities_mean"] = qb_rush_mean
        if pid in recv_index:
            i = recv_index[pid]
            tshare = float(target_shares[i])
            tshare_var = float(target_dist["variance"].get(pid, 0.0))
            tmean, tvar = _thinned_count_moments(
                team_target_mean,
                team_target_var,
                tshare,
                tshare_var,
            )
            catch = catch_dists[pid]
            rmean, rvar = _thinned_count_moments(
                tmean,
                tvar,
                float(catch["mean"]),
                float(catch["variance"]),
            )
            entry.update(
                {
                    "route_participation": route_dist_map[pid],
                    "target_share_mean": tshare,
                    "target_share_variance": tshare_var,
                    "targets_mean": tmean,
                    "targets_variance": tvar,
                    "reception_probability_given_target": catch,
                    "receptions_mean": rmean,
                    "receptions_variance": rvar,
                    "route_history_effective_dropbacks": float(route_evidence[i]),
                    "target_history_effective_opportunities": float(target_evidence[i]),
                    "catch_history_effective_targets": float(catch_evidence[pid]),
                }
            )
        player_rows.append(entry)

    unseen = sorted(
        set(players["player_id"].astype(str)) - set(player_hist["player_id"].astype(str))
    )
    team_games = int(len(team_rows))
    low_evidence_receivers = [
        row["player_id"]
        for row in player_rows
        if "target_history_effective_opportunities" in row
        and row["target_history_effective_opportunities"] < DEFAULT_ROLE_MIN_EVIDENCE
    ]
    data_quality = "high" if team_games >= 8 and not unseen else "medium" if team_games >= 3 else "low"
    pricing_ready = team_games >= 3 and len(low_evidence_receivers) < len(receive_eligible)

    hierarchy = {
        "team_offensive_plays": plays,
        "dropback_rate_given_team_plays": dropback,
        "dropback_outcome_given_dropback": outcomes,
        "designed_carry_share_given_designed_rush": carry_dist,
        "route_participation_given_dropback": {
            pid: route_dist_map[pid] for pid in route_dist_map
        },
        "targetable_attempt_rate_given_pass_attempt": targetable,
        "target_share_given_team_target": target_dist,
        "reception_probability_given_target": catch_dists,
        **optional_allocations,
        "sampling_order": [
            "sample team_offensive_plays from Gamma-Poisson",
            "sample dropback_rate, then dropbacks ~ Binomial(team plays, rate)",
            "designed rushes = team plays - dropbacks",
            "sample dropback outcome probabilities, then Multinomial(dropbacks: pass attempts/sacks/scrambles)",
            "sample designed carry shares, then Multinomial(designed rushes)",
            "QB rush opportunities = primary-QB designed carries + QB scrambles",
            "sample route participation per active receiver against dropbacks",
            "sample targetable-attempt rate, then team targets ~ Binomial(pass attempts, rate)",
            "sample target shares, then Multinomial(team targets)",
            "sample player catch probability, then receptions ~ Binomial(targets, catch probability)",
        ],
    }

    marginals = {
        "team_offensive_plays": plays,
        "qb_dropbacks": _moment_count(d_mean, d_var, label="qb_dropbacks"),
        "qb_pass_attempts": _moment_count(pa_mean, pa_var, label="qb_pass_attempts"),
        "qb_rushing_opportunities": _moment_count(
            qb_rush_mean,
            qb_rush_var,
            label="qb_rushing_opportunities",
        ),
        "team_rush_attempts": _moment_count(rush_mean, rush_var, label="team_rush_attempts"),
        "team_targets": _moment_count(team_target_mean, team_target_var, label="team_targets"),
        "primary_qb_player_id": primary_qb,
        "note": (
            "Count marginals are moment approximations; simulation should use hierarchy "
            "primitives for coherence."
        ),
    }

    redistribution = {
        "designed_carries": carry_redist,
        "routes": route_redist,
        "targets": target_redist,
        **optional_redistribution,
    }

    audit = {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "research_only": True,
        "official_winner_probabilities_modified": False,
        "forecast_game_id": str(context.game_id),
        "forecast_season": int(context.season),
        "forecast_week": int(context.week),
        "team_history_games": team_games,
        "player_history_rows": int(len(player_hist)),
        "current_player_rows": int(len(players)),
        "unseen_current_player_ids": unseen,
        "low_evidence_receivers": low_evidence_receivers,
        "data_quality": data_quality,
        "pricing_ready": bool(pricing_ready),
        "same_or_future_week_history_rows_used": 0,
        "current_game_rows_used": 0,
        "completed_2026_outcomes_used_for_model_selection": 0,
        "context_adjustments_provenance": context.adjustments_provenance,
        "guardrail": (
            "Prior completed games may update chronological state, including earlier 2026 weeks, "
            "but completed 2026 outcomes are not used here to select architecture, features, "
            "hyperparameters, thresholds or weights."
        ),
    }

    return OpportunityProjection(
        metadata={
            "engine_version": ENGINE_VERSION,
            "research_label": RESEARCH_LABEL,
            "game_id": str(context.game_id),
            "season": int(context.season),
            "week": int(context.week),
            "team": team,
            "opponent": str(context.opponent).upper().replace("JAC", "JAX"),
            "forecast_timestamp": context.forecast_timestamp,
            "data_horizon": context.data_horizon,
        },
        hierarchy=hierarchy,
        marginals=marginals,
        players=player_rows,
        redistribution=redistribution,
        audit=audit,
    )


def rolling_origin_team_diagnostics(
    team_history: pd.DataFrame,
    player_history: pd.DataFrame,
    *,
    minimum_prior_games: int = 3,
    half_life_games: float = 8.0,
    exclude_season: int | None = 2026,
) -> pd.DataFrame:
    """One-step-ahead team-volume diagnostics without outcome-driven tuning.

    By default 2026 is excluded entirely so this helper can be used for research
    diagnostics without accidentally turning completed 2026 outcomes into a model
    selection set. It evaluates only team plays and dropback rate, the two top-level
    opportunity states that do not require reconstructing a historical active roster.
    """
    team_hist = _normalize_team_history(team_history, player_history)
    rows: list[dict[str, Any]] = []
    ordered = team_hist.sort_values(["season", "week", "game_id", "team"]).reset_index(drop=True)
    for idx, actual in ordered.iterrows():
        season = int(actual.season)
        if exclude_season is not None and season == exclude_season:
            continue
        prior = ordered.iloc[:idx].copy()
        prior = prior[
            (prior["season"] < actual.season)
            | ((prior["season"] == actual.season) & (prior["week"] < actual.week))
        ]
        team_prior = prior[prior["team"].eq(actual.team)]
        if len(team_prior) < minimum_prior_games or prior.empty:
            continue
        plays = _team_plays_posterior(prior, team_prior, half_life_games=half_life_games)
        dropback = _team_beta_posterior(
            prior,
            team_prior,
            "dropbacks",
            "offensive_plays",
            label="dropback_rate",
            half_life_games=half_life_games,
        )
        actual_dropback_rate = (
            float(actual.dropbacks / actual.offensive_plays)
            if actual.offensive_plays > 0
            else np.nan
        )
        rows.append(
            {
                "game_id": actual.game_id,
                "season": season,
                "week": int(actual.week),
                "team": actual.team,
                "pred_team_plays_mean": float(plays["mean"]),
                "actual_team_plays": float(actual.offensive_plays),
                "team_plays_error": float(plays["mean"] - actual.offensive_plays),
                "pred_dropback_rate_mean": float(dropback["mean"]),
                "actual_dropback_rate": actual_dropback_rate,
                "dropback_rate_error": float(dropback["mean"] - actual_dropback_rate),
            }
        )
    return pd.DataFrame(rows)


def diagnostics_summary(diagnostics: pd.DataFrame) -> dict[str, Any]:
    if diagnostics.empty:
        return {"rows": 0, "status": "insufficient_data"}
    play_error = pd.to_numeric(diagnostics["team_plays_error"], errors="coerce").dropna()
    pass_error = pd.to_numeric(diagnostics["dropback_rate_error"], errors="coerce").dropna()
    return {
        "rows": int(len(diagnostics)),
        "team_plays_mae": float(play_error.abs().mean()),
        "team_plays_rmse": float(math.sqrt(np.mean(np.square(play_error)))),
        "dropback_rate_mae": float(pass_error.abs().mean()),
        "dropback_rate_rmse": float(math.sqrt(np.mean(np.square(pass_error)))),
        "excluded_2026_for_selection_safety": True,
    }

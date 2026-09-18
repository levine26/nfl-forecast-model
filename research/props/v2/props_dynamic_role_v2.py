from __future__ import annotations

"""Latent dynamic snap-role state for LevLine Props 2.0.

V2 replaces fixed short/long half-life tuning with a one-dimensional state-space model.
Process and observation variances are estimated only from historical snap-share trajectories
through the prior season. No prop result, sportsbook result, Fair-Line error, or 2026 outcome
enters the state-parameter fit.
"""

from dataclasses import asdict, dataclass
import math
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from props_dynamic_role import (  # noqa: E402
    CARRY_POSITIONS,
    DynamicRoleError,
    MIN_MULTIPLIER,
    MAX_MULTIPLIER,
    POSITION_SNAP_PRIOR,
    RECEIVING_POSITIONS,
    ROUTE_PRIOR,
    SUPPORTED_POSITIONS,
    normalize_lagged_snap_history,
)

ENGINE_VERSION = "levline-props-dynamic-role-v0.2.0"
RESEARCH_LABEL = "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE"
CONTRACT_VERSION = "levline-props-v2-dynamic-role-development-v0.2.0"

LOGIT_EPS = 0.02
MIN_PROCESS_VARIANCE = 0.01
MIN_OBSERVATION_VARIANCE = 0.01
MAX_VARIANCE = 4.0
INITIAL_STATE_VARIANCE = 1.0
PRIOR_EQUIVALENT_GAMES = 2.0
MIN_POSITION_TRANSITIONS = 40


@dataclass(frozen=True)
class RoleDynamics:
    position: str
    transition_count: int
    process_variance: float
    observation_variance: float
    estimation_scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LatentRoleEstimate:
    player_id: str
    position: str
    history_games: int
    posterior_snap_share: float
    posterior_logit_sd: float
    long_run_snap_share: float
    role_surprise: float
    route_level_multiplier: float
    target_trend_multiplier: float
    carry_trend_multiplier: float
    source: str
    dynamics_scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _logit(value: float) -> float:
    p = float(np.clip(value, LOGIT_EPS, 1.0 - LOGIT_EPS))
    return math.log(p / (1.0 - p))


def _inv_logit(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _clip_multiplier(value: float) -> float:
    if not math.isfinite(value):
        return 1.0
    return float(np.clip(value, MIN_MULTIPLIER, MAX_MULTIPLIER))


def _difference_sequences(frame: pd.DataFrame) -> list[np.ndarray]:
    sequences: list[np.ndarray] = []
    if frame.empty:
        return sequences
    for _, group in frame.groupby(["player_id", "team", "season"], sort=False):
        g = group.sort_values(["week", "game_id"])
        weeks = g["week"].to_numpy(dtype=float)
        shares = g["snap_share"].to_numpy(dtype=float)
        if len(shares) < 2:
            continue
        logits = np.asarray([_logit(v) for v in shares], dtype=float)
        current: list[float] = []
        for idx in range(1, len(logits)):
            gap = weeks[idx] - weeks[idx - 1]
            if not math.isfinite(float(gap)) or gap < 1 or gap > 2:
                if current:
                    sequences.append(np.asarray(current, dtype=float))
                    current = []
                continue
            current.append(float(logits[idx] - logits[idx - 1]))
        if current:
            sequences.append(np.asarray(current, dtype=float))
    return sequences


def _moments(sequences: list[np.ndarray]) -> tuple[float, float, int]:
    """Method-of-moments random-walk / measurement variance estimate.

    For y_t = x_t + e_t and x_t = x_(t-1) + w_t:
      Var(Delta y_t) = q + 2r
      Cov(Delta y_t, Delta y_(t-1)) = -r

    We estimate the lag-one covariance only within contiguous player/season sequences.
    Fixed floors/caps prevent a small or noisy historical sample from generating a degenerate
    state filter.
    """
    arrays = [np.asarray(seq, dtype=float) for seq in sequences if len(seq)]
    if not arrays:
        return 0.10, 0.10, 0
    all_diffs = np.concatenate(arrays)
    all_diffs = all_diffs[np.isfinite(all_diffs)]
    n = int(all_diffs.size)
    if n < 2:
        return 0.10, 0.10, n

    variance = float(np.var(all_diffs, ddof=1))
    lag_pairs: list[tuple[float, float]] = []
    for seq in arrays:
        finite = seq[np.isfinite(seq)]
        if len(finite) >= 2:
            lag_pairs.extend(zip(finite[:-1], finite[1:]))

    if len(lag_pairs) >= 2:
        first = np.asarray([row[0] for row in lag_pairs], dtype=float)
        second = np.asarray([row[1] for row in lag_pairs], dtype=float)
        covariance = float(np.cov(first, second, ddof=1)[0, 1])
        r_raw = max(0.0, -covariance)
        q_raw = max(0.0, variance - 2.0 * r_raw)
    else:
        # Sparse histories cannot identify q and r separately. Use the symmetric decomposition
        # implied by q + 2r = Var(diff) rather than estimating from prop outcomes.
        q_raw = variance / 3.0
        r_raw = variance / 3.0

    q = float(np.clip(q_raw, MIN_PROCESS_VARIANCE, MAX_VARIANCE))
    r = float(np.clip(r_raw, MIN_OBSERVATION_VARIANCE, MAX_VARIANCE))
    return q, r, n


def fit_role_dynamics(
    history: pd.DataFrame,
    *,
    trained_through_season: int,
) -> dict[str, RoleDynamics]:
    """Estimate position-level state variances without using prop outcomes.

    Only rows with season <= trained_through_season are eligible. Position-specific parameters
    require a minimum number of within-player transitions; otherwise the pooled historical
    estimate is used.
    """
    if history is None or history.empty:
        raise DynamicRoleError("role dynamics require non-empty lagged history")
    required = {"season", "week", "game_id", "player_id", "team", "position", "snap_share"}
    missing = required - set(history.columns)
    if missing:
        raise DynamicRoleError(f"role dynamics history missing fields: {sorted(missing)}")

    train = history[pd.to_numeric(history["season"], errors="coerce") <= int(trained_through_season)].copy()
    train["position"] = train["position"].astype("string").fillna("").str.upper().str.strip()
    train = train[train["position"].isin(SUPPORTED_POSITIONS)].copy()
    if train.empty:
        raise DynamicRoleError("no role rows exist through trained_through_season")

    pooled_diffs = _difference_sequences(train)
    pooled_q, pooled_r, pooled_n = _moments(pooled_diffs)
    result: dict[str, RoleDynamics] = {}
    for position in sorted(SUPPORTED_POSITIONS):
        diffs = _difference_sequences(train[train["position"].eq(position)])
        q, r, n = _moments(diffs)
        if n < MIN_POSITION_TRANSITIONS:
            q, r, n_for_record = pooled_q, pooled_r, n
            scope = f"pooled_fallback:{pooled_n}_transitions"
        else:
            n_for_record = n
            scope = "position_specific"
        result[position] = RoleDynamics(
            position=position,
            transition_count=int(n_for_record),
            process_variance=float(q),
            observation_variance=float(r),
            estimation_scope=scope,
        )
    return result


def fit_role_dynamics_from_snap_counts(
    snap_counts: pd.DataFrame,
    *,
    target_season: int,
) -> tuple[dict[str, RoleDynamics], dict[str, Any]]:
    """Freeze season-forward state variances using only seasons before target_season."""
    history, audit = normalize_lagged_snap_history(
        snap_counts,
        season=int(target_season),
        week=1,
    )
    if history.empty:
        raise DynamicRoleError("no prior-season snap history available for V2 dynamics")
    trained_through = int(target_season) - 1
    dynamics = fit_role_dynamics(history, trained_through_season=trained_through)
    return dynamics, {
        "trained_through_season": trained_through,
        "history": audit,
        "prop_outcomes_used_for_state_fit": 0,
        "completed_2026_outcomes_used": 0,
    }


def _latent_filter(
    values: np.ndarray,
    *,
    prior_share: float,
    process_variance: float,
    observation_variance: float,
) -> tuple[float, float]:
    mean = _logit(prior_share)
    variance = float(INITIAL_STATE_VARIANCE)
    q = float(process_variance)
    r = float(observation_variance)
    for value in np.asarray(values, dtype=float):
        if not math.isfinite(float(value)):
            continue
        # One-step random-walk prediction.
        variance = min(MAX_VARIANCE, variance + q)
        y = _logit(float(value))
        gain = variance / (variance + r)
        mean = mean + gain * (y - mean)
        variance = max(1e-9, (1.0 - gain) * variance)
    # Forecast the next game, not the last observed game.
    variance = min(MAX_VARIANCE, variance + q)
    return float(mean), float(variance)


def _long_run_share(values: np.ndarray, prior: float) -> float:
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float(prior)
    return float(
        np.clip(
            (float(vals.sum()) + PRIOR_EQUIVALENT_GAMES * float(prior))
            / (float(vals.size) + PRIOR_EQUIVALENT_GAMES),
            0.0,
            1.0,
        )
    )


def build_dynamic_role_v2_adjustments(
    snap_counts: pd.DataFrame,
    current_players: pd.DataFrame,
    *,
    season: int,
    week: int,
    team: str,
    route_prior_means: Mapping[str, float] | None = None,
    mode: str = "full",
    frozen_dynamics: Mapping[str, RoleDynamics] | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    mode = str(mode).strip().lower()
    if mode not in {"route_only", "full"}:
        raise DynamicRoleError("mode must be route_only or full")

    history, history_audit = normalize_lagged_snap_history(
        snap_counts,
        season=season,
        week=week,
    )
    if current_players is None or current_players.empty:
        raise DynamicRoleError("current_players must be non-empty")
    if history.empty:
        return {}, {
            "engine_version": ENGINE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "research_label": RESEARCH_LABEL,
            "history": history_audit,
            "adjusted_players": 0,
            "fallback_player_ids": sorted(current_players["player_id"].astype(str).tolist()),
            "estimates": [],
            "target_game_rows_used": 0,
        }

    trained_through = int(season) - 1
    if frozen_dynamics is None:
        dynamics = fit_role_dynamics(history, trained_through_season=trained_through)
        dynamics_source = "fit_inside_builder_from_prior_seasons_only"
    else:
        dynamics = {str(key): value for key, value in frozen_dynamics.items()}
        missing_dynamics = set(SUPPORTED_POSITIONS) - set(dynamics)
        if missing_dynamics:
            raise DynamicRoleError(
                f"frozen dynamics missing positions: {sorted(missing_dynamics)}"
            )
        dynamics_source = "season_forward_frozen"

    team_code = str(team or "").upper().strip()
    team_code = {"JAC": "JAX", "LA": "LAR"}.get(team_code, team_code)
    current = current_players.copy()
    current["player_id"] = current["player_id"].astype("string").fillna("").str.strip()
    current["position"] = current["position"].astype("string").fillna("").str.upper().str.strip()
    if "team" in current.columns:
        current["team"] = (
            current["team"].astype("string").fillna("").str.upper().str.strip()
            .replace({"JAC": "JAX", "LA": "LAR"})
        )
        current = current[current["team"].eq(team_code)].copy()

    route_priors = {**ROUTE_PRIOR}
    for key, value in (route_prior_means or {}).items():
        route_priors[str(key).upper()] = float(value)

    team_history = history[history["team"].eq(team_code)].copy()
    if team_history.empty:
        team_history = history

    adjustments: dict[str, dict[str, float]] = {}
    estimates: list[dict[str, Any]] = []
    fallback_players: list[str] = []

    for row in current.itertuples(index=False):
        pid = str(row.player_id)
        position = str(row.position).upper()
        if position not in SUPPORTED_POSITIONS:
            continue
        player = team_history[team_history["player_id"].astype(str).eq(pid)].copy()
        player = player.sort_values(["season", "week", "game_id"])
        values = player["snap_share"].to_numpy(dtype=float)
        if values.size == 0:
            fallback_players.append(pid)
            continue

        prior = float(POSITION_SNAP_PRIOR.get(position, 1.0))
        params = dynamics[position]
        latent_mean, latent_var = _latent_filter(
            values,
            prior_share=prior,
            process_variance=params.process_variance,
            observation_variance=params.observation_variance,
        )
        posterior_share = _inv_logit(latent_mean)
        posterior_sd = math.sqrt(latent_var)
        long_share = _long_run_share(values, prior)
        trend = _clip_multiplier(posterior_share / max(long_share, 1e-6))

        route_multiplier = 1.0
        target_multiplier = 1.0
        carry_multiplier = 1.0
        if position in RECEIVING_POSITIONS:
            route_multiplier = _clip_multiplier(
                posterior_share / max(float(route_priors[position]), 1e-6)
            )
            target_multiplier = trend
        if position in CARRY_POSITIONS:
            carry_multiplier = trend

        adjustment: dict[str, float] = {}
        if position in RECEIVING_POSITIONS:
            adjustment["route_role_multiplier"] = route_multiplier
            if mode == "full":
                adjustment["target_role_multiplier"] = target_multiplier
        if position in CARRY_POSITIONS and mode == "full":
            adjustment["carry_role_multiplier"] = carry_multiplier
        if adjustment:
            adjustments[pid] = adjustment

        estimates.append(
            LatentRoleEstimate(
                player_id=pid,
                position=position,
                history_games=int(values.size),
                posterior_snap_share=float(posterior_share),
                posterior_logit_sd=float(posterior_sd),
                long_run_snap_share=float(long_share),
                role_surprise=float(posterior_share - long_share),
                route_level_multiplier=float(route_multiplier),
                target_trend_multiplier=float(target_multiplier),
                carry_trend_multiplier=float(carry_multiplier),
                source=str(history_audit.get("source", "lagged_snap_share")),
                dynamics_scope=params.estimation_scope,
            ).to_dict()
        )

    return adjustments, {
        "engine_version": ENGINE_VERSION,
        "contract_version": CONTRACT_VERSION,
        "research_label": RESEARCH_LABEL,
        "mode": mode,
        "history": history_audit,
        "team": team_code,
        "trained_through_season_for_state_variance": trained_through,
        "dynamics": {key: value.to_dict() for key, value in dynamics.items()},
        "dynamics_source": dynamics_source,
        "adjusted_players": len(adjustments),
        "fallback_player_ids": sorted(fallback_players),
        "estimates": estimates,
        "target_game_rows_used": 0,
        "prop_outcomes_used_for_state_fit": 0,
        "completed_2026_outcomes_used": 0,
    }

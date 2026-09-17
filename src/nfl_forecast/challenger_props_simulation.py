from __future__ import annotations

"""Research-beta coherent Monte Carlo engine for LevLine offensive player props.

The football simulator is deliberately market agnostic. Sportsbook lines/prices are
accepted only by the post-simulation evaluator. Optional opportunity/efficiency posterior
parameters are sampled when supplied. QB passing yards remain receiver-led so QB and
receiver yardage are one shared process; independent QB completion/YPC posteriors are
intentionally not activated in this Sunday-beta interface. This module does not import or
mutate LevLine/F-ST winner-probability code.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping, Sequence

import numpy as np

RESEARCH_LABEL = "LEVLINE PROPS — RESEARCH BETA"
DEFAULT_MODEL_VERSION = "levline-props-simulation-v0.1.0"
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
SUPPORTED_PROPS = {
    "QB": ("passing_yards", "rushing_yards", "passing_tds", "rushing_tds", "anytime_td"),
    "RB": (
        "rushing_yards",
        "receiving_yards",
        "receptions",
        "rushing_tds",
        "receiving_tds",
        "anytime_td",
    ),
    "WR": ("receiving_yards", "receptions", "receiving_tds", "anytime_td"),
    "TE": ("receiving_yards", "receptions", "receiving_tds", "anytime_td"),
}
TD_PROPS = frozenset({"passing_tds", "rushing_tds", "receiving_tds", "anytime_td"})
DISCRETE_PROPS = frozenset({"receptions", *TD_PROPS})


class SimulationInputError(ValueError):
    """Raised when a simulation input cannot be used without fabricating information."""


@dataclass(frozen=True)
class TeamSimulationInput:
    team: str
    opponent: str
    mean_offensive_plays: float
    offensive_plays_sd: float
    neutral_pass_rate: float
    pass_rate_sd: float
    pass_rate_game_script_sensitivity: float
    expected_passing_tds: float
    expected_rushing_tds: float
    residual_catch_rate: float
    residual_yards_per_reception: float
    residual_yards_per_carry: float
    offensive_plays_gamma_shape: float | None = None
    offensive_plays_gamma_rate: float | None = None
    dropback_rate_alpha: float | None = None
    dropback_rate_beta: float | None = None
    pass_attempt_outcome_alpha: float | None = None
    sack_outcome_alpha: float | None = None
    scramble_outcome_alpha: float | None = None
    targetable_attempt_alpha: float | None = None
    targetable_attempt_beta: float | None = None


@dataclass(frozen=True)
class PlayerSimulationInput:
    player_id: str
    player: str
    position: str
    team: str
    opponent: str
    availability_probability: float
    pass_attempt_share: float
    target_share: float
    catch_rate: float
    receiving_yards_per_reception: float
    carry_share: float
    rushing_yards_per_carry: float
    receiving_td_share: float
    rushing_td_share: float
    data_quality_state: str
    receiving_yards_shape_per_reception: float = 2.0
    rushing_yards_shape_per_carry: float = 2.0
    route_participation: float = 1.0
    route_participation_alpha: float | None = None
    route_participation_beta: float | None = None
    designed_carry_share_alpha: float | None = None
    target_share_alpha: float | None = None
    catch_alpha: float | None = None
    catch_beta: float | None = None
    receiving_yards_per_reception_event_sd: float | None = None
    receiving_yards_per_reception_mean_se: float = 0.0
    rushing_yards_per_carry_event_sd: float | None = None
    rushing_yards_per_carry_mean_se: float = 0.0
    passing_td_share: float | None = None
    passing_td_allocation_alpha: float | None = None
    receiving_td_allocation_alpha: float | None = None
    rushing_td_allocation_alpha: float | None = None
    is_primary_qb: bool = False


@dataclass(frozen=True)
class GameSimulationInput:
    game_id: str
    home_team: str
    away_team: str
    data_horizon: str
    teams: tuple[TeamSimulationInput, TeamSimulationInput]
    players: tuple[PlayerSimulationInput, ...]
    model_version: str = DEFAULT_MODEL_VERSION
    shared_pace_correlation: float = 0.0
    shared_scoring_log_sd: float = 0.0


@dataclass(frozen=True)
class MarketQuote:
    line: float
    over_american_odds: float | None = None
    under_american_odds: float | None = None


@dataclass(frozen=True)
class DistributionSummary:
    model_mean: float
    model_median: float
    levline_fair_line: float
    standard_deviation: float
    prediction_interval_lower: float
    prediction_interval_upper: float
    prediction_interval_level: float
    market_line: float | None
    p_over: float | None
    p_under: float | None
    p_push: float | None
    fair_over_american_odds: float | None
    fair_under_american_odds: float | None


@dataclass(frozen=True)
class ForecastRecord:
    forecast_timestamp: str
    data_horizon: str
    model_version: str
    research_label: str
    game_id: str
    player_id: str
    player: str
    position: str
    team: str
    opponent: str
    prop_type: str
    model_mean: float
    model_median: float
    levline_fair_line: float
    standard_deviation: float
    prediction_interval_lower: float
    prediction_interval_upper: float
    prediction_interval_level: float
    market_line: float | None
    p_over: float | None
    p_under: float | None
    p_push: float | None
    fair_over_american_odds: float | None
    fair_under_american_odds: float | None
    expected_tds: float | None
    probability_1_plus_td: float | None
    probability_2_plus_td: float | None
    td_count_distribution: dict[int, float] | None
    fair_anytime_american_odds: float | None
    market_over_american_odds: float | None
    market_under_american_odds: float | None
    market_no_vig_over_probability: float | None
    probability_edge: float | None
    line_edge: float | None
    data_quality_state: str


@dataclass(frozen=True)
class GameSimulationResult:
    game_id: str
    model_version: str
    data_horizon: str
    seed: int
    simulations: int
    players: tuple[PlayerSimulationInput, ...]
    player_stats: dict[str, dict[str, np.ndarray]]
    team_stats: dict[str, dict[str, np.ndarray]]


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value):
        raise SimulationInputError(f"{name} must be finite")
    return value


def _probability(value: float, name: str) -> float:
    value = _finite(value, name)
    if value < 0.0 or value > 1.0:
        raise SimulationInputError(f"{name} must be in [0, 1]")
    return value


def _nonnegative(value: float, name: str) -> float:
    value = _finite(value, name)
    if value < 0.0:
        raise SimulationInputError(f"{name} must be nonnegative")
    return value


def validate_game_input(game: GameSimulationInput) -> None:
    if not str(game.game_id).strip():
        raise SimulationInputError("game_id is required")
    if not str(game.data_horizon).strip():
        raise SimulationInputError("data_horizon is required")
    if not str(game.model_version).strip():
        raise SimulationInputError("model_version is required")
    if game.home_team == game.away_team or not game.home_team or not game.away_team:
        raise SimulationInputError("home_team and away_team must be distinct nonempty teams")
    if len(game.teams) != 2:
        raise SimulationInputError("exactly two team inputs are required")
    team_map = {team.team: team for team in game.teams}
    if set(team_map) != {game.home_team, game.away_team}:
        raise SimulationInputError("team inputs must match home_team and away_team")
    _probability(game.shared_pace_correlation, "shared_pace_correlation")
    _nonnegative(game.shared_scoring_log_sd, "shared_scoring_log_sd")

    seen_ids: set[str] = set()
    for team in game.teams:
        if team.opponent not in team_map or team.opponent == team.team:
            raise SimulationInputError(f"invalid opponent for {team.team}")
        _nonnegative(team.mean_offensive_plays, f"{team.team}.mean_offensive_plays")
        _nonnegative(team.offensive_plays_sd, f"{team.team}.offensive_plays_sd")
        _probability(team.neutral_pass_rate, f"{team.team}.neutral_pass_rate")
        _nonnegative(team.pass_rate_sd, f"{team.team}.pass_rate_sd")
        _nonnegative(
            team.pass_rate_game_script_sensitivity,
            f"{team.team}.pass_rate_game_script_sensitivity",
        )
        _nonnegative(team.expected_passing_tds, f"{team.team}.expected_passing_tds")
        _nonnegative(team.expected_rushing_tds, f"{team.team}.expected_rushing_tds")
        _probability(team.residual_catch_rate, f"{team.team}.residual_catch_rate")
        _nonnegative(
            team.residual_yards_per_reception,
            f"{team.team}.residual_yards_per_reception",
        )
        _nonnegative(team.residual_yards_per_carry, f"{team.team}.residual_yards_per_carry")
        for alpha_name, beta_name in (
            ("offensive_plays_gamma_shape", "offensive_plays_gamma_rate"),
            ("dropback_rate_alpha", "dropback_rate_beta"),
            ("targetable_attempt_alpha", "targetable_attempt_beta"),
        ):
            alpha_value = getattr(team, alpha_name)
            beta_value = getattr(team, beta_name)
            if (alpha_value is None) != (beta_value is None):
                raise SimulationInputError(
                    f"{team.team}.{alpha_name}/{beta_name} must be supplied together"
                )
            if alpha_value is not None:
                if _nonnegative(alpha_value, f"{team.team}.{alpha_name}") <= 0.0:
                    raise SimulationInputError(f"{team.team}.{alpha_name} must be positive")
                if _nonnegative(beta_value, f"{team.team}.{beta_name}") <= 0.0:
                    raise SimulationInputError(f"{team.team}.{beta_name} must be positive")
        outcome_alpha = (
            team.pass_attempt_outcome_alpha,
            team.sack_outcome_alpha,
            team.scramble_outcome_alpha,
        )
        supplied_outcome = [value is not None for value in outcome_alpha]
        if any(supplied_outcome) and not all(supplied_outcome):
            raise SimulationInputError(
                f"{team.team} dropback outcome concentrations must be supplied together"
            )
        for name, value in zip(
            ("pass_attempt_outcome_alpha", "sack_outcome_alpha", "scramble_outcome_alpha"),
            outcome_alpha,
            strict=True,
        ):
            if value is not None and _nonnegative(value, f"{team.team}.{name}") <= 0.0:
                raise SimulationInputError(f"{team.team}.{name} must be positive")

    primary_qb_by_team: dict[str, int] = {team_code: 0 for team_code in team_map}
    for player in game.players:
        pid = str(player.player_id).strip()
        if not pid or pid.lower() in {"nan", "none", "<na>"}:
            raise SimulationInputError("stable player_id is required; ambiguous identity fails closed")
        if pid in seen_ids:
            raise SimulationInputError(f"duplicate player_id: {pid}")
        seen_ids.add(pid)
        if not str(player.player).strip():
            raise SimulationInputError(f"player name missing for {pid}")
        position = str(player.position).upper()
        if position not in SUPPORTED_POSITIONS:
            raise SimulationInputError(f"unsupported position for {pid}: {player.position}")
        if player.team not in team_map or player.opponent != team_map[player.team].opponent:
            raise SimulationInputError(f"team/opponent mismatch for {pid}")
        if not str(player.data_quality_state).strip():
            raise SimulationInputError(f"data_quality_state is required for {pid}")
        if player.is_primary_qb:
            if position != "QB":
                raise SimulationInputError(f"is_primary_qb requires QB position for {pid}")
            primary_qb_by_team[player.team] += 1
        for field_name in (
            "availability_probability",
            "pass_attempt_share",
            "target_share",
            "catch_rate",
            "carry_share",
            "receiving_td_share",
            "rushing_td_share",
            "route_participation",
        ):
            _probability(getattr(player, field_name), f"{pid}.{field_name}")
        if player.passing_td_share is not None:
            _probability(player.passing_td_share, f"{pid}.passing_td_share")
        for field_name in (
            "receiving_yards_per_reception",
            "rushing_yards_per_carry",
            "receiving_yards_shape_per_reception",
            "rushing_yards_shape_per_carry",
            "receiving_yards_per_reception_mean_se",
            "rushing_yards_per_carry_mean_se",
        ):
            value = _nonnegative(getattr(player, field_name), f"{pid}.{field_name}")
            if "shape" in field_name and value <= 0:
                raise SimulationInputError(f"{pid}.{field_name} must be positive")
        for field_name in (
            "receiving_yards_per_reception_event_sd",
            "rushing_yards_per_carry_event_sd",
            "designed_carry_share_alpha",
            "target_share_alpha",
            "passing_td_allocation_alpha",
            "receiving_td_allocation_alpha",
            "rushing_td_allocation_alpha",
        ):
            value = getattr(player, field_name)
            if value is not None:
                _nonnegative(value, f"{pid}.{field_name}")
        for alpha_name, beta_name in (
            ("route_participation_alpha", "route_participation_beta"),
            ("catch_alpha", "catch_beta"),
        ):
            alpha_value = getattr(player, alpha_name)
            beta_value = getattr(player, beta_name)
            if (alpha_value is None) != (beta_value is None):
                raise SimulationInputError(
                    f"{pid}.{alpha_name}/{beta_name} must be supplied together"
                )
            if alpha_value is not None:
                if _nonnegative(alpha_value, f"{pid}.{alpha_name}") <= 0.0:
                    raise SimulationInputError(f"{pid}.{alpha_name} must be positive")
                if _nonnegative(beta_value, f"{pid}.{beta_name}") <= 0.0:
                    raise SimulationInputError(f"{pid}.{beta_name} must be positive")

    for team_code, primary_count in primary_qb_by_team.items():
        if primary_count > 1:
            raise SimulationInputError(f"{team_code} has multiple primary QBs")

    for team_code in team_map:
        roster = [p for p in game.players if p.team == team_code]
        for share_name in (
            "pass_attempt_share",
            "target_share",
            "carry_share",
            "receiving_td_share",
            "rushing_td_share",
        ):
            total = float(sum(getattr(p, share_name) for p in roster))
            if total > 1.0 + 1e-9:
                raise SimulationInputError(
                    f"{team_code} modeled {share_name} sums to {total:.6f}, above 1.0"
                )
        explicit_passing_td = [
            p.passing_td_share for p in roster if p.passing_td_share is not None
        ]
        if explicit_passing_td and sum(explicit_passing_td) > 1.0 + 1e-9:
            raise SimulationInputError(
                f"{team_code} modeled passing_td_share sums above 1.0"
            )
        for share_name, alpha_name in (
            ("target_share", "target_share_alpha"),
            ("carry_share", "designed_carry_share_alpha"),
            ("receiving_td_share", "receiving_td_allocation_alpha"),
            ("rushing_td_share", "rushing_td_allocation_alpha"),
        ):
            posterior_mode = any(
                getattr(p, alpha_name) is not None and getattr(p, alpha_name) > 0.0
                for p in roster
            )
            if posterior_mode:
                missing = [
                    p.player_id
                    for p in roster
                    if getattr(p, share_name) > 0.0
                    and (
                        getattr(p, alpha_name) is None
                        or getattr(p, alpha_name) <= 0.0
                    )
                ]
                if missing:
                    raise SimulationInputError(
                        f"{team_code}.{alpha_name} missing positive concentration for {missing}"
                    )


def _weights_with_residual(base_shares: np.ndarray, active: np.ndarray) -> np.ndarray:
    modeled = active * base_shares[None, :]
    residual_base = max(0.0, 1.0 - float(base_shares.sum()))
    residual = np.full((active.shape[0], 1), residual_base, dtype=float)
    weights = np.concatenate([modeled, residual], axis=1)
    empty = weights.sum(axis=1) <= 0.0
    weights[empty, -1] = 1.0
    return weights


def _sample_beta_or_fixed(
    alpha: float | None,
    beta: float | None,
    fixed: float,
    n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if alpha is None and beta is None:
        return np.full(n, float(fixed), dtype=float)
    if alpha is None or beta is None:
        raise SimulationInputError("Beta posterior requires both alpha and beta")
    return rng.beta(float(alpha), float(beta), size=n)


def _sample_weights_with_residual(
    base_shares: np.ndarray,
    active: np.ndarray,
    allocation_alpha: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    alphas = np.asarray(allocation_alpha, dtype=float)
    if not np.any(alphas > 0.0):
        return _weights_with_residual(base_shares, active)
    if np.any(alphas < 0.0) or np.any(~np.isfinite(alphas)):
        raise SimulationInputError("allocation concentrations must be finite and nonnegative")

    modeled_share = float(np.sum(base_shares))
    modeled_alpha = float(np.sum(alphas))
    residual_share = max(0.0, 1.0 - modeled_share)
    residual_alpha = (
        modeled_alpha * residual_share / modeled_share
        if modeled_share > 0.0 and residual_share > 0.0
        else 0.0
    )
    params = np.concatenate([alphas, np.array([residual_alpha], dtype=float)])
    draws = np.zeros((active.shape[0], len(params)), dtype=float)
    for j, value in enumerate(params):
        if value > 0.0:
            draws[:, j] = rng.gamma(shape=value, scale=1.0, size=active.shape[0])
        elif j == len(params) - 1 and residual_share > 0.0:
            draws[:, j] = residual_share
        elif j < len(base_shares):
            draws[:, j] = base_shares[j]
    draws[:, :-1] *= active
    empty = draws.sum(axis=1) <= 0.0
    draws[empty, -1] = 1.0
    return draws


def _allocate_counts(
    totals: np.ndarray,
    weights: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    totals = np.asarray(totals, dtype=np.int64)
    if weights.ndim != 2 or len(totals) != weights.shape[0]:
        raise ValueError("allocation shape mismatch")
    n, buckets = weights.shape
    out = np.zeros((n, buckets), dtype=np.int64)
    remaining_n = totals.copy()
    remaining_w = weights.sum(axis=1).astype(float)
    for j in range(buckets - 1):
        p = np.divide(
            weights[:, j], remaining_w, out=np.zeros(n, dtype=float), where=remaining_w > 0
        )
        p = np.clip(p, 0.0, 1.0)
        draw = rng.binomial(remaining_n, p)
        out[:, j] = draw
        remaining_n -= draw
        remaining_w -= weights[:, j]
        remaining_w = np.maximum(remaining_w, 0.0)
    out[:, -1] = remaining_n
    return out


def _allocate_events_with_capacity(
    totals: np.ndarray,
    base_weights: np.ndarray,
    capacities: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Allocate integer events exactly while never exceeding per-bucket capacities."""
    totals = np.asarray(totals, dtype=np.int64)
    capacities = np.asarray(capacities, dtype=np.int64).copy()
    if base_weights.shape != capacities.shape or len(totals) != capacities.shape[0]:
        raise ValueError("capacity allocation shape mismatch")
    totals = np.minimum(totals, capacities.sum(axis=1))
    out = np.zeros_like(capacities)
    max_events = int(totals.max(initial=0))
    rows = np.arange(len(totals))
    for event in range(max_events):
        active_rows = totals > event
        if not np.any(active_rows):
            break
        eligible = capacities > 0
        weights = np.where(eligible, base_weights, 0.0)
        row_sums = weights.sum(axis=1)
        fallback = active_rows & (row_sums <= 0.0)
        if np.any(fallback):
            weights[fallback] = capacities[fallback]
            row_sums = weights.sum(axis=1)
        probs = np.divide(
            weights,
            row_sums[:, None],
            out=np.zeros_like(weights, dtype=float),
            where=row_sums[:, None] > 0,
        )
        cdf = np.cumsum(probs, axis=1)
        u = rng.random(len(totals))
        choices = np.sum(u[:, None] > cdf, axis=1)
        choices = np.minimum(choices, weights.shape[1] - 1)
        rr = rows[active_rows]
        cc = choices[active_rows]
        out[rr, cc] += 1
        capacities[rr, cc] -= 1
    return out


def _compound_yards(
    counts: np.ndarray,
    mean_per_event: float,
    shape_per_event: float,
    rng: np.random.Generator,
    *,
    event_sd: float | None = None,
    mean_se: float = 0.0,
) -> np.ndarray:
    counts = np.asarray(counts, dtype=np.int64)
    mean_per_event = float(mean_per_event)
    mean_se = float(mean_se)
    if mean_per_event <= 0.0:
        return np.zeros_like(counts)

    latent_mean = (
        np.maximum(rng.normal(mean_per_event, mean_se, size=len(counts)), 0.0)
        if mean_se > 0.0
        else np.full(len(counts), mean_per_event, dtype=float)
    )
    values = np.zeros(len(counts), dtype=float)
    if event_sd is not None and float(event_sd) > 0.0:
        sd = float(event_sd)
        positive = (counts > 0) & (latent_mean > 0.0)
        aggregate_shape = np.zeros(len(counts), dtype=float)
        aggregate_scale = np.zeros(len(counts), dtype=float)
        aggregate_shape[positive] = counts[positive] * np.square(latent_mean[positive] / sd)
        aggregate_scale[positive] = np.square(sd) / latent_mean[positive]
        values[positive] = rng.gamma(aggregate_shape[positive], aggregate_scale[positive])
    else:
        shapes = counts.astype(float) * float(shape_per_event)
        positive = (shapes > 0.0) & (latent_mean > 0.0)
        scales = np.zeros(len(counts), dtype=float)
        scales[positive] = latent_mean[positive] / float(shape_per_event)
        values[positive] = rng.gamma(shapes[positive], scales[positive])
    return np.rint(np.maximum(values, 0.0)).astype(np.int64)


def _allocate_integer_total_by_weight(total: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Largest-remainder allocation with exact row totals; deterministic after draws."""
    total = np.asarray(total, dtype=np.int64)
    weights = np.asarray(weights, dtype=float)
    sums = weights.sum(axis=1)
    safe = weights.copy()
    empty = sums <= 0.0
    safe[empty, -1] = 1.0
    sums = safe.sum(axis=1)
    raw = total[:, None] * safe / sums[:, None]
    out = np.floor(raw).astype(np.int64)
    remainder = total - out.sum(axis=1)
    frac = raw - out
    rows = np.arange(len(total))
    for _ in range(weights.shape[1]):
        needs = remainder > 0
        if not np.any(needs):
            break
        choices = np.argmax(frac, axis=1)
        rr = rows[needs]
        cc = choices[needs]
        out[rr, cc] += 1
        frac[rr, cc] = -1.0
        remainder[rr] -= 1
    return out


def _team_latent_state(
    game: GameSimulationInput,
    n: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shared_pace = rng.normal(size=n)
    script = rng.normal(size=n)
    if game.shared_scoring_log_sd > 0.0:
        sigma = float(game.shared_scoring_log_sd)
        scoring = np.exp(sigma * rng.normal(size=n) - 0.5 * sigma * sigma)
    else:
        scoring = np.ones(n, dtype=float)
    return shared_pace, script, scoring


def simulate_game(
    game: GameSimulationInput,
    *,
    simulations: int = 20_000,
    seed: int = 0,
) -> GameSimulationResult:
    """Simulate coherent football outcomes without accepting any sportsbook information."""
    validate_game_input(game)
    if simulations < 1:
        raise SimulationInputError("simulations must be positive")
    n = int(simulations)
    rng = np.random.default_rng(int(seed))
    shared_pace, script, scoring_multiplier = _team_latent_state(game, n, rng)
    rho = float(game.shared_pace_correlation)

    player_stats: dict[str, dict[str, np.ndarray]] = {
        p.player_id: {
            "pass_attempts": np.zeros(n, dtype=np.int64),
            "completions": np.zeros(n, dtype=np.int64),
            "passing_yards": np.zeros(n, dtype=np.int64),
            "passing_tds": np.zeros(n, dtype=np.int64),
            "routes": np.zeros(n, dtype=np.int64),
            "targets": np.zeros(n, dtype=np.int64),
            "receptions": np.zeros(n, dtype=np.int64),
            "receiving_yards": np.zeros(n, dtype=np.int64),
            "receiving_tds": np.zeros(n, dtype=np.int64),
            "carries": np.zeros(n, dtype=np.int64),
            "rushing_yards": np.zeros(n, dtype=np.int64),
            "rushing_tds": np.zeros(n, dtype=np.int64),
            "anytime_td": np.zeros(n, dtype=np.int64),
            "active": np.zeros(n, dtype=np.int64),
        }
        for p in game.players
    }
    team_stats: dict[str, dict[str, np.ndarray]] = {}

    for team in game.teams:
        roster = [p for p in game.players if p.team == team.team]
        active = (
            np.column_stack(
                [rng.random(n) < float(p.availability_probability) for p in roster]
            )
            if roster
            else np.empty((n, 0), dtype=bool)
        )
        for j, p in enumerate(roster):
            player_stats[p.player_id]["active"] = active[:, j].astype(np.int64)

        explicit_primary = [j for j, p in enumerate(roster) if p.is_primary_qb]
        if explicit_primary:
            primary_qb_index = explicit_primary[0]
        else:
            qb_candidates = [
                j
                for j, p in enumerate(roster)
                if p.position.upper() == "QB" and p.pass_attempt_share > 0.0
            ]
            primary_qb_index = (
                max(qb_candidates, key=lambda j: roster[j].pass_attempt_share)
                if qb_candidates
                else None
            )

        independent_pace = rng.normal(size=n)
        if (
            team.offensive_plays_gamma_shape is not None
            and team.offensive_plays_gamma_rate is not None
        ):
            shape = float(team.offensive_plays_gamma_shape)
            rate = float(team.offensive_plays_gamma_rate)
            mean_plays = shape / rate
            variance_plays = mean_plays + shape / (rate * rate)
            raw_rate = rng.gamma(shape=shape, scale=1.0 / rate, size=n)
            raw_plays = rng.poisson(raw_rate)
            raw_z = (raw_plays - mean_plays) / np.sqrt(max(variance_plays, 1e-9))
            play_z = rho * shared_pace + np.sqrt(max(0.0, 1.0 - rho * rho)) * raw_z
            plays = np.rint(mean_plays + np.sqrt(variance_plays) * play_z)
        else:
            play_z = rho * shared_pace + np.sqrt(max(0.0, 1.0 - rho * rho)) * independent_pace
            plays = np.rint(
                float(team.mean_offensive_plays) + float(team.offensive_plays_sd) * play_z
            )
        plays = np.maximum(plays, 0.0).astype(np.int64)

        trailing_signal = -script if team.team == game.home_team else script
        if team.dropback_rate_alpha is not None and team.dropback_rate_beta is not None:
            dropback_rate = rng.beta(
                float(team.dropback_rate_alpha),
                float(team.dropback_rate_beta),
                size=n,
            )
            dropback_rate = np.clip(
                dropback_rate
                + float(team.pass_rate_game_script_sensitivity) * trailing_signal,
                0.0,
                1.0,
            )
            dropbacks = rng.binomial(plays, dropback_rate)
            designed_rush_attempts = plays - dropbacks
            if (
                team.pass_attempt_outcome_alpha is not None
                and team.sack_outcome_alpha is not None
                and team.scramble_outcome_alpha is not None
            ):
                outcome_weights = np.column_stack(
                    [
                        rng.gamma(float(team.pass_attempt_outcome_alpha), 1.0, size=n),
                        rng.gamma(float(team.sack_outcome_alpha), 1.0, size=n),
                        rng.gamma(float(team.scramble_outcome_alpha), 1.0, size=n),
                    ]
                )
                dropback_alloc = _allocate_counts(dropbacks, outcome_weights, rng)
                pass_attempts = dropback_alloc[:, 0]
                sacks = dropback_alloc[:, 1]
                scrambles = dropback_alloc[:, 2]
            else:
                pass_attempts = dropbacks.copy()
                sacks = np.zeros(n, dtype=np.int64)
                scrambles = np.zeros(n, dtype=np.int64)
        else:
            pass_rate = (
                float(team.neutral_pass_rate)
                + float(team.pass_rate_game_script_sensitivity) * trailing_signal
                + float(team.pass_rate_sd) * rng.normal(size=n)
            )
            pass_rate = np.clip(pass_rate, 0.0, 1.0)
            pass_attempts = rng.binomial(plays, pass_rate)
            dropbacks = pass_attempts.copy()
            sacks = np.zeros(n, dtype=np.int64)
            scrambles = np.zeros(n, dtype=np.int64)
            designed_rush_attempts = plays - dropbacks
        rush_attempts = designed_rush_attempts + scrambles

        qb_shares = np.array([p.pass_attempt_share for p in roster], dtype=float)
        qb_weights = _weights_with_residual(qb_shares, active)
        qb_attempt_alloc = _allocate_counts(pass_attempts, qb_weights, rng)
        for j, p in enumerate(roster):
            player_stats[p.player_id]["pass_attempts"] = qb_attempt_alloc[:, j]

        modeled_routes: list[np.ndarray] = []
        for j, p in enumerate(roster):
            fixed_route = (
                float(p.route_participation)
                if p.target_share > 0.0
                or p.route_participation_alpha is not None
                or p.route_participation_beta is not None
                else 0.0
            )
            route_probability = _sample_beta_or_fixed(
                p.route_participation_alpha,
                p.route_participation_beta,
                fixed_route,
                n,
                rng,
            )
            routes = rng.binomial(dropbacks, np.clip(route_probability, 0.0, 1.0))
            routes = routes * active[:, j].astype(np.int64)
            player_stats[p.player_id]["routes"] = routes
            modeled_routes.append(routes)

        if (
            team.targetable_attempt_alpha is not None
            and team.targetable_attempt_beta is not None
        ):
            targetable_rate = rng.beta(
                float(team.targetable_attempt_alpha),
                float(team.targetable_attempt_beta),
                size=n,
            )
            team_targets = rng.binomial(pass_attempts, targetable_rate)
        else:
            team_targets = pass_attempts.copy()

        target_shares = np.array([p.target_share for p in roster], dtype=float)
        target_alphas = np.array(
            [0.0 if p.target_share_alpha is None else p.target_share_alpha for p in roster],
            dtype=float,
        )
        target_weights = _sample_weights_with_residual(
            target_shares,
            active,
            target_alphas,
            rng,
        )
        route_capacity = (
            np.column_stack(modeled_routes + [team_targets])
            if modeled_routes
            else team_targets[:, None]
        )
        target_alloc = _allocate_events_with_capacity(
            team_targets,
            target_weights,
            route_capacity,
            rng,
        )

        modeled_receptions: list[np.ndarray] = []
        modeled_receiving_yards: list[np.ndarray] = []
        for j, p in enumerate(roster):
            targets = target_alloc[:, j]
            catch_probability = _sample_beta_or_fixed(
                p.catch_alpha,
                p.catch_beta,
                float(p.catch_rate),
                n,
                rng,
            )
            receptions = rng.binomial(targets, np.clip(catch_probability, 0.0, 1.0))
            receiving_yards = _compound_yards(
                receptions,
                float(p.receiving_yards_per_reception),
                float(p.receiving_yards_shape_per_reception),
                rng,
                event_sd=p.receiving_yards_per_reception_event_sd,
                mean_se=float(p.receiving_yards_per_reception_mean_se),
            )
            player_stats[p.player_id]["targets"] = targets
            player_stats[p.player_id]["receptions"] = receptions
            player_stats[p.player_id]["receiving_yards"] = receiving_yards
            modeled_receptions.append(receptions)
            modeled_receiving_yards.append(receiving_yards)

        residual_targets = target_alloc[:, -1]
        residual_receptions = rng.binomial(residual_targets, float(team.residual_catch_rate))
        residual_receiving_yards = _compound_yards(
            residual_receptions,
            float(team.residual_yards_per_reception),
            2.0,
            rng,
        )
        rec_matrix = (
            np.column_stack(modeled_receptions + [residual_receptions])
            if modeled_receptions
            else residual_receptions[:, None]
        )
        rec_yard_matrix = (
            np.column_stack(modeled_receiving_yards + [residual_receiving_yards])
            if modeled_receiving_yards
            else residual_receiving_yards[:, None]
        )
        team_completions = rec_matrix.sum(axis=1)
        team_passing_yards = rec_yard_matrix.sum(axis=1)

        qb_completion_alloc = _allocate_events_with_capacity(
            team_completions,
            qb_weights,
            qb_attempt_alloc,
            rng,
        )
        qb_yard_weights = qb_completion_alloc.astype(float)
        no_completions = qb_yard_weights.sum(axis=1) <= 0
        qb_yard_weights[no_completions] = qb_attempt_alloc[no_completions]
        qb_passing_yards = _allocate_integer_total_by_weight(
            team_passing_yards,
            qb_yard_weights,
        )
        for j, p in enumerate(roster):
            player_stats[p.player_id]["completions"] = qb_completion_alloc[:, j]
            player_stats[p.player_id]["passing_yards"] = qb_passing_yards[:, j]

        carry_shares = np.array([p.carry_share for p in roster], dtype=float)
        carry_alphas = np.array(
            [
                0.0 if p.designed_carry_share_alpha is None else p.designed_carry_share_alpha
                for p in roster
            ],
            dtype=float,
        )
        carry_weights = _sample_weights_with_residual(
            carry_shares,
            active,
            carry_alphas,
            rng,
        )
        carry_alloc = _allocate_counts(designed_rush_attempts, carry_weights, rng)
        if np.any(scrambles > 0):
            if primary_qb_index is None:
                carry_alloc[:, -1] += scrambles
            else:
                primary_active = active[:, primary_qb_index].astype(np.int64)
                assigned_scrambles = scrambles * primary_active
                carry_alloc[:, primary_qb_index] += assigned_scrambles
                carry_alloc[:, -1] += scrambles - assigned_scrambles

        modeled_rush_yards: list[np.ndarray] = []
        for j, p in enumerate(roster):
            carries = carry_alloc[:, j]
            rushing_yards = _compound_yards(
                carries,
                float(p.rushing_yards_per_carry),
                float(p.rushing_yards_shape_per_carry),
                rng,
                event_sd=p.rushing_yards_per_carry_event_sd,
                mean_se=float(p.rushing_yards_per_carry_mean_se),
            )
            player_stats[p.player_id]["carries"] = carries
            player_stats[p.player_id]["rushing_yards"] = rushing_yards
            modeled_rush_yards.append(rushing_yards)
        residual_carries = carry_alloc[:, -1]
        residual_rushing_yards = _compound_yards(
            residual_carries,
            float(team.residual_yards_per_carry),
            2.0,
            rng,
        )
        team_rushing_yards = (
            np.column_stack(modeled_rush_yards + [residual_rushing_yards]).sum(axis=1)
            if modeled_rush_yards
            else residual_rushing_yards
        )

        passing_tds = rng.poisson(float(team.expected_passing_tds) * scoring_multiplier)
        passing_tds = np.minimum(passing_tds, team_completions)
        receiving_td_shares = np.array(
            [p.receiving_td_share for p in roster],
            dtype=float,
        )
        receiving_td_alphas = np.array(
            [
                0.0
                if p.receiving_td_allocation_alpha is None
                else p.receiving_td_allocation_alpha
                for p in roster
            ],
            dtype=float,
        )
        receiving_td_weights = _sample_weights_with_residual(
            receiving_td_shares,
            active,
            receiving_td_alphas,
            rng,
        )
        receiving_td_alloc = _allocate_events_with_capacity(
            passing_tds,
            receiving_td_weights,
            rec_matrix,
            rng,
        )
        passing_tds = receiving_td_alloc.sum(axis=1)

        passing_td_shares = np.array(
            [
                p.pass_attempt_share if p.passing_td_share is None else p.passing_td_share
                for p in roster
            ],
            dtype=float,
        )
        passing_td_alphas = np.array(
            [
                0.0 if p.passing_td_allocation_alpha is None else p.passing_td_allocation_alpha
                for p in roster
            ],
            dtype=float,
        )
        qb_td_weights = _sample_weights_with_residual(
            passing_td_shares,
            active,
            passing_td_alphas,
            rng,
        )
        qb_td_alloc = _allocate_events_with_capacity(
            passing_tds,
            qb_td_weights,
            qb_completion_alloc,
            rng,
        )
        for j, p in enumerate(roster):
            player_stats[p.player_id]["receiving_tds"] = receiving_td_alloc[:, j]
            player_stats[p.player_id]["passing_tds"] = qb_td_alloc[:, j]

        rushing_tds = rng.poisson(float(team.expected_rushing_tds) * scoring_multiplier)
        rushing_tds = np.minimum(rushing_tds, rush_attempts)
        rushing_td_shares = np.array([p.rushing_td_share for p in roster], dtype=float)
        rushing_td_alphas = np.array(
            [
                0.0 if p.rushing_td_allocation_alpha is None else p.rushing_td_allocation_alpha
                for p in roster
            ],
            dtype=float,
        )
        rushing_td_weights = _sample_weights_with_residual(
            rushing_td_shares,
            active,
            rushing_td_alphas,
            rng,
        )
        rushing_td_alloc = _allocate_events_with_capacity(
            rushing_tds,
            rushing_td_weights,
            carry_alloc,
            rng,
        )
        rushing_tds = rushing_td_alloc.sum(axis=1)
        for j, p in enumerate(roster):
            player_stats[p.player_id]["rushing_tds"] = rushing_td_alloc[:, j]
            player_stats[p.player_id]["anytime_td"] = (
                player_stats[p.player_id]["receiving_tds"]
                + player_stats[p.player_id]["rushing_tds"]
            )

        route_matrix = (
            np.column_stack(modeled_routes)
            if modeled_routes
            else np.empty((n, 0), dtype=np.int64)
        )
        team_stats[team.team] = {
            "offensive_plays": plays,
            "dropbacks": dropbacks,
            "pass_attempts": pass_attempts,
            "sacks": sacks,
            "scrambles": scrambles,
            "designed_rush_attempts": designed_rush_attempts,
            "rush_attempts": rush_attempts,
            "modeled_qb_pass_attempts": qb_attempt_alloc[:, :-1].sum(axis=1),
            "residual_qb_pass_attempts": qb_attempt_alloc[:, -1],
            "modeled_routes": route_matrix.sum(axis=1),
            "team_targets": team_targets,
            "targets": target_alloc[:, :-1].sum(axis=1),
            "residual_targets": residual_targets,
            "completions": team_completions,
            "modeled_receptions": rec_matrix[:, :-1].sum(axis=1),
            "residual_receptions": residual_receptions,
            "passing_yards": team_passing_yards,
            "modeled_receiving_yards": rec_yard_matrix[:, :-1].sum(axis=1),
            "residual_receiving_yards": residual_receiving_yards,
            "modeled_carries": carry_alloc[:, :-1].sum(axis=1),
            "residual_carries": residual_carries,
            "rushing_yards": team_rushing_yards,
            "passing_tds": passing_tds,
            "modeled_receiving_tds": receiving_td_alloc[:, :-1].sum(axis=1),
            "residual_receiving_tds": receiving_td_alloc[:, -1],
            "modeled_qb_passing_tds": qb_td_alloc[:, :-1].sum(axis=1),
            "residual_qb_passing_tds": qb_td_alloc[:, -1],
            "rushing_tds": rushing_tds,
            "modeled_rushing_tds": rushing_td_alloc[:, :-1].sum(axis=1),
            "residual_rushing_tds": rushing_td_alloc[:, -1],
        }

    return GameSimulationResult(
        game_id=game.game_id,
        model_version=game.model_version,
        data_horizon=game.data_horizon,
        seed=int(seed),
        simulations=n,
        players=game.players,
        player_stats=player_stats,
        team_stats=team_stats,
    )


def american_to_implied_probability(odds: float) -> float:
    odds = _finite(odds, "american odds")
    if odds == 0.0:
        raise ValueError("American odds cannot be zero")
    if odds > 0.0:
        return 100.0 / (odds + 100.0)
    return (-odds) / ((-odds) + 100.0)


def probability_to_american(probability: float) -> float | None:
    p = float(probability)
    if not isfinite(p) or p <= 0.0 or p >= 1.0:
        return None
    if p < 0.5:
        return 100.0 * (1.0 - p) / p
    return -100.0 * p / (1.0 - p)


def _fair_side_probabilities(p_over: float, p_under: float) -> tuple[float | None, float | None]:
    non_push = p_over + p_under
    if non_push <= 0.0:
        return None, None
    return p_over / non_push, p_under / non_push


def evaluate_distribution(
    samples: Sequence[float] | np.ndarray,
    *,
    market_line: float | None = None,
    discrete: bool = False,
    interval_level: float = 0.80,
) -> DistributionSummary:
    """Summarize a simulated distribution and independently evaluate an arbitrary line."""
    values = np.asarray(samples, dtype=float)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("samples must be a nonempty finite one-dimensional distribution")
    if not 0.0 < interval_level < 1.0:
        raise ValueError("interval_level must be in (0, 1)")
    alpha = (1.0 - interval_level) / 2.0
    if discrete:
        median = float(np.quantile(values, 0.5, method="inverted_cdf"))
    else:
        median = float(np.quantile(values, 0.5))
    fair_line = median
    p_over = p_under = p_push = None
    fair_over = fair_under = None
    line_value = None if market_line is None else _finite(market_line, "market_line")
    if line_value is not None:
        p_over = float(np.mean(values > line_value))
        p_under = float(np.mean(values < line_value))
        p_push = float(np.mean(values == line_value))
        over_conditional, under_conditional = _fair_side_probabilities(p_over, p_under)
        fair_over = (
            probability_to_american(over_conditional) if over_conditional is not None else None
        )
        fair_under = (
            probability_to_american(under_conditional) if under_conditional is not None else None
        )
    return DistributionSummary(
        model_mean=float(np.mean(values)),
        model_median=median,
        levline_fair_line=fair_line,
        standard_deviation=float(np.std(values, ddof=0)),
        prediction_interval_lower=float(np.quantile(values, alpha)),
        prediction_interval_upper=float(np.quantile(values, 1.0 - alpha)),
        prediction_interval_level=float(interval_level),
        market_line=line_value,
        p_over=p_over,
        p_under=p_under,
        p_push=p_push,
        fair_over_american_odds=fair_over,
        fair_under_american_odds=fair_under,
    )


def _td_distribution(samples: np.ndarray) -> dict[int, float]:
    values, counts = np.unique(np.asarray(samples, dtype=np.int64), return_counts=True)
    total = float(counts.sum())
    return {int(v): float(c / total) for v, c in zip(values, counts, strict=True)}


def _market_no_vig_over_probability(quote: MarketQuote | None) -> float | None:
    if quote is None or quote.over_american_odds is None or quote.under_american_odds is None:
        return None
    over = american_to_implied_probability(quote.over_american_odds)
    under = american_to_implied_probability(quote.under_american_odds)
    return over / (over + under)


def build_forecasts(
    result: GameSimulationResult,
    *,
    market_quotes: Mapping[tuple[str, str], MarketQuote] | None = None,
    forecast_timestamp: str | None = None,
    interval_level: float = 0.80,
) -> list[ForecastRecord]:
    """Create canonical player-prop forecasts from already-completed pure simulations."""
    if forecast_timestamp is None:
        forecast_timestamp = datetime.now(timezone.utc).isoformat()
    quotes = market_quotes or {}
    forecasts: list[ForecastRecord] = []
    for player in result.players:
        position = player.position.upper()
        for prop_type in SUPPORTED_PROPS[position]:
            samples = result.player_stats[player.player_id][prop_type]
            quote = quotes.get((player.player_id, prop_type))
            summary = evaluate_distribution(
                samples,
                market_line=None if quote is None else quote.line,
                discrete=prop_type in DISCRETE_PROPS,
                interval_level=interval_level,
            )
            is_td = prop_type in TD_PROPS
            p1 = float(np.mean(samples >= 1)) if is_td else None
            p2 = float(np.mean(samples >= 2)) if is_td else None
            expected_tds = float(np.mean(samples)) if is_td else None
            anytime_fair = probability_to_american(p1) if prop_type == "anytime_td" else None
            no_vig_over = _market_no_vig_over_probability(quote)
            probability_edge = (
                None
                if no_vig_over is None or summary.p_over is None
                else float(summary.p_over - no_vig_over)
            )
            line_edge = (
                None
                if summary.market_line is None
                else float(summary.levline_fair_line - summary.market_line)
            )
            forecasts.append(
                ForecastRecord(
                    forecast_timestamp=forecast_timestamp,
                    data_horizon=result.data_horizon,
                    model_version=result.model_version,
                    research_label=RESEARCH_LABEL,
                    game_id=result.game_id,
                    player_id=player.player_id,
                    player=player.player,
                    position=position,
                    team=player.team,
                    opponent=player.opponent,
                    prop_type=prop_type,
                    model_mean=summary.model_mean,
                    model_median=summary.model_median,
                    levline_fair_line=summary.levline_fair_line,
                    standard_deviation=summary.standard_deviation,
                    prediction_interval_lower=summary.prediction_interval_lower,
                    prediction_interval_upper=summary.prediction_interval_upper,
                    prediction_interval_level=summary.prediction_interval_level,
                    market_line=summary.market_line,
                    p_over=summary.p_over,
                    p_under=summary.p_under,
                    p_push=summary.p_push,
                    fair_over_american_odds=summary.fair_over_american_odds,
                    fair_under_american_odds=summary.fair_under_american_odds,
                    expected_tds=expected_tds,
                    probability_1_plus_td=p1,
                    probability_2_plus_td=p2,
                    td_count_distribution=_td_distribution(samples) if is_td else None,
                    fair_anytime_american_odds=anytime_fair,
                    market_over_american_odds=None if quote is None else quote.over_american_odds,
                    market_under_american_odds=None if quote is None else quote.under_american_odds,
                    market_no_vig_over_probability=no_vig_over,
                    probability_edge=probability_edge,
                    line_edge=line_edge,
                    data_quality_state=player.data_quality_state,
                )
            )
    return forecasts


def forecasts_as_dicts(forecasts: Sequence[ForecastRecord]) -> list[dict]:
    return [asdict(record) for record in forecasts]

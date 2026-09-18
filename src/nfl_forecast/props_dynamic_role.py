from __future__ import annotations

"""Strictly lagged snap-role state for LevLine Props 2.0 research challengers.

This module never calls offensive snap share a route count. It uses prior-game
offensive participation as an observable proxy for current role and exposes only
multipliers accepted by the existing opportunity handoff.

Two distinct uses are supported:
- route level: player-specific participation level relative to the preregistered
  position route prior, because V1 has no observed historical routes in the replay;
- carry/target trend: short-horizon snap-share state relative to the longer-horizon
  state, because V1 already has lagged carry/target allocation evidence.

All target-game and future-game rows are rejected.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

ENGINE_VERSION = "levline-props-dynamic-role-v0.1.0"
RESEARCH_LABEL = "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE"

POSITION_SNAP_PRIOR = {
    "RB": 0.55,
    "WR": 0.90,
    "TE": 0.75,
}
ROUTE_PRIOR = {
    "RB": 0.55,
    "WR": 0.90,
    "TE": 0.75,
}
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
RECEIVING_POSITIONS = frozenset({"RB", "WR", "TE"})
CARRY_POSITIONS = frozenset({"RB"})
PRIOR_EQUIVALENT_GAMES = 2.0
SHORT_HALF_LIFE_GAMES = 2.0
LONG_HALF_LIFE_GAMES = 8.0
MIN_MULTIPLIER = 0.20
MAX_MULTIPLIER = 2.00


class DynamicRoleError(ValueError):
    pass


@dataclass(frozen=True)
class DynamicRoleEstimate:
    player_id: str
    position: str
    history_games: int
    short_snap_share: float
    long_snap_share: float
    route_level_multiplier: float
    target_trend_multiplier: float
    carry_trend_multiplier: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_id(value: Any) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return bool(text) and text.lower() not in {"nan", "<na>", "none", "null"}


def _team(value: Any) -> str:
    text = str(value or "").upper().strip()
    return {"JAC": "JAX", "LA": "LAR"}.get(text, text)


def _effective_weights(n: int, half_life_games: float) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return np.power(0.5, age / float(half_life_games))


def _posterior_share(values: np.ndarray, *, prior: float, half_life_games: float) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return float(prior)
    weights = _effective_weights(len(values), half_life_games)
    numerator = float(np.dot(values, weights)) + PRIOR_EQUIVALENT_GAMES * float(prior)
    denominator = float(weights.sum()) + PRIOR_EQUIVALENT_GAMES
    return float(np.clip(numerator / denominator, 0.0, 1.0))


def _clip_multiplier(value: float) -> float:
    if not math.isfinite(value):
        return 1.0
    return float(np.clip(value, MIN_MULTIPLIER, MAX_MULTIPLIER))


def normalize_lagged_snap_history(
    snap_counts: pd.DataFrame,
    *,
    season: int,
    week: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return one strictly prior player/game offensive snap-share row.

    Prefer provider offense percentage. If unavailable, derive share from the
    maximum offensive snap count on the same team/game, which corresponds to the
    team offensive-play exposure for full-participation players.
    """

    if snap_counts is None or snap_counts.empty:
        return pd.DataFrame(), {"status": "unavailable", "reason": "empty_snap_counts"}

    required = {"game_id", "season", "week", "player_id"}
    missing = required - set(snap_counts.columns)
    if missing:
        raise DynamicRoleError(f"snap history missing fields: {sorted(missing)}")

    work = snap_counts.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["player_id"] = work["player_id"].astype("string").fillna("").str.strip()
    work = work[
        work["season"].notna()
        & work["week"].notna()
        & work["player_id"].map(_valid_id)
    ].copy()
    unsafe = (work["season"] > int(season)) | (
        work["season"].eq(int(season)) & work["week"].ge(int(week))
    )
    work = work[~unsafe].copy()
    if work.empty:
        return pd.DataFrame(), {
            "status": "unavailable",
            "reason": "no_strictly_lagged_snap_rows",
            "target_season": int(season),
            "target_week": int(week),
        }

    if "team" in work.columns:
        work["team"] = work["team"].map(_team)
    else:
        work["team"] = ""

    position_col = next(
        (c for c in ("position", "position_group") if c in work.columns),
        None,
    )
    if position_col is not None:
        work["position"] = (
            work[position_col].astype("string").fillna("").str.upper().str.strip()
        )
    else:
        work["position"] = ""

    pct_col = next(
        (
            c
            for c in (
                "offense_pct",
                "offensive_snap_pct",
                "offense_snaps_pct",
                "snap_share",
            )
            if c in work.columns
        ),
        None,
    )
    snap_col = next(
        (c for c in ("offense_snaps", "offensive_snaps", "off_snaps") if c in work.columns),
        None,
    )

    share = pd.Series(np.nan, index=work.index, dtype=float)
    source = "none"
    if pct_col is not None:
        pct = pd.to_numeric(work[pct_col], errors="coerce")
        pct = np.where(pct > 1.0, pct / 100.0, pct)
        share = pd.Series(pct, index=work.index, dtype=float)
        source = f"provider:{pct_col}"

    derived_count = 0
    if snap_col is not None:
        snaps = pd.to_numeric(work[snap_col], errors="coerce")
        if share.isna().any():
            if work["team"].ne("").any():
                denom = (
                    pd.DataFrame(
                        {
                            "game_id": work["game_id"].astype(str),
                            "team": work["team"],
                            "snaps": snaps,
                        },
                        index=work.index,
                    )
                    .groupby(["game_id", "team"], sort=False)["snaps"]
                    .transform("max")
                )
            else:
                denom = (
                    pd.DataFrame(
                        {"game_id": work["game_id"].astype(str), "snaps": snaps},
                        index=work.index,
                    )
                    .groupby("game_id", sort=False)["snaps"]
                    .transform("max")
                )
            derived = snaps / denom.replace(0.0, np.nan)
            fill = share.isna() & derived.notna()
            share.loc[fill] = derived.loc[fill]
            derived_count = int(fill.sum())
            source = (
                f"{source}+derived_team_game_snap_ratio" if source != "none"
                else "derived_team_game_snap_ratio"
            )

    work["snap_share"] = pd.to_numeric(share, errors="coerce")
    work = work[work["snap_share"].between(0.0, 1.0, inclusive="both")].copy()
    if work.empty:
        return pd.DataFrame(), {
            "status": "unavailable",
            "reason": "no_valid_snap_share_rows",
        }

    # Collapse accidental duplicate source rows without inflating game evidence.
    out = (
        work.sort_values(["season", "week", "game_id"])
        .groupby(["game_id", "season", "week", "team", "player_id"], as_index=False, sort=False)
        .agg(
            position=("position", "last"),
            snap_share=("snap_share", "max"),
        )
    )
    return out, {
        "status": "available",
        "source": source,
        "strictly_lagged": True,
        "target_season": int(season),
        "target_week": int(week),
        "rows": int(len(out)),
        "unique_players": int(out["player_id"].nunique()),
        "derived_share_rows": derived_count,
    }


def build_dynamic_role_adjustments(
    snap_counts: pd.DataFrame,
    current_players: pd.DataFrame,
    *,
    season: int,
    week: int,
    team: str,
    route_prior_means: Mapping[str, float] | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    """Build role multipliers for one current offense from prior-game snap shares."""

    history, history_audit = normalize_lagged_snap_history(
        snap_counts,
        season=season,
        week=week,
    )
    if current_players is None or current_players.empty:
        raise DynamicRoleError("current_players must be non-empty")

    team_code = _team(team)
    current = current_players.copy()
    current["player_id"] = current["player_id"].astype("string").fillna("").str.strip()
    current["position"] = current["position"].astype("string").fillna("").str.upper().str.strip()
    if "team" in current.columns:
        current["team"] = current["team"].map(_team)
        current = current[current["team"].eq(team_code)].copy()

    route_priors = {**ROUTE_PRIOR}
    for key, value in (route_prior_means or {}).items():
        route_priors[str(key).upper()] = float(value)

    adjustments: dict[str, dict[str, float]] = {}
    estimates: list[dict[str, Any]] = []
    fallback_players: list[str] = []

    if history.empty:
        return {}, {
            "engine_version": ENGINE_VERSION,
            "research_label": RESEARCH_LABEL,
            "history": history_audit,
            "adjusted_players": 0,
            "fallback_player_ids": sorted(current["player_id"].astype(str).tolist()),
            "estimates": [],
        }

    team_history = history[history["team"].eq(team_code)].copy()
    if team_history.empty:
        team_history = history

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
        short_share = _posterior_share(
            values, prior=prior, half_life_games=SHORT_HALF_LIFE_GAMES
        )
        long_share = _posterior_share(
            values, prior=prior, half_life_games=LONG_HALF_LIFE_GAMES
        )
        trend = _clip_multiplier(short_share / max(long_share, 1e-6))

        route_multiplier = 1.0
        target_multiplier = 1.0
        carry_multiplier = 1.0
        if position in RECEIVING_POSITIONS:
            route_prior = float(route_priors[position])
            route_multiplier = _clip_multiplier(short_share / max(route_prior, 1e-6))
            # Target allocation already contains lagged target evidence. Apply only
            # the recent-vs-long role trend so snap share does not double-count level.
            target_multiplier = trend
        if position in CARRY_POSITIONS:
            # Carry allocation already contains lagged carry evidence; use trend only.
            carry_multiplier = trend

        adjustment = {}
        if position in RECEIVING_POSITIONS:
            adjustment["route_role_multiplier"] = route_multiplier
            adjustment["target_role_multiplier"] = target_multiplier
        if position in CARRY_POSITIONS:
            adjustment["carry_role_multiplier"] = carry_multiplier
        if adjustment:
            adjustments[pid] = adjustment

        estimates.append(
            DynamicRoleEstimate(
                player_id=pid,
                position=position,
                history_games=int(values.size),
                short_snap_share=short_share,
                long_snap_share=long_share,
                route_level_multiplier=route_multiplier,
                target_trend_multiplier=target_multiplier,
                carry_trend_multiplier=carry_multiplier,
                source=str(history_audit.get("source", "lagged_snap_share")),
            ).to_dict()
        )

    return adjustments, {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "history": history_audit,
        "team": team_code,
        "adjusted_players": len(adjustments),
        "fallback_player_ids": sorted(fallback_players),
        "estimates": estimates,
        "hyperparameters": {
            "prior_equivalent_games": PRIOR_EQUIVALENT_GAMES,
            "short_half_life_games": SHORT_HALF_LIFE_GAMES,
            "long_half_life_games": LONG_HALF_LIFE_GAMES,
            "min_multiplier": MIN_MULTIPLIER,
            "max_multiplier": MAX_MULTIPLIER,
            "position_snap_prior": POSITION_SNAP_PRIOR,
            "route_prior": route_priors,
        },
        "target_game_rows_used": 0,
    }

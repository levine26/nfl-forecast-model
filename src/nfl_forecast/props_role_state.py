from __future__ import annotations

"""Point-in-time snap-share role challenger for LevLine Props.

This module converts strictly lagged offensive snap-share evidence into route-role
multipliers that plug into the existing opportunity-model role-adjustment contract.
It does not use target-game snaps, target-game outcomes, sportsbook results, or 2026
outcomes for architecture/hyperparameter selection.

Rationale:
- nflverse/PFR snap counts update repeatedly during the season;
- the frozen historical Props reconstruction used fixed RB/WR/TE route priors;
- snap share is not treated as a route count, only as a pregame workload proxy.

The default four-game window matches the canonical player-state contract's
prior_snap_share_4 concept and is fixed before challenger evaluation.
"""

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .props_player_state import normalize_team_code

ENGINE_VERSION = "levline-props-snap-route-role-v0.1.0"
RESEARCH_LABEL = "LEVLINE PROPS 2.0 RESEARCH CHALLENGER"
SUPPORTED_ROUTE_POSITIONS = frozenset({"RB", "WR", "TE"})
DEFAULT_LOOKBACK_GAMES = 4
MIN_PRIOR_GAMES = 2


class SnapRoleError(ValueError):
    pass


@dataclass(frozen=True)
class SnapRoleBuild:
    adjustments_by_team: dict[str, dict[str, dict[str, float]]]
    audit: dict[str, Any]


def _first_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def _valid_id(value: Any) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return bool(text) and text.lower() not in {"nan", "<na>", "none", "null"}


def _normalized_snap_share(frame: pd.DataFrame) -> pd.Series:
    pct_col = _first_column(frame, ("offense_pct", "offensive_pct", "off_pct"))
    if pct_col is not None:
        values = pd.to_numeric(frame[pct_col], errors="coerce")
        finite = values[np.isfinite(values)]
        if not finite.empty and float(finite.max()) > 1.5:
            values = values / 100.0
        return values.clip(lower=0.0, upper=1.0)

    snap_col = _first_column(frame, ("offense_snaps", "offensive_snaps", "off_snaps"))
    if snap_col is None:
        raise SnapRoleError("snap counts require offense_pct or offense_snaps")
    snaps = pd.to_numeric(frame[snap_col], errors="coerce")
    if "game_id" not in frame.columns or "team" not in frame.columns:
        raise SnapRoleError("deriving snap share requires game_id and team")
    team_max = (
        pd.DataFrame(
            {
                "game_id": frame["game_id"].astype(str),
                "team": frame["team"].map(normalize_team_code),
                "_snaps": snaps,
            }
        )
        .groupby(["game_id", "team"], sort=False)["_snaps"]
        .transform("max")
    )
    return (snaps / team_max.replace(0.0, np.nan)).clip(lower=0.0, upper=1.0)


def _prepare_snap_history(
    snap_counts: pd.DataFrame,
    *,
    season: int,
    week: int,
) -> pd.DataFrame:
    required = {"game_id", "season", "week", "player_id", "team"}
    missing = required - set(snap_counts.columns)
    if missing:
        raise SnapRoleError(f"snap counts missing fields: {sorted(missing)}")
    work = snap_counts.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["player_id"] = work["player_id"].astype("string").fillna("").str.strip()
    work["team"] = work["team"].map(normalize_team_code)
    work["_snap_share"] = _normalized_snap_share(work)
    safe = (
        work["season"].notna()
        & work["week"].notna()
        & work["player_id"].map(_valid_id)
        & work["_snap_share"].notna()
        & (
            work["season"].lt(int(season))
            | (work["season"].eq(int(season)) & work["week"].lt(int(week)))
        )
    )
    work = work[safe].copy()
    work["season"] = work["season"].astype(int)
    work["week"] = work["week"].astype(int)
    return work.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def build_lagged_snap_route_adjustments(
    snap_counts: pd.DataFrame,
    player_state: pd.DataFrame,
    *,
    season: int,
    week: int,
    route_prior_means: Mapping[str, float],
    lookback_games: int = DEFAULT_LOOKBACK_GAMES,
    minimum_prior_games: int = MIN_PRIOR_GAMES,
) -> SnapRoleBuild:
    """Create route-role multipliers from strictly prior offensive snap shares.

    For a receiver-eligible player with enough lagged games:

        route_role_multiplier = mean(last-N offensive snap share) / position route prior

    The existing opportunity layer then applies that multiplier to the route prior
    and performs team-level availability/route-slot reconciliation.

    This intentionally leaves target and carry multipliers unchanged so the first
    challenger isolates the fixed-route-prior weakness rather than simultaneously
    changing every usage channel.
    """

    if int(lookback_games) < 1:
        raise SnapRoleError("lookback_games must be positive")
    if int(minimum_prior_games) < 1 or int(minimum_prior_games) > int(lookback_games):
        raise SnapRoleError("minimum_prior_games must be within the lookback window")

    required_state = {"player_id", "position", "team"}
    missing = required_state - set(player_state.columns)
    if missing:
        raise SnapRoleError(f"player_state missing fields: {sorted(missing)}")

    priors = {str(k).upper(): float(v) for k, v in route_prior_means.items()}
    for position in SUPPORTED_ROUTE_POSITIONS:
        value = priors.get(position)
        if value is None or not math.isfinite(value) or not 0.0 < value < 1.0:
            raise SnapRoleError(f"route prior for {position} must be finite within (0,1)")

    history = _prepare_snap_history(snap_counts, season=season, week=week)
    current = player_state.copy()
    current["player_id"] = current["player_id"].astype("string").fillna("").str.strip()
    current["position"] = current["position"].astype(str).str.upper().str.strip()
    current["team"] = current["team"].map(normalize_team_code)

    adjustments: dict[str, dict[str, dict[str, float]]] = {}
    player_audit: dict[str, Any] = {}
    used = 0
    insufficient = 0
    missing_history = 0

    for row in current.itertuples(index=False):
        player_id = str(row.player_id)
        position = str(row.position).upper()
        team = normalize_team_code(row.team)
        if position not in SUPPORTED_ROUTE_POSITIONS:
            continue

        rows = history[history["player_id"].astype(str).eq(player_id)].tail(int(lookback_games))
        if rows.empty:
            missing_history += 1
            player_audit[player_id] = {
                "status": "no_prior_snap_rows",
                "position": position,
                "team": team,
            }
            continue

        positive = rows[pd.to_numeric(rows["_snap_share"], errors="coerce").gt(0.0)]
        if len(positive) < int(minimum_prior_games):
            insufficient += 1
            player_audit[player_id] = {
                "status": "insufficient_positive_prior_games",
                "position": position,
                "team": team,
                "prior_rows": int(len(rows)),
                "positive_prior_rows": int(len(positive)),
            }
            continue

        share = float(pd.to_numeric(rows["_snap_share"], errors="coerce").dropna().mean())
        if not math.isfinite(share) or share <= 0.0:
            insufficient += 1
            continue

        base = float(priors[position])
        multiplier = min(max(share / base, 0.0), 1.0 / base)
        adjustments.setdefault(team, {})[player_id] = {
            "route_role_multiplier": float(multiplier)
        }
        used += 1
        player_audit[player_id] = {
            "status": "applied",
            "position": position,
            "team": team,
            "lagged_games_used": int(len(rows)),
            "mean_lagged_snap_share": share,
            "position_route_prior": base,
            "route_role_multiplier": float(multiplier),
            "last_evidence_season": int(rows.iloc[-1]["season"]),
            "last_evidence_week": int(rows.iloc[-1]["week"]),
        }

    return SnapRoleBuild(
        adjustments_by_team=adjustments,
        audit={
            "engine_version": ENGINE_VERSION,
            "research_label": RESEARCH_LABEL,
            "history_policy": "STRICTLY_PRIOR_WEEK",
            "target_season": int(season),
            "target_week": int(week),
            "lookback_games": int(lookback_games),
            "minimum_prior_games": int(minimum_prior_games),
            "players_adjusted": int(used),
            "players_without_history": int(missing_history),
            "players_with_insufficient_history": int(insufficient),
            "target_week_rows_used": 0,
            "completed_2026_outcomes_used_for_model_selection": 0,
            "adjustment_scope": "route_role_multiplier_only",
            "players": player_audit,
        },
    )

from __future__ import annotations

"""Leakage-safe player-state engineering for LevLine challenger research.

The module is intentionally research-only. Stable nflverse IDs are required for player
value. Current-game performance is used only to update state for later games; pregame
features are lagged and never see current-game snaps, workload, EPA, or outcomes.
"""

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

TEAM_NORMALIZATION = {"JAC": "JAX"}
LEGACY_FRANCHISE_CODES = {"OAK", "SD", "STL"}
ROLE_SHRINKAGE = {"qb": 150.0, "target": 45.0, "rush": 65.0}
ROLE_ORDER = ("qb", "target", "rush")


@dataclass(frozen=True)
class PlayerStateBuild:
    player_game_roles: pd.DataFrame
    player_state: pd.DataFrame
    team_pregame_state: pd.DataFrame
    audit: dict[str, Any]


def normalize_team_code(value: Any) -> str:
    code = str(value or "").upper().strip()
    return TEAM_NORMALIZATION.get(code, code)


def _number(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype="string")
    return frame[column].astype("string").fillna("")


def _valid_id(series: pd.Series) -> pd.Series:
    value = series.astype("string").fillna("").str.strip()
    return value.ne("") & value.ne("<NA>") & value.str.lower().ne("nan")


def _normalized_name(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.lower().str.replace(r"[^a-z]", "", regex=True)


def _base_play_frame(pbp: pd.DataFrame) -> pd.DataFrame:
    required = {"game_id", "season", "week", "posteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise ValueError(f"PBP missing player-state keys: {sorted(missing)}")
    work = pbp.copy()
    work["season"] = pd.to_numeric(work.season, errors="coerce")
    work["week"] = pd.to_numeric(work.week, errors="coerce")
    work = work[work.season.notna() & work.week.notna() & work.posteam.notna()].copy()
    work["season"] = work.season.astype(int)
    work["week"] = work.week.astype(int)
    work["team"] = work.posteam.map(normalize_team_code)
    work["epa_value"] = _number(work, "epa", np.nan)
    work["success_value"] = _number(work, "success", np.nan)
    return work


def _role_rows(
    work: pd.DataFrame,
    *,
    role: str,
    id_col: str,
    name_col: str,
    opportunity_mask: pd.Series,
) -> pd.DataFrame:
    player_id = _text(work, id_col)
    mask = opportunity_mask.fillna(False) & _valid_id(player_id)
    role_frame = work.loc[mask, ["game_id", "season", "week", "team", "epa_value", "success_value"]].copy()
    role_frame["player_id"] = player_id.loc[mask].astype(str).str.strip()
    role_frame["player_name"] = _text(work, name_col).loc[mask].astype(str)
    role_frame["role"] = role
    role_frame["opportunities"] = 1.0
    role_frame["epa_sum"] = pd.to_numeric(role_frame.epa_value, errors="coerce").fillna(0.0)
    role_frame["success_sum"] = pd.to_numeric(role_frame.success_value, errors="coerce").fillna(0.0)
    role_frame["air_yards_sum"] = 0.0
    role_frame["air_yards_n"] = 0.0
    if role == "target" and "air_yards" in work.columns:
        air = pd.to_numeric(work.loc[mask, "air_yards"], errors="coerce")
        role_frame["air_yards_sum"] = air.fillna(0.0).to_numpy()
        role_frame["air_yards_n"] = air.notna().astype(float).to_numpy()
    return role_frame.drop(columns=["epa_value", "success_value"])


def build_player_game_roles(pbp: pd.DataFrame) -> pd.DataFrame:
    """Aggregate stable-ID QB/target/rush opportunities to player-game-role rows."""
    work = _base_play_frame(pbp)
    pass_attempt = _number(work, "pass_attempt").eq(1)
    sack = _number(work, "sack").eq(1)
    rush_attempt = _number(work, "rush_attempt").eq(1)

    role_frames = [
        _role_rows(
            work,
            role="qb",
            id_col="passer_player_id",
            name_col="passer_player_name",
            opportunity_mask=pass_attempt | sack,
        ),
        _role_rows(
            work,
            role="target",
            id_col="receiver_player_id",
            name_col="receiver_player_name",
            opportunity_mask=_valid_id(_text(work, "receiver_player_id")),
        ),
        _role_rows(
            work,
            role="rush",
            id_col="rusher_player_id",
            name_col="rusher_player_name",
            opportunity_mask=rush_attempt,
        ),
    ]
    combined = pd.concat(role_frames, ignore_index=True)
    if combined.empty:
        return combined
    keys = ["game_id", "season", "week", "team", "player_id", "role"]
    grouped = (
        combined.groupby(keys, as_index=False, sort=False)
        .agg(
            player_name=("player_name", "last"),
            opportunities=("opportunities", "sum"),
            epa_sum=("epa_sum", "sum"),
            success_sum=("success_sum", "sum"),
            air_yards_sum=("air_yards_sum", "sum"),
            air_yards_n=("air_yards_n", "sum"),
        )
    )
    return grouped.sort_values(["season", "week", "game_id", "team", "role", "player_id"]).reset_index(drop=True)


def add_chronological_player_values(
    player_game_roles: pd.DataFrame,
    *,
    shrinkage: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Add empirical-Bayes role value using only information before each game."""
    if player_game_roles.empty:
        return player_game_roles.copy()
    strength = {**ROLE_SHRINKAGE, **(shrinkage or {})}
    frame = player_game_roles.copy().sort_values(
        ["season", "week", "game_id", "role", "player_id"]
    )

    # League role priors advance once per week, preventing Sunday night information
    # from leaking into an earlier game from the same historical week.
    blocks = (
        frame.groupby(["role", "season", "week"], as_index=False)
        .agg(block_opportunities=("opportunities", "sum"), block_epa=("epa_sum", "sum"), block_success=("success_sum", "sum"))
        .sort_values(["role", "season", "week"])
    )
    for value, source in (("prior_role_opportunities", "block_opportunities"), ("prior_role_epa", "block_epa"), ("prior_role_success", "block_success")):
        cumulative = blocks.groupby("role", sort=False)[source].cumsum()
        blocks[value] = cumulative - blocks[source]
    blocks["role_epa_prior"] = np.where(
        blocks.prior_role_opportunities.gt(0),
        blocks.prior_role_epa / blocks.prior_role_opportunities,
        0.0,
    )
    blocks["role_success_prior"] = np.where(
        blocks.prior_role_opportunities.gt(0),
        blocks.prior_role_success / blocks.prior_role_opportunities,
        0.5,
    )
    frame = frame.merge(
        blocks[["role", "season", "week", "role_epa_prior", "role_success_prior"]],
        on=["role", "season", "week"],
        how="left",
        validate="many_to_one",
    )

    player_key = ["player_id", "role"]
    grouped = frame.groupby(player_key, sort=False)
    frame["prior_opportunities"] = grouped.opportunities.cumsum() - frame.opportunities
    frame["prior_epa_sum"] = grouped.epa_sum.cumsum() - frame.epa_sum
    frame["prior_success_sum"] = grouped.success_sum.cumsum() - frame.success_sum
    frame["shrinkage_opportunities"] = frame.role.map(strength).fillna(75.0).astype(float)

    denom_before = frame.prior_opportunities + frame.shrinkage_opportunities
    frame["player_value_before"] = (
        frame.prior_epa_sum + frame.shrinkage_opportunities * frame.role_epa_prior
    ) / denom_before
    frame["player_success_before"] = (
        frame.prior_success_sum + frame.shrinkage_opportunities * frame.role_success_prior
    ) / denom_before
    frame["player_confidence_before"] = np.where(
        denom_before.gt(0), frame.prior_opportunities / denom_before, 0.0
    )

    after_opportunities = frame.prior_opportunities + frame.opportunities
    denom_after = after_opportunities + frame.shrinkage_opportunities
    frame["player_value_after"] = (
        frame.prior_epa_sum + frame.epa_sum + frame.shrinkage_opportunities * frame.role_epa_prior
    ) / denom_after
    frame["player_success_after"] = (
        frame.prior_success_sum + frame.success_sum + frame.shrinkage_opportunities * frame.role_success_prior
    ) / denom_after
    frame["player_confidence_after"] = after_opportunities / denom_after
    frame["player_uncertainty_after"] = 1.0 - frame.player_confidence_after
    frame["rookie_or_no_history"] = frame.prior_opportunities.eq(0)
    return frame


def build_team_pregame_state(player_state: pd.DataFrame) -> pd.DataFrame:
    """Lag completed-game player value/usage into the team's next same-season game."""
    if player_state.empty:
        return pd.DataFrame()
    frame = player_state.copy()
    totals = frame.groupby(["game_id", "season", "week", "team", "role"])["opportunities"].transform("sum")
    frame["usage_share"] = np.where(totals.gt(0), frame.opportunities / totals, 0.0)
    frame["weighted_value"] = frame.usage_share * frame.player_value_after
    frame["weighted_success"] = frame.usage_share * frame.player_success_after
    frame["weighted_uncertainty"] = frame.usage_share * frame.player_uncertainty_after
    frame["share_sq"] = frame.usage_share**2

    post = (
        frame.groupby(["game_id", "season", "week", "team", "role"], as_index=False)
        .agg(
            postgame_player_value=("weighted_value", "sum"),
            postgame_player_success=("weighted_success", "sum"),
            postgame_lineup_uncertainty=("weighted_uncertainty", "sum"),
            postgame_role_concentration=("share_sq", "sum"),
            postgame_known_players=("player_id", "nunique"),
        )
        .sort_values(["team", "role", "season", "week", "game_id"])
    )
    group = post.groupby(["team", "role", "season"], sort=False)
    lag_map = {
        "postgame_player_value": "pregame_player_value",
        "postgame_player_success": "pregame_player_success",
        "postgame_lineup_uncertainty": "pregame_lineup_uncertainty",
        "postgame_role_concentration": "pregame_role_concentration",
        "postgame_known_players": "pregame_known_players",
    }
    for source, target in lag_map.items():
        post[target] = group[source].shift(1)
    post["state_missing"] = post.pregame_player_value.isna()
    return post[[
        "game_id",
        "season",
        "week",
        "team",
        "role",
        "pregame_player_value",
        "pregame_player_success",
        "pregame_lineup_uncertainty",
        "pregame_role_concentration",
        "pregame_known_players",
        "state_missing",
    ]].reset_index(drop=True)


def build_game_player_features(
    schedules: pd.DataFrame,
    team_pregame_state: pd.DataFrame,
    *,
    roles: Iterable[str] = ("target", "rush"),
) -> pd.DataFrame:
    """Create compact matchup features; v0.9A defaults to non-QB skill roles.

    QB state remains a separate v0.8 ablation, so target/rush is the default here. This
    makes incremental player-value testing interpretable rather than silently double
    counting the existing QB feature family.
    """
    needed = {"game_id", "home_team", "away_team", "season", "week"}
    missing = needed - set(schedules.columns)
    if missing:
        raise ValueError(f"Schedules missing player-state merge keys: {sorted(missing)}")
    games = schedules.copy()
    games["home_team"] = games.home_team.map(normalize_team_code)
    games["away_team"] = games.away_team.map(normalize_team_code)
    state = team_pregame_state.copy()
    state["team"] = state.team.map(normalize_team_code)
    role_list = [role for role in roles if role in ROLE_ORDER]

    metrics = [
        "pregame_player_value",
        "pregame_player_success",
        "pregame_lineup_uncertainty",
        "pregame_role_concentration",
        "pregame_known_players",
        "state_missing",
    ]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        for role in role_list:
            piece = state[state.role.eq(role)][["game_id", "team", *metrics]].copy()
            rename = {metric: f"{side}_{role}_{metric}" for metric in metrics}
            piece = piece.rename(columns={"team": team_col, **rename})
            games = games.merge(piece, on=["game_id", team_col], how="left", validate="one_to_one")

    for role in role_list:
        for metric in (
            "pregame_player_value",
            "pregame_player_success",
            "pregame_lineup_uncertainty",
            "pregame_role_concentration",
        ):
            home = f"home_{role}_{metric}"
            away = f"away_{role}_{metric}"
            games[f"v09a_diff_{role}_{metric}"] = pd.to_numeric(games[home], errors="coerce") - pd.to_numeric(games[away], errors="coerce")
        home_missing = games[f"home_{role}_state_missing"].fillna(True).astype(bool)
        away_missing = games[f"away_{role}_state_missing"].fillna(True).astype(bool)
        games[f"v09a_{role}_state_missing_count"] = home_missing.astype(int) + away_missing.astype(int)
    return games


def v09a_feature_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(column for column in frame.columns if column.startswith("v09a_"))


def audit_player_data(
    pbp: pd.DataFrame,
    *,
    snap_counts: pd.DataFrame | None = None,
    depth_charts: pd.DataFrame | None = None,
    ngs_passing: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Explicit identity/coverage audit. Unknown sources are reported, never invented."""
    work = _base_play_frame(pbp)
    role_defs = {
        "qb": ("passer_player_id", _number(work, "pass_attempt").eq(1) | _number(work, "sack").eq(1)),
        "target": ("receiver_player_id", _valid_id(_text(work, "receiver_player_id"))),
        "rush": ("rusher_player_id", _number(work, "rush_attempt").eq(1)),
    }
    coverage: dict[str, Any] = {}
    for role, (column, opportunity) in role_defs.items():
        ids = _text(work, column)
        denominator = int(opportunity.sum())
        known = int((opportunity & _valid_id(ids)).sum())
        coverage[role] = {
            "opportunities": denominator,
            "stable_id_rows": known,
            "missing_id_rows": denominator - known,
            "missing_id_rate": (denominator - known) / denominator if denominator else None,
        }

    roles = build_player_game_roles(work)
    names = []
    for role, id_col, name_col in (
        ("qb", "passer_player_id", "passer_player_name"),
        ("target", "receiver_player_id", "receiver_player_name"),
        ("rush", "rusher_player_id", "rusher_player_name"),
    ):
        ids = _text(work, id_col)
        mask = _valid_id(ids)
        sample = pd.DataFrame({
            "player_id": ids.loc[mask].astype(str),
            "name": _normalized_name(_text(work, name_col).loc[mask]),
            "role": role,
        })
        names.append(sample)
    name_map = pd.concat(names, ignore_index=True) if names else pd.DataFrame()
    conflicts = 0
    if not name_map.empty:
        variants = name_map[name_map.name.ne("")].groupby("player_id").name.nunique()
        conflicts = int(variants.gt(1).sum())

    transitions = 0
    transition_players = 0
    rookies = 0
    if not roles.empty:
        season_teams = roles.groupby(["season", "player_id"]).team.nunique()
        transitions = int((season_teams - 1).clip(lower=0).sum())
        transition_players = int(season_teams.gt(1).sum())
        first_season = roles.groupby("player_id").season.min()
        rookies = int(len(first_season))

    qb = roles[roles.role.eq("qb")].copy() if not roles.empty else pd.DataFrame()
    relief_games = 0
    starter_ambiguous_games = 0
    if not qb.empty:
        meaningful = qb[qb.opportunities.ge(5)]
        passers = meaningful.groupby("game_id").player_id.nunique()
        relief_games = int(passers.gt(1).sum())
        starter_ambiguous_games = relief_games

    game_plays = work.groupby("game_id").size()
    partial_candidates = int(game_plays.lt(80).sum())
    raw_codes = set(_text(work, "posteam").str.upper().dropna())
    legacy = sorted(code for code in raw_codes if code in LEGACY_FRANCHISE_CODES)
    jac_rows = int(_text(work, "posteam").str.upper().eq("JAC").sum())

    return {
        "status": "healthy",
        "rows": int(len(work)),
        "seasons": sorted(int(x) for x in work.season.dropna().unique()),
        "maximum_pbp_season": int(work.season.max()) if len(work) else None,
        "stable_id_coverage": coverage,
        "player_id_name_conflicts": conflicts,
        "fail_closed_identity_policy": True,
        "jax_jac_rows_normalized": jac_rows,
        "legacy_franchise_codes_observed": legacy,
        "midseason_team_transition_events": transitions,
        "players_with_multi_team_season": transition_players,
        "players_first_observed_in_dataset": rookies,
        "backup_qb_relief_or_multi_passer_games": relief_games,
        "starter_ambiguity_games_from_pbp": starter_ambiguous_games,
        "low_play_count_partial_game_candidates": partial_candidates,
        "snap_counts": {"status": "available" if snap_counts is not None and not snap_counts.empty else "missing", "rows": int(len(snap_counts)) if snap_counts is not None else 0},
        "depth_charts": {"status": "available" if depth_charts is not None and not depth_charts.empty else "missing", "rows": int(len(depth_charts)) if depth_charts is not None else 0},
        "ngs_passing": {"status": "available" if ngs_passing is not None and not ngs_passing.empty else "missing", "rows": int(len(ngs_passing)) if ngs_passing is not None else 0},
        "injury_uncertainty": "not_reconstructable_from_core_pbp; prohibited until timestamped historical source is validated",
        "position_change_audit": "requires stable-ID historical depth-chart/roster coverage; unknown when source is missing",
        "participation_data_coverage": "snap-count source audited separately; PBP opportunity is not treated as snap participation",
    }


def build_player_state(
    pbp: pd.DataFrame,
    *,
    snap_counts: pd.DataFrame | None = None,
    depth_charts: pd.DataFrame | None = None,
    ngs_passing: pd.DataFrame | None = None,
    shrinkage: dict[str, float] | None = None,
) -> PlayerStateBuild:
    game_roles = build_player_game_roles(pbp)
    state = add_chronological_player_values(game_roles, shrinkage=shrinkage)
    team_state = build_team_pregame_state(state)
    audit = audit_player_data(
        pbp,
        snap_counts=snap_counts,
        depth_charts=depth_charts,
        ngs_passing=ngs_passing,
    )
    audit["player_game_role_rows"] = int(len(game_roles))
    audit["team_pregame_state_rows"] = int(len(team_state))
    audit["pregame_state_missing_rate"] = float(team_state.state_missing.mean()) if len(team_state) else None
    audit["shrinkage_opportunities"] = {key: float(value) for key, value in {**ROLE_SHRINKAGE, **(shrinkage or {})}.items()}
    return PlayerStateBuild(game_roles, state, team_state, audit)

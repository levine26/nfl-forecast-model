from __future__ import annotations

"""Canonical simulation handoff for LevLine Props opportunity distributions."""

from typing import Any, Mapping

import pandas as pd

from nfl_forecast.props_opportunity import ForecastContext, OpportunityProjection, _allocation_channel
from nfl_forecast.props_opportunity_adapter import (
    build_opportunity_projection_from_canonical_state,
    current_players_from_canonical_state,
    prepare_player_history_for_opportunity,
)

CARRY_POSITIONS = frozenset({"QB", "RB", "FB", "WR"})
RECEIVING_POSITIONS = frozenset({"RB", "FB", "WR", "TE"})


def normalize_player_opportunity_history(
    player_history: pd.DataFrame,
    team_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Normalize rushing aliases without double-counting QB scrambles.

    Non-QB rush_attempts or legacy carries may be copied directly to
    designed_carries. QB generic rush counts are unsafe because nflverse
    rushing attempts include scrambles, which the hierarchy separately samples
    from the dropback branch. QB rows therefore require player-level
    qb_scrambles or unambiguous team-game scramble counts.
    """
    out = player_history.copy()
    if "designed_carries" in out.columns:
        out["designed_carries"] = pd.to_numeric(out["designed_carries"], errors="coerce")
        out["designed_carry_source"] = "explicit_designed_carries"
        return out

    alias = "rush_attempts" if "rush_attempts" in out.columns else (
        "carries" if "carries" in out.columns else None
    )
    if alias is None:
        return out
    if "position" not in out.columns:
        raise ValueError("Rushing alias normalization requires player position")

    raw = pd.to_numeric(out[alias], errors="coerce")
    out["designed_carries"] = raw
    out["designed_carry_source"] = f"{alias}:non_qb_direct"
    qb_mask = out["position"].astype(str).str.upper().eq("QB") & raw.notna()
    if not qb_mask.any():
        return out

    scrambles = pd.Series(0.0, index=out.index, dtype=float)
    if "qb_scrambles" in out.columns:
        player_scrambles = pd.to_numeric(out["qb_scrambles"], errors="coerce")
        if player_scrambles.loc[qb_mask].isna().any():
            raise ValueError("QB rows require complete player-level qb_scrambles when supplied")
        scrambles.loc[qb_mask] = player_scrambles.loc[qb_mask]
        source = f"{alias}_minus_player_qb_scrambles"
    else:
        if not {"game_id", "team"}.issubset(out.columns):
            raise ValueError("QB generic rush counts require game_id/team plus scramble evidence")
        required_team = {"game_id", "team", "qb_scrambles"}
        if team_history is None or not required_team.issubset(team_history.columns):
            if raw.loc[qb_mask].fillna(0.0).gt(0).any():
                raise ValueError(
                    "QB rush_attempts/carries require qb_scrambles so designed carries "
                    "can be separated from scramble opportunities"
                )
            source = f"{alias}:qb_zero"
        else:
            exposure = team_history[["game_id", "team", "qb_scrambles"]].copy()
            if exposure.duplicated(["game_id", "team"]).any():
                raise ValueError("team_history has duplicate game_id/team scramble exposure")
            exposure["qb_scrambles"] = pd.to_numeric(exposure["qb_scrambles"], errors="coerce")
            key_to_scramble = {
                (str(row.game_id), str(row.team)): row.qb_scrambles
                for row in exposure.itertuples(index=False)
            }
            qb_counts = (
                out.loc[qb_mask]
                .assign(
                    _game=out.loc[qb_mask, "game_id"].astype(str),
                    _team=out.loc[qb_mask, "team"].astype(str),
                )
                .groupby(["_game", "_team"])
                .size()
            )
            for idx in out.index[qb_mask]:
                key = (str(out.at[idx, "game_id"]), str(out.at[idx, "team"]))
                scramble = key_to_scramble.get(key)
                if scramble is None or pd.isna(scramble):
                    if float(raw.at[idx] or 0.0) > 0:
                        raise ValueError(f"Missing team qb_scrambles for QB history row {key}")
                    continue
                if int(qb_counts.get(key, 0)) != 1 and float(scramble) > 0:
                    raise ValueError(
                        f"Multiple QB history rows make team scramble allocation ambiguous for {key}"
                    )
                scrambles.at[idx] = float(scramble)
            source = f"{alias}_minus_team_qb_scrambles"

    designed = raw.loc[qb_mask] - scrambles.loc[qb_mask]
    if designed.lt(-1e-9).any():
        raise ValueError("QB scrambles cannot exceed QB generic rush attempts")
    out.loc[qb_mask, "designed_carries"] = designed.clip(lower=0.0)
    out.loc[qb_mask, "designed_carry_source"] = source
    return out

def _optional_allocation(
    player_history: pd.DataFrame,
    current_players: pd.DataFrame,
    *,
    history_column: str,
    label: str,
    positions: frozenset[str],
    multiplier_column: str,
    half_life_games: float,
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, float]]:
    if history_column not in player_history.columns:
        return None, {
            "status": "unavailable",
            "reason": f"{history_column} not supplied",
        }, {}
    values = pd.to_numeric(player_history[history_column], errors="coerce")
    if (values.dropna() < 0).any():
        raise ValueError(f"{history_column} must be non-negative")
    if values.fillna(0.0).sum() <= 0:
        return None, {
            "status": "unavailable",
            "reason": f"{history_column} has no positive historical evidence",
        }, {}

    eligible = current_players[current_players["position"].isin(positions)].copy().reset_index(drop=True)
    if eligible.empty:
        return None, {"status": "unavailable", "reason": "no eligible current players"}, {}
    dist, redistribution, _, evidence = _allocation_channel(
        player_history,
        eligible,
        history_column=history_column,
        label=label,
        multiplier_column=multiplier_column,
        half_life_games=half_life_games,
    )
    evidence_map = {
        str(pid): float(value)
        for pid, value in zip(eligible["player_id"].astype(str), evidence)
    }
    return dist, redistribution, evidence_map


def attach_scoring_opportunity_allocations(
    projection: OpportunityProjection,
    player_history: pd.DataFrame,
    current_players: pd.DataFrame,
    *,
    half_life_games: float = 8.0,
) -> OpportunityProjection:
    """Attach scoring-area opportunity-share distributions when evidence exists."""
    specifications = (
        (
            "red_zone_carries",
            "red_zone_carry_share",
            CARRY_POSITIONS,
            "carry_role_multiplier",
        ),
        (
            "goal_line_carries",
            "goal_line_carry_share",
            CARRY_POSITIONS,
            "carry_role_multiplier",
        ),
        (
            "red_zone_targets",
            "red_zone_target_share",
            RECEIVING_POSITIONS,
            "target_role_multiplier",
        ),
        (
            "end_zone_targets",
            "end_zone_target_share",
            RECEIVING_POSITIONS,
            "target_role_multiplier",
        ),
        (
            "first_read_targets",
            "first_read_target_share",
            RECEIVING_POSITIONS,
            "target_role_multiplier",
        ),
    )

    audit: dict[str, Any] = {}
    player_map = {str(row["player_id"]): row for row in projection.players}
    for history_column, label, positions, multiplier in specifications:
        dist, redistribution, evidence = _optional_allocation(
            player_history,
            current_players,
            history_column=history_column,
            label=label,
            positions=positions,
            multiplier_column=multiplier,
            half_life_games=half_life_games,
        )
        projection.redistribution[label] = redistribution
        if dist is None:
            audit[label] = {"status": "unavailable", **redistribution}
            continue
        projection.hierarchy[label] = dist
        audit[label] = {
            "status": "available",
            "history_column": history_column,
            "concentration_total": float(dist["concentration_total"]),
        }
        for player_id, mean in dist["mean_share"].items():
            row = player_map.get(str(player_id))
            if row is None:
                continue
            row[f"{label}_mean"] = float(mean)
            row[f"{label}_variance"] = float(dist["variance"][player_id])
            row[f"{label}_history_effective_opportunities"] = float(evidence.get(player_id, 0.0))
    projection.audit["scoring_opportunity_channels"] = audit
    return projection


def build_simulation_ready_opportunity_projection(
    team_history: pd.DataFrame,
    player_history: pd.DataFrame,
    player_state: pd.DataFrame,
    context: ForecastContext,
    *,
    availability_priors: Mapping[str, Any] | None = None,
    route_prior_means: Mapping[str, float] | None = None,
    primary_qb_player_id: str | None = None,
    primary_qb_provenance: str | None = None,
    role_adjustments: Mapping[str, Mapping[str, float]] | None = None,
    role_adjustments_provenance: str | None = None,
    half_life_games: float = 8.0,
) -> OpportunityProjection:
    """Preferred one-call interface for the simulation lane."""
    normalized_history = normalize_player_opportunity_history(
        player_history,
        team_history=team_history,
    )
    normalized_team_history = team_history.copy()
    if "dropbacks" in normalized_team_history.columns:
        normalized_team_history["dropbacks"] = pd.to_numeric(
            normalized_team_history["dropbacks"], errors="coerce"
        ).astype(float)

    projection = build_opportunity_projection_from_canonical_state(
        normalized_team_history,
        normalized_history,
        player_state,
        context,
        availability_priors=availability_priors,
        route_prior_means=route_prior_means,
        primary_qb_player_id=primary_qb_player_id,
        primary_qb_provenance=primary_qb_provenance,
        role_adjustments=role_adjustments,
        role_adjustments_provenance=role_adjustments_provenance,
        half_life_games=half_life_games,
    )

    projection.audit["designed_carry_normalization"] = {
        str(key): int(value)
        for key, value in normalized_history["designed_carry_source"]
        .value_counts(dropna=False)
        .to_dict()
        .items()
    }

    # Reuse the same canonical transforms to attach scoring-area shares. This duplicates
    # no model logic; it only exposes the model-ready rows required by allocation helpers.
    current_players = current_players_from_canonical_state(
        player_state,
        game_id=context.game_id,
        team=context.team,
        availability_priors=availability_priors,
        primary_qb_player_id=primary_qb_player_id,
        primary_qb_provenance=primary_qb_provenance,
        role_adjustments=role_adjustments,
        role_adjustments_provenance=role_adjustments_provenance,
    )
    prepared_history, _ = prepare_player_history_for_opportunity(
        normalized_history,
        normalized_team_history,
        route_prior_means=route_prior_means,
    )
    return attach_scoring_opportunity_allocations(
        projection,
        prepared_history,
        current_players,
        half_life_games=half_life_games,
    )

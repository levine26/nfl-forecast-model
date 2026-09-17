from __future__ import annotations

"""Adapters from the canonical Props player-state contract to opportunity-model inputs."""

import math
from typing import Any, Mapping

import pandas as pd

from nfl_forecast.props_opportunity import (
    ForecastContext,
    OpportunityProjection,
    build_opportunity_projection,
)

CANONICAL_SCHEMA = "levline_props_player_state.v1"
REQUIRED_COLUMNS = {
    "game_id",
    "player_id",
    "player_name",
    "position",
    "team",
    "expected_active_state",
    "availability_source_status",
    "expected_role",
}
UNCERTAIN_STATES = frozenset({"QUESTIONABLE", "DOUBTFUL", "UNKNOWN"})
ROUTE_ELIGIBLE_POSITIONS = frozenset({"RB", "FB", "WR", "TE"})
ROLE_MULTIPLIER_FIELDS = (
    "role_multiplier",
    "carry_role_multiplier",
    "target_role_multiplier",
    "route_role_multiplier",
)


def _beta_prior(value: Any, *, state: str) -> tuple[float, float]:
    if isinstance(value, Mapping):
        alpha = value.get("alpha")
        beta = value.get("beta")
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        alpha, beta = value
    else:
        raise ValueError(
            f"Availability prior for {state} must supply explicit beta (alpha, beta) parameters"
        )
    try:
        alpha = float(alpha)
        beta = float(beta)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid beta prior for availability state {state}") from exc
    if not math.isfinite(alpha) or not math.isfinite(beta) or alpha <= 0 or beta <= 0:
        raise ValueError(f"Availability beta prior for {state} must be finite and positive")
    return alpha, beta


def _provenance(value: str | None, *, label: str) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "unknown"}:
        raise ValueError(f"{label} requires explicit point-in-time provenance")
    return text


def current_players_from_canonical_state(
    player_state: pd.DataFrame,
    *,
    game_id: str,
    team: str,
    availability_priors: Mapping[str, Any] | None = None,
    primary_qb_player_id: str | None = None,
    primary_qb_provenance: str | None = None,
    role_adjustments: Mapping[str, Mapping[str, float]] | None = None,
    role_adjustments_provenance: str | None = None,
) -> pd.DataFrame:
    """Translate canonical point-in-time player state to model-ready current players.

    OUT and AVAILABLE are treated as deterministic only because those are explicit
    canonical states. QUESTIONABLE, DOUBTFUL and UNKNOWN require caller-supplied,
    preregistered Beta priors. Optional QB/role overrides require explicit provenance;
    they exist for genuine point-in-time starter, promotion, demotion and limitation
    evidence and never infer current-game role from actual participation.
    """
    missing = REQUIRED_COLUMNS - set(player_state.columns)
    if missing:
        raise ValueError(f"Canonical player_state missing fields: {sorted(missing)}")
    if "schema_version" in player_state.columns:
        schemas = set(player_state["schema_version"].dropna().astype(str))
        if schemas and schemas != {CANONICAL_SCHEMA}:
            raise ValueError(f"Unsupported canonical player-state schema(s): {sorted(schemas)}")

    team_norm = "JAX" if str(team).upper() == "JAC" else str(team).upper()
    work = player_state[
        player_state["game_id"].astype(str).eq(str(game_id))
        & player_state["team"].astype(str).str.upper().replace({"JAC": "JAX"}).eq(team_norm)
    ].copy()
    if work.empty:
        raise ValueError(f"No canonical player-state rows for game={game_id}, team={team_norm}")

    ids = work["player_id"].astype("string").fillna("").str.strip()
    if ids.eq("").any() or ids.str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Canonical player_state contains ambiguous player identity")
    if ids.duplicated().any():
        raise ValueError("Canonical player_state contains duplicate player_id")

    priors = {str(k).upper(): v for k, v in (availability_priors or {}).items()}
    probabilities: list[float] = []
    uncertainties: list[float] = []
    prior_sources: list[str] = []
    for _, row in work.iterrows():
        state = str(row["expected_active_state"]).upper().strip()
        source_status = str(row["availability_source_status"]).upper().strip()
        if state == "OUT":
            probabilities.append(0.0)
            uncertainties.append(0.0)
            prior_sources.append("canonical_explicit_out")
            continue
        if state == "AVAILABLE":
            probabilities.append(1.0)
            uncertainties.append(0.0)
            prior_sources.append("canonical_explicit_available")
            continue
        if state not in UNCERTAIN_STATES:
            raise ValueError(f"Unsupported expected_active_state: {state}")
        if state not in priors:
            raise ValueError(
                f"Availability state {state} ({source_status}) requires an explicit "
                "preregistered Beta prior; none was supplied"
            )
        alpha, beta = _beta_prior(priors[state], state=state)
        total = alpha + beta
        mean = alpha / total
        variance = alpha * beta / (total * total * (total + 1.0))
        probabilities.append(mean)
        uncertainties.append(math.sqrt(variance))
        prior_sources.append(f"explicit_beta_prior:{state}:alpha={alpha:g}:beta={beta:g}")

    inferred_primary = work["expected_role"].astype(str).eq("QB_PRIMARY")
    qb_override_source = "canonical_expected_role"
    if primary_qb_player_id is not None:
        qb_override_source = _provenance(primary_qb_provenance, label="primary QB override")
        primary_id = str(primary_qb_player_id)
        matched = work[ids.astype(str).eq(primary_id)]
        if len(matched) != 1 or str(matched.iloc[0]["position"]).upper() != "QB":
            raise ValueError("primary_qb_player_id must identify exactly one canonical QB row")
        inferred_primary = ids.astype(str).eq(primary_id)

    adjustments = {str(k): v for k, v in (role_adjustments or {}).items()}
    role_source = "none"
    if adjustments:
        role_source = _provenance(role_adjustments_provenance, label="role adjustments")
        unknown_ids = sorted(set(adjustments) - set(ids.astype(str)))
        if unknown_ids:
            raise ValueError(f"Role adjustments reference unknown player_id(s): {unknown_ids}")

    out = pd.DataFrame(
        {
            "player_id": ids.astype(str),
            "player_name": work["player_name"].astype(str),
            "position": work["position"].astype(str).str.upper(),
            "availability_probability": probabilities,
            "availability_uncertainty": uncertainties,
            "is_primary_qb": inferred_primary.to_numpy(dtype=bool),
            "role_multiplier": 1.0,
            "carry_role_multiplier": 1.0,
            "target_role_multiplier": 1.0,
            "route_role_multiplier": 1.0,
            "availability_prior_source": prior_sources,
            "primary_qb_source": qb_override_source,
            "role_adjustment_source": role_source,
        }
    )

    for player_id, values in adjustments.items():
        if not isinstance(values, Mapping):
            raise ValueError(f"Role adjustment for {player_id} must be a mapping")
        invalid = set(values) - set(ROLE_MULTIPLIER_FIELDS)
        if invalid:
            raise ValueError(f"Unsupported role adjustment fields for {player_id}: {sorted(invalid)}")
        mask = out["player_id"].eq(player_id)
        for field, raw in values.items():
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid {field} for {player_id}") from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field} for {player_id} must be finite and non-negative")
            out.loc[mask, field] = value
    return out.reset_index(drop=True)


def prepare_player_history_for_opportunity(
    player_history: pd.DataFrame,
    team_history: pd.DataFrame,
    *,
    route_prior_means: Mapping[str, float] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Represent missing route observations as explicit prior-only zero-exposure rows.

    The core engine requires a numeric ``routes`` column. The props-data lane correctly
    permits route history to be missing, so this adapter distinguishes missing evidence
    from an observed zero. Missing receiver routes carry an explicit per-player prior mean
    and zero historical route exposure; no observed route count is fabricated.
    """
    required = {"game_id", "team", "player_id", "position"}
    missing = required - set(player_history.columns)
    if missing:
        raise ValueError(f"player_history missing route-adapter fields: {sorted(missing)}")
    if "dropbacks" not in team_history.columns:
        raise ValueError("team_history requires dropbacks for route participation exposure")

    out = player_history.copy()
    if "routes" not in out.columns:
        out["routes"] = pd.NA
    out["position"] = out["position"].astype(str).str.upper()
    observed_routes = pd.to_numeric(out["routes"], errors="coerce")
    out["route_history_observed"] = observed_routes.notna()
    out["route_prior_mean"] = math.nan

    exposure = team_history[["game_id", "team", "dropbacks"]].copy()
    exposure["dropbacks"] = pd.to_numeric(exposure["dropbacks"], errors="coerce")
    if exposure.duplicated(["game_id", "team"]).any():
        raise ValueError("team_history has duplicate game_id/team route exposure")
    out = out.drop(columns=["dropbacks"], errors="ignore").merge(
        exposure,
        on=["game_id", "team"],
        how="left",
        validate="many_to_one",
    )

    receiver_missing = out["position"].isin(ROUTE_ELIGIBLE_POSITIONS) & ~out["route_history_observed"]
    observed_receiver = out["position"].isin(ROUTE_ELIGIBLE_POSITIONS) & out["route_history_observed"]
    if out.loc[observed_receiver, "dropbacks"].isna().any():
        raise ValueError("Observed routes are missing matching team dropback exposure")

    priors = {str(k).upper(): float(v) for k, v in (route_prior_means or {}).items()}
    missing_positions = sorted(set(out.loc[receiver_missing, "position"]) - set(priors))
    if missing_positions:
        raise ValueError(
            "Missing route history requires explicit preregistered position prior means for: "
            f"{missing_positions}"
        )
    for position, mean in priors.items():
        if not math.isfinite(mean) or mean <= 0 or mean >= 1:
            raise ValueError(f"Route prior mean for {position} must be strictly within (0, 1)")

    # Missing route rows carry zero exposure and an explicit per-player prior mean.
    # This prevents observed same-position teammates from silently replacing the
    # preregistered missing-route prior inside the core hierarchical model.
    for position in ROUTE_ELIGIBLE_POSITIONS:
        mask = receiver_missing & out["position"].eq(position)
        if mask.any():
            out.loc[mask, "routes"] = 0.0
            out.loc[mask, "dropbacks"] = 0.0
            out.loc[mask, "route_prior_mean"] = priors[position]
    non_receiver_missing = (
        ~out["position"].isin(ROUTE_ELIGIBLE_POSITIONS)
        & ~out["route_history_observed"]
    )
    out.loc[non_receiver_missing, "routes"] = 0.0
    out.loc[non_receiver_missing, "dropbacks"] = 0.0

    prior_only_ids: list[str] = []
    for player_id, group in out[out["position"].isin(ROUTE_ELIGIBLE_POSITIONS)].groupby(
        "player_id", sort=False
    ):
        if not bool(group["route_history_observed"].any()):
            prior_only_ids.append(str(player_id))

    audit = {
        "policy": "observed_routes_or_explicit_position_prior",
        "observed_route_rows": int(out["route_history_observed"].sum()),
        "missing_route_rows_prior_encoded": int(receiver_missing.sum()),
        "route_prior_only_player_ids": sorted(prior_only_ids),
        "route_prior_means": priors,
        "prior_only_dropbacks_per_missing_row": 0.0,
        "fabricated_observed_routes": 0,
    }
    return out, audit


def build_opportunity_projection_from_canonical_state(
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
    """End-to-end handoff from canonical current state to opportunity projection."""
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
    prepared_history, route_audit = prepare_player_history_for_opportunity(
        player_history,
        team_history,
        route_prior_means=route_prior_means,
    )
    projection = build_opportunity_projection(
        team_history,
        prepared_history,
        current_players,
        context,
        half_life_games=half_life_games,
    )

    prior_only = set(route_audit["route_prior_only_player_ids"])
    availability_source = dict(
        zip(current_players["player_id"], current_players["availability_prior_source"])
    )
    qb_source = dict(zip(current_players["player_id"], current_players["primary_qb_source"]))
    role_source = dict(zip(current_players["player_id"], current_players["role_adjustment_source"]))
    beta_prior_audit: dict[str, dict[str, float]] = {}
    for state, value in (availability_priors or {}).items():
        normalized = str(state).upper()
        if normalized in UNCERTAIN_STATES:
            alpha, beta = _beta_prior(value, state=normalized)
            beta_prior_audit[normalized] = {"alpha": alpha, "beta": beta}

    projection.audit["canonical_player_state_adapter"] = {
        "schema": CANONICAL_SCHEMA,
        "availability_beta_priors": beta_prior_audit,
        "primary_qb_override_used": primary_qb_player_id is not None,
        "primary_qb_provenance": primary_qb_provenance if primary_qb_player_id else None,
        "role_adjustments_used": bool(role_adjustments),
        "role_adjustments_provenance": role_adjustments_provenance if role_adjustments else None,
        "route_history": route_audit,
    }
    for row in projection.players:
        pid = row["player_id"]
        row["availability_prior_source"] = availability_source.get(pid)
        row["primary_qb_source"] = qb_source.get(pid)
        row["role_adjustment_source"] = role_source.get(pid)
        row["route_history_prior_only"] = pid in prior_only
        if pid in prior_only and "route_history_effective_dropbacks" in row:
            row["route_history_effective_dropbacks"] = 0.0
    return projection
